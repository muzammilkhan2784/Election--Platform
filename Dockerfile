# ── base ─────────────────────────────────────────────────────────────────────
# Shared by both targets: dependencies, application code, unprivileged user.
FROM python:3.12-slim AS base

# PYTHONUNBUFFERED keeps log output in order when Docker captures stdout.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies are copied and installed before the application code so this
# layer stays cached when only source files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user rather than root. The prometheus directory is
# where Gunicorn workers pool their metrics so /metrics can aggregate across them.
RUN useradd --create-home appuser \
    && mkdir -p /tmp/prometheus \
    && chown -R appuser:appuser /app /tmp/prometheus
USER appuser

EXPOSE 3000

# ── dev ──────────────────────────────────────────────────────────────────────
# Adds test dependencies. Build with:  docker compose build --build-arg ...
# or:  docker build --target dev -t election-app:dev .
FROM base AS dev

USER root
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
USER appuser

CMD ["python", "run.py"]

# ── production ───────────────────────────────────────────────────────────────
# Last stage, so this is what builds by default. Gunicorn serves the app with
# multiple worker processes; Flask's built-in server is not used here.
FROM base AS production

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:3000", "server:application"]
