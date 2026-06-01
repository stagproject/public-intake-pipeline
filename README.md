# public-intake-pipeline

**Portfolio repository** for Upwork and client technical reviews.

It demonstrates production-style patterns for:

- **Public web / API ingestion** (lawful, rate-limited, no auth bypass)
- **Stable record IDs** and **content hashing**
- **Supabase / Postgres** pipeline state and **idempotent** upserts
- **Local folder intake** (ZIP / HTML / XML) with manifests
- **Object storage** for raw source artifacts (S3-compatible)

This repo is a **curated subset** of a larger private monorepo. It does not include internal sales tooling, customer deliveries, deployment secrets, or operator runbooks.

## Start here

| Document | Audience |
|----------|----------|
| [`docs/CLIENT_OVERVIEW.md`](docs/CLIENT_OVERVIEW.md) | Recruiters / clients — 15-minute tour |
| [`docs/ADAPTER_CONTRACT.md`](docs/ADAPTER_CONTRACT.md) | How a new source collector plugs in |
| [`sql/intake_pipeline_schema.sql`](sql/intake_pipeline_schema.sql) | Example Postgres schema |

## Code map

| Path | Purpose |
|------|---------|
| [`intake_pipeline/collectors/sec_edgar.py`](intake_pipeline/collectors/sec_edgar.py) | Example: SEC EDGAR RSS + submissions API |
| [`intake_pipeline/local_inbox.py`](intake_pipeline/local_inbox.py) | Folder-based document intake + JSON manifest |
| [`intake_pipeline/db.py`](intake_pipeline/db.py) | Batched Supabase `.in_()` helpers |
| [`intake_pipeline/store.py`](intake_pipeline/store.py) | Generic status upsert / skip-if-exists |
| [`intake_pipeline/adapters/base.py`](intake_pipeline/adapters/base.py) | Collector adapter protocol |

## Quick start

```bash
git clone https://github.com/stagproject/public-intake-pipeline.git
cd public-intake-pipeline
cp .env.example .env   # fill Supabase + optional object storage

uv sync
uv run python -m intake_pipeline.local_inbox --help
uv run python -m intake_pipeline.collectors.sec_edgar --help
```

Place sample `.htm` / `.zip` files in `data/inbox/` (empty by default).

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Supabase project (for DB examples)
- For SEC collector: valid `SEC_USER_AGENT` per [SEC fair access](https://www.sec.gov/os/webmaster-faq#code-support)

## License

MIT — see [`LICENSE`](LICENSE).
