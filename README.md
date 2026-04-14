# QA Matrix — Quality Assurance Control & Monitoring System

An automotive quality assurance application for tracking defects, managing quality control scores, and monitoring plant/MFG/workstation status across Trim, Chassis, and Final assembly areas.

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture & Data Pipeline](#system-architecture--data-pipeline)
3. [Pages & Navigation](#pages--navigation)
4. [QA Matrix Tab](#qa-matrix-tab)
5. [Repeats Tab — Defect Processing Pipeline](#repeats-tab--defect-processing-pipeline)
6. [Defect Data Page](#defect-data-page)
7. [Data Schema](#data-schema)
8. [Status Calculation Logic](#status-calculation-logic)
9. [Import & Export](#import--export)
10. [AI Sentiment Analysis & Semantic Matching](#ai-sentiment-analysis--semantic-matching)
11. [Database](#database)
12. [Tech Stack](#tech-stack)

---

## Overview

The QA Matrix system helps automotive quality teams:

- **Track quality concerns** across Trim, Chassis, and Final assembly lines
- **Monitor defect recurrence** with weekly tracking (W-6 to W-1)
- **Score quality controls** across 50+ control points (T10–T100, C10–C80, F10–F100, etc.)
- **Auto-calculate statuses** (OK/NG) for Workstation, MFG, and Plant levels
- **Match defects to concerns** using AI-powered sentiment analysis & semantic matching
- **Upload & manage defect data** from DVX, SCA, and YARD sources

---

## System Architecture & Data Pipeline

The system follows a structured data pipeline similar to a Python ML/NLP workflow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE OVERVIEW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. DATA INGESTION          Raw data upload (CSV/Excel/Google Sheets)   │
│         │                                                               │
│         ▼                                                               │
│  2. DATA PREPROCESSING      Parsing, cleaning, type casting,           │
│         │                   null handling, deduplication                │
│         ▼                                                               │
│  3. DATA SEPARATION         Split by source (DVX/SCA/YARD),           │
│         │                   store in raw + consolidated tables          │
│         ▼                                                               │
│  4. FEATURE EXTRACTION      Extract key features: defect description,  │
│         │                   location, gravity, defect code             │
│         ▼                                                               │
│  5. SENTIMENT ANALYSIS      AI-powered semantic understanding of       │
│         │                   defect descriptions using NLP (Gemini)     │
│         ▼                                                               │
│  6. PAIRING / MATCHING      Match defects → QA concerns using          │
│         │                   cosine-like semantic similarity            │
│         ▼                                                               │
│  7. POST-PROCESSING         Confidence filtering, manual review,       │
│         │                   reassignment, new concern creation         │
│         ▼                                                               │
│  8. AGGREGATION             Update recurrence counts, recalculate      │
│         │                   ratings and statuses                       │
│         ▼                                                               │
│  9. VISUALIZATION           Dashboard, matrix view, status badges,     │
│                             charts, filtered table views               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Stage Details

| Stage | Python Equivalent | Description |
|-------|-------------------|-------------|
| **Data Ingestion** | `pandas.read_excel()` / `pandas.read_csv()` | Upload raw defect data from Excel/CSV files or Google Sheets URLs |
| **Data Preprocessing** | `df.dropna()`, `df.astype()`, `df.fillna()` | Parse raw file data, clean empty rows, cast types (numbers, strings), handle null/missing values, validate required fields |
| **Data Separation** | `df.groupby('source')` | Split incoming data by source type (DVX, SCA, YARD) and store into separate database collections (raw `defect_data` + consolidated `final_defect`) |
| **Feature Extraction** | `sklearn.feature_extraction` | Extract meaningful features from each defect: `defect_description`, `location_details`, `defect_code`, `gravity`, `quantity` — structured for AI consumption |
| **Sentiment Analysis** | `transformers.pipeline('sentiment-analysis')` | AI (Google Gemini) performs deep semantic understanding of defect descriptions — goes beyond keyword matching to understand the actual manufacturing problem (e.g., "scratch on panel" ≈ "surface damage on body part") |
| **Pairing / Matching** | `sklearn.metrics.pairwise.cosine_similarity()` | Semantic similarity matching between defect descriptions and QA concern descriptions. Each match returns a confidence score (0–1) analogous to cosine similarity |
| **Post-Processing** | `df.loc[df['confidence'] >= threshold]` | Filter matches by confidence threshold (≥ 0.3), allow manual review/reassignment, create new concerns for unmatched defects |
| **Aggregation** | `df.groupby('concern').agg({'quantity': 'sum'})` | Sum matched defect quantities per concern, update W-1 recurrence counts, recalculate MFG/Quality/Plant ratings and OK/NG statuses |
| **Visualization** | `matplotlib` / `seaborn` / `plotly` | Interactive dashboards with charts, status badges, filterable matrix table, diff views for applied changes |

---

## Pages & Navigation

| Page | Route | Description |
|------|-------|-------------|
| **QA Matrix** | `/` | Main page with QA Matrix table and Repeats tab |
| **Defect Data** | `/defect-upload` | Upload and manage raw defect data (DVX, SCA, YARD) |

The main page has two tabs:
- **QA Matrix** — View/edit the full quality matrix table with dashboard
- **Repeats** — Defect processing pipeline: matching, pairing, and recurrence updates

---

## QA Matrix Tab

### Dashboard
Two dashboard views are available:
- **Summary View** — Overview cards showing total concerns, OK counts by Workstation/MFG/Plant, breakdowns by area (Trim/Chassis/Final) and source (DVX/ER3/ER4/Field/SCA). Click any card to filter the table.
- **Matrix Dashboard** — Visual matrix view of defect ratings vs. status levels.

### QA Matrix Table

The table displays all QA concerns with 80+ columns organized into sections:

| Section | Columns | Description |
|---------|---------|-------------|
| **Basic Info** | S.No, Source, Station, Area, Concern | Identity fields |
| **Defect Codes** | Defect Code, Location Code | Defect classification codes |
| **Defect Rating** | DR (1/3/5) | Severity: 1=Low, 3=Medium, 5=High |
| **Recurrence** | W-6 to W-1 | Weekly defect counts (last 6 weeks) |
| **RC+DR** | Recurrence + Defect Rating | Auto-calculated sum |
| **Trim Scores** | T10–T100, TPQG | 11 trim quality control checkpoints |
| **Chassis Scores** | C10–C80, P10–P30, RSub, TS, CPQG | 15 chassis quality control checkpoints |
| **Final Scores** | F10–F100, FPQG | 11 final assembly checkpoints |
| **Residual Torque** | Res. Torque | Torque verification score |
| **Quality Control** | 1.1–5.3 | 11 control method ratings (see below) |
| **Q' Control Detail** | CVT, SHOWER, Dynamic/UB, CC4 | 4 detailed control scores |
| **Control Rating** | MFG, Quality, Plant | Auto-calculated aggregate ratings |
| **Guaranteed Quality** | Workstation, MFG, Plant | Status indicators (OK/NG) |

### Quality Control Methods (1.1–5.3)

| Code | Name | Description |
|------|------|-------------|
| 1.1 | Frequency Control | Periodic frequency-based checking |
| 1.2 | Visual Control | Visual inspection |
| 1.3 | Periodic Audit | Periodic audit / process monitoring |
| 1.4 | Human Control | 100% human control without tracking |
| 3.1 | SAE Alert | SAE (Error Proofing) alert system |
| 3.2 | Frequency Measure | Frequency control with measurements |
| 3.3 | Manual Tool | 100% manual control with tool |
| 3.4 | Human Tracking | 100% human control with tracking |
| 5.1 | Auto Control | 100% automatic control |
| 5.2 | Impossibility | Impossibility of assembly or subsequent machining |
| 5.3 | SAE Prohibition | SAE (Error Proofing) prohibition |

### Inline Editing

- **Weekly recurrence** — Click any W-1 to W-6 cell to edit counts directly
- **Scores** — Click any score cell (Trim/Chassis/Final/QControl) to enter values
- **Defect Rating** — Dropdown selector (1/3/5)
- **Row edit mode** — Click pencil icon to edit Source, Station, Designation, Concern, Action, Resp, Target
- **Delete** — Click trash icon to remove a concern

### Filtering

- **Search** — Filter by concern text, station, or S.No
- **Source filter** — DVX, ER3, ER4, Field, SCA
- **Designation filter** — Trim, Chassis, Final
- **Rating filter** — 1, 3, or 5
- **Status filter** — OK (all OK) or NG (any NG)
- **Dashboard click** — Click dashboard cards to auto-filter

---

## Repeats Tab — Defect Processing Pipeline

The Repeats tab executes the core **data processing pipeline** for updating the QA Matrix with new defect data.

### Pipeline Execution Workflow

```
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│  1. FETCH    │───▶│  2. PREPROCESS   │───▶│  3. FEATURE       │
│  Raw Data    │    │  Clean & Parse   │    │  EXTRACTION       │
└──────────────┘    └──────────────────┘    └───────────────────┘
                                                     │
                                                     ▼
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│  6. POST-    │◀───│  5. PAIRING      │◀───│  4. SENTIMENT     │
│  PROCESSING  │    │  Match → Concern │    │  ANALYSIS (AI)    │
└──────────────┘    └──────────────────┘    └───────────────────┘
       │
       ▼
┌──────────────┐    ┌──────────────────┐
│  7. APPLY &  │───▶│  8. VISUALIZE    │
│  AGGREGATE   │    │  Diff & Status   │
└──────────────┘    └──────────────────┘
```

### Step-by-Step Breakdown

#### Step 1: Data Fetching (Ingestion)
- **Trigger**: User clicks "Start Pairing"
- **Operation**: Fetches all records from `final_defect` table
- **Python equivalent**: `df = pd.read_sql("SELECT * FROM final_defect", conn)`

#### Step 2: Data Preprocessing
- **Operation**: Clean raw defect entries, normalize text fields, handle missing values
- **Transforms**: Strip whitespace, standardize casing, fill empty fields with defaults
- **Python equivalent**: `df['description'] = df['description'].str.strip().str.lower()`

#### Step 3: Feature Extraction
- **Operation**: Extract structured features from each defect for AI consumption
- **Features**: `locationDetails`, `defectDescription`, `defectDescriptionDetails`, `gravity`, `quantity`
- **Python equivalent**: `features = df[['location', 'description', 'details', 'gravity', 'quantity']]`

#### Step 4: Sentiment Analysis & Semantic Understanding (AI)
- **Operation**: Send defect descriptions to Google Gemini AI for deep semantic analysis
- **Process**: The AI understands the *meaning* of each defect — not just keywords
- **Example**: "Rayure panneau" (scratch on panel) is semantically matched to "Surface damage on body exterior"
- **Batching**: Processed in batches of 200 defects to avoid token limits
- **Python equivalent**: 
  ```python
  from transformers import pipeline
  nlp = pipeline('text-classification', model='gemini-flash')
  embeddings = nlp(defect_descriptions)
  ```

#### Step 5: Pairing / Matching
- **Operation**: Match each defect to the most semantically similar QA concern
- **Output**: Each match contains `{ defectIndex, matchedSNo, confidence, reason }`
- **Confidence threshold**: Matches with confidence < 0.3 are treated as unmatched
- **Python equivalent**:
  ```python
  from sklearn.metrics.pairwise import cosine_similarity
  similarity_matrix = cosine_similarity(defect_embeddings, concern_embeddings)
  best_matches = similarity_matrix.argmax(axis=1)
  ```

#### Step 6: Post-Processing & Manual Review
- **Unpair** — Remove incorrect AI matches (`df.drop(index)`)
- **Reassign** — Move a defect to a different concern (`df.loc[idx, 'concern'] = new_sno`)
- **Manual Pair** — Force-pair an unmatched defect (`df.at[idx, 'matched'] = True`)
- **Add New Concern** — Create a new QA matrix entry from an unmatched defect (`df.append(new_row)`)

#### Step 7: Aggregation & Apply
- **Operation**: Sum matched defect quantities per concern, update W-1 recurrence column
- **Recalculation**: Triggers full status recalculation (MFG/Quality/Plant ratings, OK/NG statuses)
- **Python equivalent**:
  ```python
  recurrence_updates = matched_df.groupby('matched_sno')['quantity'].sum()
  qa_matrix['W-1'] = qa_matrix['sNo'].map(recurrence_updates).fillna(0)
  ```

#### Step 8: Visualization & Diff
- **View Changes** — See a before/after diff of recurrence counts and status changes
- **Undo** — Revert all applied changes (rollback to pre-pipeline state)

### Alternative Data Ingestion Methods

- **File Upload** — Upload a DVX/Repeat Issues Excel file directly (bypasses database fetch)
- **Google Sheets Link** — Fetch data from a public Google Sheets URL via proxy

### Unique Defects View (Exploratory Data Analysis)

A collapsible EDA section showing all unique defect types:
- **Grouping**: `df.groupby(['defect_code', 'description']).agg({'quantity': 'sum'})`
- **Sorting**: By total quantity (descending)
- **Export**: Download grouped results as Excel

---

## Defect Data Page

Manage raw defect data — the **data ingestion & storage layer** of the pipeline.

### Sources (Data Separation)
- **DVX** — DVX inspection defects
- **SCA** — SCA audit defects  
- **YARD** — Yard inspection defects

Each source is stored and managed independently (`df.groupby('source')`).

### Features per Source
- **Upload CSV/Excel** — Parse and preview before uploading (preprocessing step)
- **Preview & Edit** — Review parsed data, edit cells, delete rows before confirming upload (data cleaning)
- **Review** — View all stored data for a source
- **Clear All** — Delete all data for a source

### Delete Data (Password Protected)
- Click the red **Delete Data** button in the header
- Select target: DVX, SCA, YARD, Final Defect Table, or All
- Enter password to confirm deletion
- Data is permanently removed from the database

### Data Flow (ETL Pipeline)

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Raw File   │────▶│  PREPROCESSING   │────▶│  defect_data    │
│  (CSV/XLSX) │     │  Parse, Clean,   │     │  (Raw Storage)  │
│             │     │  Validate        │     │                 │
└─────────────┘     └──────────────────┘     └─────────────────┘
                                                      │
                                                      ▼
                                              ┌─────────────────┐
                                              │  final_defect   │
                                              │  (Consolidated) │
                                              │  Used by AI     │
                                              │  Pairing Engine │
                                              └─────────────────┘
```

---

## Data Schema

### QA Matrix Entry

```typescript
{
  sNo: number;              // Serial number (unique ID)
  source: string;            // DVX, ER3, ER4, FIELD, SCA
  operationStation: string;  // Station code
  designation: string;       // TRIM, CHASSIS, or FINAL
  concern: string;           // Defect description
  defectCode: string;        // Defect classification code
  defectLocationCode: string; // Location classification code
  defectRating: 1 | 3 | 5;  // Severity rating
  weeklyRecurrence: number[]; // [W-6, W-5, W-4, W-3, W-2, W-1]
  recurrence: number;        // Sum of weekly recurrence
  recurrenceCountPlusDefect: number; // recurrence + defectRating
  
  // Score sections (each value: number | null)
  trim: { T10..T100, TPQG }       // 11 trim scores
  chassis: { C10..C80, P10..P30, RSub, TS, CPQG } // 15 chassis scores
  final: { F10..F100, FPQG, ResidualTorque }       // 12 final scores
  qControl: { 11 control method scores }
  qControlDetail: { CVT, SHOWER, DynamicUB, CC4 }
  
  // Auto-calculated
  controlRating: { MFG, Quality, Plant }
  guaranteedQuality: { Workstation, MFG, Plant }
  workstationStatus: 'OK' | 'NG'
  mfgStatus: 'OK' | 'NG'
  plantStatus: 'OK' | 'NG'
  
  // Action tracking
  mfgAction: string;
  resp: string;
  target: string;
}
```

---

## Status Calculation Logic

Statuses are **auto-calculated** whenever scores or recurrence values change (similar to `df.apply(calculate_status, axis=1)`):

### MFG Rating
```python
# MFG Rating = Sum of all non-null values in (Trim + Chassis + Final scores)
#              (excluding Residual Torque)
mfg_rating = df[trim_cols + chassis_cols + final_cols].sum(axis=1, skipna=True)
```

### Quality Rating
```python
# Quality Rating = Sum of all non-null Quality Control scores (1.1 to 5.3)
quality_rating = df[qcontrol_cols].sum(axis=1, skipna=True)
```

### Plant Rating
```python
# Plant Rating = Sum of (Residual Torque + all QControl scores + all QControl Detail scores)
plant_rating = df[['ResidualTorque'] + qcontrol_cols + qcontrol_detail_cols].sum(axis=1, skipna=True)
```

### Status Rules
```python
# Vectorized status calculation
df['workstation_status'] = np.where(
    (df['recurrence'] == 0) & (df['mfg_rating'] >= df['defect_rating']),
    'OK', 'NG'
)
df['mfg_status'] = np.where(df['mfg_rating'] >= df['defect_rating'], 'OK', 'NG')
df['plant_status'] = np.where(df['plant_rating'] >= df['defect_rating'], 'OK', 'NG')
```

| Status | Condition |
|--------|-----------|
| **Workstation OK** | No recurrence (all weeks = 0) AND MFG Rating ≥ Defect Rating |
| **Workstation NG** | Any recurrence > 0 OR MFG Rating < Defect Rating |
| **MFG OK** | MFG Rating ≥ Defect Rating |
| **MFG NG** | MFG Rating < Defect Rating |
| **Plant OK** | Plant Rating ≥ Defect Rating |
| **Plant NG** | Plant Rating < Defect Rating |

---

## Import & Export

### QA Matrix Import (Excel/CSV)

Upload a file with the following column order:

| Col | Field |
|-----|-------|
| 1 | S. No |
| 2 | Source |
| 3 | Operation / Station |
| 4 | Designation |
| 5 | Concern Description [Mode of failure] |
| 6 | Defect Code |
| 7 | Location Code |
| 8 | Defect Rating (1/3/5) |
| 9–14 | W-6 to W-1 (Recurrence) |
| 15 | Recurrence Count + Defect Rating |
| 16–26 | T10–T100, TPQG |
| 27–41 | C10–C80, P10–P30, RSub, TS, CPQG |
| 42–52 | F10–F100, FPQG |
| 53 | Residual Torque |
| 54–64 | Quality Control 1.1–5.3 |
| 65–68 | CVT, SHOWER, Dynamic/UB, CC4 |
| 69–71 | Control Rating (MFG, Quality, Plant) |
| 72–74 | Guaranteed Quality (WS, MFG, Plant) |
| 75 | MFG Action |
| 76 | Responsible |
| 77 | Target |

### QA Matrix Export

- **Export Excel** — Downloads `.xlsx` file with all visible (filtered) data
- **Export CSV** — Downloads `.csv` file with all visible (filtered) data

Both exports use the same column format as imports, so exported files can be re-imported.

---

## AI Sentiment Analysis & Semantic Matching

The system uses an AI model (Google Gemini) to perform **sentiment analysis** and **semantic matching** of defects to QA concerns.

### NLP Pipeline

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Input Defects  │────▶│  TOKENIZATION &      │────▶│  SEMANTIC       │
│  (Raw Text)     │     │  EMBEDDING           │     │  UNDERSTANDING  │
│                 │     │  (Gemini NLP Engine)  │     │  (Context-aware)│
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Matched Pairs  │◀────│  CONFIDENCE          │◀────│  SIMILARITY     │
│  + Scores       │     │  SCORING (0–1)       │     │  MATCHING       │
│                 │     │  + Reasoning         │     │  (vs QA Matrix) │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
```

### How It Works

1. **Tokenization**: Defect descriptions are processed by the Gemini NLP engine
2. **Semantic Embedding**: The AI creates internal representations of meaning — not surface-level keywords
3. **Similarity Matching**: Each defect embedding is compared against all QA concern embeddings
4. **Confidence Scoring**: Each match receives a confidence score (0–1) — similar to cosine similarity
5. **Reasoning**: The AI provides a human-readable explanation for each match/non-match
6. **Threshold Filtering**: Matches with confidence < 0.3 are classified as unmatched
7. **Batching**: Processed in batches of 200 defects for efficiency (avoiding token limits)

### Python Equivalent

```python
from transformers import AutoModel, AutoTokenizer
import torch
from sklearn.metrics.pairwise import cosine_similarity

# Load model
model = AutoModel.from_pretrained('google/gemini-flash')
tokenizer = AutoTokenizer.from_pretrained('google/gemini-flash')

# Encode defects and concerns
defect_embeddings = model.encode(defect_descriptions)
concern_embeddings = model.encode(concern_descriptions)

# Compute similarity matrix
similarity = cosine_similarity(defect_embeddings, concern_embeddings)

# Get best matches with confidence
best_matches = similarity.argmax(axis=1)
confidence_scores = similarity.max(axis=1)

# Filter low-confidence matches
matched = confidence_scores >= 0.3
results = pd.DataFrame({
    'defect_index': range(len(defects)),
    'matched_sno': np.where(matched, concerns[best_matches]['sNo'], None),
    'confidence': confidence_scores
})
```

### Backend Function

The `match-defects` edge function handles the AI communication:
- Uses the Lovable AI Gateway (`ai.gateway.lovable.dev`)
- Employs function calling for structured JSON output
- Handles rate limiting (429) and credit depletion (402) gracefully
- Processes defects in parallel batches for performance

---

## Database

### Tables (Data Storage Layer)

| Table | Purpose | Python Equivalent |
|-------|---------|-------------------|
| `qa_matrix_entries` | All QA Matrix concerns with scores, statuses, and metadata | `qa_matrix_df` — main DataFrame |
| `defect_data` | Raw uploaded defect data with source and timestamp | `raw_defects_df` — raw upload history |
| `final_defect` | Consolidated defect records for AI pairing | `clean_defects_df` — preprocessed & ready for NLP |

### Auto-Save (Incremental Updates)

All changes to the QA Matrix table are automatically saved to the database:
- **Change Detection**: JSON diff comparison (`df.compare(df_original)`)
- **Upsert Strategy**: Only modified rows are saved (by `s_no` primary key)
- **Batch Processing**: Supports bulk saves for imports and pipeline updates

### Edge Functions (Backend Microservices)

| Function | Purpose | Python Equivalent |
|----------|---------|-------------------|
| `match-defects` | AI-powered semantic matching of defects to QA concerns | `sklearn` similarity pipeline |
| `delete-defects` | Password-protected deletion of defect data | `df.drop()` with auth |
| `fetch-spreadsheet` | Proxy for fetching external spreadsheet URLs | `requests.get()` proxy |

---

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + shadcn/ui components
- **Database**: Lovable Cloud (PostgreSQL) — equivalent to `SQLAlchemy + PostgreSQL`
- **AI/NLP**: Google Gemini via Lovable AI Gateway — equivalent to `transformers + sklearn`
- **File Parsing**: SheetJS (xlsx) — equivalent to `pandas.read_excel()` / `openpyxl`
- **State Management**: React hooks + custom `useQAMatrixDB` hook — equivalent to `pandas DataFrame` in-memory
- **Charts**: Recharts — equivalent to `matplotlib` / `plotly`
