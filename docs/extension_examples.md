# Extension Examples

ADE is designed around small adapters and backends so new data types and review
artifacts can be added without turning the local workflow into a hosted system.
These examples are intentionally lightweight and conceptual; use the current
modules as the source of truth before implementing an extension.

## Extend the Visual Engine Safely

Visual backends must declare `VisualBackendCapabilities` and use the versioned
configuration, dataset-role, reproducibility, and artifact contracts in
`ade.visual`. Optional model files are provisioned locally and explicitly; an
execution backend must never download them implicitly. Dataset fingerprints
bind content, effective configuration, and backend identity without recording
host-specific absolute paths.

Exact NumPy search remains the reference implementation for future memory-bank
search. An accelerated backend must identify itself, serialize its parameters,
and demonstrate results within documented tolerance of exact search. The Stage
1 modules are boundary and serialization code, not an invitation to claim that
reference scoring or deep inference already works.

Reference-memory extensions should construct `ReferenceVectorRecord` values and
use `build_reference_memory`, `load_reference_memory`, and
`validate_reference_memory`. Search consumers should depend on
`ReferenceSimilaritySearch`; `ExactNumpySearch` defines ordering, distance, and
top-k conformance for future FAISS adapters. Extensions must preserve content
identity, role-leakage checks, canonical relative paths, and immutable completed
versions. They must not mutate memory directories or enable implicit downloads.

## Add A New Adapter

Start with `src/ade/adapters/base.py`. A data adapter validates an input source,
summarizes it, and yields traceable records in deterministic order. Existing
examples include `image_adapter.py`, `tabular_adapter.py`, and
`timeseries_adapter.py`.

```python
from pathlib import Path

from ade.adapters.base import DataAdapter
from ade.models import DatasetSummary


class ExampleAdapter(DataAdapter[dict[str, object]]):
    name = "example"

    def validate(self, input_path: Path) -> None:
        if not input_path.exists():
            raise FileNotFoundError(input_path)

    def summarize(self, input_path: Path) -> DatasetSummary:
        return DatasetSummary(
            input_path=input_path,
            input_type="example",
            record_count=0,
        )

    def iter_records(self, input_path: Path):
        yield from ()
```

Next step: add focused tests for validation, summary fields, deterministic
record order, and report metadata before wiring a new CLI path.

## Add A Lightweight Scoring Backend

Scoring backends live behind `src/ade/discovery/base.py` and are registered in
`src/ade/discovery/registry.py`. A backend should rank embeddings as candidate
anomalies or candidate patterns without claiming automated truth.

```python
class ExampleScorer:
    name = "example_score"

    def score(self, embeddings, max_candidates=None):
        ranked = []
        # Build CandidateAnomaly objects with transparent metadata here.
        return ranked[:max_candidates] if max_candidates is not None else ranked
```

Keep the scoring metadata explainable: include a backend name, normalized score
where useful, and reason text that helps a reviewer understand why the item was
ranked.

## Add A Custom Report Or Export Step

Report rendering interfaces live in `src/ade/reporting/base.py`, while the
current Markdown/JSON generation path is implemented in
`src/ade/reporting/report_generator.py`. Existing CLI export examples include
HTML report export and local dashboard export.

```python
from pathlib import Path


def export_review_artifact(report_json: Path, output_path: Path) -> Path:
    """Read an existing ADE report and write a local review artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("Local review artifact", encoding="utf-8")
    return output_path
```

Custom exports should preserve stable IDs such as `anomaly_id` and
`concept_id`, keep human-review language visible, and avoid adding cloud,
auth, database, or production deployment assumptions.
