"""
QA Matrix - Severity & Controllability Scoring (1-3-5 Logic)
=============================================================
Implements the automotive quality severity rating system and
controllability scoring across Trim, Chassis, and Final areas.

Usage:
    python severity_scorer.py --matrix qa_matrix.csv --output scored_matrix.csv
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from enum import IntEnum


# ─── Severity Rating System ────────────────────────────────────────────

class SeverityLevel(IntEnum):
    """
    1-3-5 Defect Rating Scale:
    1 = Minor (cosmetic, no safety impact)
    3 = Moderate (functional impact, customer complaint likely)
    5 = Critical (safety-related, regulatory concern)
    """
    MINOR = 1
    MODERATE = 3
    CRITICAL = 5


# ─── Score Structures ──────────────────────────────────────────────────

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
    ResidualTorque: Optional[int] = None  # Special: counts toward Plant, not MFG
    
    def values_without_residual(self) -> List[Optional[int]]:
        """Values for MFG calculation (excludes ResidualTorque)."""
        return [self.F10, self.F20, self.F30, self.F40, self.F50,
                self.F60, self.F70, self.F80, self.F90, self.F100, self.FPQG]


@dataclass
class QControlScores:
    """Quality control scoring (1.x = freq, 3.x = manual, 5.x = auto)."""
    # 1.x - Frequency-based controls
    freq_control_1_1: Optional[int] = None
    visual_control_1_2: Optional[int] = None
    periodic_audit_1_3: Optional[int] = None
    human_control_1_4: Optional[int] = None
    # 3.x - Manual/Semi-auto controls
    sae_alert_3_1: Optional[int] = None
    freq_measure_3_2: Optional[int] = None
    manual_tool_3_3: Optional[int] = None
    human_tracking_3_4: Optional[int] = None
    # 5.x - Automatic controls
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


# ─── Core Scoring Functions ────────────────────────────────────────────

def sum_non_null(values: List[Optional[int]]) -> int:
    """
    Sum values treating None as 0.
    Equivalent to: np.nansum(values)
    """
    return sum(v for v in values if v is not None)


def calculate_mfg_rating(
    trim: TrimScores,
    chassis: ChassisScores,
    final: FinalScores
) -> int:
    """
    Calculate Manufacturing (MFG) Rating.
    
    Formula:
        MFG = sum(Trim) + sum(Chassis) + sum(Final excluding ResidualTorque)
    
    Equivalent to:
        mfg_rating = np.nansum(trim_values) + np.nansum(chassis_values) + np.nansum(final_values)
    """
    trim_sum = sum_non_null(trim.values())
    chassis_sum = sum_non_null(chassis.values())
    final_sum = sum_non_null(final.values_without_residual())
    
    return trim_sum + chassis_sum + final_sum


def calculate_quality_rating(q_control: QControlScores) -> int:
    """
    Calculate Quality Rating from quality control scores.
    
    Formula:
        Quality = sum(all QControl scores)
    """
    return sum_non_null(q_control.values())


def calculate_plant_rating(
    final: FinalScores,
    q_control: QControlScores,
    q_control_detail: QControlDetail
) -> int:
    """
    Calculate Plant Rating.
    
    Formula:
        Plant = ResidualTorque + sum(QControl) + sum(QControlDetail)
    
    Note: ResidualTorque is unique - it belongs to Final but counts toward Plant.
    """
    residual = final.ResidualTorque if final.ResidualTorque is not None else 0
    q_sum = sum_non_null(q_control.values())
    detail_sum = sum_non_null(q_control_detail.values())
    
    return residual + q_sum + detail_sum


def calculate_controllability(
    defect_rating: int,
    mfg_rating: int,
    quality_rating: int,
    plant_rating: int,
    has_recurrence: bool
) -> Dict[str, str]:
    """
    Determine OK/NG status for each level.
    
    Logic:
        - Workstation: NG if recurrence exists, else OK if MFG ≥ DefectRating
        - MFG Status:  OK if MFG_Rating ≥ DefectRating, else NG
        - Plant Status: OK if Plant_Rating ≥ DefectRating, else NG
    
    Equivalent to:
        df['ws_status'] = np.where(df['has_recurrence'], 'NG',
                           np.where(df['mfg_rating'] >= df['defect_rating'], 'OK', 'NG'))
        df['mfg_status'] = np.where(df['mfg_rating'] >= df['defect_rating'], 'OK', 'NG')
        df['plant_status'] = np.where(df['plant_rating'] >= df['defect_rating'], 'OK', 'NG')
    """
    ws_status = "NG" if has_recurrence else ("OK" if mfg_rating >= defect_rating else "NG")
    mfg_status = "OK" if mfg_rating >= defect_rating else "NG"
    plant_status = "OK" if plant_rating >= defect_rating else "NG"
    
    return {
        "workstation_status": ws_status,
        "mfg_status": mfg_status,
        "plant_status": plant_status,
    }


def score_single_entry(
    defect_rating: int,
    trim: TrimScores,
    chassis: ChassisScores,
    final: FinalScores,
    q_control: QControlScores,
    q_control_detail: QControlDetail,
    weekly_recurrence: List[int]
) -> Dict:
    """
    Complete scoring pipeline for a single QA Matrix entry.
    
    Returns all calculated ratings and statuses.
    """
    mfg = calculate_mfg_rating(trim, chassis, final)
    quality = calculate_quality_rating(q_control)
    plant = calculate_plant_rating(final, q_control, q_control_detail)
    
    recurrence = sum(weekly_recurrence)
    has_recurrence = any(w > 0 for w in weekly_recurrence)
    
    statuses = calculate_controllability(defect_rating, mfg, quality, plant, has_recurrence)
    
    return {
        "mfg_rating": mfg,
        "quality_rating": quality,
        "plant_rating": plant,
        "recurrence": recurrence,
        "recurrence_count_plus_defect": recurrence + defect_rating,
        **statuses,
    }


def batch_score_matrix(matrix_df: pd.DataFrame) -> pd.DataFrame:
    """
    Score the entire QA Matrix DataFrame.
    
    Equivalent to:
        df[['mfg_rating', 'quality_rating', 'plant_rating']] = df.apply(calculate_ratings, axis=1)
        df[['ws_status', 'mfg_status', 'plant_status']] = df.apply(determine_statuses, axis=1)
    """
    df = matrix_df.copy()
    
    results = []
    for _, row in df.iterrows():
        # Parse scores from row (simplified - adapt column names as needed)
        result = score_single_entry(
            defect_rating=int(row.get('defect_rating', 1)),
            trim=TrimScores(),  # Would parse from row columns
            chassis=ChassisScores(),
            final=FinalScores(),
            q_control=QControlScores(),
            q_control_detail=QControlDetail(),
            weekly_recurrence=eval(str(row.get('weekly_recurrence', '[0,0,0,0,0,0]')))
        )
        results.append(result)
    
    result_df = pd.DataFrame(results)
    for col in result_df.columns:
        df[col] = result_df[col].values
    
    ng_count = (df['plant_status'] == 'NG').sum()
    ok_count = (df['plant_status'] == 'OK').sum()
    print(f"[SCORE] Plant Status: {ok_count} OK, {ng_count} NG out of {len(df)} entries")
    
    return df


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - Severity Scorer")
    parser.add_argument("--matrix", "-m", required=True, help="QA Matrix CSV")
    parser.add_argument("--output", "-o", default="scored_matrix.csv", help="Output file")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - SEVERITY & CONTROLLABILITY SCORER")
    print("=" * 60)
    
    matrix_df = pd.read_csv(args.matrix)
    scored = batch_score_matrix(matrix_df)
    scored.to_csv(args.output, index=False)
    
    print(f"\n[EXPORT] Saved scored matrix to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
