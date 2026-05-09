# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

# Installer uv depuis l'image officielle
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# User non-root
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

# Étape 1 : installer les deps runtime (cache layer si pyproject/uv.lock inchangés)
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Étape 2 : copier le code applicatif
COPY --chown=app:app app.py utils.py ./
RUN mkdir -p data && chown -R app:app /app

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3).status == 200 else 1)"

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
