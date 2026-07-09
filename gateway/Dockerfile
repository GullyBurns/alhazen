# Gateway Dockerfile for Skillful-Alhazen
#
# A warm Python service that imports skill CLI modules once and drives their
# existing main() in-process. Unlike the dashboard image, this carries ONLY
# Python + uv + the venv + the skills tree (no Node) — it is the container where
# the polyglot "run a skill" weight legitimately lives.

# ==============================================================================
# Stage 1: Python base with uv
# ==============================================================================
FROM python:3.11-slim AS python-base
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ==============================================================================
# Stage 2: Install Python dependencies (cached on dep files only)
# ==============================================================================
FROM python-base AS deps
WORKDIR /app
# build-essential lets the semantic extra's compiled deps (hdbscan) build from
# source. This stage is discarded — the runtime image only copies /app/.venv.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock README.md ./
# Source needed for the dynamic version (pyproject reads src/.../__init__.py)
COPY src/skillful_alhazen/__init__.py ./src/skillful_alhazen/
# Skill runtime deps + the gateway's own. pipeline (sf-hamilton) for tech_recon.py;
# semantic (umap/hdbscan/voyage) for scilit map/cluster/embed. No torch — pymde
# stays in the embedding-map extra.
RUN uv sync --extra typedb --extra skills --extra qdrant --extra pipeline --extra semantic --extra gateway --no-dev

# ==============================================================================
# Stage 3: Runtime
# ==============================================================================
FROM python-base AS runner
WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml uv.lock README.md ./
# Only the package is baked. Skill code is NOT copied — it is mounted at runtime
# from the staged tree (compose mounts ./.skills-build at $SKILL_ROOT), so a skill
# update is a re-stage + `docker compose restart gateway`, never an image rebuild.
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV SKILL_ROOT=/app/skills-mounted
ENV GATEWAY_HOST=0.0.0.0
ENV GATEWAY_PORT=8900
ENV TYPEDB_HOST=typedb
ENV TYPEDB_PORT=1729
# No baked TYPEDB_DATABASE: each skill the gateway spawns uses its own per-repo
# default (alh_core / alh_deep_research / alh_personal) via os.getenv fallback.

EXPOSE 8900

HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8900/health').status==200 else 1)" || exit 1

CMD ["python", "-m", "skillful_alhazen.gateway"]
