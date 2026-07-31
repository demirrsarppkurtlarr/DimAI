# DimAI knowledge cold store (Supabase)

1. Open Supabase SQL editor and run `kb_chunks.sql` (enables `vector`, table, RPC).
2. On Render set:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY` (or `SUPABASE_KEY`)
   - optional `DIMAI_KB_PUSH=1` on one boot to upsert hot chunks
3. DimAI boots a local hot index from seed JSON; when Supabase is configured it
   also pulls high-quality remote chunks and can `match_kb_chunks` by embedding.

Local hashed embeddings (384-d) are stored in `embedding vector(384)` so the
same `EmbeddingEngine` query vector works remotely — no paid embedding API.
