# Modality Capability Matrix

ADE is an adapter-based autonomous discovery platform. The current repository
has a mature local visual workflow plus lightweight tabular and time-series
foundations with end-to-end CLI reports. Other modalities remain planned
adapter paths. ADE is not a visual-only system.

| Modality | Current Status | Implemented Locally | Not Implemented |
| --- | --- | --- | --- |
| Visual image folders | Implemented local workflow | Image adapter, profiling, patch extraction, deterministic embeddings, candidate anomaly ranking, candidate concept grouping, evidence bundles, Markdown/JSON reports, HTML export, validation, benchmark, local verification | Deep visual encoders, production hosted review |
| Tabular CSV | Implemented lightweight adapter foundation and CLI workflow | CSV adapter, profiling, deterministic row-level features, candidate row anomaly ranking, candidate tabular pattern grouping, Markdown/JSON reports, demo data generator | Database ingestion, relational joins, supervised learning, production personalization |
| Time-series CSV | Implemented lightweight adapter foundation and explicit CLI workflow | Timestamped CSV adapter, signal profiling, point/window-style features, candidate anomaly ranking, candidate time-series pattern grouping, Markdown/JSON reports, demo data generator | Forecasting, production streaming, live sensors, alerting |
| Video | Planned adapter path | Interface-oriented architecture only | Video ingestion, frame sampling workflow, reports |
| Logs | Planned adapter path | Interface-oriented architecture only | Log parser, event-session modeling, reports |
| Audio input | Planned adapter path | Interface-oriented architecture only | Audio ingestion, acoustic features, reports |
| Documents | Planned adapter path | Interface-oriented architecture only | Document parsing, text embeddings, reports |
| Multimodal datasets | Planned adapter path | Interface-oriented architecture only | Cross-modal alignment, multimodal reports |
| Sensor streams | Planned adapter path | None | Sensor ingestion, stream processing, alerting |
| Live satellite feeds | Planned adapter path | None | Live feed ingestion, geospatial normalization, stream processing |
| Live streams | Planned adapter path | None | Production streaming, cloud ingestion, alerting |

All current outputs are candidate findings for human review. ADE does not claim
automated truth, supervised learning, production personalization, cloud hosting,
authentication, billing, or production streaming in this local technical preview
workflow.
