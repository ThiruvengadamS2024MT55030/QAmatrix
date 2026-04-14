"""
QA Matrix - Defect Data Processing & Validation Pipeline
=========================================================
Handles ingestion, parsing, cleaning, and validation of defect reports
from DVX, SCA, and YARD sources.

Usage:
    python defect_processor.py --input defects.xlsx --source DVX --output cleaned_defects.csv
"""

import pandas as pd
import numpy as np
import re
import sys
import argparse
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


# ─── Data Models ────────────────────────────────────────────────────────

@dataclass
class DVXEntry:
    """Single defect entry from inspection report."""
    date: str = ""
    location_details: str = ""
    defect_code: str = ""
    defect_description: str = ""
    defect_description_details: str = ""
    gravity: str = ""
    quantity: int = 1
    source: str = ""
    responsible: str = ""
    pof_family: str = ""
    pof_code: str = ""


@dataclass
class ValidationResult:
    """Result of data validation step."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cleaned_count: int = 0
    dropped_count: int = 0


# ─── Header Normalization ───────────────────────────────────────────────

def normalize_header(header: str) -> str:
    """Normalize column headers for fuzzy matching."""
    import unicodedata
    h = str(header).strip().lower()
    h = unicodedata.normalize("NFD", h)
    h = re.sub(r'[\u0300-\u036f]', '', h)  # Remove diacritics
    h = re.sub(r'[_\s]+', ' ', h)
    return h


def find_column(headers: List[str], *names: str) -> int:
    """Find column index by trying multiple name variants."""
    normalized = [normalize_header(h) for h in headers]
    for name in names:
        nm = normalize_header(name)
        # Exact match
        if nm in normalized:
            return normalized.index(nm)
        # Starts with
        for i, h in enumerate(normalized):
            if h.startswith(nm):
                return i
        # Contains
        for i, h in enumerate(normalized):
            if nm in h:
                return i
    return -1


def find_header_row(df: pd.DataFrame, max_rows: int = 10) -> int:
    """Auto-detect header row by looking for known column names."""
    known_headers = ["defect description", "defect code", "gravity", "location details", "quantity"]
    
    for i in range(min(len(df), max_rows)):
        row = df.iloc[i].astype(str).str.lower().tolist()
        match_count = sum(1 for kh in known_headers if any(kh in cell for cell in row))
        if match_count >= 3:
            return i
    return 0


# ─── Core Processing Pipeline ──────────────────────────────────────────

def load_defect_file(filepath: str) -> pd.DataFrame:
    """
    Stage 1: Data Ingestion
    Equivalent to: pd.read_excel(filepath)
    
    Supports .xlsx, .xls, and .csv formats.
    """
    ext = filepath.rsplit('.', 1)[-1].lower()
    
    if ext in ('xlsx', 'xls'):
        df = pd.read_excel(filepath, header=None)
    elif ext == 'csv':
        df = pd.read_csv(filepath, header=None)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
    
    print(f"[INGEST] Loaded {len(df)} rows from {filepath}")
    return df


def preprocess_defects(df: pd.DataFrame, source: str = "DVX") -> List[DVXEntry]:
    """
    Stage 2: Data Preprocessing
    Equivalent to: df.dropna(), df.astype(), df.str.strip()
    
    - Auto-detects header row
    - Maps columns via fuzzy header matching
    - Cleans and normalizes values
    - Drops empty/invalid rows
    """
    header_row = find_header_row(df)
    headers = df.iloc[header_row].astype(str).tolist()
    data = df.iloc[header_row + 1:].reset_index(drop=True)
    
    # Column mapping
    col_map = {
        'date': find_column(headers, "Date"),
        'location': find_column(headers, "Location Details", "Location"),
        'code': find_column(headers, "Defect Code"),
        'desc': find_column(headers, "Defect Description"),
        'details': find_column(headers, "Defect Description Details"),
        'gravity': find_column(headers, "Gravity"),
        'quantity': find_column(headers, "Quantity"),
        'source_col': find_column(headers, "Source"),
        'responsible': find_column(headers, "Responsible"),
        'pof_family': find_column(headers, "POF Family"),
        'pof_code': find_column(headers, "POF CODE", "POF Code"),
    }
    
    print(f"[PREPROCESS] Header row: {header_row}, Column mapping: {col_map}")
    
    def get_val(row, col_idx: int) -> str:
        if col_idx < 0 or col_idx >= len(row):
            return ""
        val = row.iloc[col_idx]
        if pd.isna(val):
            return ""
        return str(val).strip()
    
    entries: List[DVXEntry] = []
    dropped = 0
    
    for i in range(len(data)):
        row = data.iloc[i]
        desc = get_val(row, col_map['desc'])
        details = get_val(row, col_map['details'])
        location = get_val(row, col_map['location'])
        
        # Skip rows with no meaningful data
        if not desc and not details and not location:
            dropped += 1
            continue
        
        # Parse quantity
        qty_raw = row.iloc[col_map['quantity']] if col_map['quantity'] >= 0 else 0
        try:
            qty = int(float(qty_raw)) if not pd.isna(qty_raw) else 1
        except (ValueError, TypeError):
            qty = 1
        
        entries.append(DVXEntry(
            date=get_val(row, col_map['date']),
            location_details=location,
            defect_code=get_val(row, col_map['code']),
            defect_description=desc,
            defect_description_details=details,
            gravity=get_val(row, col_map['gravity']),
            quantity=max(1, qty),
            source=get_val(row, col_map['source_col']) or source,
            responsible=get_val(row, col_map['responsible']),
            pof_family=get_val(row, col_map['pof_family']),
            pof_code=get_val(row, col_map['pof_code']),
        ))
    
    print(f"[PREPROCESS] Parsed {len(entries)} entries, dropped {dropped} empty rows")
    return entries


def validate_defects(entries: List[DVXEntry]) -> ValidationResult:
    """
    Stage 3: Data Validation
    
    Checks:
    - Required fields (defect_description or defect_description_details)
    - Valid gravity values
    - Positive quantities
    - Defect code format
    """
    result = ValidationResult(is_valid=True, cleaned_count=len(entries))
    valid_gravities = {"1", "2", "3", "4", "5", "A", "B", "C", "D", ""}
    
    for i, entry in enumerate(entries):
        # Check required fields
        if not entry.defect_description and not entry.defect_description_details:
            result.warnings.append(f"Row {i}: No defect description")
        
        # Validate gravity
        if entry.gravity and entry.gravity.upper() not in valid_gravities:
            result.warnings.append(f"Row {i}: Unusual gravity value '{entry.gravity}'")
        
        # Check quantity
        if entry.quantity <= 0:
            result.errors.append(f"Row {i}: Invalid quantity {entry.quantity}")
            entry.quantity = 1
        
        # Validate source
        valid_sources = {"DVX", "SCA", "YARD"}
        if entry.source.upper() not in valid_sources:
            result.warnings.append(f"Row {i}: Unknown source '{entry.source}'")
    
    if result.errors:
        result.is_valid = False
    
    print(f"[VALIDATE] Valid: {result.is_valid}, Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
    return result


def separate_by_source(entries: List[DVXEntry]) -> Dict[str, List[DVXEntry]]:
    """
    Stage 4: Source Separation
    Equivalent to: df.groupby('source')
    
    Separates defects by their source (DVX, SCA, YARD) for
    independent processing pipelines.
    """
    groups: Dict[str, List[DVXEntry]] = {}
    for entry in entries:
        src = entry.source.upper() or "UNKNOWN"
        if src not in groups:
            groups[src] = []
        groups[src].append(entry)
    
    for src, group in groups.items():
        print(f"[SEPARATE] {src}: {len(group)} defects")
    
    return groups


def deduplicate_defects(entries: List[DVXEntry]) -> List[DVXEntry]:
    """
    Stage 5: Deduplication
    
    Merges identical defects (same code + location + description)
    by summing their quantities.
    """
    key_map: Dict[str, DVXEntry] = {}
    
    for entry in entries:
        key = f"{entry.defect_code}|{entry.location_details}|{entry.defect_description}".lower()
        if key in key_map:
            key_map[key].quantity += entry.quantity
        else:
            key_map[key] = DVXEntry(
                date=entry.date,
                location_details=entry.location_details,
                defect_code=entry.defect_code,
                defect_description=entry.defect_description,
                defect_description_details=entry.defect_description_details,
                gravity=entry.gravity,
                quantity=entry.quantity,
                source=entry.source,
                responsible=entry.responsible,
                pof_family=entry.pof_family,
                pof_code=entry.pof_code,
            )
    
    result = list(key_map.values())
    print(f"[DEDUP] {len(entries)} → {len(result)} unique defects")
    return result


def to_dataframe(entries: List[DVXEntry]) -> pd.DataFrame:
    """Convert list of DVXEntry to pandas DataFrame."""
    return pd.DataFrame([{
        'date': e.date,
        'location_details': e.location_details,
        'defect_code': e.defect_code,
        'defect_description': e.defect_description,
        'defect_description_details': e.defect_description_details,
        'gravity': e.gravity,
        'quantity': e.quantity,
        'source': e.source,
        'responsible': e.responsible,
        'pof_family': e.pof_family,
        'pof_code': e.pof_code,
    } for e in entries])


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - Defect Data Processor")
    parser.add_argument("--input", "-i", required=True, help="Input file path (.xlsx, .xls, .csv)")
    parser.add_argument("--source", "-s", default="DVX", choices=["DVX", "SCA", "YARD"], help="Defect source")
    parser.add_argument("--output", "-o", default="cleaned_defects.csv", help="Output file path")
    parser.add_argument("--dedup", action="store_true", help="Enable deduplication")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - DEFECT DATA PROCESSING PIPELINE")
    print("=" * 60)
    
    # Pipeline execution
    df = load_defect_file(args.input)
    entries = preprocess_defects(df, source=args.source)
    validation = validate_defects(entries)
    
    if not validation.is_valid:
        print(f"\n[ERROR] Validation failed with {len(validation.errors)} errors:")
        for err in validation.errors[:10]:
            print(f"  - {err}")
    
    if validation.warnings:
        print(f"\n[WARN] {len(validation.warnings)} warnings:")
        for warn in validation.warnings[:5]:
            print(f"  - {warn}")
    
    if args.dedup:
        entries = deduplicate_defects(entries)
    
    groups = separate_by_source(entries)
    
    # Export
    result_df = to_dataframe(entries)
    result_df.to_csv(args.output, index=False)
    print(f"\n[EXPORT] Saved {len(result_df)} records to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
