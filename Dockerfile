FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE.md requirements.txt ./
COPY configs ./configs
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[api]"

EXPOSE 8000

CMD ["uvicorn", "ade.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
