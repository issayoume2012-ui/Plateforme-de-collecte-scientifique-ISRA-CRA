-- ISRA / CRA Saint-Louis — Supabase PostgreSQL
-- Exécuter dans Supabase > SQL Editor avec le rôle postgres.
create extension if not exists pgcrypto;

create table if not exists public.cra_users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  display_name text not null default '',
  role text not null default 'Chercheur',
  password_hash text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  permissions jsonb not null default '[]'::jsonb
);

-- Stockage JSONB compatible avec les nombreux modules et formulaires dynamiques de l'application.
create table if not exists public.cra_records (
  table_name text not null,
  id text not null,
  owner_email text not null default '',
  payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key (table_name, id)
);
create index if not exists cra_records_table_owner_idx on public.cra_records(table_name, owner_email);
create index if not exists cra_records_payload_gin_idx on public.cra_records using gin(payload);

-- Journal de traçabilité append-only : conserver les états avant/après.
create table if not exists public.cra_audit_log (
  id bigint generated always as identity primary key,
  actor_email text not null default 'system',
  action text not null,
  table_name text not null,
  record_id text not null default '',
  before_data jsonb,
  after_data jsonb,
  event_at timestamptz not null default now()
);
create index if not exists cra_audit_log_event_idx on public.cra_audit_log(event_at desc);
create index if not exists cra_audit_log_record_idx on public.cra_audit_log(table_name, record_id);

-- Les tables ne sont jamais accessibles directement depuis anon/authenticated.
-- L'application Streamlit utilise uniquement la clé service_role côté serveur.
alter table public.cra_users enable row level security;
alter table public.cra_records enable row level security;
alter table public.cra_audit_log enable row level security;
revoke all on public.cra_users, public.cra_records, public.cra_audit_log from anon, authenticated;
grant all on public.cra_users, public.cra_records, public.cra_audit_log to service_role;
grant usage, select on sequence public.cra_audit_log_id_seq to service_role;

-- Audit SQL de secours, atomique avec INSERT/UPDATE/DELETE des enregistrements.
create or replace function public.cra_audit_records_trigger()
returns trigger language plpgsql security definer set search_path=public as $$
declare old_payload jsonb; new_payload jsonb; rec_id text; tbl text; op text;
begin
  if TG_OP='DELETE' then old_payload := OLD.payload; rec_id := OLD.id; tbl := OLD.table_name; op := 'DELETE';
  elsif TG_OP='UPDATE' then old_payload := OLD.payload; new_payload := NEW.payload; rec_id := NEW.id; tbl := NEW.table_name; op := 'UPDATE';
  else new_payload := NEW.payload; rec_id := NEW.id; tbl := NEW.table_name; op := 'INSERT'; end if;
  insert into public.cra_audit_log(actor_email,action,table_name,record_id,before_data,after_data,event_at)
  values (coalesce(nullif(current_setting('request.jwt.claim.email',true),''), current_user), op, tbl, rec_id, old_payload, new_payload, now());
  if TG_OP='DELETE' then return OLD; else return NEW; end if;
end; $$;
drop trigger if exists cra_records_audit on public.cra_records;
create trigger cra_records_audit after insert or update or delete on public.cra_records
for each row execute function public.cra_audit_records_trigger();

create or replace function public.cra_audit_users_trigger()
returns trigger language plpgsql security definer set search_path=public as $$
declare old_row jsonb; new_row jsonb; rec_id text; op text;
begin
  if TG_OP='DELETE' then old_row := to_jsonb(OLD) - 'password_hash'; rec_id := OLD.id::text; op := 'DELETE';
  elsif TG_OP='UPDATE' then old_row := to_jsonb(OLD) - 'password_hash'; new_row := to_jsonb(NEW) - 'password_hash'; rec_id := NEW.id::text; op := 'UPDATE';
  else new_row := to_jsonb(NEW) - 'password_hash'; rec_id := NEW.id::text; op := 'INSERT'; end if;
  insert into public.cra_audit_log(actor_email,action,table_name,record_id,before_data,after_data,event_at)
  values (coalesce(nullif(current_setting('request.jwt.claim.email',true),''), current_user), op, 'cra_users', rec_id, old_row, new_row, now());
  if TG_OP='DELETE' then return OLD; else return NEW; end if;
end; $$;
drop trigger if exists cra_users_audit on public.cra_users;
create trigger cra_users_audit after insert or update or delete on public.cra_users
for each row execute function public.cra_audit_users_trigger();

-- Empêcher toute modification/suppression du journal, même par l'application.
create or replace function public.cra_deny_audit_mutation()
returns trigger language plpgsql as $$ begin raise exception 'cra_audit_log is append-only'; end; $$;
drop trigger if exists cra_audit_immutable on public.cra_audit_log;
create trigger cra_audit_immutable before update or delete on public.cra_audit_log
for each row execute function public.cra_deny_audit_mutation();
