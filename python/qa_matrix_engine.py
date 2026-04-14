"""
QA Matrix Unified Engine
========================
Consolidated backend logic for the QA Matrix application. 
Combines defect processing, matching, scoring, and recurrence tracking.

Usage:
    python qa_matrix_engine.py [subcommand] [options]
    Run 'python qa_matrix_engine.py --help' for details.
"""

import pandas as pd
import numpy as np
import re
import json
import argparse
import sys
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
import unicodedata

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

@dataclass
class MatchResult:
    """Result of matching a defect to a QA concern."""
    defect_index: int
    matched_sno: Optional[int]
    confidence: float
    reason: str
    method: str  # "fuzzy", "ai", "manual"

@dataclass
class AggregatedMatch:
    """Aggregated match result for a single QA concern."""
    qa_sno: int
    qa_concern: str
    defect_entries: List[Dict]
    repeat_count: int
    avg_confidence: float

@dataclass
class WeeklyRecurrence:
    """6-week rolling recurrence window."""
    w6: int = 0  # 6 weeks ago (oldest)
    w5: int = 0
    w4: int = 0
    w3: int = 0
    w2: int = 0
    w1: int = 0  # Last week (most recent)
    
    def to_list(self) -> List[int]:
        return [self.w6, self.w5, self.w4, self.w3, self.w2, self.w1]
    
    @classmethod
    def from_list(cls, values: List[int]) -> 'WeeklyRecurrence':
        padded = (values + [0] * 6)[:6]
        return cls(w6=padded[0], w5=padded[1], w4=padded[2], 
                   w3=padded[3], w2=padded[4], w1=padded[5])
    
    @property
    def total(self) -> int:
        return sum(self.to_list())
    
    @property
    def has_recurrence(self) -> bool:
        return any(w > 0 for w in self.to_list())

@dataclass
class StatusChange:
    """Records a status transition."""
    s_no: int
    concern: str
    field: str
    old_status: str
    new_status: str
    reason: str

class SeverityLevel(IntEnum):
    """1-3-5 Defect Rating Scale."""
    MINOR = 1
    MODERATE = 3
    CRITICAL = 5

# ─── Scoring Structures ──────────────────────────────────────────────

@dataclass
class TrimScores:
    """Trim area inspection scores (T10-T100 + TPQG)."""
    T10: Optional[int] = None
    T20: Optional[int] = None
    T30: Optional[int] = None
    T40: Optional[int] = None
    T50: Optional[int] = None
    T60: Optional[int] = None
    T70: Optional[int] = None
    T80: Optional[int] = None
    T90: Optional[int] = None
    T100: Optional[int] = None
    TPQG: Optional[int] = None
    
    def values(self) -> List[Optional[int]]:
        return [self.T10, self.T20, self.T30, self.T40, self.T50,
                self.T60, self.T70, self.T80, self.T90, self.T100, self.TPQG]

@dataclass
class ChassisScores:
    """Chassis area inspection scores."""
    C10: Optional[int] = None
    C20: Optional[int] = None
    C30: Optional[int] = None
    C40: Optional[int] = None
    C45: Optional[int] = None
    P10: Optional[int] = None
    P20: Optional[int] = None
    P30: Optional[int] = None
    C50: Optional[int] = None
    C60: Optional[int] = None
    C70: Optional[int] = None
    RSub: Optional[int] = None
    TS: Optional[int] = None
    C80: Optional[int] = None
    CPQG: Optional[int] = None
    
    def values(self) -> List[Optional[int]]:
        return [self.C10, self.C20, self.C30, self.C40, self.C45,
                self.P10, self.P20, self.P30, self.C50, self.C60,
                self.C70, self.RSub, self.TS, self.C80, self.CPQG]

@dataclass
class FinalScores:
    """Final assembly inspection scores (F10-F100 + FPQG + ResidualTorque)."""
    F10: Optional[int] = None
    F20: Optional[int] = None
    F30: Optional[int] = None
    F40: Optional[int] = None
    F50: Optional[int] = None
    F60: Optional[int] = None
    F70: Optional[int] = None
    F80: Optional[int] = None
    F90: Optional[int] = None
    F100: Optional[int] = None
    FPQG: Optional[int] = None
    ResidualTorque: Optional[int] = None
    
    def values_without_residual(self) -> List[Optional[int]]:
        return [self.F10, self.F20, self.F30, self.F40, self.F50,
                self.F60, self.F70, self.F80, self.F90, self.F100, self.FPQG]

@dataclass
class QControlScores:
    """Quality control scoring."""
    freq_control_1_1: Optional[int] = None
    visual_control_1_2: Optional[int] = None
    periodic_audit_1_3: Optional[int] = None
    human_control_1_4: Optional[int] = None
    sae_alert_3_1: Optional[int] = None
    freq_measure_3_2: Optional[int] = None
    manual_tool_3_3: Optional[int] = None
    human_tracking_3_4: Optional[int] = None
    auto_control_5_1: Optional[int] = None
    impossibility_5_2: Optional[int] = None
    sae_prohibition_5_3: Optional[int] = None
    
    def values(self) -> List[Optional[int]]:
        return [
            self.freq_control_1_1, self.visual_control_1_2,
            self.periodic_audit_1_3, self.human_control_1_4,
            self.sae_alert_3_1, self.freq_measure_3_2,
            self.manual_tool_3_3, self.human_tracking_3_4,
            self.auto_control_5_1, self.impossibility_5_2,
            self.sae_prohibition_5_3,
        ]

@dataclass
class QControlDetail:
    """Additional quality checkpoints."""
    CVT: Optional[int] = None
    SHOWER: Optional[int] = None
    DynamicUB: Optional[int] = None
    CC4: Optional[int] = None
    
    def values(self) -> List[Optional[int]]:
        return [self.CVT, self.SHOWER, self.DynamicUB, self.CC4]

# ─── Constants ──────────────────────────────────────────────────────────

SYNONYMS: Dict[str, List[str]] = {
    "brake": ["braking", "brk"], "seat": ["seating", "st"], "belt": ["seatbelt", "seat belt"],
    "window": ["windshield", "glass", "pane"], "wiper": ["wipers"], "lock": ["locked", "locking", "unlocked"],
    "bolt": ["bolts", "screw", "fastener"], "missing": ["absent", "not present", "shortage"],
    "damage": ["damaged", "broken", "crack", "cracked", "torn"], "noise": ["noisy", "vibration", "rattle", "squeak"],
    "leak": ["leaking", "leakage"], "error": ["wrong", "incorrect", "mismatch"], "assy": ["assembly", "asy"],
    "insecure": ["loose", "not secure", "unsecure"], "malfunction": ["not working", "failure", "defective", "faulty"],
    "torque": ["tightening", "tq"], "lamp": ["light", "bulb", "headlamp", "headlight"],
    "paint": ["painting", "painted", "colour", "color"], "wheel": ["tyre", "tire", "rim"],
    "connector": ["connect", "connection", "plug"], "harness": ["wiring", "wire", "cable"],
    "front": ["fr", "frt"], "rear": ["rr"], "left": ["lh", "lhf", "lhr"], "right": ["rh", "rhf", "rhr"],
}

STATION_PREFIXES = {"t": "trim", "c": "chassis", "f": "final", "p": "paint"}

STATUS_RULES = {
    "workstation": {"description": "NG if any recurrence > 0, else OK if MFG Rating \u2265 Defect Rating", "priority": 1},
    "mfg": {"description": "OK if MFG Rating \u2265 Defect Rating, else NG", "priority": 2},
    "plant": {"description": "OK if Plant Rating \u2265 Defect Rating, else NG", "priority": 3},
}

# ─── Utility Functions ───────────────────────────────────────────────

def tokenize(text: str) -> List[str]:
    return [t for t in re.sub(r'[^a-z0-9\s/\-]', ' ', text.lower()).split() if len(t) > 1]

def expand_synonyms(tokens: List[str]) -> List[str]:
    expanded = set(tokens)
    for token in tokens:
        if token in SYNONYMS: expanded.update(SYNONYMS[token])
        for key, syns in SYNONYMS.items():
            if token in syns: expanded.add(key); expanded.update(syns)
    return list(expanded)

def bigrams(text: str) -> Set[str]:
    clean = re.sub(r'[^a-z0-9]', '', text.lower())
    return {clean[i:i+2] for i in range(len(clean) - 1)}

def dice_coefficient(a: str, b: str) -> float:
    bi_a, bi_b = bigrams(a), bigrams(b)
    if not bi_a and not bi_b: return 0.0
    return (2 * len(bi_a & bi_b)) / (len(bi_a) + len(bi_b))

def jaccard_similarity(a: List[str], b: List[str]) -> float:
    set_a, set_b = set(a), set(b)
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union > 0 else 0.0

def weighted_token_overlap(query: List[str], target: List[str]) -> float:
    target_set = set(target)
    total_weight = 0.0; matched_weight = 0.0
    for qt in query:
        w = 0.5 if len(qt) <= 2 else (0.8 if len(qt) <= 4 else 1.0)
        total_weight += w
        if qt in target_set: matched_weight += w
        else:
            for tt in target:
                if tt in qt or qt in tt: matched_weight += w * 0.6; break
    return matched_weight / total_weight if total_weight > 0 else 0.0

def station_bonus(dvx_location: str, qa_station: str) -> float:
    dvx = dvx_location.lower().strip(); qa = qa_station.lower().strip()
    if dvx == qa: return 0.3
    clean_dvx = re.sub(r'[^a-z0-9]', '', dvx); clean_qa = re.sub(r'[^a-z0-9]', '', qa)
    if len(clean_dvx) >= 2 and clean_dvx == clean_qa: return 0.25
    if clean_dvx and clean_qa and clean_dvx[0] == clean_qa[0] and clean_dvx[0] in STATION_PREFIXES: return 0.1
    return 0.0

def normalize_header(header: str) -> str:
    h = str(header).strip().lower()
    h = unicodedata.normalize("NFD", h)
    h = re.sub(r'[\u0300-\u036f]', '', h)
    return re.sub(r'[_\s]+', ' ', h)

def find_column(headers: List[str], *names: str) -> int:
    normalized = [normalize_header(h) for h in headers]
    for name in names:
        nm = normalize_header(name)
        if nm in normalized: return normalized.index(nm)
        for i, h in enumerate(normalized):
            if h.startswith(nm): return i
        for i, h in enumerate(normalized):
            if nm in h: return i
    return -1

def find_header_row(df: pd.DataFrame, max_rows: int = 10) -> int:
    known_headers = ["defect description", "defect code", "gravity", "location details", "quantity"]
    for i in range(min(len(df), max_rows)):
        row = df.iloc[i].astype(str).str.lower().tolist()
        if sum(1 for kh in known_headers if any(kh in cell for cell in row)) >= 3: return i
    return 0

def sum_jsonb_values(jsonb_data: dict, exclude_keys: List[str] = None) -> int:
    exclude = set(exclude_keys or [])
    return sum(int(v) for k, v in jsonb_data.items() if k not in exclude and v is not None and isinstance(v, (int, float)))

def sum_non_null(values: List[Optional[int]]) -> int:
    return sum(v for v in values if v is not None)

# ─── Functional Modules ─────────────────────────────────────────────

# --- Defect Processor ---
def load_defect_file(filepath: str) -> pd.DataFrame:
    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext in ('xlsx', 'xls'): return pd.read_excel(filepath, header=None)
    if ext == 'csv': return pd.read_csv(filepath, header=None)
    raise ValueError(f"Unsupported file format: .{ext}")

def preprocess_defects(df: pd.DataFrame, source: str = "DVX") -> List[DVXEntry]:
    header_row = find_header_row(df)
    headers = df.iloc[header_row].astype(str).tolist()
    data = df.iloc[header_row + 1:].reset_index(drop=True)
    col_map = {
        'date': find_column(headers, "Date", "Inspection Date"),
        'location': find_column(headers, "Location Details", "Location", "Area", "Zone"),
        'code': find_column(headers, "Defect Code", "Code"),
        'desc': find_column(headers, "Defect Description", "Description", "Defect"),
        'details': find_column(headers, "Defect Description Details", "Details", "Comment"),
        'gravity': find_column(headers, "Gravity", "Severity", "Rating"),
        'quantity': find_column(headers, "Quantity", "Qty", "Count"),
        'source_col': find_column(headers, "Source", "Origin"),
        'responsible': find_column(headers, "Responsible", "Resp", "Owner"),
        'pof_family': find_column(headers, "POF Family", "Family"),
        'pof_code': find_column(headers, "POF CODE", "POF Code"),
    }
    
    def get_val(row, col_idx):
        if col_idx < 0 or col_idx >= len(row): return ""
        val = row.iloc[col_idx]
        return str(val).strip() if not pd.isna(val) else ""

    entries = []
    for i in range(len(data)):
        row = data.iloc[i]
        desc, details, loc = get_val(row, col_map['desc']), get_val(row, col_map['details']), get_val(row, col_map['location'])
        if not desc and not details and not loc: continue
        qty_raw = row.iloc[col_map['quantity']] if col_map['quantity'] >= 0 else 1
        try: qty = int(float(qty_raw)) if not pd.isna(qty_raw) else 1
        except: qty = 1
        entries.append(DVXEntry(
            date=get_val(row, col_map['date']), location_details=loc, defect_code=get_val(row, col_map['code']),
            defect_description=desc, defect_description_details=details, gravity=get_val(row, col_map['gravity']),
            quantity=max(1, qty), source=get_val(row, col_map['source_col']) or source,
            responsible=get_val(row, col_map['responsible']), pof_family=get_val(row, col_map['pof_family']),
            pof_code=get_val(row, col_map['pof_code']),
        ))
    return entries

def validate_defects(entries: List[DVXEntry]) -> ValidationResult:
    res = ValidationResult(is_valid=True, cleaned_count=len(entries))
    valid_g = {"1", "2", "3", "4", "5", "A", "B", "C", "D", ""}
    for i, e in enumerate(entries):
        if not e.defect_description and not e.defect_description_details: res.warnings.append(f"Row {i}: No description")
        if e.gravity and e.gravity.upper() not in valid_g: res.warnings.append(f"Row {i}: Unusual gravity '{e.gravity}'")
        if e.quantity <= 0: res.errors.append(f"Row {i}: Invalid qty {e.quantity}"); e.quantity = 1
    if res.errors: res.is_valid = False
    return res

# --- Defect Matcher ---
def fuzzy_match_single(dvx_text: str, dvx_loc: str, concerns: List[Dict], threshold: float = 0.15) -> Optional[MatchResult]:
    raw_tokens = tokenize(dvx_text)
    if not raw_tokens: return None
    query_tokens = expand_synonyms(raw_tokens)
    best_score = 0.0; best_idx = -1
    for i, qa in enumerate(concerns):
        target_text = f"{qa['concern']} {qa.get('operation_station', '')} {qa.get('designation', '')}"
        raw_target = tokenize(target_text)
        target_tokens = expand_synonyms(raw_target)
        jaccard = jaccard_similarity(query_tokens, target_tokens)
        target_joined = " ".join(raw_target)
        substr = sum(1 for t in raw_tokens if t in target_joined) / len(raw_tokens) if raw_tokens else 0
        dice = dice_coefficient(dvx_text, target_text)
        weighted = weighted_token_overlap(raw_tokens, raw_target)
        station = station_bonus(dvx_loc, qa.get('operation_station', ''))
        score = jaccard * 0.2 + substr * 0.25 + dice * 0.15 + weighted * 0.25 + station * 0.15
        if score > best_score: best_score = score; best_idx = i
    return MatchResult(-1, concerns[best_idx]['s_no'], round(best_score, 3), f"Fuzzy: {concerns[best_idx]['concern'][:50]}", "fuzzy") if best_idx != -1 and best_score >= threshold else None

def batch_fuzzy_match(defects: List[Dict], concerns: List[Dict], threshold: float = 0.15) -> List[MatchResult]:
    results = []
    for i, d in enumerate(defects):
        text = f"{d.get('defect_description', '')} {d.get('defect_description_details', '')}"
        match = fuzzy_match_single(text, d.get('location_details', ''), concerns, threshold)
        if match: match.defect_index = i; results.append(match)
        else: results.append(MatchResult(i, None, 0.0, "No match", "fuzzy"))
    return results

def ai_match_batch(defects: List[Dict], concerns: List[Dict], api_key: str, gateway_url: str = "https://ai.gateway.lovable.dev/v1/chat/completions", model: str = "google/gemini-1.5-flash", batch_size: int = 50) -> List[MatchResult]:
    try: import requests
    except: return batch_fuzzy_match(defects, concerns)
    concerns_txt = "\n".join(f"[{c['s_no']}] \"{c['concern']}\" (station: {c.get('operation_station', '')})" for c in concerns)
    all_results = []
    for b_start in range(0, len(defects), batch_size):
        batch = defects[b_start:b_start + batch_size]
        defects_txt = "\n".join(f"[{b_start+j}] {d.get('defect_description', '')} @ {d.get('location_details', '')}" for j, d in enumerate(batch))
        payload = {
            "model": model, "messages": [{"role": "system", "content": "Automotive QA expert. Match defects to concerns."}, {"role": "user", "content": f"Concerns:\n{concerns_txt}\n\nDefects:\n{defects_txt}"}],
            "tools": [{"type": "function", "function": {"name": "submit_matches", "parameters": {"type": "object", "properties": {"matches": {"type": "array", "items": {"type": "object", "properties": {"defectIndex": {"type": "number"}, "matchedSNo": {"type": ["number", "null"]}, "confidence": {"type": "number"}, "reason": {"type": "string"}}, "required": ["defectIndex", "matchedSNo", "confidence", "reason"]}}}, "required": ["matches"]}}}]
        }
        try:
            resp = requests.post(gateway_url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=120)
            resp.raise_for_status()
            parsed = json.loads(resp.json()["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])
            res_map = {m["defectIndex"]: m for m in parsed.get("matches", [])}
            for j in range(len(batch)):
                idx = b_start + j
                m = res_map.get(idx, {"matchedSNo": None, "confidence": 0.0, "reason": "No AI result"})
                all_results.append(MatchResult(idx, m["matchedSNo"], m["confidence"], m["reason"], "ai"))
        except: all_results.extend(batch_fuzzy_match(batch, concerns))
    return all_results

# --- Scoring & Ratings ---
def calculate_mfg_rating_from_dict(trim: dict, chassis: dict, final: dict) -> int:
    return sum_jsonb_values(trim) + sum_jsonb_values(chassis) + sum_jsonb_values(final, ["ResidualTorque"])

def calculate_plant_rating_from_dict(final: dict, q_control: dict, q_control_detail: dict) -> int:
    return int(final.get("ResidualTorque", 0) or 0) + sum_jsonb_values(q_control) + sum_jsonb_values(q_control_detail)

def determine_statuses(dr: int, mfg: int, plant: int, has_rec: bool) -> Tuple[str, str, str]:
    ws = "NG" if has_rec else ("OK" if mfg >= dr else "NG")
    return ws, ("OK" if mfg >= dr else "NG"), ("OK" if plant >= dr else "NG")

def recalculate_entry(entry: dict) -> dict:
    dr = int(entry.get('defect_rating', 1))
    def parse_col(val, default):
        if isinstance(val, (dict, list)): return val
        try: return json.loads(str(val).replace("'", '"')) if val else default
        except: return default
    trim, chassis, final = parse_col(entry.get('trim'), {}), parse_col(entry.get('chassis'), {}), parse_col(entry.get('final'), {})
    qc, qcd = parse_col(entry.get('q_control'), {}), parse_col(entry.get('q_control_detail'), {})
    weekly = parse_col(entry.get('weekly_recurrence'), [0]*6)
    mfg_r = calculate_mfg_rating_from_dict(trim, chassis, final)
    plant_r = calculate_plant_rating_from_dict(final, qc, qcd)
    rec = sum(weekly); has_rec = any(w > 0 for w in weekly)
    ws, mfg_s, plant_s = determine_statuses(dr, mfg_r, plant_r, has_rec)
    return {**entry, 'recurrence': rec, 'recurrence_count_plus_defect': dr + rec, 'control_rating': {'MFG': mfg_r, 'Plant': plant_r}, 'workstation_status': ws, 'mfg_status': mfg_s, 'plant_status': plant_s}

# --- Recurrence Manager ---
def shift_weekly_window(rec_list: List[int]) -> List[int]:
    return rec_list[1:] + [0] if len(rec_list) == 6 else [0]*6

def compute_statuses_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    res = df.copy()
    dr = res['defect_rating'].fillna(1).astype(int)
    mfg_r = res['mfg_rating'].fillna(0).astype(int) if 'mfg_rating' in res else pd.Series(0, index=res.index)
    plant_r = res['plant_rating'].fillna(0).astype(int) if 'plant_rating' in res else pd.Series(0, index=res.index)
    def parse_rec(w):
        if isinstance(w, str):
            try: w = json.loads(w.replace("'", '"'))
            except: return False
        return any(x > 0 for x in w) if isinstance(w, list) else False
    has_rec = res['weekly_recurrence'].apply(parse_rec)
    res['workstation_status'] = np.where(has_rec, 'NG', np.where(mfg_r >= dr, 'OK', 'NG'))
    res['mfg_status'] = np.where(mfg_r >= dr, 'OK', 'NG')
    res['plant_status'] = np.where(plant_r >= dr, 'OK', 'NG')
    return res

# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix Unified Engine")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # Process
    p_proc = subparsers.add_parser("process", help="Process raw defect files")
    p_proc.add_argument("--input", "-i", required=True); p_proc.add_argument("--output", "-o", default="cleaned.csv")
    
    # Match
    p_match = subparsers.add_parser("match", help="Match defects to matrix")
    p_match.add_argument("--defects", "-d", required=True); p_match.add_argument("--matrix", "-m", required=True)
    p_match.add_argument("--mode", choices=["fuzzy", "ai"], default="fuzzy"); p_match.add_argument("--api-key", help="API Key")
    p_match.add_argument("--output", "-o", default="matches.csv")

    # Score
    p_score = subparsers.add_parser("score", help="Calculate ratings and statuses")
    p_score.add_argument("--matrix", "-m", required=True); p_score.add_argument("--output", "-o", default="scored.csv")

    # Recurrence
    p_rec = subparsers.add_parser("recurrence", help="Shift weekly recurrence window")
    p_rec.add_argument("--matrix", "-m", required=True); p_rec.add_argument("--output", "-o", default="updated_matrix.csv")

    args = parser.parse_args()

    if args.command == "process":
        df = load_defect_file(args.input)
        entries = preprocess_defects(df)
        pd.DataFrame([e.__dict__ for e in entries]).to_csv(args.output, index=False)
        print(f"Processed {len(entries)} entries to {args.output}")
    
    elif args.command == "match":
        def_df = pd.read_csv(args.defects); mat_df = pd.read_csv(args.matrix)
        defects = def_df.to_dict('records'); concerns = mat_df.to_dict('records')
        if args.mode == "ai" and args.api_key: matches = ai_match_batch(defects, concerns, args.api_key)
        else: matches = batch_fuzzy_match(defects, concerns)
        pd.DataFrame([m.__dict__ for m in matches]).to_csv(args.output, index=False)
        print(f"Matched {len(defects)} defects to {args.output}")

    elif args.command == "score":
        df = pd.read_csv(args.matrix)
        # Using a simple row-by-row recalculation for safety in the unified script
        records = df.to_dict('records')
        updated = [recalculate_entry(r) for r in records]
        pd.DataFrame(updated).to_csv(args.output, index=False)
        print(f"Scored {len(updated)} entries to {args.output}")

    elif args.command == "recurrence":
        df = pd.read_csv(args.matrix)
        def shift_row(w):
            if isinstance(w, str):
                try: w = json.loads(w.replace("'", '"'))
                except: w = [0]*6
            if isinstance(w, list) and len(w) == 6: return json.dumps(w[1:] + [0])
            return json.dumps([0]*6)
        df['weekly_recurrence'] = df['weekly_recurrence'].apply(shift_row)
        df.to_csv(args.output, index=False)
        print(f"Shifted recurrence windows to {args.output}")

    else: parser.print_help()

if __name__ == "__main__":
    main()
