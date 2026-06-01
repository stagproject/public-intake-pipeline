# Collector adapter contract

This repository is structured so a hiring client can plug in **new public sources** without rewriting the core pipeline.

## Interface

See [`intake_pipeline/adapters/base.py`](../intake_pipeline/adapters/base.py):

- `CollectorAdapter.source_key` — stable string (`"vendor_directory"`, `"public_api_xyz"`, …)
- `CollectorAdapter.collect()` → `list[CollectedRecord]`

Each `CollectedRecord` should include at minimum:

| Field | Purpose |
|-------|---------|
| `record_id` | Stable primary key for deduplication |
| `source_url` | Evidence / audit trail |
| `content_hash` | Detect content changes on re-run |
| `metadata` | JSON-serializable extras (timestamps, tags, pagination cursor, …) |

## Persistence pattern

1. **Check** `intake_batch_status` for existing `record_id` → skip download if unchanged policy requires it.
2. **Store raw artifact** (optional) in object storage; path in metadata.
3. **Upsert** status row as `pending` (or your next stage name).
4. **Re-run safe:** repeating the job must not create duplicate primary keys.

Implementation reference: [`intake_pipeline/store.py`](../intake_pipeline/store.py).

## Example implementation

| Source type | Reference file |
|-------------|----------------|
| Government open API + RSS | [`intake_pipeline/collectors/sec_edgar.py`](../intake_pipeline/collectors/sec_edgar.py) |
| User-provided files | [`intake_pipeline/local_inbox.py`](../intake_pipeline/local_inbox.py) |

## Constraints (from client requirements)

- Public, lawful sources only  
- Respect `robots.txt` and site terms where applicable  
- Rate limits and retries  
- No CAPTCHA / paywall / credential bypass  

## First milestone mapping (typical Upwork intake job)

| Deliverable | This repo |
|-------------|-----------|
| Review repo + adapter interface | This doc + `adapters/base.py` |
| One production collector | New module under `intake_pipeline/collectors/` |
| Supabase storage | `store.py` + `sql/intake_pipeline_schema.sql` |
| Dedup on repeat run | `document_exists()` + upsert |
