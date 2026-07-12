# Dashboard Frontend Contract

This contract describes the local data shapes an ADE dashboard should read. The
current branch includes a local static dashboard export, but no dashboard app,
server, authentication, database, or hosted deployment is implemented.
Candidate findings require human review.

Fields marked current are produced by the current local pipeline or helper
scripts. Fields marked planned are useful for dashboard design but should not be
assumed to exist until implemented.

## Local Static Dashboard Export

Current command:

```powershell
python -m ade.cli --export-local-dashboard --output data/dashboard
```

Current outputs:

- `data/dashboard/index.html`
- `data/dashboard/dashboard_data.json`

The export reads existing local artifacts and tolerates missing report,
benchmark, run-history, and feedback files. It is a demo viewer and review aid,
not a deployed dashboard app.

## Report JSON Payload

Current source: `data/reports/<name>.json`

```json
{
  "run_id": "ade_20260709_120000_abc123",
  "run_metadata": {},
  "dataset_summary": {},
  "dataset_profile": {},
  "candidate_anomalies": [],
  "candidate_concepts": [],
  "candidate_unknown_concepts": [],
  "evidence_summary": {},
  "confidence_scores": {},
  "hypotheses": [],
  "limitations": [],
  "feedback_supported": true,
  "supported_feedback_labels": []
}
```

Dashboard readers should tolerate additive fields and should ignore unknown
fields.

## Candidate Anomalies

Current required dashboard target field:

- `anomaly_id`: stable report-level target ID such as `anomaly_001`

Common current or optional fields:

- `rank`
- `score` or `novelty_score`
- `score_breakdown`
- `patch_id`
- `image_path` or source path metadata
- `coordinates`
- `preview_path`
- `reason`
- `nearest_neighbors`
- `concept_id` if already assigned

Planned fields:

- reviewer state joined from feedback JSONL
- UI selection state
- cross-run match references

## Candidate Concepts

Current required dashboard target field:

- `concept_id`: stable report-level target ID such as `concept_001`

Reports may expose concept groups under `candidate_concepts` or the earlier
`candidate_unknown_concepts` field. Dashboard readers should support both while
preferring `candidate_concepts` when present.

Common current or optional fields:

- `item_count`
- `average_anomaly_score`
- `representative_item`
- `summary`
- `evidence_items`
- `confidence_score`
- `confidence_breakdown`
- `nearest_neighbors`
- `warnings`

Planned fields:

- reviewer state joined from feedback JSONL
- cross-run concept lineage
- adapter-specific concept renderers

## Dataset Profile

Current fields:

- `input_path`
- `input_type`
- `total_files`
- `supported_image_files`
- `unsupported_files`
- `unreadable_files`
- `valid_images`
- `image_width_min`
- `image_width_max`
- `image_height_min`
- `image_height_max`
- `unique_image_sizes`
- `estimated_patch_count`
- `warnings`
- `is_valid`

The current implementation profiles image folders. Future adapters should add
adapter-specific profile fields without claiming support before implementation.

## Evidence and Confidence Fields

Current evidence may include:

- source item path
- patch ID
- preview asset path
- rank
- anomaly score
- coordinates and scale metadata
- feature or score deviations
- near visual matches
- notes and warnings

Confidence fields are review-prioritization signals only. A dashboard should
show component breakdowns when present and keep the human review requirement
visible.

## Feedback Metadata

Current report-level metadata may include:

- `feedback_supported`
- `supported_feedback_labels`
- `feedback_store_path`

Dashboard readers should disable feedback submission if `feedback_supported` is
false or absent.

## Feedback JSONL Record Shape

Current source: `data/feedback/feedback.jsonl`

```json
{
  "feedback_id": "fb_20260709_120000_abc123",
  "created_at": "2026-07-09T12:00:00+00:00",
  "report_path": "data/reports/demo_report.json",
  "run_id": "ade_20260709_120000_abc123",
  "target_type": "anomaly",
  "target_id": "anomaly_001",
  "label": "interesting",
  "notes": "Local review note",
  "reviewer": "local"
}
```

Valid current target types are `anomaly` and `concept`. `target_id` should match
`anomaly_id` or `concept_id` from the report.

## Benchmark JSON Shape

Current source: `data/benchmarks/*.json`

```json
{
  "benchmark_id": "bench_20260709_120000_abc123",
  "generated_at": "2026-07-09T12:00:00+00:00",
  "input_path": "data/raw/demo_images",
  "config_path": "configs/default.yaml",
  "output_path": "data/benchmarks/demo_benchmark.json",
  "report_json_path": "data/reports/benchmark_report.json",
  "report_valid": true,
  "duration_seconds": 1.23,
  "command": [],
  "warnings": [],
  "metadata": {}
}
```

Benchmark values are local repeatability metadata, not public performance claims.

## Run History Shape

Current source: `data/reports/runs/index.json`

Expected dashboard fields are drawn from run metadata entries:

- `run_id`
- `generated_at`
- `input_path`
- `markdown_report_path`
- `json_report_path`
- `number_of_images`
- `number_of_patches`
- `number_of_candidate_anomalies`
- `number_of_candidate_unknown_concepts`
- `human_review_required`

Readers should handle a missing index by showing an empty state with repair
guidance.

## Validation and Error States

A dashboard should provide clear states for:

- report JSON missing
- invalid JSON
- report validation warnings
- report validation errors
- missing preview asset
- missing run index
- missing feedback store
- unsupported report schema version
- empty candidate anomaly or concept lists
- input profile warnings

Errors should be actionable and should not expose raw tracebacks in the UI.

## Current vs Planned Fields

Current:

- report JSON
- `anomaly_id`
- `concept_id`
- dataset profile
- evidence and confidence summaries
- feedback metadata
- feedback JSONL records
- benchmark JSON
- run history index
- static HTML report export

Planned:

- interactive local dashboard
- persistent dashboard state
- cross-run visual comparison
- adapter-aware non-visual review panels
- database-backed reviewer workflows
- hosted authentication and audit controls

Planned fields must not be treated as implemented until the relevant code and
tests exist.
