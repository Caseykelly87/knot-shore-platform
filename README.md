# Knot Shore Grocery Platform

This repository orchestrates the four services of the Knot Shore Grocery
Platform into a single `docker compose up` demonstration. The services form
a one-direction pipeline: a simulation engine generates daily store and
department data, an ETL job turns that data into canonical parquet tables
and runs detection rules over them, an API serves the canonical tables, and
a portal renders them as a dashboard.

Each service lives in its own repository and is included here as a git
submodule. The Dockerfiles and the compose file in this repository build the
services from those submodules and wire them together; the service
repositories themselves carry no orchestration-specific files.

## Services

| Service | Submodule | Role |
|---|---|---|
| Simulation engine | `services/sim-engine` | Generates daily CSV output for the paired-year window |
| ETL | `services/etl` | Builds the canonical parquet tables and runs detection rules |
| API | `services/api` | Serves the canonical tables over HTTP |
| Portal | `services/portal` | Renders the dashboard from the API |

## Prerequisites

- Docker, with Docker Compose v2 (the `docker compose` subcommand)

## Setup

Clone with submodules:

```bash
git clone --recursive https://github.com/Caseykelly87/knot-shore-platform.git
cd knot-shore-platform
```

If the repository was cloned without `--recursive`, populate the submodules
before continuing:

```bash
git submodule update --init
```

## Run

```bash
docker compose up
```

The first run builds all four images and takes several minutes.

## What to expect

The services come up in pipeline order. The simulation engine runs first and
exits once it has written its CSV output. The ETL job then runs and exits
once it has written the canonical parquet tables. The API starts after the
canonical tables exist and reports healthy once it is serving them. The
portal starts after the API is healthy.

When the pipeline has settled, the dashboard is at <http://localhost:3000>
and the API at <http://localhost:8000>, with interactive API docs at
<http://localhost:8000/docs>. The dashboard renders data from a canonical
run produced during this `docker compose up`, not from a pre-built snapshot.

To stop the platform:

```bash
docker compose down
```

The canonical data persists in named volumes between runs. To discard it and
force a fresh pipeline run:

```bash
docker compose down -v
```

## Further reading

The portal's `/about` section is the platform's engineering documentation:
its architecture, the design decisions behind each service, and the lessons
from building them. It is available at <http://localhost:3000/about> once
the platform is up.

For what would change to run this at production scale — a managed database,
a scheduler, monitoring, and authentication — see `/about/operations`, the
platform's production-shape documentation.
