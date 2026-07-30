-- DimAI learned-knowledge table (Supabase SQL Editor'da çalıştır)
create table if not exists learned (
  id bigint generated always as identity primary key,
  q text not null,
  kw text[] not null default '{}',
  a text not null,
  url text default '',
  created_at timestamptz default now()
);

-- Public erişimi kapat: RLS açık, policy yok.
-- Sunucu service_role anahtarıyla bağlandığı için RLS'i atlar.
alter table learned enable row level security;
