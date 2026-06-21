# CLAUDE.md

<!-- agent-core-onboarding:start -->
## ⚠️ First: install the agent-core baseline

Before working in this repository with an AI agent (Claude Code / Codex / Gemini
CLI), install the **powered-storage-org `agent-core` baseline** so your agent
loads our shared org standards (signed conventional commits, the gated
`ci.yaml` → GHCR release flow, the standard `Makefile`, container hardening).
Without it your agent has no shared rules and will drift from org conventions.

```sh
# 1. Install the baseline once (Linux/macOS; Windows: pwsh ./install.ps1)
git clone git@github.com:powered-storage-org/agent-core.git
cd agent-core && ./install.sh

# 2. Link it into THIS repo, then point your agent at its adapter
cd "$OLDPWD"            # back to this repo
~/.org-ai/install.sh --link
```

Then start coding with your agent pointed at its adapter:

- Claude Code → `~/.org-ai/claude/CLAUDE.md`
- Codex → `~/.org-ai/codex/AGENTS.md`
- Gemini CLI → `~/.org-ai/gemini/GEMINI.md`

Full project list & onboarding details: `~/.org-ai/docs/repositories.md`.
<!-- agent-core-onboarding:end -->


Project guide for Claude Code when working in this repository.

## Project

WeatherFlow Collector — gathers, processes, and forwards meteorological data
from WeatherFlow Tempest sources (REST API, WebSocket, local UDP) into
InfluxDB / file / WebSocket-server sinks. Fork of
[lux4rd0/weatherflow-collector](https://github.com/lux4rd0/weatherflow-collector)
with minor customizations.

Entry point: `src/weatherflow-collector.py`.

## Layout

```
src/
  weatherflow-collector.py   # main entry point
  config.py                  # env-var driven configuration
  config_validator.py
  event_manager.py           # event bus between collectors/handlers
  logger.py
  station_metadata_manager.py
  collector/                 # data sources: rest_*, udp, websocket
  handlers/                  # incoming-data routing/normalization
  processor/                 # per-source processors (rest_*, udp, websocket, system_metrics)
  provider/                  # outbound integrations (collector_data, export, websocket_server)
  storage/                   # sinks: file, influxdb, influxdb_delete
  utils/                     # calculate_weather_metrics, utils
grafana/                     # dashboards + provisioning
docker-compose.yaml          # influxdb + grafana + collector stack
Dockerfile                   # uv-based multi-stage image
pyproject.toml / uv.lock     # Python deps managed by uv
```

## Tooling

- Package manager: **uv** (`uv sync`, `uv lock`, `uv run …`).
- Linter / formatter: **ruff** (config in `pyproject.toml`).
- Python: **3.12+**.

### Common commands

```bash
uv sync                       # install deps (incl. dev) into .venv
uv run ruff check src         # lint
uv run ruff format --check src  # format check (CI uses this)
uv run ruff format src        # apply formatting
uv run python src/weatherflow-collector.py
```

### Docker

```bash
docker build -t weatherflow-collector:dev .
docker compose up -d          # full stack (influxdb + grafana + collector)
```

The Dockerfile is multi-stage: a `ghcr.io/astral-sh/uv` builder resolves
deps from `uv.lock` into `/app/.venv`, which is copied into a slim
runtime image. Source lives in `src/` and is the only app code copied.

## CI

`.github/workflows/ci.yaml` runs on every push and pull request:

- **Lint job** — always runs (`ruff check` + `ruff format --check`).
- **Docker build/publish job** — runs **only** for tags matching `v*.*.*`
  (e.g. `v0.1.0`). The Docker tag is the version **without** the leading
  `v` (e.g. `0.1.0`), plus `latest`. Image is pushed to
  `ghcr.io/<owner>/<repo>`.

Non-tag pushes never build a Docker image.

## Conventions

- Configuration is environment-variable driven (see `src/config.py` and
  `docker-compose.yaml`). Don't hardcode credentials.
- Keep dependency changes in `pyproject.toml` and refresh `uv.lock` with
  `uv lock`; don't hand-edit the lockfile.
- Container runs as the non-root `weatherflow` user; preserve that when
  editing the Dockerfile.
