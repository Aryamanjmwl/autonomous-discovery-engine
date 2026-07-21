# Temporal Visual Demo Evidence

This guide walks through ADE's generated local demo sequence workflow, from deterministic
observations to a validated temporal evidence package and connected ADE Studio review.
Everything runs locally in the ADE Technical Preview. The generator downloads nothing and
does not change the default image-folder analysis workflow.

## What the Demo Contains

Run `scripts/create_temporal_demo_data.py` to create three synthetic sequences under
`data/raw/temporal_demo/`:

- `scene_revisit_shift`: a generated rectangular object changes position slightly across
  three observations.
- `plant_growth_like`: a generated circular shape changes size across three observations.
  The name describes a visual pattern only; it is not a biological finding.
- `inspection_damage_like`: a generated local mark appears and increases in later
  observations. The name is illustrative and does not establish real damage.

Each sequence contains three deterministic 64×64 PNG files and a canonical `manifest.json`.
The manifest records stable observation IDs, sequence indexes, synthetic scene/entity IDs,
image dimensions, and metadata identifying the content as a generated local demo sequence.

Synthetic local data keeps the workflow reproducible, small, inspectable, and independent
of external datasets, network services, coordinate systems, or cloud infrastructure.

## Evidence Workflow

```text
Generated local observations
→ temporal manifest
→ temporal CLI analysis
→ immutable temporal artifact
→ temporal JSON/Markdown/HTML report
→ ADE Studio review
```

ADE produces:

- a temporal manifest describing the ordered observation sequence;
- an immutable content-addressed temporal result artifact with integrity metadata;
- a deterministic JSON report and a cautious Markdown review report;
- an optional static HTML rendering of the validated JSON report;
- a temporal report that connected ADE Studio can display after validating both the report
  and its referenced artifact.

## Run the Demo in PowerShell

Run these commands from the repository root. Use a new report filename if you repeat the
analysis because temporal artifacts are immutable.

### 1. Generate the Local Sequences

```powershell
python scripts/create_temporal_demo_data.py
```

### 2. Select and Validate a Manifest

```powershell
$manifest = "data/raw/temporal_demo/scene_revisit_shift/manifest.json"
$report = "data/reports/temporal_demo_scene.md"
$reportJson = "data/reports/temporal_demo_scene.json"
$reportHtml = "data/reports/temporal_demo_scene.html"

python -m ade.cli --validate-temporal-manifest $manifest
```

### 3. Run Temporal Analysis

```powershell
python -m ade.cli --temporal-manifest $manifest --temporal-output $report `
  --temporal-strategy adjacent_difference --temporal-patch-size 16
```

The command publishes the immutable artifact first and then writes the Markdown and JSON
reports. Patch evidence is included because `--temporal-patch-size 16` was explicitly set.

### 4. Validate the Artifact and Report

```powershell
$artifactPath = (Get-Content $reportJson -Raw | ConvertFrom-Json).artifact_provenance.artifact_path

python -m ade.cli --validate-temporal-artifact $artifactPath
python -m ade.cli --validate-temporal-report $reportJson
```

### 5. Export Temporal HTML

```powershell
python -m ade.cli --export-temporal-html-report $reportJson --temporal-output $reportHtml
```

Open `data/reports/temporal_demo_scene.html` locally to review the sequence summary,
candidate change events, real patch coordinates, warnings, and limitations.

### 6. Run the End-to-End Smoke Verifier

```powershell
python scripts/verify_temporal_demo.py
```

The verifier regenerates the deterministic demo, validates one manifest, analyzes one
sequence in a temporary output directory, validates its artifact and report, and exports
HTML. Temporary evidence is removed when verification finishes.

## Review the Report in ADE Studio

The JSON report must remain in `data/reports/` with its referenced artifact available.
Start the existing local Studio backend in the first PowerShell terminal:

```powershell
pip install -e ".[studio]"
python -m ade.studio.api --host 127.0.0.1 --port 8765
```

Start the frontend in a second PowerShell terminal:

```powershell
cd apps/studio/frontend
npm install
npm run typecheck
npm run build
npm run dev
```

Open the local address printed by the frontend. In connected mode, select
`temporal_demo_scene.json` on the Reports screen. ADE Studio displays it only if the
temporal report and referenced artifact both validate. The Findings screen then presents
the real candidate change events and computed patch evidence from that report.

## Interpreting the Output

A high change score is a review-prioritization signal relative to this synthetic observation
sequence. A candidate temporal change may be described cautiously as possible
movement/growth/damage/change, but the score does not identify a cause or establish a
verified real-world event.

Lighting, viewpoint, scale, alignment, and content differences can affect temporal scores.
This demo is not a continuous observation service, does not connect to remote imagery, and
does not register observations to geographic coordinates. Every candidate change event
requires human review before interpretation.

## Optional Real Screenshots for README or Portfolio

After running the workflow, a developer may manually capture:

1. the generated `data/raw/temporal_demo/scene_revisit_shift/` folder;
2. the real `temporal_demo_scene.html` report;
3. the connected Studio Reports screen showing the temporal visual report;
4. the connected Studio Findings screen showing candidate change events.

Do not use mock screenshots. Do not fabricate report values, event rows, artifact paths, or
Studio states. Capture only real local outputs produced by the commands above.
