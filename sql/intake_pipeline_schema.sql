-- Example schema for public-intake-pipeline (Supabase / PostgreSQL)
-- Generic names — not tied to a private product schema.

CREATE TABLE IF NOT EXISTS intake_watchlist (
  cik text PRIMARY KEY,
  label text,
  is_active boolean DEFAULT true,
  priority integer DEFAULT 1000,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE intake_watchlist IS 'Entities to monitor (example: SEC CIK).';

CREATE TABLE IF NOT EXISTS intake_batch_status (
  document_id text PRIMARY KEY,
  source_key text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  metadata jsonb DEFAULT '{}'::jsonb,
  error_message text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intake_batch_status_status ON intake_batch_status (status);
CREATE INDEX IF NOT EXISTS idx_intake_batch_status_source ON intake_batch_status (source_key);

COMMENT ON TABLE intake_batch_status IS 'Per-record pipeline state; upsert on document_id for idempotent runs.';

-- Example seed (Apple CIK) — remove or edit in production
-- INSERT INTO intake_watchlist (cik, label, is_active, priority)
-- VALUES ('0000320193', 'Demo issuer', true, 1)
-- ON CONFLICT (cik) DO NOTHING;
