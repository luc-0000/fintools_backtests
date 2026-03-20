# Environment And Configuration

## Source Anchors

- Source: service.conf
- Source: end_points/init_global.py
- Source: end_points/config/db_init.py
- Source: local_agents/tauric_mcp/default_config.py

## Boot Config Contract

`manage.py` reads `CFG_PATH` from the process environment. If unset, it loads `./service.conf`.

`load_config_file()` treats the config file as Python source and executes it with `exec()`. Any replacement implementation must preserve these semantics or explicitly harden them and migrate callers.

## Required Config Keys

| Key | Purpose | Default Behavior |
| --- | --- | --- |
| `VERSION_FILE` | Build/version text file path | falls back to `./version.txt` in init logic |
| `LISTEN` | server bind host | `0.0.0.0` |
| `PORT` | server bind port | `8888` |
| `DEBUG` | uvicorn reload toggle | `False` unless config enables it |
| `DB_HOST` | MySQL host | env fallback or `localhost` |
| `DB_PORT` | MySQL port | env fallback or `3306` |
| `DB_USER` | MySQL username | env fallback or `root` |
| `DB_PASSWORD` | MySQL password | env fallback or empty string |
| `DB_NAME` | primary schema | env fallback or `fintools_backtest` |

## Database Binding Model

Bind keys from `end_points/common/const/consts.py`:

- `cn_stocks`
- `cn_stocks_m`
- `cn_stocks_in_pool`

Replication requirement:

- one primary engine for `DB_NAME`
- extra engines for the fixed bind-key schemas above
- connection settings:
  - `pool_pre_ping=True`
  - `pool_recycle=3600`
  - main engine `pool_size=5`, `max_overflow=15`
  - bind engines `pool_size=3`, `max_overflow=10`

## Global Runtime State

`global_var` stores:

- `version`
- `db`
- `db_engine`
- `db_session`
- `db_engines`
- `db_binds`

This is shared mutable process state. Reimplementations should either preserve it for compatibility or replace it with explicit dependency injection across all routes and services.

## Agent-Side Environment

Agent modules call `load_dotenv()`. The codebase implies environment-based credentials for:

- LLM providers
- Tushare and other market/news APIs
- optional MCP and storage backends

Exact env var names are not centralized in one file and must be recovered per adapter/module during a deeper hardening pass.

## Risks To Preserve Or Eliminate Explicitly

- `service.conf` currently contains plaintext DB credentials in source.
- config file execution via `exec()` is code execution by design.
- several agent systems rely on side-loaded `.env` rather than typed config.
