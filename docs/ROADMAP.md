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

Stage 4C adds optional CPU FAISS search behind exact-NumPy conformance tests and
lazy provisioning. Exact NumPy remains default. GPU indexing, performance
claims, benchmark qualification, and automatic backend selection are deferred.

Stage 4D adds optional fitted empirical-percentile and minmax score transforms,
identity passthrough, threshold-candidate generation, and held-out evaluation.
Supervised metrics require complete labeled held-out data; unlabeled evaluation
estimates review workload only. Calibration and thresholds remain disabled by
default and are not connected to the pipeline, Studio, or report UI. Candidate
operating points require human review and are not universal anomaly
probabilities.

Stage 4E adds a reproducible visual benchmark validation harness for explicitly
provisioned datasets and prediction records. It validates canonical benchmark
manifests, computes dependency-free labeled held-out ranking metrics and
candidate operating points, reports unlabeled review workload, and publishes
integrity-checked evaluation artifacts. No public dataset is downloaded and no
public benchmark performance is claimed. DINOv2, FAISS, and calibration remain
optional and explicit.

## Stage 5: API and Docker

### Stage 5B: Temporal CLI and Reports

- Explicit manifest validation and adjacent/baseline temporal analysis commands
- Immutable temporal artifact publication and validation before report success
- Deterministic JSON plus cautious Markdown and HTML review reports
- Optional real patch evidence; no fake heatmaps, live feeds, or geospatial registration
- Candidate temporal changes require human review

Stage 5A now provides an additive temporal visual change-detection foundation for
explicit ordered observation manifests. Adjacent/baseline comparison, optional patch
evidence, deterministic summaries, and integrity-checked JSON artifacts are local
library APIs. Normal image-folder analysis remains unchanged; live feeds and
monitoring are out of scope.

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
## Stage 4F: Optional Visual Evidence Integration

Stage 4F connects real advanced visual artifacts to JSON, Markdown, HTML, and connected ADE Studio
views without enabling the underlying workflows by default. Reference scoring, fitted calibration,
candidate operating points, spatial maps, and benchmark validation remain optional. All candidate
findings require human review under Technical Preview limitations. Full temporal report and CLI
workflow is implemented through the explicit Stage 5B CLI and report path.

## Stage 5C: Temporal Studio Integration

- Discover validated local temporal reports and integrity-checked result artifacts
- Show real sequence summaries, candidate change events, patch metadata, and provenance
- Keep malformed reports out of connected views while exposing local warnings
- No live feeds, geospatial UI, synthetic charts, or monitoring claims
