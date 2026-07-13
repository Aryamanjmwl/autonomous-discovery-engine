# ADE Report Schema

ADE reports are written as Markdown for review and JSON for downstream tooling.
The schema is intended to be stable enough for technical preview workflows while
remaining pre-1.0 and subject to additive changes.

All discoveries are candidate findings and require human review.

## Top-Level Fields

Common top-level JSON fields include:

- `project`: project or report title metadata.
- `run_id`: stable ID for the analysis run.
- `run_metadata`: timestamp, input path, output paths, counts, pipeline version, and review flags.
- `dataset_summary`: high-level dataset and patch counts.
- `dataset_profile`: input validation/profile results for the current adapter.
- `configuration`: selected runtime settings when included by the report generator.
- `feature_summary`: lightweight representation strategy details when included.
- `candidate_anomalies`: ranked candidate anomaly records.
- `candidate_concepts` or `candidate_unknown_concepts`: grouped candidate concept records.
- `evidence_summary`: supporting examples, near matches, confidence context, and warnings.
- `confidence_scores`: bounded review-prioritization signals when available.
- `review_memory_summary`: optional local feedback-memory counts when enabled.
- `hypotheses`: cautious template-based hypotheses.
- `limitations`: current limitations and human-review requirements.
- `feedback`: local feedback metadata when feedback support is enabled.
- `artifact_manifest`: optional generated artifact references when present.

The exact set of fields may grow through additive changes during the private
preview. Existing fields should not be renamed without a compatibility note.

## Candidate Anomalies

Each newly generated candidate anomaly should include:

- `anomaly_id`: deterministic report-level ID such as `anomaly_001`.
- `rank`: report rank.
- `score` or `novelty_score`: review-prioritization score.
- `patch_id` or source item reference.
- `image_path` or source path metadata when available.
- `coordinates`: patch location when available.
- `score_breakdown`: scoring components when available.
- `preview_path`: relative asset path when a preview image was generated.
- `reason`: concise factual explanation when available.
- `review_memory_signal`: optional feedback-informed ranking hint when prior
  local feedback matches the candidate target.

`anomaly_id` is the preferred feedback target ID for `--target-type anomaly`.
Older reports may only include legacy `id` fields; validators should warn rather
than fail solely because a legacy report lacks the newer ID.

## Candidate Concepts

Each newly generated candidate concept should include:

- `concept_id`: deterministic report-level ID such as `concept_001`.
- `item_count` or support count.
- `average_anomaly_score` or equivalent score summary.
- `representative_item` or representative evidence.
- `summary`: cautious concept summary.
- `evidence_items`: supporting candidate anomalies or patches.
- `confidence_score` and component breakdowns when available.
- `nearest_neighbors` or near-match evidence when visual memory is enabled.
- `review_memory_signal`: optional feedback-informed ranking hint when prior
  local feedback matches the candidate concept.

`concept_id` is the preferred feedback target ID for `--target-type concept`.

## Dataset Profile

`dataset_profile` describes the input before analysis:

- input path and input type
- total files
- supported, unsupported, unreadable, and valid image counts
- image size range and unique image sizes
- estimated patch count
- warnings
- validity flag

The current implementation profiles image folders, tabular CSV files, and
timestamped CSV files. Tabular reports may include `tabular_profile`;
time-series reports may include `timeseries_profile`. Future adapters should add
their own profiles without claiming support before implementation exists.

## Tabular and Time-Series Reports

Tabular reports use `modality: "tabular"` and include row-level
`candidate_anomalies`, candidate tabular concepts, `tabular_profile`, backend
metadata, and run metadata. Time-series reports use `modality: "timeseries"` and
include timestamped candidate findings, candidate time-series concepts,
`timeseries_profile`, backend metadata, and run metadata.

Both report types are lightweight adapter-foundation reports. Their candidate
anomalies and possible patterns require human review. They do not imply
supervised learning, production personalization, forecasting, streaming, live
sensor ingestion, or database-backed workflows.

## Evidence and Confidence Fields

Evidence fields should be factual and conservative. They may include preview
asset paths, patch coordinates, score breakdowns, near visual matches, concept
consistency, source diversity, support counts, confidence components, notes, and
warnings.

Confidence values are review-prioritization aids. They are not guarantees that a
candidate anomaly or candidate concept is meaningful.

## Feedback Metadata

Reports can advertise local feedback support through fields such as:

- `feedback_supported`
- `supported_feedback_labels`
- `feedback_store_path`

Feedback records are stored separately as local JSONL artifacts and should not be
treated as production audit records.

## Review Memory Fields

`review_memory_summary` is an additive report object derived from the local
feedback JSONL store. It may include total feedback count, label counts, label
counts by target type, configured positive/negative/neutral labels, and an
explanation that the data is review-informed ranking support.

Candidate-level `review_memory_signal` objects may include:

- `priority_delta`
- `matched_feedback_count`
- `positive_feedback_count`
- `negative_feedback_count`
- `known_pattern_count`
- `duplicate_count`
- `needs_more_data_count`
- `notes`
- `explanation`

These fields are deterministic summaries of human-review feedback. They do not
prove that a candidate anomaly or candidate concept is meaningful and do not
replace human review.

## Backward Compatibility

During the technical preview:

- Additive fields are acceptable.
- Stable IDs (`anomaly_id`, `concept_id`) should be present on newly generated reports.
- Older reports without these IDs may validate with warnings.
- Consumers should ignore unknown fields unless a future schema version states otherwise.
