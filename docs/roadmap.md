# ADE Roadmap

ADE is the Autonomous Discovery Engine: a modular unsupervised discovery platform that ingests datasets, builds representations, discovers candidate anomalies and hidden concepts, groups evidence, explains findings, and exports professional reports, APIs, and eventually enterprise workflows.

Core product principle: discovery with evidence, not only anomaly scores.

## Stage 1: Public-Ready Foundation

- Clean package structure
- Reliable CLI
- Passing test suite
- Typed public interfaces
- Pydantic or YAML configuration with clear validation
- Deterministic demo data
- JSON, Markdown, and future HTML reports
- README quickstart
- Architecture docs
- Changelog
- Security policy
- Contribution guide
- Release checklist
- GitHub Actions CI
- Formatting and linting

## Stage 2: Strong Image Discovery Engine

- Richer image features
- Color histograms
- Texture features
- Edge and shape features
- Multi-scale patch presets
- Diversity-aware candidate selection
- Memory-aware novelty scoring
- Patch-level evidence
- Similarity search
- Lightweight visual memory
- Near-duplicate detection
- Cluster summaries
- Better report visuals
- Evidence ranking
- Run metadata

## Stage 3: Pluggable Architecture

- `DataAdapter` interface
- `EmbeddingBackend` interface
- `ScoringBackend` interface
- `ClusteringBackend` interface
- `EvidenceRanker` interface
- `ReportRenderer` interface

## Stage 4: Advanced ML/Discovery Backends

- `StatisticalBackend`
- `ClassicalVisionBackend`
- Optional `CLIPBackend`
- Optional `DINOv2Backend`
- Optional `ResNetBackend`
- `CustomBackend` interface
- Distance-based novelty
- PatchCore-style normal-memory scoring
- Isolation Forest
- Local Outlier Factor
- HDBSCAN outlier scoring
- Ensemble novelty scoring
- Confidence scoring
- Optional FAISS indexing
- Persistent memory banks
- Persistent embedding cache

## Stage 5: API and Docker

- FastAPI service
- Dataset registry
- Run creation endpoint
- Run status endpoint
- Findings endpoint
- Report download endpoint
- Feedback endpoint
- Dockerfile
- Docker Compose

## Stage 6: Dashboard

- Run browser
- Dataset explorer
- Finding explorer
- Evidence viewer
- Cluster viewer
- Feedback labels
- Export controls

## Stage 7: Multi-Modal Expansion

1. Tabular adapter
2. Time-series adapter
3. Logs adapter
4. Video adapter
5. Audio/spectrogram adapter
6. Multimodal fusion

## Stage 8: Enterprise Readiness

- PostgreSQL
- Object storage
- Job queue
- Users
- Teams
- Projects
- RBAC
- Audit logs
- API keys
- SSO/OIDC
- Usage limits
- Billing hooks
- Monitoring
- Backup/restore
- Retention policies
- Kubernetes/Helm

## Stage 9: Domain Packages

Initial verticals:

1. Manufacturing / quality control
2. Research / scientific datasets
3. Cybersecurity / logs

## Delayed or Rejected for Now

- No mobile app priority
- No blockchain audit trail
- No premature SOC 2/HIPAA claims
- No Kubernetes-first design
- No heavy ML dependencies in the default install
- No dashboard before the core engine is solid
- No attempt to support every data modality at once
