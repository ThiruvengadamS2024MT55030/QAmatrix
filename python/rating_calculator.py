"""
QA Matrix - MFG / Plant Rating Calculator
==========================================
Calculates manufacturing and plant ratings, determines OK/NG statuses,
and provides summary analytics.

Usage:
    python rating_calculator.py --matrix qa_matrix.csv --output ratings_report.csv
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import argparse


# ─── Rating Data Models ────────────────────────────────────────────────

@dataclass
class ControlRating:
    """Three-tier control rating."""
    MFG: int = 0
    Quality: int = 0
    Plant: int = 0


@dataclass
class RatingResult:
    """Complete rating result for a matrix entry."""
    s_no: int
    concern: str
    defect_rating: int
    mfg_rating: int
    quality_rating: int
    plant_rating: int
    recurrence: int
    workstation_status: str
    mfg_status: str
    plant_status: str


# ─── Rating Calculation Logic ──────────────────────────────────────────

def sum_jsonb_values(jsonb_data: dict, exclude_keys: List[str] = None) -> int:
    """
    Sum all numeric values in a JSONB-like dict, excluding specified keys.
    
    Equivalent to:
        sum(v for k, v in data.items() if k not in exclude and v is not None)
    """
    exclude = set(exclude_keys or [])
    total = 0
    for key, val in jsonb_data.items():
        if key in exclude:
            continue
        if val is not None and isinstance(val, (int, float)):
            total += int(val)
    return total


def calculate_mfg_rating_from_dict(trim: dict, chassis: dict, final: dict) -> int:
    """
    MFG Rating = sum(Trim) + sum(Chassis) + sum(Final without ResidualTorque)
    
    Python equivalent:
        mfg = (pd.Series(trim).sum() + 
               pd.Series(chassis).sum() + 
               pd.Series(final).drop('ResidualTorque').sum())
    """
    trim_sum = sum_jsonb_values(trim)
    chassis_sum = sum_jsonb_values(chassis)
    final_sum = sum_jsonb_values(final, exclude_keys=["ResidualTorque"])
    return trim_sum + chassis_sum + final_sum


def calculate_quality_rating_from_dict(q_control: dict) -> int:
    """
    Quality Rating = sum(QControl scores)
    
    Python equivalent:
        quality = pd.Series(q_control).sum()
    """
    return sum_jsonb_values(q_control)


def calculate_plant_rating_from_dict(final: dict, q_control: dict, q_control_detail: dict) -> int:
    """
    Plant Rating = ResidualTorque + sum(QControl) + sum(QControlDetail)
    
    Python equivalent:
        plant = final.get('ResidualTorque', 0) + pd.Series(q_control).sum() + pd.Series(q_detail).sum()
    """
    residual = final.get("ResidualTorque", 0) or 0
    q_sum = sum_jsonb_values(q_control)
    detail_sum = sum_jsonb_values(q_control_detail)
    return int(residual) + q_sum + detail_sum


def determine_statuses(
    defect_rating: int,
    mfg_rating: int,
    plant_rating: int,
    has_recurrence: bool
) -> Tuple[str, str, str]:
    """
    Determine OK/NG statuses using vectorized logic.
    
    Python equivalent:
        ws = np.where(has_recurrence, 'NG', np.where(mfg >= dr, 'OK', 'NG'))
        mfg = np.where(mfg_rating >= dr, 'OK', 'NG')
        plant = np.where(plant_rating >= dr, 'OK', 'NG')
    """
    ws = "NG" if has_recurrence else ("OK" if mfg_rating >= defect_rating else "NG")
    mfg = "OK" if mfg_rating >= defect_rating else "NG"
    plant = "OK" if plant_rating >= defect_rating else "NG"
    return ws, mfg, plant


def recalculate_entry(entry: dict) -> dict:
    """
    Full recalculation of a single QA Matrix entry.
    
    This mirrors the TypeScript recalculateStatuses() function exactly.
    """
    dr = int(entry.get('defect_rating', 1))
    weekly = entry.get('weekly_recurrence', [0, 0, 0, 0, 0, 0])
    if isinstance(weekly, str):
        weekly = eval(weekly)
    
    trim = entry.get('trim', {})
    chassis = entry.get('chassis', {})
    final = entry.get('final', {})
    q_control = entry.get('q_control', {})
    q_control_detail = entry.get('q_control_detail', {})
    
    if isinstance(trim, str): trim = eval(trim)
    if isinstance(chassis, str): chassis = eval(chassis)
    if isinstance(final, str): final = eval(final)
    if isinstance(q_control, str): q_control = eval(q_control)
    if isinstance(q_control_detail, str): q_control_detail = eval(q_control_detail)
    
    # Calculate ratings
    mfg_rating = calculate_mfg_rating_from_dict(trim, chassis, final)
    quality_rating = calculate_quality_rating_from_dict(q_control)
    plant_rating = calculate_plant_rating_from_dict(final, q_control, q_control_detail)
    
    # Recurrence
    recurrence = sum(weekly)
    has_recurrence = any(w > 0 for w in weekly)
    
    # Statuses
    ws_status, mfg_status, plant_status = determine_statuses(
        dr, mfg_rating, plant_rating, has_recurrence
    )
    
    return {
        **entry,
        'recurrence': recurrence,
        'recurrence_count_plus_defect': dr + recurrence,
        'control_rating': {'MFG': mfg_rating, 'Quality': quality_rating, 'Plant': plant_rating},
        'workstation_status': ws_status,
        'mfg_status': mfg_status,
        'plant_status': plant_status,
    }


def batch_recalculate(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalculate all entries in the matrix.
    
    Equivalent to:
        df = df.apply(recalculate_entry, axis=1, result_type='expand')
    """
    records = matrix_df.to_dict('records')
    updated = [recalculate_entry(r) for r in records]
    result = pd.DataFrame(updated)
    
    # Summary statistics
    ng_ws = (result['workstation_status'] == 'NG').sum()
    ng_mfg = (result['mfg_status'] == 'NG').sum()
    ng_plant = (result['plant_status'] == 'NG').sum()
    
    print(f"[RATING] Status Summary:")
    print(f"  Workstation NG: {ng_ws}/{len(result)}")
    print(f"  MFG NG:         {ng_mfg}/{len(result)}")
    print(f"  Plant NG:       {ng_plant}/{len(result)}")
    
    return result


def generate_rating_report(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a summary report of all ratings.
    
    Equivalent to:
        report = df.groupby('designation').agg({
            'plant_status': lambda x: (x == 'NG').sum(),
            'mfg_status': lambda x: (x == 'NG').sum(),
        })
    """
    report = matrix_df.groupby('designation').agg(
        total_concerns=('s_no', 'count'),
        plant_ng=('plant_status', lambda x: (x == 'NG').sum()),
        mfg_ng=('mfg_status', lambda x: (x == 'NG').sum()),
        ws_ng=('workstation_status', lambda x: (x == 'NG').sum()),
        avg_defect_rating=('defect_rating', 'mean'),
        total_recurrence=('recurrence', 'sum'),
    ).reset_index()
    
    report['plant_ng_pct'] = (report['plant_ng'] / report['total_concerns'] * 100).round(1)
    
    return report


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - Rating Calculator")
    parser.add_argument("--matrix", "-m", required=True, help="QA Matrix CSV")
    parser.add_argument("--output", "-o", default="ratings_report.csv", help="Output file")
    parser.add_argument("--report", "-r", action="store_true", help="Generate summary report")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - MFG / PLANT RATING CALCULATOR")
    print("=" * 60)
    
    matrix_df = pd.read_csv(args.matrix)
    calculated = batch_recalculate(matrix_df)
    
    if args.report:
        report = generate_rating_report(calculated)
        print(f"\n[REPORT] Summary by Designation:")
        print(report.to_string(index=False))
        report.to_csv(args.output.replace('.csv', '_report.csv'), index=False)
    
    calculated.to_csv(args.output, index=False)
    print(f"\n[EXPORT] Saved to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
