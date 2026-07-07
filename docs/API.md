# ADE Local API

ADE includes a small local FastAPI service for running the existing discovery
pipeline through HTTP. The service is intended for local development and
integration testing. It uses local filesystem paths and does not add
authentication, uploads, queues, or a database.

## Run Locally

Install the API extra:

```bash
pip install -e .[api]
```

Start the service:

```bash
uvicorn ade.api.app:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `GET /version`
- `POST /runs`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/report`

## Example Run

```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_path": "data/raw/demo_images",
    "output_dir": "data/reports",
    "config_path": "configs/default.yaml",
    "run_name": "demo_report"
  }'
```

The response includes the ADE run id, Markdown report path, JSON report path,
candidate anomaly count, candidate concept count, and run status.

## Run History

List known runs:

```bash
curl http://localhost:8000/runs
```

Fetch metadata for a run:

```bash
curl http://localhost:8000/runs/ade_YYYYMMDD_HHMMSS_xxxxxx
```

Fetch report paths for a run:

```bash
curl http://localhost:8000/runs/ade_YYYYMMDD_HHMMSS_xxxxxx/report
```

## Limitations

- Local filesystem paths only.
- Synchronous run execution.
- No authentication yet.
- No database yet.
- No file upload endpoint yet.
- Not intended as a production multi-tenant service.
