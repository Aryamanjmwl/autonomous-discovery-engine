# ADE Report Schema

ADE reports are written as Markdown for review and JSON for downstream tooling.
The schema is intended to be stable enough for private-alpha workflows while
remaining pre-1.0 and subject to additive changes.

All discoveries are candidate findings and require human review.

## Top-Level Fields

Common top-level JSON fields include:

- `project`: project or report title metadata.
- `run_id`: stable ID for the analysis run.
- `run_metadata`: timestamp, input path, output paths, counts, pipeline version, and review flags.
- `dataset_summary`: high-level dataset and patch counts.
- `dataset_profile`: input validation results for the current image-folder adapter.
- `configuration`: selected runtime settings when included by the report generator.
- `feature_summary`: lightweight representation strategy details when included.
- `candidate_anomalies`: ranked candidate anomaly records.
- `candidate_concepts` or `candidate_unknown_concepts`: grouped candidate concept records.
- `evidence_summary`: supporting examples, near matches, confidence context, and warnings.
- `confidence_scores`: bounded review-prioritization signals when available.
- `hypotheses`: cautious template-based hypotheses.
- `limitations`: current limitations and human-review requirements.
- `feedback`: local feedback metadata when feedback support is enabled.
- `artifact_manifest`: optional generated artifact references when present.

The exact set of fields may grow through additive changes during the private
alpha. Existing fields should not be renamed without a compatibility note.

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

The current implementation profiles image folders only. Future adapters should
add their own profiles without claiming support before implementation exists.

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

## Backward Compatibility

During the private alpha:

- Additive fields are acceptable.
- Stable IDs (`anomaly_id`, `concept_id`) should be present on newly generated reports.
- Older reports without these IDs may validate with warnings.
- Consumers should ignore unknown fields unless a future schema version states otherwise.
