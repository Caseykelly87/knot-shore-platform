# Knot Shore grocery simulation engine.
#
# One-shot service: generates the paired-year canonical window of daily
# store and department CSV output, writes it to the shared sim-output
# volume, then exits.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_FORMAT=json

WORKDIR /app

# Install the package editable so knot_shore stays under src/ next to
# seed_data/. The realism layer resolves its bundled economic fixture by
# a path relative to the package; a non-editable install moves the
# package into site-packages and breaks that lookup.
COPY pyproject.toml ./
COPY src ./src
COPY seed_data ./seed_data
RUN pip install --no-cache-dir -e .

# Initialize the dimension and promotion tables, then backfill the two
# 184-day canonical windows. backfill skips dates already present, so a
# fresh volume yields a complete, deterministic run.
CMD python -m knot_shore init --seed 42 --output /data/sim-output \
 && python -m knot_shore backfill --start-date 2024-07-01 --days 184 --output /data/sim-output \
 && python -m knot_shore backfill --start-date 2025-07-01 --days 184 --output /data/sim-output
