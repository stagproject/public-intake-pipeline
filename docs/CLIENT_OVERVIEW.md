# Overview for External Reviewers

**Repository:** `public-intake-pipeline` (public portfolio)  
**Purpose:** Demonstrate Python + Supabase + public-source intake patterns for hiring and client technical review.

---

## What this project is

A **document intake pipeline** that:

1. Collects data from **lawful public sources** (example: U.S. SEC EDGAR).
2. Normalizes **stable record IDs**, **source URLs**, and **content hashes**.
3. Tracks **pipeline state in Supabase/Postgres** (idempotent, resumable).
4. Supports **local folder intake** (ZIP / HTML / XML) with JSON manifests.

This is a **curated public repo**. A larger private codebase adds LLM extraction, catalog sales, and customer delivery — those are intentionally **not published here**.

---

## Design principles

| Principle | Implementation |
|-----------|----------------|
| Public sources only | SEC APIs with required `User-Agent`; configurable delay |
| Stable record ID | `document_id` / `record_id` as primary key |
| Idempotent runs | Skip or upsert if row already exists |
| Evidence | `source_url`, `content_hash`, optional object storage path |
| Batched DB queries | `intake_pipeline/db.py` — safe `.in_()` chunk sizes |

---

## Layout

| Path | Role |
|------|------|
| `intake_pipeline/collectors/` | Public API / RSS collectors |
| `intake_pipeline/local_inbox.py` | Folder-based intake |
| `intake_pipeline/store.py` | Supabase status upsert |
| `intake_pipeline/adapters/` | Adapter contract for new sources |
| `sql/intake_pipeline_schema.sql` | Example tables |
| `data/inbox/` | Drop test files here (not committed) |

---

## Review in 15 minutes

1. [`docs/ADAPTER_CONTRACT.md`](ADAPTER_CONTRACT.md) — how to add a source  
2. [`intake_pipeline/collectors/sec_edgar.py`](../intake_pipeline/collectors/sec_edgar.py) — rate limits, skip-if-exists, metadata  
3. [`intake_pipeline/local_inbox.py`](../intake_pipeline/local_inbox.py) — manifest + optional DB register  
4. [`intake_pipeline/store.py`](../intake_pipeline/store.py) — upsert pattern  
5. [`sql/intake_pipeline_schema.sql`](../sql/intake_pipeline_schema.sql) — schema  

---

## Runnable after clone?

| Track | Time | Needs |
|-------|------|--------|
| **A — Local inbox** | ~5 min | `uv sync` + a file in `data/inbox/` |
| **B — SEC + Supabase** | ~5–15 min | `.env`, SQL schema, `intake_watchlist` row, `SEC_USER_AGENT` |

**Path A** does not use the network (except `uv sync`). **Path B** writes real `pending` rows to `intake_batch_status`.

**Not published here:** LLM extraction, warehouse schedulers, catalog/sales delivery, or internal ops docs.

Full step-by-step commands: **[`README.md` — 5-minute setup](../README.md#5-minute-setup)**.

---

## Setup (short)

```bash
git clone https://github.com/stagproject/public-intake-pipeline.git
cd public-intake-pipeline
uv sync

# Path A — no .env required
# (add a file under data/inbox/ first)
uv run python -m intake_pipeline.local_inbox

# Path B — Supabase + SEC
cp .env.example .env   # edit SUPABASE_* and SEC_USER_AGENT
# Run sql/intake_pipeline_schema.sql in Supabase SQL editor
uv run python -m intake_pipeline.collectors.sec_edgar --mode TEST
uv run python -m intake_pipeline.collectors.sec_edgar --mode DAILY --max-new 3
```

---

## Mapping to a client “intake + Supabase” milestone

| Client ask | This repo |
|------------|-----------|
| Review repo + adapter | `adapters/base.py`, `ADAPTER_CONTRACT.md` |
| One collector end-to-end | `collectors/sec_edgar.py` (or new file alongside it) |
| Store in Supabase | `store.py` + schema |
| Dedup on repeat run | `document_exists()` + upsert |

---

*Public portfolio — no credentials or customer data included.*
