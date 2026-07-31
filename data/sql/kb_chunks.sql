-- DimAI knowledge chunks — cold store for Supabase (pgvector).
-- Run once in Supabase SQL editor (or via migration).
-- Local hashed embeddings (dim=384) are stored so Render can query remotely
-- with the same EmbeddingEngine vectors.

create extension if not exists vector;

create table if not exists public.kb_chunks (
  id bigserial primary key,
  chunk_id text unique not null,
  kind text not null default 'qa',          -- qa | code | chat
  title text not null default '',
  body text not null default '',
  code text not null default '',
  lang text not null default '',
  tags text[] not null default '{}',
  quality real not null default 0.7,
  source text not null default '',
  url text not null default '',
  embedding vector(384),
  created_at timestamptz not null default now()
);

create index if not exists kb_chunks_kind_idx on public.kb_chunks (kind);
create index if not exists kb_chunks_quality_idx on public.kb_chunks (quality desc);
create index if not exists kb_chunks_tags_gin on public.kb_chunks using gin (tags);

-- IVFFlat needs data; HNSW is fine for moderate sizes
create index if not exists kb_chunks_embedding_hnsw
  on public.kb_chunks
  using hnsw (embedding vector_cosine_ops);

-- Match by cosine distance (caller sends local EmbeddingEngine vector)
create or replace function public.match_kb_chunks(
  query_embedding vector(384),
  match_count int default 8,
  filter_kind text default null,
  min_quality real default 0.0
)
returns table (
  chunk_id text,
  kind text,
  title text,
  body text,
  code text,
  lang text,
  tags text[],
  quality real,
  source text,
  url text,
  score float
)
language sql
stable
as $$
  select
    c.chunk_id,
    c.kind,
    c.title,
    c.body,
    c.code,
    c.lang,
    c.tags,
    c.quality,
    c.source,
    c.url,
    (1 - (c.embedding <=> query_embedding))::float as score
  from public.kb_chunks c
  where c.embedding is not null
    and c.quality >= min_quality
    and (filter_kind is null or c.kind = filter_kind)
  order by c.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

-- Service role used by DimAI; tighten if exposing anon.
alter table public.kb_chunks enable row level security;

drop policy if exists "service all kb_chunks" on public.kb_chunks;
create policy "service all kb_chunks"
  on public.kb_chunks
  for all
  using (true)
  with check (true);
