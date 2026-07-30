-- DimAI learned-knowledge table (Supabase SQL Editor'da çalıştır)
create table if not exists learned (
  id bigint generated always as identity primary key,
  q text not null,
  kw text[] not null default '{}',
  a text not null,
  url text default '',
  created_at timestamptz default now()
);

-- Optional quality score (self-improvement promotions). Safe if already exists.
alter table learned add column if not exists quality double precision;

-- Public erişimi kapat: RLS açık, policy yok.
-- Sunucu service_role anahtarıyla bağlandığı için RLS'i atlar.
alter table learned enable row level security;

-- Self-improvement: every request/response episode with scores + reflection
create table if not exists episodes (
  id bigint generated always as identity primary key,
  q text not null,
  a text not null,
  source text default '',
  accuracy double precision,
  quality double precision,
  completeness double precision,
  overall double precision,
  success boolean default false,
  failure_reason text default '',
  reflection jsonb default '{}'::jsonb,
  kw text[] not null default '{}',
  created_at timestamptz default now()
);
alter table episodes enable row level security;

-- Learning queue: validate before promoting into `learned`
create table if not exists learning_queue (
  id bigint generated always as identity primary key,
  q text not null,
  a text not null,
  url text default '',
  overall double precision,
  status text default 'pending',
  kw text[] not null default '{}',
  reflection jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
alter table learning_queue enable row level security;
