# ADE Tabular CSV Support

ADE includes an initial CSV adapter for lightweight row-level discovery. This
is the first non-image modality in the project. It keeps the same cautious ADE
workflow: profile the input, build deterministic representations, rank
candidate anomalies, group evidence into candidate concepts, and write
reviewable Markdown/JSON reports.

## Supported Workflow

Run ADE on a CSV file:

```bash
python -m ade.cli --input data/raw/example.csv --output data/reports/tabular_report.md
```

The CLI infers tabular mode from the `.csv` input path. Existing image-folder
commands are unchanged.

## What the Current CSV Adapter Does

- Validates that the input exists, is a file, and has a `.csv` extension
- Reads UTF-8 CSV files with a header row
- Counts rows and columns
- Detects numeric and categorical/text columns
- Tracks per-column missing values
- Records simple per-column metadata
- Emits row-level records with stable ids such as `row-000001`

## Feature Strategy

The current tabular feature engine is intentionally small and deterministic:

- Numeric values are centered and scaled with safe constant-column handling
- Missing-value indicators are included
- Categorical values use simple frequency/rarity signals
- Each row includes a completeness ratio
- NaN and infinite values are replaced with safe finite values

No supervised learning, deep learning, or complex feature engineering is used
in this foundation branch.

## Report Output

Tabular reports include:

- Modality: `tabular`
- Row and column counts
- Numeric and categorical column counts
- Missing-value summary
- Feature extraction metadata
- Top candidate row-level findings
- Candidate tabular concept groups
- Limitations and human-review disclaimer

The JSON report keeps the existing ADE report shape where practical, including
`candidate_anomalies`, `candidate_unknown_concepts`, `run_metadata`, and run
history index entries. This keeps run listing and the local dashboard usable
for tabular runs.

## Limitations

- CSV files only for now
- Row-level discovery only
- No time-series semantics
- No relational/database ingestion
- No supervised learning
- No privacy, security, or compliance guarantees
- Scores are ranking signals, not proof of significance

All candidate row anomalies and candidate tabular concepts require human
review before operational, scientific, commercial, financial, or clinical use.
