"""
QA Matrix - Recurrence Aggregation Engine (W-6 to W-1)
=======================================================
Tracks weekly recurrence of defects across 6 rolling weeks.
Updates recurrence counts and shifts weekly buckets.

Usage:
    python recurrence_aggregator.py --matrix qa_matrix.csv --defects defects.csv --output updated_matrix.csv
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import argparse
from datetime import datetime, timedelta


# ─── Data Models ────────────────────────────────────────────────────────

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


# ─── Aggregation Functions ──────────────────────────────────────────────

def shift_weekly_window(recurrence: WeeklyRecurrence) -> WeeklyRecurrence:
    """
    Shift the weekly window forward by one week.
    W-6 is dropped, all others shift left, W-1 becomes 0.
    
    Equivalent to:
        df['weekly'] = df['weekly'].apply(lambda x: x[1:] + [0])
    """
    values = recurrence.to_list()
    shifted = values[1:] + [0]
    return WeeklyRecurrence.from_list(shifted)


def aggregate_defect_counts(
    matched_pairs: List[Dict],
    current_recurrence: Dict[int, WeeklyRecurrence]
) -> Dict[int, WeeklyRecurrence]:
    """
    Aggregate matched defect quantities into W-1 (last week).
    
    Equivalent to:
        grouped = df.groupby('qa_sno')['quantity'].sum()
        matrix['w1'] += grouped
    
    Parameters:
        matched_pairs: List of dicts with {qa_sno: int, quantity: int}
        current_recurrence: Current recurrence state keyed by S.No
    
    Returns:
        Updated recurrence dict
    """
    updated = {k: WeeklyRecurrence.from_list(v.to_list()) for k, v in current_recurrence.items()}
    
    # Group by QA concern S.No
    # Equivalent to: df.groupby('qa_sno')['quantity'].sum()
    aggregation: Dict[int, int] = {}
    for pair in matched_pairs:
        sno = pair['qa_sno']
        qty = pair.get('quantity', 1)
        aggregation[sno] = aggregation.get(sno, 0) + qty
    
    # Update W-1 with aggregated counts
    for sno, total_qty in aggregation.items():
        if sno in updated:
            updated[sno].w1 += total_qty
        else:
            rec = WeeklyRecurrence()
            rec.w1 = total_qty
            updated[sno] = rec
    
    print(f"[AGGREGATE] Updated {len(aggregation)} concerns with new defect counts")
    return updated


def calculate_total_recurrence(recurrence: WeeklyRecurrence, defect_rating: int) -> Tuple[int, int]:
    """
    Calculate total recurrence and recurrence + defect rating.
    
    Equivalent to:
        df['recurrence'] = df['weekly'].apply(sum)
        df['recurrence_plus_defect'] = df['recurrence'] + df['defect_rating']
    
    Returns:
        (total_recurrence, recurrence_count_plus_defect)
    """
    total = recurrence.total
    return total, total + defect_rating


def weekly_trend_analysis(recurrence: WeeklyRecurrence) -> Dict:
    """
    Analyze weekly trend for a concern.
    
    Detects:
    - Increasing trend (worsening quality)
    - Decreasing trend (improving quality)
    - Stable (no change)
    - Spike (sudden increase in W-1)
    """
    values = recurrence.to_list()
    non_zero = [v for v in values if v > 0]
    
    if len(non_zero) == 0:
        return {"trend": "inactive", "severity": "none"}
    
    # Check for recent spike
    if values[-1] > 0 and all(v == 0 for v in values[:-1]):
        return {"trend": "new_spike", "severity": "watch"}
    
    # Compare recent vs older
    recent_avg = np.mean(values[-2:]) if len(values) >= 2 else values[-1]
    older_avg = np.mean(values[:3]) if len(values) >= 3 else 0
    
    if recent_avg > older_avg * 1.5:
        return {"trend": "increasing", "severity": "high"}
    elif recent_avg < older_avg * 0.5:
        return {"trend": "decreasing", "severity": "low"}
    else:
        return {"trend": "stable", "severity": "medium"}


def batch_shift_all_weeks(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """
    Shift all weekly recurrence windows forward by one week for the entire matrix.
    Called at the start of a new week.
    
    Equivalent to:
        matrix_df['weekly_recurrence'] = matrix_df['weekly_recurrence'].apply(
            lambda x: x[1:] + [0]
        )
    """
    df = matrix_df.copy()
    
    def shift_row(weekly_list):
        if isinstance(weekly_list, list) and len(weekly_list) == 6:
            return weekly_list[1:] + [0]
        return [0, 0, 0, 0, 0, 0]
    
    df['weekly_recurrence'] = df['weekly_recurrence'].apply(shift_row)
    df['recurrence'] = df['weekly_recurrence'].apply(sum)
    
    print(f"[SHIFT] Shifted weekly windows for {len(df)} concerns")
    return df


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - Recurrence Aggregator")
    parser.add_argument("--matrix", "-m", required=True, help="QA Matrix CSV file")
    parser.add_argument("--defects", "-d", help="Matched defects CSV (with qa_sno column)")
    parser.add_argument("--shift", action="store_true", help="Shift weekly window (new week)")
    parser.add_argument("--output", "-o", default="updated_matrix.csv", help="Output file")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - RECURRENCE AGGREGATION ENGINE")
    print("=" * 60)
    
    matrix_df = pd.read_csv(args.matrix)
    print(f"[LOAD] Loaded {len(matrix_df)} matrix entries")
    
    if args.shift:
        matrix_df = batch_shift_all_weeks(matrix_df)
    
    if args.defects:
        defects_df = pd.read_csv(args.defects)
        print(f"[LOAD] Loaded {len(defects_df)} matched defects")
        
        # Build matched pairs
        matched_pairs = defects_df[['qa_sno', 'quantity']].to_dict('records')
        
        # Build current recurrence state
        current_rec = {}
        for _, row in matrix_df.iterrows():
            sno = int(row['s_no'])
            weekly = eval(row['weekly_recurrence']) if isinstance(row['weekly_recurrence'], str) else row['weekly_recurrence']
            current_rec[sno] = WeeklyRecurrence.from_list(weekly if isinstance(weekly, list) else [0]*6)
        
        # Aggregate
        updated_rec = aggregate_defect_counts(matched_pairs, current_rec)
        
        # Write back
        for sno, rec in updated_rec.items():
            mask = matrix_df['s_no'] == sno
            matrix_df.loc[mask, 'weekly_recurrence'] = str(rec.to_list())
            total, plus_defect = calculate_total_recurrence(
                rec, int(matrix_df.loc[mask, 'defect_rating'].iloc[0]) if mask.any() else 1
            )
            matrix_df.loc[mask, 'recurrence'] = total
            matrix_df.loc[mask, 'recurrence_count_plus_defect'] = plus_defect
    
    matrix_df.to_csv(args.output, index=False)
    print(f"\n[EXPORT] Saved to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
