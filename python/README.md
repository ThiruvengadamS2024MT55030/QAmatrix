# QA Matrix - Python Processing Pipeline

## Scripts

| Script | Purpose |
|--------|---------|
| `defect_processor.py` | Defect data ingestion, parsing, validation & deduplication |
| `recurrence_aggregator.py` | Weekly recurrence tracking (W-6 to W-1) |
| `severity_scorer.py` | 1-3-5 severity scoring & controllability calculation |
| `rating_calculator.py` | MFG / Quality / Plant rating computation |
| `status_automator.py` | OK/NG status automation with diff detection |
| `ai_defect_matcher.py` | AI-powered semantic matching (fuzzy + Google Gemini) |

## Setup

```bash
pip install -r requirements.txt
```

## Pipeline Example

```bash
# 1. Process raw defect file
python defect_processor.py -i defects.xlsx -s DVX -o cleaned.csv --dedup

# 2. Match defects to QA concerns
python ai_defect_matcher.py -d cleaned.csv -m qa_matrix.csv -o matches.csv --mode fuzzy

# 3. Aggregate recurrence
python recurrence_aggregator.py -m qa_matrix.csv -d matches.csv -o updated.csv

# 4. Recalculate ratings
python rating_calculator.py -m updated.csv -o rated.csv --report

# 5. Automate statuses
python status_automator.py -m rated.csv -o final.csv --summary
```

## AI Matching

For AI-powered matching via Google Gemini:

```bash
python ai_defect_matcher.py -d defects.csv -m matrix.csv --mode ai --api-key YOUR_KEY
```

Falls back to fuzzy matching if API is unavailable or rate-limited.
