# Temporal Visual Change Detection

Stage 5A adds an explicit, local, offline foundation for comparing repeated image
observations of the same scene or entity. It does not run during normal image-folder
analysis. A caller must supply a versioned JSON observation manifest and invoke the
temporal library API.

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
