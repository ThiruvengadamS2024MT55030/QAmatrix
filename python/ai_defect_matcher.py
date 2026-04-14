"""
QA Matrix - AI-Assisted Defect Matching Integration
=====================================================
Implements NLP-based semantic matching of defect reports to QA Matrix concerns.
Supports both local fuzzy matching and AI (Google Gemini) assisted matching.

Usage:
    python ai_defect_matcher.py --defects defects.csv --matrix qa_matrix.csv --output matches.csv
    python ai_defect_matcher.py --defects defects.csv --matrix qa_matrix.csv --mode ai --api-key YOUR_KEY
"""

import pandas as pd
import numpy as np
import re
import json
import argparse
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict


# ─── Data Models ────────────────────────────────────────────────────────

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


# ─── Manufacturing Synonym Dictionary ──────────────────────────────────

SYNONYMS: Dict[str, List[str]] = {
    "brake": ["braking", "brk"],
    "seat": ["seating", "st"],
    "belt": ["seatbelt", "seat belt"],
    "window": ["windshield", "glass", "pane"],
    "wiper": ["wipers"],
    "lock": ["locked", "locking", "unlocked"],
    "bolt": ["bolts", "screw", "fastener"],
    "missing": ["absent", "not present", "shortage"],
    "damage": ["damaged", "broken", "crack", "cracked", "torn"],
    "noise": ["noisy", "vibration", "rattle", "squeak"],
    "leak": ["leaking", "leakage"],
    "error": ["wrong", "incorrect", "mismatch"],
    "assy": ["assembly", "asy"],
    "insecure": ["loose", "not secure", "unsecure"],
    "malfunction": ["not working", "failure", "defective", "faulty"],
    "torque": ["tightening", "tq"],
    "lamp": ["light", "bulb", "headlamp", "headlight"],
    "paint": ["painting", "painted", "colour", "color"],
    "wheel": ["tyre", "tire", "rim"],
    "connector": ["connect", "connection", "plug"],
    "harness": ["wiring", "wire", "cable"],
    "front": ["fr", "frt"],
    "rear": ["rr"],
    "left": ["lh", "lhf", "lhr"],
    "right": ["rh", "rhf", "rhr"],
}

STATION_PREFIXES = {"t": "trim", "c": "chassis", "f": "final", "p": "paint"}


# ─── Tokenization & NLP Utilities ──────────────────────────────────────

def tokenize(text: str) -> List[str]:
    """
    Tokenize text into normalized tokens.
    Equivalent to: sklearn.feature_extraction.text preprocessing
    """
    return [t for t in re.sub(r'[^a-z0-9\s/\-]', ' ', text.lower()).split() if len(t) > 1]


def expand_synonyms(tokens: List[str]) -> List[str]:
    """Expand tokens with manufacturing synonyms."""
    expanded = set(tokens)
    for token in tokens:
        if token in SYNONYMS:
            expanded.update(SYNONYMS[token])
        for key, syns in SYNONYMS.items():
            if token in syns:
                expanded.add(key)
                expanded.update(syns)
    return list(expanded)


def bigrams(text: str) -> Set[str]:
    """Generate character bigrams for Dice coefficient."""
    clean = re.sub(r'[^a-z0-9]', '', text.lower())
    return {clean[i:i+2] for i in range(len(clean) - 1)}


def dice_coefficient(a: str, b: str) -> float:
    """Dice coefficient using character bigrams."""
    bi_a, bi_b = bigrams(a), bigrams(b)
    if not bi_a and not bi_b:
        return 0.0
    intersection = len(bi_a & bi_b)
    return (2 * intersection) / (len(bi_a) + len(bi_b))


def jaccard_similarity(a: List[str], b: List[str]) -> float:
    """Jaccard similarity between token sets."""
    set_a, set_b = set(a), set(b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def weighted_token_overlap(query: List[str], target: List[str]) -> float:
    """Weighted overlap giving more importance to longer tokens."""
    target_set = set(target)
    total_weight = 0.0
    matched_weight = 0.0
    
    for qt in query:
        w = 0.5 if len(qt) <= 2 else (0.8 if len(qt) <= 4 else 1.0)
        total_weight += w
        if qt in target_set:
            matched_weight += w
        else:
            for tt in target:
                if tt in qt or qt in tt:
                    matched_weight += w * 0.6
                    break
    
    return matched_weight / total_weight if total_weight > 0 else 0.0


def station_bonus(dvx_location: str, qa_station: str) -> float:
    """Score bonus for matching station codes."""
    dvx = dvx_location.lower().strip()
    qa = qa_station.lower().strip()
    if dvx == qa:
        return 0.3
    clean_dvx = re.sub(r'[^a-z0-9]', '', dvx)
    clean_qa = re.sub(r'[^a-z0-9]', '', qa)
    if len(clean_dvx) >= 2 and clean_dvx == clean_qa:
        return 0.25
    if clean_dvx and clean_qa and clean_dvx[0] == clean_qa[0] and clean_dvx[0] in STATION_PREFIXES:
        return 0.1
    return 0.0


# ─── Local Fuzzy Matching Engine ───────────────────────────────────────

def fuzzy_match_single(
    dvx_text: str,
    dvx_location: str,
    concerns: List[Dict],
    threshold: float = 0.15
) -> Optional[MatchResult]:
    """
    Find best matching QA concern using multi-signal fuzzy matching.
    
    Signals combined:
    - Jaccard similarity (20%)
    - Substring overlap (25%)
    - Dice coefficient (15%)
    - Weighted token overlap (25%)
    - Station code bonus (15%)
    
    Equivalent to: sklearn cosine_similarity + custom features
    """
    raw_tokens = tokenize(dvx_text)
    if not raw_tokens:
        return None
    
    query_tokens = expand_synonyms(raw_tokens)
    best_score = 0.0
    best_idx = -1
    
    for i, qa in enumerate(concerns):
        target_text = f"{qa['concern']} {qa.get('operation_station', '')} {qa.get('designation', '')}"
        raw_target = tokenize(target_text)
        target_tokens = expand_synonyms(raw_target)
        
        # Multi-signal scoring
        jaccard = jaccard_similarity(query_tokens, target_tokens)
        
        target_joined = " ".join(raw_target)
        substring = sum(1 for t in raw_tokens if t in target_joined) / len(raw_tokens) if raw_tokens else 0
        
        dice = dice_coefficient(dvx_text, target_text)
        weighted = weighted_token_overlap(raw_tokens, raw_target)
        station = station_bonus(dvx_location, qa.get('operation_station', ''))
        
        score = jaccard * 0.2 + substring * 0.25 + dice * 0.15 + weighted * 0.25 + station * 0.15
        
        if score > best_score:
            best_score = score
            best_idx = i
    
    if best_idx == -1 or best_score < threshold:
        return None
    
    return MatchResult(
        defect_index=-1,  # Set by caller
        matched_sno=concerns[best_idx]['s_no'],
        confidence=round(best_score, 3),
        reason=f"Fuzzy match: {concerns[best_idx]['concern'][:50]}",
        method="fuzzy"
    )


def batch_fuzzy_match(
    defects: List[Dict],
    concerns: List[Dict],
    threshold: float = 0.15
) -> List[MatchResult]:
    """
    Batch fuzzy matching of all defects against all concerns.
    
    Equivalent to:
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(defect_vectors, concern_vectors)
        matches = similarity_matrix.argmax(axis=1)
    """
    results = []
    
    for i, defect in enumerate(defects):
        text = f"{defect.get('defect_description', '')} {defect.get('defect_description_details', '')}"
        location = defect.get('location_details', '')
        
        match = fuzzy_match_single(text, location, concerns, threshold)
        
        if match:
            match.defect_index = i
            results.append(match)
        else:
            results.append(MatchResult(
                defect_index=i,
                matched_sno=None,
                confidence=0.0,
                reason="No match found",
                method="fuzzy"
            ))
    
    matched = sum(1 for r in results if r.matched_sno is not None)
    print(f"[FUZZY] Matched {matched}/{len(defects)} defects (threshold={threshold})")
    return results


# ─── AI-Powered Matching (Google Gemini) ───────────────────────────────

def ai_match_batch(
    defects: List[Dict],
    concerns: List[Dict],
    api_key: str,
    gateway_url: str = "https://ai.gateway.lovable.dev/v1/chat/completions",
    model: str = "google/gemini-3-flash-preview",
    batch_size: int = 200
) -> List[MatchResult]:
    """
    AI-powered semantic matching using Google Gemini via Lovable AI Gateway.
    
    This mirrors the match-defects Edge Function.
    
    Pipeline:
    1. Build concern context string
    2. Batch defects (max 200 per request)
    3. Send to Gemini with tool-calling for structured output
    4. Parse results with confidence scores
    
    Equivalent to:
        from transformers import pipeline
        nlp = pipeline("zero-shot-classification")
        results = nlp(defect_texts, candidate_labels=concern_labels)
    """
    try:
        import requests
    except ImportError:
        print("[AI] requests library not installed. Run: pip install requests")
        return batch_fuzzy_match(defects, concerns)
    
    # Build concern context
    concerns_text = "\n".join(
        f"[{c['s_no']}] \"{c['concern']}\" (station: {c.get('operation_station', '')}, area: {c.get('designation', '')})"
        for c in concerns
    )
    
    all_results = []
    
    for batch_start in range(0, len(defects), batch_size):
        batch = defects[batch_start:batch_start + batch_size]
        
        defects_text = "\n".join(
            f"[{batch_start + j}] Location: \"{d.get('location_details', '')}\" | "
            f"Defect: \"{d.get('defect_description', '')}\" | "
            f"Details: \"{d.get('defect_description_details', '')}\" | "
            f"Gravity: {d.get('gravity', '')}"
            for j, d in enumerate(batch)
        )
        
        system_prompt = (
            "You are an automotive quality assurance expert. Match defect reports to QA concerns "
            "based on semantic meaning — not just keywords. Consider the actual problem, location, "
            "component type, and manufacturing context. Return null for unmatched defects."
        )
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"QA Concerns:\n{concerns_text}\n\nDefects:\n{defects_text}\n\nMatch each defect to the best QA concern."}
            ],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "submit_matches",
                    "description": "Submit matching results",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "matches": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "defectIndex": {"type": "number"},
                                        "matchedSNo": {"type": ["number", "null"]},
                                        "confidence": {"type": "number"},
                                        "reason": {"type": "string"}
                                    },
                                    "required": ["defectIndex", "matchedSNo", "confidence", "reason"]
                                }
                            }
                        },
                        "required": ["matches"]
                    }
                }
            }],
            "tool_choice": {"type": "function", "function": {"name": "submit_matches"}}
        }
        
        try:
            resp = requests.post(
                gateway_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=120
            )
            
            if resp.status_code == 429:
                print(f"[AI] Rate limited. Falling back to fuzzy matching for batch {batch_start}.")
                all_results.extend(batch_fuzzy_match(batch, concerns))
                continue
            
            if resp.status_code == 402:
                print(f"[AI] Credits depleted. Falling back to fuzzy matching.")
                all_results.extend(batch_fuzzy_match(batch, concerns))
                continue
            
            resp.raise_for_status()
            data = resp.json()
            
            tool_call = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [{}])[0]
            parsed = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            
            for m in parsed.get("matches", []):
                all_results.append(MatchResult(
                    defect_index=m["defectIndex"],
                    matched_sno=m["matchedSNo"],
                    confidence=m["confidence"],
                    reason=m["reason"],
                    method="ai"
                ))
            
            print(f"[AI] Batch {batch_start}-{batch_start + len(batch)}: {len(parsed.get('matches', []))} results")
            
        except Exception as e:
            print(f"[AI] Error in batch {batch_start}: {e}. Falling back to fuzzy.")
            all_results.extend(batch_fuzzy_match(batch, concerns))
    
    return all_results


# ─── Aggregation ───────────────────────────────────────────────────────

def aggregate_matches(
    matches: List[MatchResult],
    defects: List[Dict],
    concerns: List[Dict],
    confidence_threshold: float = 0.3
) -> Tuple[List[AggregatedMatch], List[Dict]]:
    """
    Aggregate individual matches into concern-level repeat counts.
    
    Equivalent to:
        df.groupby('matched_sno').agg({
            'quantity': 'sum',
            'confidence': 'mean'
        })
    """
    concern_map = {c['s_no']: c['concern'] for c in concerns}
    
    grouped: Dict[int, AggregatedMatch] = {}
    unmatched = []
    
    for match in matches:
        defect = defects[match.defect_index] if match.defect_index < len(defects) else {}
        qty = defect.get('quantity', 1)
        
        if match.matched_sno is not None and match.confidence >= confidence_threshold:
            sno = match.matched_sno
            if sno not in grouped:
                grouped[sno] = AggregatedMatch(
                    qa_sno=sno,
                    qa_concern=concern_map.get(sno, ""),
                    defect_entries=[],
                    repeat_count=0,
                    avg_confidence=0.0
                )
            grouped[sno].defect_entries.append(defect)
            grouped[sno].repeat_count += qty
        else:
            unmatched.append(defect)
    
    # Calculate average confidence
    for sno, agg in grouped.items():
        relevant = [m.confidence for m in matches if m.matched_sno == sno and m.confidence >= confidence_threshold]
        agg.avg_confidence = round(np.mean(relevant), 3) if relevant else 0.0
    
    result = sorted(grouped.values(), key=lambda x: x.repeat_count, reverse=True)
    print(f"[AGGREGATE] {len(result)} concerns paired, {len(unmatched)} unmatched (threshold={confidence_threshold})")
    return result, unmatched


# ─── CLI Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Matrix - AI Defect Matcher")
    parser.add_argument("--defects", "-d", required=True, help="Defects CSV file")
    parser.add_argument("--matrix", "-m", required=True, help="QA Matrix CSV file")
    parser.add_argument("--output", "-o", default="matches.csv", help="Output file")
    parser.add_argument("--mode", choices=["fuzzy", "ai"], default="fuzzy", help="Matching mode")
    parser.add_argument("--api-key", help="API key for AI matching")
    parser.add_argument("--threshold", type=float, default=0.3, help="Confidence threshold")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QA MATRIX - AI DEFECT MATCHING ENGINE")
    print("=" * 60)
    
    defects_df = pd.read_csv(args.defects)
    matrix_df = pd.read_csv(args.matrix)
    
    defects = defects_df.to_dict('records')
    concerns = matrix_df[['s_no', 'concern', 'operation_station', 'designation']].to_dict('records')
    
    print(f"[LOAD] {len(defects)} defects, {len(concerns)} concerns")
    
    if args.mode == "ai" and args.api_key:
        matches = ai_match_batch(defects, concerns, args.api_key)
    else:
        if args.mode == "ai" and not args.api_key:
            print("[WARN] No API key provided, falling back to fuzzy matching")
        matches = batch_fuzzy_match(defects, concerns, threshold=args.threshold)
    
    # Aggregate
    aggregated, unmatched = aggregate_matches(matches, defects, concerns, args.threshold)
    
    # Export
    results = []
    for m in matches:
        results.append({
            'defect_index': m.defect_index,
            'matched_sno': m.matched_sno,
            'confidence': m.confidence,
            'reason': m.reason,
            'method': m.method,
        })
    
    pd.DataFrame(results).to_csv(args.output, index=False)
    print(f"\n[EXPORT] Saved {len(results)} match results to {args.output}")
    
    # Summary
    print(f"\n[SUMMARY]")
    print(f"  Total defects:  {len(defects)}")
    print(f"  Matched:        {sum(1 for m in matches if m.matched_sno is not None)}")
    print(f"  Unmatched:      {len(unmatched)}")
    print(f"  Unique concerns: {len(aggregated)}")
    if aggregated:
        print(f"  Top repeat:     S.No {aggregated[0].qa_sno} - {aggregated[0].qa_concern[:40]} ({aggregated[0].repeat_count}x)")
    print("=" * 60)


if __name__ == "__main__":
    main()
