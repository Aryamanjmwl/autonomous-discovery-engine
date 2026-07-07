# ADE Docker Usage

ADE includes a lightweight Docker setup for running the local API service.
The image installs the Python package with the `api` extra and serves
`ade.api.app:app` with Uvicorn.

## Build

```bash
docker build -t ade-local-api .
```

## Run

```bash
docker run --rm -p 8000:8000 \
  -v "%cd%/data/raw:/app/data/raw" \
  -v "%cd%/data/reports:/app/data/reports" \
  -v "%cd%/configs:/app/configs:ro" \
  ade-local-api
```

On PowerShell, use `${PWD}` instead of `%cd%` if preferred.

## Docker Compose

```bash
docker compose up --build
```

The compose file runs one service:

- API port: `8000`
- Raw data mount: `./data/raw:/app/data/raw`
- Report output mount: `./data/reports:/app/data/reports`
- Config mount: `./configs:/app/configs:ro`

## Notes

Generated reports, run metadata, caches, bytecode, virtual environments, and
local demo data are excluded from the Docker build context through
`.dockerignore`.

This Docker setup is for local operation. It intentionally does not include a
database, queue worker, object storage, authentication, or orchestration layer.
