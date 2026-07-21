# Temporal Visual Change Detection

Stages 5A and 5B provide an explicit, local, offline workflow for comparing repeated image
observations of the same scene or entity. It does not run during normal image-folder
analysis. A caller must supply a versioned JSON observation manifest and explicitly
invoke the temporal library API or CLI.

## Observation manifest

A manifest declares `schema_version`, dataset name/version/root, a sequence ID,
optional scene/entity IDs and metadata, and at least two observations. Every
observation has a unique ID and canonical relative source path, and uses exactly one
ordering system across the sequence: timezone-aware ISO-8601 timestamps or
non-negative unique sequence indexes. Optional fields include scene/entity IDs,
metadata, image dimensions, SHA-256, and a mask path.

Validation rejects parent traversal and paths outside the dataset root. Strict mode
requires every image and declared mask to exist. Serialization orders observations
deterministically. Image dimensions are measured during analysis.

Minimal sequence-index manifest:

```json
{
  "schema_version": 1,
  "dataset_name": "inspection-revisits",
  "dataset_version": "1",
  "dataset_root": "./inspection-data",
  "sequence_id": "asset-17",
  "scene_id": "bay-a",
  "entity_id": "asset-17",
  "observations": [
    {"observation_id": "o0", "source_path": "frames/0.png", "timestamp": null,
     "sequence_index": 0, "entity_id": null, "scene_id": null, "metadata": {},
     "width": null, "height": null, "image_sha256": null, "mask_path": null},
    {"observation_id": "o1", "source_path": "frames/1.png", "timestamp": null,
     "sequence_index": 1, "entity_id": null, "scene_id": null, "metadata": {},
     "width": null, "height": null, "image_sha256": null, "mask_path": null}
  ],
  "metadata": {}
}
```

## Explicit CLI Workflow

```powershell
python -m ade.cli --validate-temporal-manifest data/temporal/manifest.json
python -m ade.cli --temporal-manifest data/temporal/manifest.json `
  --temporal-output data/reports/temporal_report.md `
  --temporal-strategy adjacent_difference
python -m ade.cli --validate-temporal-artifact data/reports/temporal_report_artifacts/<id>
python -m ade.cli --validate-temporal-report data/reports/temporal_report.json
python -m ade.cli --export-temporal-html-report data/reports/temporal_report.json `
  --temporal-output data/reports/temporal_report.html
```

`baseline_difference` is also available. `--temporal-patch-size` explicitly enables
computed patch evidence; without it, reports contain no patch evidence. The analysis
publishes and validates an immutable content-addressed result artifact before writing
Markdown and deterministic JSON. HTML export displays metadata and evidence only.

## Scoring, evidence, and persistence

`analyze_temporal_change` reuses ADE's deterministic statistical visual features.
`adjacent_difference` compares consecutive observations; `baseline_difference`
compares every later observation with the first. Normalized Euclidean feature
distance ranks candidate change events. Optional fixed-size patch comparison provides
real computed coordinates, pair IDs, scale, and scores for matching grids. No
synthetic heatmap is emitted.

The summary includes observation count/range, maximum score, mean adjacent score,
strongest pair, ranked events, warnings, and alignment limitations. Outputs are
review-prioritization signals: candidate temporal changes and possible
movement/growth/damage/change that require human review.

Results publish as immutable, content-addressed directories containing canonical
JSON and an integrity manifest. Sibling temporary publication and validation enforce
exact files, containment, size, SHA-256, schema, and content identity. Pickle is not
used.

Suitable offline datasets include satellite scene revisits, plant growth sequences,
and industrial inspection sequences. This stage has no live satellite feeds,
streaming ingestion, cloud processing, geospatial registration, scientific
confirmation, or automatic live monitoring. Lighting, viewpoint, scale, alignment,
and seasonal differences can all produce high scores.

## ADE Studio Discovery

Stage 5C lets connected ADE Studio discover these reports from the configured local report
directory. A report is shown only when its temporal schema validates and its referenced
content-addressed artifact passes integrity validation. Studio displays the observation
sequence, candidate change events, optional real patch evidence, warnings, and provenance.
It does not add live monitoring, geospatial registration, or scientific confirmation.

## Deterministic Generated Demo Workflow

The Stage 5D generator creates three tiny synthetic local sequences without downloads:
`scene_revisit_shift`, `plant_growth_like`, and `inspection_damage_like`. Their names
describe generated shapes only; they do not establish real movement, growth, or damage.

Run the complete workflow from the repository root in PowerShell:

```powershell
python scripts/create_temporal_demo_data.py

$manifest = "data/raw/temporal_demo/scene_revisit_shift/manifest.json"
$report = "data/reports/temporal_demo_scene.md"
$reportJson = "data/reports/temporal_demo_scene.json"
$reportHtml = "data/reports/temporal_demo_scene.html"

python -m ade.cli --validate-temporal-manifest $manifest
python -m ade.cli --temporal-manifest $manifest --temporal-output $report `
  --temporal-strategy adjacent_difference --temporal-patch-size 16

$artifactPath = (Get-Content $reportJson -Raw | ConvertFrom-Json).artifact_provenance.artifact_path
python -m ade.cli --validate-temporal-artifact $artifactPath
python -m ade.cli --validate-temporal-report $reportJson
python -m ade.cli --export-temporal-html-report $reportJson --temporal-output $reportHtml
python scripts/verify_temporal_demo.py
```

The report and immutable artifact can then be viewed in connected ADE Studio after starting
its local backend and frontend. Use a new report name for another immutable demo run. The
workflow has no live feed, satellite API, cloud processing, geospatial registration, or
scientific confirmation. Every candidate change event is a review-prioritization signal and
requires human review.
