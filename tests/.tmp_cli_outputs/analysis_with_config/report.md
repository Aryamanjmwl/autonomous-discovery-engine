# ADE Discovery Report

ADE Discovery Report for exploratory review. Findings below are candidate patterns and require human review.

**Run ID:** `ade_20260619_121633_1c4d11`

## Dataset Summary

- Input directory: `tests\.tmp_cli_outputs\analysis_with_config\images`
- Number of input images: 6
- Number of extracted patches: 24
- Number of candidate anomalies: 2
- Number of candidate unknown concepts: 2

## Top Candidate Anomalies

| Rank | Preview | Source | Coordinates | Novelty score |
| --- | --- | --- | --- | ---: |
| 1 | ![candidate anomaly 1](preview_assets/anomaly_0001.png) | `tests\.tmp_cli_outputs\analysis_with_config\images\demo_image_05.png` | `(128, 0, 128, 128)` | 0.3098 |
| 2 | ![candidate anomaly 2](preview_assets/anomaly_0002.png) | `tests\.tmp_cli_outputs\analysis_with_config\images\demo_image_02.png` | `(0, 128, 128, 128)` | 0.2751 |

## Candidate Unknown Concepts

### concept-001

- Supporting patches: 1
- Average novelty: 0.3098
- Cluster consistency: 1.0000
- Confidence score: 0.7600

Evidence summary for this possible pattern:
- ![concept-001 example 1](preview_assets/concept_001_example_001.png) `tests\.tmp_cli_outputs\analysis_with_config\images\demo_image_05.png` at (128, 0, 128, 128); novelty score 0.3098

Cautious hypothesis:

concept-001 may represent a candidate unknown concept because 1 supporting patch(es) show elevated novelty relative to this dataset. This is a hypothesis for expert review, not a validated discovery.

### concept-002

- Supporting patches: 1
- Average novelty: 0.2751
- Cluster consistency: 1.0000
- Confidence score: 0.7041

Evidence summary for this possible pattern:
- ![concept-002 example 1](preview_assets/concept_002_example_001.png) `tests\.tmp_cli_outputs\analysis_with_config\images\demo_image_02.png` at (0, 128, 128, 128); novelty score 0.2751

Cautious hypothesis:

concept-002 may represent a candidate unknown concept because 1 supporting patch(es) show elevated novelty relative to this dataset. This is a hypothesis for expert review, not a validated discovery.


## Human Expert Review Required

All results are exploratory candidate findings. Candidate anomalies, candidate unknown concepts, possible relationships, and hypotheses require human expert review before any scientific, clinical, operational, commercial, or financial interpretation.
