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
- Patch-level evidence
- Similarity search
- Near-duplicate detection
- Cluster summaries
- Better report visuals
- Evidence ranking
- Run metadata

The visual-engine program now begins with a contract and reproducibility
foundation: schema-versioned requests/results, explicit dataset roles, bounded
configuration, deterministic fingerprints, and strict local manifests. This is
not a deep-backend or reference-anomaly implementation.

Immutable content-addressed reference memory, deterministic bounded farthest-
first coreset selection, and exact batched NumPy similarity search are now
implemented as standalone Stage 2 foundations. Reference anomaly scoring and
spatial anomaly maps are implemented as separate Stage 3 typed APIs. These raw
scores remain uncalibrated and require human review. Deep representations are
not implemented yet.

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
- Isolation Forest
- Local Outlier Factor
- HDBSCAN outlier scoring
- Ensemble novelty scoring
- Confidence scoring
- Optional FAISS indexing
- Persistent embedding cache

PatchCore-style reference scoring and spatial maps now satisfy their Stage 3
contract gates. DINOv2, FAISS and calibration fitting remain future work and
must satisfy the visual-engine completion specification before implementation.

Stage 4A establishes the backend-neutral visual representation provider
contracts and wraps the existing lightweight deterministic features without
changing default output. Deep provider execution, model provisioning, DINOv2
preprocessing, and model-quality evaluation remain deferred.

Stage 4B supplies the explicitly selected DINOv2 provider foundation: lazy
optional runtime imports, local/offline provisioning by default, bounded batch
encoding, discovered feature dimensions, and stable model provenance. Pipeline,
report, Studio, calibration, benchmark qualification, and FAISS integration are
still deferred.

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
