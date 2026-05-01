create table if not exists oauth_connections (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null,
  user_id text not null,
  provider text not null,
  connected_email text,
  scopes text[] not null default '{}',
  permissions text[] not null default '{}',
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, user_id, provider)
);
