# economic-data-etl canonical pipeline.
#
# One-shot service: ingests the simulation engine's CSV output, runs the
# transform and detection stages, writes the four canonical parquets to
# the shared canonical volume, then exits.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_FORMAT=json

WORKDIR /app

# requirements.txt carries the runtime and dev dependencies together.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The pipeline runs as modules from the repo root; config/ holds the
# detection rules, resolved through a working-directory-relative path.
COPY src ./src
COPY scripts ./scripts
COPY config ./config

# Run as a non-root user. /app is chowned here; /data/canonical is a
# compose-managed named volume — if its default ownership prevents the
# pipeline writing parquets, the compose file will need a complementary
# adjustment (entrypoint chown or user: directive).
RUN useradd --create-home --uid 1000 appuser \
 && chown -R appuser:appuser /app
USER appuser

# build_canonical_fixtures.py orchestrates the ingest/transform stage
# (sim_cli) and the detection stage (detect_cli), writing all four
# canonical parquets to --output-dir.
CMD python scripts/build_canonical_fixtures.py \
 --sim-output-root /data/sim-output \
 --output-dir /data/canonical
