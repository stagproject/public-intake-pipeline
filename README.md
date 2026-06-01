# public-intake-pipeline

**Portfolio repository** for Upwork and client technical reviews.

It demonstrates production-style patterns for:

- **Public web / API ingestion** (lawful, rate-limited, no auth bypass)
- **Stable record IDs** and **content hashing**
- **Supabase / Postgres** pipeline state and **idempotent** upserts
- **Local folder intake** (ZIP / HTML / XML) with manifests
- **Object storage** for raw source artifacts (S3-compatible)

This repo is a **curated subset** of a larger private monorepo. It does not include internal sales tooling, customer deliveries, deployment secrets, or operator runbooks.

---

## Is this repo runnable after download?

**Yes — with the right expectations.**

| What you get | Reality |
|--------------|---------|
| Real Python package | `uv sync` installs dependencies; commands run |
| **Local inbox** | Works **without** Supabase or SEC credentials (see [5-minute setup A](#5-minute-setup-path-a--local-inbox-only)) |
| **SEC collector + DB** | Needs `.env`, Supabase schema, and a watchlist row (see [Path B](#5-minute-setup-path-b--sec--supabase)) |
| Full private product | **Not included** — no LLM extraction warehouse, catalog sales, or customer JSONL delivery |

---

## What works without extra services

| Feature | Command | Notes |
|---------|---------|--------|
| Local file intake | `uv run python -m intake_pipeline.local_inbox` | Put files in `data/inbox/` first |
| CLI / imports | `uv run python -m intake_pipeline.collectors.sec_edgar --help` | No network required for `--help` |
| Code review | Read `docs/CLIENT_OVERVIEW.md` | No install required |

---

## What needs configuration

| Feature | You must provide |
|---------|------------------|
| SEC `DAILY` collector | `SEC_USER_AGENT` in `.env` ([SEC fair access](https://www.sec.gov/os/webmaster-faq#code-support)) |
| Supabase writes | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, tables from [`sql/intake_pipeline_schema.sql`](sql/intake_pipeline_schema.sql) |
| SEC `DAILY` discovery | At least one active row in `intake_watchlist` (example seed in SQL file) |
| Raw file upload to cloud | Optional: `OBJECT_STORAGE_*` variables in `.env` |
| Inbox → Supabase | `uv run python -m intake_pipeline.local_inbox --register` (requires `.env` + schema) |

`--mode TEST` for the SEC collector only checks that EDGAR is reachable; it does **not** write to the database.

---

## What is **not** in this public repo

- Multi-tenant warehouse / scheduled Cloud Run jobs  
- LLM batch extraction (Vertex / Gemini) and structured “listings” product tables  
- Upwork catalog tooling, sample PDFs, or customer delivery bundles  
- Internal operator runbooks (Japanese) or deployment secrets  

Those live in a **private** codebase. This repository is the **intake + Supabase state + dedup** slice only.

---

## Start here (documentation)

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

---

## 5-minute setup

**Requirements:** Python 3.10+, [uv](https://github.com/astral-sh/uv) (or pip + venv).

```bash
git clone https://github.com/stagproject/public-intake-pipeline.git
cd public-intake-pipeline
uv sync
```

### 5-minute setup — Path A · local inbox only

No Supabase, no SEC account. Best first run after clone.

1. Copy any `.htm`, `.html`, `.zip`, or `.xml` into `data/inbox/`  
   (If you have none, create a tiny `data/inbox/sample.htm` with a few lines of HTML.)
2. Run:

```bash
uv run python -m intake_pipeline.local_inbox
```

3. Check output:
   - `data/outbox/ingest_manifest_*.json` — manifest with `document_id`, hashes, paths  
   - `data/staging/*.htm` — normalized copies  
   - `data/outbox/processed/` — archived originals  

**Success:** console prints `OK <filename> -> <document_id>` and `Wrote manifest: ...`.

### 5-minute setup — Path B · SEC + Supabase

End-to-end public-source intake into Postgres (demo scale).

1. **Environment**

```bash
cp .env.example .env
```

Edit `.env`:

- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — from your Supabase project  
- `SEC_USER_AGENT` — e.g. `YourName you@example.com` (required by SEC)  
- Optional: `OBJECT_STORAGE_*` for raw `.htm` upload  

2. **Database** — open Supabase → SQL Editor → paste and run  
   [`sql/intake_pipeline_schema.sql`](sql/intake_pipeline_schema.sql)  
   Uncomment the example `INSERT INTO intake_watchlist` or add your own CIK.

3. **Connectivity check**

```bash
uv run python -m intake_pipeline.collectors.sec_edgar --mode TEST
```

4. **Ingest up to a few new filings**

```bash
uv run python -m intake_pipeline.collectors.sec_edgar --mode DAILY --max-new 3
```

5. **Verify** — in Supabase Table Editor, open `intake_batch_status` and confirm new `pending` rows with `metadata` JSON (`source_url`, `content_hash`, …).

6. **Dedup check** — run the same `DAILY` command again; existing `document_id` values should be skipped (no duplicate primary keys).

**Optional:** register inbox files to Supabase:

```bash
uv run python -m intake_pipeline.local_inbox --register
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Inbox is empty` | Add files under `data/inbox/` |
| `SEC_USER_AGENT is required` | Set in `.env` per SEC guidelines |
| `No rows in intake_watchlist` | Run schema SQL + insert an active CIK |
| `SUPABASE_URL ... must be set` | Copy `.env.example` → `.env` and fill keys |
| Import errors after clone | Run `uv sync` from repo root |

---

## Requirements (summary)

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) recommended  
- Supabase project — only for Path B  
- Valid `SEC_USER_AGENT` — only for SEC collector  

## License

MIT — see [`LICENSE`](LICENSE).
