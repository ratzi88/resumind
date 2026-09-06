# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

ARG EMBEDDING_MODEL=all-MiniLM-L6-v2
ARG TORCH_VERSION=2.7.1+cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST_DIR=/app/frontend-dist \
    HF_HOME=/home/resumind/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/resumind/.cache/sentence-transformers \
    EMBEDDING_MODEL=${EMBEDDING_MODEL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}" \
    && python -m pip install -r /tmp/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/frontend/dist/ /app/frontend-dist/

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin resumind \
    && mkdir -p /home/resumind/.cache/huggingface /home/resumind/.cache/sentence-transformers \
    && chown -R resumind:resumind /app /home/resumind

USER resumind

# Bundle the embedding model so job matching does not need a download on first use.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
