"""
QA Matrix - OK/NG Status Automation Engine
===========================================
Automates the determination of Workstation, MFG, and Plant statuses
based on scoring rules and recurrence data.

Usage:
    python status_automator.py --matrix qa_matrix.csv --output status_report.csv
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import argparse


# ─── Status Rules ──────────────────────────────────────────────────────

STATUS_RULES = {
    "workstation": {
        "description": "NG if any weekly recurrence > 0, else OK if MFG Rating ≥ Defect Rating",
        "priority": 1,
    },
    "mfg": {
        "description": "OK if MFG Rating ≥ Defect Rating, else NG", 
        "priority": 2,
    },
    "plant": {
        "description": "OK if Plant Rating ≥ Defect Rating, else NG",
        "priority": 3,
    },
}


@dataclass
class StatusChange:
    """Records a status transition."""
    s_no: int
    concern: str
    field: str
    old_status: str
    new_status: str
    reason: str


# ─── Vectorized Status Calculation ─────────────────────────────────────

def compute_statuses_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all statuses using NumPy vectorized operations.
    
    This is the most efficient approach for large datasets.
    
    Equivalent to:
        df['ws_status'] = np.where(
            df['has_recurrence'], 'NG',
            np.where(df['mfg_rating'] >= df['defect_rating'], 'OK', 'NG')
        )
        df['mfg_status'] = np.where(df['mfg_rating'] >= df['defect_rating'], 'OK', 'NG')
        df['plant_status'] = np.where(df['plant_rating'] >= df['defect_rating'], 'OK', 'NG')
    """
    result = df.copy()
    
    dr = result['defect_rating'].astype(int)
    mfg_r = result.get('mfg_rating', pd.Series(0, index=result.index)).fillna(0).astype(int)
    plant_r = result.get('plant_rating', pd.Series(0, index=result.index)).fillna(0).astype(int)
    
    # Parse weekly recurrence to check for any > 0
    def has_recurrence(weekly):
        if isinstance(weekly, str):
            weekly = eval(weekly)
        if isinstance(weekly, list):
            return any(w > 0 for w in weekly)
        return False
    
    has_rec = result['weekly_recurrence'].apply(has_recurrence)
    
    # Vectorized status assignment
    result['workstation_status'] = np.where(
        has_rec, 'NG',
        np.where(mfg_r >= dr, 'OK', 'NG')
    )
    result['mfg_status'] = np.where(mfg_r >= dr, 'OK', 'NG')
    result['plant_status'] = np.where(plant_r >= dr, 'OK', 'NG')
    
    return result


def detect_status_changes(old_df: pd.DataFrame, new_df: pd.DataFrame) -> List[StatusChange]:
    """
    Compare old and new DataFrames to detect status transitions.
    
    Useful for generating diff reports (like the UpdateDiffDialog in the frontend).
    """
    changes = []
    status_fields = ['workstation_status', 'mfg_status', 'plant_status']
    
    for _, old_row in old_df.iterrows():
        sno = old_row['s_no']
        new_row = new_df[new_df['s_no'] == sno]
        
        if new_row.empty:
            continue
        
        new_row = new_row.iloc[0]
        
        for field in status_fields:
            old_val = str(old_row.get(field, ''))
            new_val = str(new_row.get(field, ''))
            
            if old_val != new_val:
                changes.append(StatusChange(
                    s_no=int(sno),
                    concern=str(old_row.get('concern', '')),
                    field=field.replace('_', ' ').title(),
                    old_status=old_val,
                    new_status=new_val,
                    reason=f"Rating recalculation: {field}"
                ))
    
    return changes


def generate_ng_summary(df: pd.DataFrame) -> Dict:
    """
    Generate a summary of NG statuses across the matrix.
    
    Equivalent to:
        summary = {
            'total': len(df),
            'ws_ng': (df['workstation_status'] == 'NG').sum(),
            'mfg_ng': (df['mfg_status'] == 'NG').sum(),
            'plant_ng': (df['plant_status'] == 'NG').sum(),
        }
    """
    total = len(df)
    ws_ng = (df['workstation_status'] == 'NG').sum()
    mfg_ng = (df['mfg_status'] == 'NG').sum()
    plant_ng = (df['plant_status'] == 'NG').sum()
    
    # Critical: entries that are NG at plant level with severity 5
    critical = df[(df['plant_status'] == 'NG') & (df['defect_rating'] == 5)]
    
    return {
        "total_concerns": total,
        "workstation_ng": int(ws_ng),
        "workstation_ok": int(total - ws_ng),
        "mfg_ng": int(mfg_ng),
        "mfg_ok": int(total - mfg_ng),
        "plant_ng": int(plant_ng),
        "plant_ok": int(total - plant_ng),
        "critical_count": len(critical),
        "plant_ng_pct": round(plant_ng / total * 100, 1) if total > 0 else 0,
        "by_designation": df.groupby('designation').apply(
            lambda g: {"total": len(g), "plant_ng": int((g['plant_status'] == 'NG').sum())}
        ).to_dict() if 'designation' in df.columns else {},
    }


def apply_repeat_updates(
    matrix_df: pd.DataFrame,
    matched_repeats: List[Dict]
) -> Tuple[pd.DataFrame, List[StatusChange]]:
    """
    Apply repeat matching results to the matrix and auto-recalculate statuses.
    
    This mirrors the handleApplyToMatrix() function from the frontend.
    
    Parameters:
        matrix_df: Current QA Matrix
        matched_repeats: List of {qa_sno, repeat_count} from AI matching
    
    Returns:
        (updated_matrix, list_of_changes)
    """
    old_df = matrix_df.copy()
    updated = matrix_df.copy()
    
    for repeat in matched_repeats:
        sno = repeat['qa_sno']
        count = repeat['repeat_count']
        mask = updated['s_no'] == sno
        
        if not mask.any():
            continue
        
        # Update W-1 (last week) - index 5 in the array
        def update_weekly(weekly):
            if isinstance(weekly, str):
                weekly = eval(weekly)
            if isinstance(weekly, list) and len(weekly) == 6:
                weekly[5] += count
                return weekly
            return [0, 0, 0, 0, 0, count]
        
        updated.loc[mask, 'weekly_recurrence'] = updated.loc[mask, 'weekly_recurrence'].apply(update_weekly)
        updated.loc[mask, 'recurrence'] = updated.loc[mask, 'weekly_recurrence'].apply(
            lambda w: sum(eval(w) if isinstance(w, str) else w)
        )
    
    # Recalculate all statuses
    updated = compute_statuses_vectorized(updated)
    
    # Detect changes
    changes = detect_status_changes(old_df, updated)
    
    print(f"[APPLY] Updated {len(matched_repeats)} concerns, detected {len(changes)} status changes")
    return updated, changes


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - Status Automator")
    parser.add_argument("--matrix", "-m", required=True, help="QA Matrix CSV")
    parser.add_argument("--output", "-o", default="status_report.csv", help="Output file")
    parser.add_argument("--summary", action="store_true", help="Print NG summary")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - OK/NG STATUS AUTOMATION ENGINE")
    print("=" * 60)
    
    matrix_df = pd.read_csv(args.matrix)
    updated = compute_statuses_vectorized(matrix_df)
    
    if args.summary:
        summary = generate_ng_summary(updated)
        print(f"\n[SUMMARY] Status Report:")
        print(f"  Total Concerns:    {summary['total_concerns']}")
        print(f"  Workstation NG:    {summary['workstation_ng']}")
        print(f"  MFG NG:            {summary['mfg_ng']}")
        print(f"  Plant NG:          {summary['plant_ng']} ({summary['plant_ng_pct']}%)")
        print(f"  Critical (Sev 5):  {summary['critical_count']}")
    
    updated.to_csv(args.output, index=False)
    print(f"\n[EXPORT] Saved to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
