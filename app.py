# -*- coding: utf-8 -*-
"""
ISRA – CRA SAINT-LOUIS
Plateforme de fiches techniques, fiches de mesure et questionnaires partageables.

Installation :
    pip install -r requirements.txt
Lancement :
    streamlit run app.py

Au premier démarrage, les tables Supabase sont créées automatiquement via SUPABASE_DB_URL.
Lancez avec : streamlit run app.py
"""

from __future__ import annotations

import json
import re
import uuid
import hashlib
import hmac
import zipfile
import time
from datetime import date, datetime
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------
# CONFIGURATION ET DESIGN
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="ISRA | CRA Saint-Louis",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

GREEN = "#247A66"
DARK = "#16483F"
GOLD = "#DDB64C"
WATER = "#BFE9DE"
INK = "#18352A"
MUTED = "#66776D"
CONTACT_EMAIL = "issayoume1801@gmail.com"

st.markdown(f"""
<style>
html, body, [class*="css"] {{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}}
.stApp {{background:#F1FAF7;color:{INK};}}
.block-container {{padding:1.2rem clamp(0.7rem,2.2vw,2rem) 2rem;max-width:1500px;width:100%;}}
.hero {{background:linear-gradient(115deg,{DARK},{GREEN},#2C8B60);
padding:27px 30px;border-radius:20px;color:white;border-bottom:5px solid {GOLD};
margin-bottom:22px;box-shadow:0 12px 28px #103f2d20;}}
.hero h1 {{color:white;font-weight:900;margin:0;font-size:clamp(25px,3vw,38px);letter-spacing:.4px;}}
.isra-band {{background:#fff;border:1px solid #dce9df;border-left:7px solid {GOLD};border-radius:13px;padding:10px 16px;margin:0 0 16px;color:{DARK};font-weight:900;letter-spacing:1px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;}}
.hero p {{color:#e4f1e9;margin:8px 0 0;}}
.eyebrow {{color:{GOLD};font-weight:800;letter-spacing:1.5px;text-transform:uppercase;font-size:11px;}}
.section-title {{font-size:25px;font-weight:800;color:{DARK};margin:3px 0;}}
.section-sub {{color:{MUTED};font-size:13px;margin-bottom:17px;}}
.card {{background:white;border:1px solid #CDE8DF;border-radius:16px;padding:18px 20px;margin:8px 0 16px;}}
div[data-testid="stMetric"] {{background:white;border:1px solid #e1ebe4;border-radius:14px;padding:13px;}}
.stButton>button {{border-radius:10px;font-weight:700;}}
.stButton>button[kind="primary"] {{background:{GREEN};border-color:{GREEN};}}
a {{color:{GREEN};}}
/* Mise en page adaptative : téléphone, tablette et ordinateur */
[data-testid="stHorizontalBlock"] {{gap:clamp(.45rem,1.4vw,1.1rem);}}
[data-testid="stVerticalBlock"] {{gap:.7rem;}}
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [data-baseweb="select"], [data-testid="stNumberInput"] input {{
  min-height:44px;border-radius:10px;font-size:16px;
}}
.stButton>button, [data-testid="stDownloadButton"] button {{min-height:44px;width:100%;white-space:normal;}}
[data-testid="stDataFrame"], [data-testid="stTable"] {{width:100%;overflow-x:auto;}}
@media (max-width: 900px) {{
  .block-container {{padding:1rem .85rem 1.5rem;}}
  .hero {{padding:21px 19px;border-radius:16px;}}
  .card {{padding:15px;border-radius:13px;}}
  .section-title {{font-size:clamp(20px,4vw,25px);}}
}}
@media (max-width: 640px) {{
  .block-container {{padding:.65rem .55rem 1.2rem;}}
  .hero {{padding:17px 15px;margin-bottom:13px;}}
  .hero h1 {{font-size:25px;line-height:1.2;}}
  .hero p {{font-size:13px;line-height:1.5;}}
  .isra-band {{font-size:10px;padding:9px 11px;gap:7px;}}
  .card {{padding:12px;margin:6px 0 12px;}}
  [data-testid="stMetric"] {{padding:9px;}}
  [data-testid="stMetricValue"] {{font-size:1.35rem;}}
  [data-testid="stHorizontalBlock"] {{flex-wrap:wrap;}}
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {{min-width:100% !important;flex:1 1 100% !important;}}
  .stButton>button, [data-testid="stDownloadButton"] button {{min-height:46px;font-size:15px;}}
  input, textarea {{font-size:16px !important;}}
}}
footer {{visibility:hidden;}}
[data-testid="stToolbar"] {{display:none !important;}}
[data-testid="stHeader"] {{background:transparent;}}
</style>
""", unsafe_allow_html=True)


def heading(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="eyebrow">{kicker}</div><div class="section-title">{title}</div>'
        f'<div class="section-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


st.markdown("""
<div class="hero">
  <div class="eyebrow">INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES · ISRA</div>
  <h1>ISRA — CRA SAINT-LOUIS</h1>
  <p>Plateforme de collecte scientifique : fiches techniques, mesures de terrain et enquêtes numériques.</p>
  <b>Supervision scientifique : M. Keita</b>
</div>
<div class="isra-band"><span>ISRA — INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES</span><span>CRA SAINT-LOUIS · RECHERCHE & INNOVATION</span></div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# SUPABASE POSTGRESQL — stockage centralisé
# ---------------------------------------------------------------------
import os
from urllib.parse import quote
from supabase import create_client, Client

# Lire les paramètres depuis Streamlit Cloud (st.secrets), avec repli
# sur les variables d'environnement en local. Aucun secret n'est enregistré ici.
def _config_value(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return str(os.getenv(name, default))

SUPABASE_URL = _config_value("SUPABASE_URL", "https://mlmbvjzkesnwportvmax.supabase.co")
SUPABASE_ANON_KEY = _config_value("SUPABASE_ANON_KEY")
SUPABASE_DB_HOST = _config_value("SUPABASE_DB_HOST", "aws-1-eu-west-3.pooler.supabase.com")
SUPABASE_DB_PORT = _config_value("SUPABASE_DB_PORT", "5432")
SUPABASE_DB_NAME = _config_value("SUPABASE_DB_NAME", "postgres")
SUPABASE_DB_USER = _config_value("SUPABASE_DB_USER", "postgres.mlmbvjzkesnwportvmax")
SUPABASE_DB_PASSWORD = _config_value("SUPABASE_DB_PASSWORD")
SUPABASE_DB_URL = _config_value("SUPABASE_DB_URL")
if not SUPABASE_DB_URL and SUPABASE_DB_PASSWORD:
    SUPABASE_DB_URL = (
        f"postgresql://{quote(SUPABASE_DB_USER, safe='')}:{quote(SUPABASE_DB_PASSWORD, safe='')}"
        f"@{SUPABASE_DB_HOST}:{SUPABASE_DB_PORT}/{SUPABASE_DB_NAME}?sslmode=require"
    )
SUPABASE_SERVICE_ROLE_KEY = _config_value("SUPABASE_SERVICE_ROLE_KEY")
CRA_ADMIN_EMAIL = _config_value("CRA_ADMIN_EMAIL", "keita@2026")
CRA_ADMIN_PASSWORD = _config_value("CRA_ADMIN_PASSWORD")

# Création automatique du schéma PostgreSQL au démarrage.
# La clé service_role ne permet PAS de créer des tables : cette opération
# nécessite une connexion PostgreSQL avec un rôle autorisé (postgres).
_SCHEMA_SQL = r"""
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
alter table public.cra_users enable row level security;
alter table public.cra_records enable row level security;
alter table public.cra_audit_log enable row level security;
revoke all on public.cra_users, public.cra_records, public.cra_audit_log from anon, authenticated;
grant all on public.cra_users, public.cra_records, public.cra_audit_log to service_role;
grant usage, select on sequence public.cra_audit_log_id_seq to service_role;
create or replace function public.cra_audit_records_trigger()
returns trigger language plpgsql security definer set search_path=public as $$
declare old_payload jsonb; new_payload jsonb; rec_id text; tbl text; op text;
begin
 if TG_OP='DELETE' then old_payload:=OLD.payload; rec_id:=OLD.id; tbl:=TG_TABLE_NAME; op:='DELETE';
 elsif TG_OP='UPDATE' then old_payload:=OLD.payload; new_payload:=NEW.payload; rec_id:=NEW.id; tbl:=TG_TABLE_NAME; op:='UPDATE';
 else new_payload:=NEW.payload; rec_id:=NEW.id; tbl:=TG_TABLE_NAME; op:='INSERT'; end if;
 insert into public.cra_audit_log(actor_email,action,table_name,record_id,before_data,after_data,event_at)
 values (coalesce(nullif(current_setting('request.jwt.claim.email',true),''),current_user),op,tbl,rec_id,old_payload,new_payload,now());
 if TG_OP='DELETE' then return OLD; else return NEW; end if;
end; $$;

-- Migration explicite du module Pointage (la table est aussi déclarée dans la liste métier).
-- Elle reste définie ici pour forcer sa présence et ses droits après mise à jour.
create table if not exists public.cra_attendance (
  id text primary key,
  owner_email text not null default '',
  payload jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists cra_attendance_owner_idx on public.cra_attendance(owner_email);
create index if not exists cra_attendance_created_idx on public.cra_attendance(created_at desc);
create index if not exists cra_attendance_payload_gin_idx on public.cra_attendance using gin(payload);
alter table public.cra_attendance enable row level security;
revoke all on public.cra_attendance from anon, authenticated;
grant all on public.cra_attendance to service_role;
drop trigger if exists cra_attendance_audit on public.cra_attendance;
create trigger cra_attendance_audit after insert or update or delete on public.cra_attendance
for each row execute function public.cra_audit_records_trigger();
drop trigger if exists cra_records_audit on public.cra_records;
create trigger cra_records_audit after insert or update or delete on public.cra_records
for each row execute function public.cra_audit_records_trigger();

-- Tables métier autonomes : tables PostgreSQL classiques, sans INHERITS.
-- Chaque module possède sa propre table avec id, propriétaire, données JSONB et date.
-- Les données historiques sont copiées depuis cra_records sans les supprimer.
do $$
declare t text; c record;
begin
  foreach t in array array[
    'cra_collaboration','cra_culture_folders','cra_cultures','cra_forms',
    'cra_measurement_drafts','cra_measurement_sheets',
    'cra_phytosanitary_diagnostics','cra_responses','cra_technical_sheets',
    'cra_trial_observations','cra_trials','cra_attendance'
  ] loop
    -- Convertit les anciennes tables héritées créées par les versions précédentes.
    if to_regclass(format('public.%I', t)) is not null and exists (
      select 1 from pg_inherits i
      where i.inhrelid = to_regclass(format('public.%I', t))
        and i.inhparent = 'public.cra_records'::regclass
    ) then
      execute format('drop index if exists public.%I', t || '_table_id_uidx');
      execute format('alter table public.%I no inherit public.cra_records', t);
      for c in
        select conname from pg_constraint
        where conrelid = to_regclass(format('public.%I', t)) and contype = 'c'
      loop
        execute format('alter table public.%I drop constraint %I', t, c.conname);
      end loop;
      if exists (
        select 1 from information_schema.columns
        where table_schema='public' and table_name=t and column_name='table_name'
      ) then
        execute format('alter table public.%I drop column table_name', t);
      end if;
      if not exists (
        select 1 from pg_constraint
        where conrelid=to_regclass(format('public.%I', t)) and contype='p'
      ) then
        execute format('alter table public.%I add constraint %I primary key (id)', t, t || '_pkey');
      end if;
    end if;

    execute format(
      'create table if not exists public.%I (' ||
      'id text primary key, owner_email text not null default %L, ' ||
      'payload jsonb not null, created_at timestamptz not null default now())',
      t, ''
    );
    execute format('create index if not exists %I on public.%I (owner_email)', t || '_owner_idx', t);
    execute format('create index if not exists %I on public.%I (created_at desc)', t || '_created_idx', t);
    execute format('create index if not exists %I on public.%I using gin(payload)', t || '_payload_gin_idx', t);

    -- Copie idempotente : les données originales restent dans cra_records.
    execute format(
      'insert into public.%I (id,owner_email,payload,created_at) ' ||
      'select id,coalesce(owner_email,%L),payload,created_at from public.cra_records ' ||
      'where table_name=%L on conflict (id) do nothing',
      t, '', t
    );

    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from anon, authenticated', t);
    execute format('grant all on public.%I to service_role', t);
    execute format('drop trigger if exists %I on public.%I', t || '_audit', t);
    execute format(
      'create trigger %I after insert or update or delete on public.%I ' ||
      'for each row execute function public.cra_audit_records_trigger()',
      t || '_audit', t
    );
  end loop;
end; $$;

create or replace function public.cra_audit_users_trigger()
returns trigger language plpgsql security definer set search_path=public as $$
declare old_row jsonb; new_row jsonb; rec_id text; op text;
begin
 if TG_OP='DELETE' then old_row:=to_jsonb(OLD)-'password_hash'; rec_id:=OLD.id::text; op:='DELETE';
 elsif TG_OP='UPDATE' then old_row:=to_jsonb(OLD)-'password_hash'; new_row:=to_jsonb(NEW)-'password_hash'; rec_id:=NEW.id::text; op:='UPDATE';
 else new_row:=to_jsonb(NEW)-'password_hash'; rec_id:=NEW.id::text; op:='INSERT'; end if;
 insert into public.cra_audit_log(actor_email,action,table_name,record_id,before_data,after_data,event_at)
 values (coalesce(nullif(current_setting('request.jwt.claim.email',true),''),current_user),op,'cra_users',rec_id,old_row,new_row,now());
 if TG_OP='DELETE' then return OLD; else return NEW; end if;
end; $$;
drop trigger if exists cra_users_audit on public.cra_users;
create trigger cra_users_audit after insert or update or delete on public.cra_users
for each row execute function public.cra_audit_users_trigger();
create or replace function public.cra_deny_audit_mutation()
returns trigger language plpgsql as $$ begin raise exception 'cra_audit_log is append-only'; end; $$;
drop trigger if exists cra_audit_immutable on public.cra_audit_log;
create trigger cra_audit_immutable before update or delete on public.cra_audit_log
for each row execute function public.cra_deny_audit_mutation();


-- Actualise le cache de schéma PostgREST après la création des tables.
drop trigger if exists cra_records_route_insert on public.cra_records;
drop function if exists public.cra_route_record_insert();
notify pgrst, 'reload schema';
"""

@st.cache_resource(show_spinner=False)
def _bootstrap_supabase_schema_once(db_url: str, schema_version: str = "attendance-v1"):
    """Initialise le schéma une seule fois par processus Streamlit, pas à chaque clic."""
    if not db_url:
        raise RuntimeError(
            "SUPABASE_DB_URL manquant. Ajoutez l'URI PostgreSQL Supabase dans les secrets Streamlit."
        )
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Dépendance psycopg absente. Ajoutez `psycopg[binary]>=3.2` à requirements.txt."
        ) from exc
    with psycopg.connect(db_url, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
    return True

@st.cache_resource(show_spinner=False)
def _get_supabase_client(url: str, service_key: str) -> Client:
    return create_client(url, service_key)

if not SUPABASE_SERVICE_ROLE_KEY:
    st.error("Configuration manquante : définissez SUPABASE_SERVICE_ROLE_KEY dans les secrets Streamlit.")
    st.stop()
try:
    # IMPORTANT : ne jamais exécuter les migrations SQL lourdes au démarrage
    # de chaque instance Streamlit. Les tables sont provisionnées une fois
    # lors du déploiement. Les migrations restent disponibles en mode explicite.
    _run_migrations = _config_value("RUN_DB_MIGRATIONS", "false").strip().lower() in {"1", "true", "yes", "oui"}
    if _run_migrations:
        _bootstrap_supabase_schema_once(SUPABASE_DB_URL, "attendance-v3")
    _SUPABASE: Client = _get_supabase_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except Exception as exc:
    st.error(f"Connexion Supabase impossible : {exc}")
    st.stop()

class DBResult:
    def __init__(self, data): self.data = data or []

class SupabaseQuery:
    def __init__(self, table):
        self.table=table; self.action="select"; self.payload={}; self.filters=[]
        self.columns="*"; self.sort=None; self.max_rows=None
    def select(self, columns="*"): self.action="select"; self.columns=columns; return self
    def insert(self, payload): self.action="insert"; self.payload=dict(payload); return self
    def update(self, payload): self.action="update"; self.payload=dict(payload); return self
    def delete(self): self.action="delete"; return self
    def eq(self, column, value): self.filters.append((column,value)); return self
    def order(self, column, desc=False): self.sort=(column,desc); return self
    def limit(self, value): self.max_rows=int(value); return self
    def _audit(self, operation, row_id, before=None, after=None):
        _SUPABASE.table("cra_audit_log").insert({
            "actor_email":st.session_state.get("cra_user_email","public"), "action":operation,
            "table_name":self.table,"record_id":str(row_id or ""),"before_data":before,
            "after_data":after,"event_at":datetime.utcnow().isoformat()
        }).execute()
    def _fetch_pages(self, query):
        """Récupère les lignes par pages pour éviter la limite PostgREST de 1 000."""
        output=[]; page_size=500; maximum=self.max_rows or 5000
        while len(output)<maximum:
            page=query.range(len(output), min(len(output)+page_size, maximum)-1).execute().data or []
            output.extend(page)
            if len(page)<page_size: break
        return output[:maximum]
    def _record_query(self):
        # Chaque module lit désormais sa table PostgreSQL autonome.
        q=_SUPABASE.table(self.table).select("id,owner_email,payload,created_at")
        for key,value in self.filters:
            if key in {"id","owner_email","created_at"}:
                q=q.eq(key,value)
            else:
                q=q.filter(f"payload->>{key}","eq",(str(value).lower() if isinstance(value, bool) else str(value)))
        if self.sort:
            col,desc=self.sort
            if col in {"created_at","id","owner_email"}:
                q=q.order(col,desc=desc)
        return q
    def execute(self):
        if self.table == "cra_users":
            q=_SUPABASE.table("cra_users")
            if self.action == "insert":
                row=dict(self.payload); row.setdefault("id",str(uuid.uuid4())); row.setdefault("created_at",datetime.utcnow().isoformat())
                result=q.insert(row).execute()
                for r in result.data or []: self._audit("INSERT",r.get("id"),after=r)
                return DBResult(result.data)
            if self.action == "update":
                patch={k:v for k,v in self.payload.items() if k in {"active","display_name","role","permissions","password_hash"}}
                uq=_SUPABASE.table("cra_users").update(patch)
                for k,v in self.filters: uq=uq.eq(k,v)
                result=uq.execute()
                for r in result.data or []: self._audit("UPDATE",r.get("id"),after=r)
                return DBResult(result.data)
            if self.action == "delete": raise PermissionError("Suppression des comptes interdite : désactivez le compte.")
            q=q.select(self.columns)
            for k,v in self.filters: q=q.eq(k,v)
            if self.sort: q=q.order(self.sort[0],desc=self.sort[1])
            if self.max_rows is not None: q=q.limit(self.max_rows)
            return DBResult(q.execute().data)
        if self.action == "insert":
            row=dict(self.payload); row.setdefault("id",str(uuid.uuid4())); row.setdefault("created_at",datetime.utcnow().isoformat())
            # Toute nouvelle saisie est classée dans le dossier actif, sauf
            # les dossiers eux-mêmes et les invitations de collaboration.
            active_folder = st.session_state.get("cra_active_workspace_folder")
            if active_folder and self.table not in {"cra_culture_folders", "cra_collaboration"}:
                row.setdefault("folder_id", active_folder.get("id"))
                row.setdefault("folder_name", active_folder.get("folder_name", ""))
            stored={"id":str(row["id"]),"owner_email":row.get("owner_email",""),"payload":row,"created_at":row["created_at"]}
            _SUPABASE.table(self.table).insert(stored).execute()
            self._audit("INSERT",row["id"],after=row); return DBResult([row])

        owner=st.session_state.get("cra_user_email")
        shared_ids,shared_folders=collaboration_permissions() if owner and self.table!="cra_collaboration" else ({},set())
        permitted=shared_ids.get(self.table,set())
        base=self._record_query()
        if owner and self.table!="cra_collaboration":
            # Charge d'abord les données du propriétaire depuis l'index SQL.
            own_q=base.eq("owner_email",owner)
            stored=self._fetch_pages(own_q)
            # Les fiches partagées sont récupérées par identifiant, sans charger toute la table.
            if permitted:
                shared_q=self._record_query().in_("id",list(permitted))
                stored.extend(self._fetch_pages(shared_q))
            # Les éléments des dossiers partagés sont le seul cas nécessitant
            # une recherche complémentaire dans le JSONB.
            if shared_folders:
                folder_q=self._record_query().in_("payload->>folder_id",list(shared_folders))
                stored.extend(self._fetch_pages(folder_q))
            dedup={x.get("id"):x for x in stored if x.get("id")}
            stored=list(dedup.values())
        else:
            stored=self._fetch_pages(base)
        rows=[dict(x.get("payload") or {}) for x in stored]
        selected=[r for r in rows if all(r.get(k)==v for k,v in self.filters)]
        if owner and self.table!="cra_collaboration":
            selected=[r for r in selected if r.get("owner_email")==owner or r.get("id") in permitted or r.get("id") in shared_folders or r.get("folder_id") in shared_folders]
        if self.action in ("update","delete"):
            for row in selected:
                key=_SUPABASE.table(self.table).delete() if self.action=="delete" else _SUPABASE.table(self.table).update({"payload":{**row,**self.payload},"owner_email":({**row,**self.payload}).get("owner_email","")})
                key.eq("id",str(row["id"])).execute()
                self._audit(self.action.upper(),row["id"],before=row,after=({**row,**self.payload} if self.action=="update" else None))
            return DBResult(selected if self.action=="update" else [])
        if self.sort and self.sort[0] not in {"created_at","id","owner_email"}:
            col,desc=self.sort; selected.sort(key=lambda x:str(x.get(col) or ""),reverse=desc)
        if self.max_rows is not None: selected=selected[:self.max_rows]
        if self.columns!="*":
            cols=[c.strip() for c in self.columns.split(",")]; selected=[{k:r.get(k) for k in cols} for r in selected]
        return DBResult(selected)

class SupabaseDatabase:
    def table(self,name): return SupabaseQuery(name)

DB=SupabaseDatabase()
DB_MESSAGE="Base centrale Supabase PostgreSQL active · journal d’audit activé."

def collaboration_permissions():
    email=st.session_state.get("cra_user_email",""); shared_records={}; shared_folders=set()
    if not email: return shared_records,shared_folders
    cache=st.session_state.get("_cra_collab_cache")
    if cache and cache.get("email")==email and time.monotonic()-cache.get("at",0)<20:
        return cache["records"],set(cache["folders"])
    try:
        for item in DB.table("cra_collaboration").select("*").execute().data or []:
            recipients=item.get("shared_with",[])
            if isinstance(recipients,str):
                try: recipients=json.loads(recipients)
                except Exception: recipients=[recipients]
            if email in recipients and item.get("status","active")=="active":
                if item.get("target_type")=="folder": shared_folders.add(item.get("target_id"))
                elif item.get("target_table") and item.get("target_id"):
                    shared_records.setdefault(item.get("target_table"),set()).add(item.get("target_id"))
        st.session_state["_cra_collab_cache"]={"email":email,"at":time.monotonic(),"records":shared_records,"folders":list(shared_folders)}
    except Exception as exc: st.error(f"Lecture des droits de collaboration impossible : {exc}")
    return shared_records,shared_folders

def db_rows(table: str, limit: int=5000) -> list[dict]:
    return DB.table(table).select("*").order("created_at",desc=True).limit(limit).execute().data or []


@st.cache_data(ttl=30, show_spinner=False)
def _cached_questionnaire_rows(table: str, owner_email: str, limit: int) -> list[dict]:
    """Cache court des listes admin pour éviter deux lectures Supabase à chaque rerun.

    owner_email fait partie de la clé afin de ne jamais partager le cache entre comptes.
    """
    return db_rows(table, limit)

def culture_catalogue() -> list[str]:
    base = ["Riz", "Tomate", "Maïs", "Oignon", "Canne à sucre", "Niébé", "Mil", "Sorgho", "Pastèque", "Piment", "Aubergine", "Laitue", "Chou", "Autre / saisir"]
    saved = db_rows("cra_cultures", 2000)
    names = [str(x.get("name", "")).strip() for x in saved if x.get("name")]
    return list(dict.fromkeys(base[:-1] + names + ["Autre / saisir"]))


def choose_culture(label: str, key: str) -> str:
    """Culture librement saisissable ; le référentiel sert uniquement de suggestion."""
    suggestions = [name for name in culture_catalogue() if name != "Autre / saisir"]
    st.caption("Champ libre : saisissez directement la culture étudiée, même si elle n'existe pas encore dans le référentiel.")
    value = st.text_input(label, key=key, placeholder="Ex. : Riz, tomate, niébé, variété ou culture émergente")
    if suggestions:
        st.caption("Cultures déjà référencées (suggestions) : " + " · ".join(suggestions))
    return value.strip()


def db_insert(table: str, payload: dict) -> bool:
    try:
        data = dict(payload)
        owner = st.session_state.get("cra_user_email")
        if owner and table != "cra_users":
            data.setdefault("owner_email", owner)
        DB.table(table).insert(data).execute()
        return True
    except Exception as exc:
        st.error(f"Enregistrement {table} : {exc}")
        return False


def db_update(table: str, row_id: str, payload: dict) -> bool:
    try:
        DB.table(table).update(payload).eq("id", row_id).execute()
        return True
    except Exception as exc:
        st.error(f"Modification {table} : {exc}")
        return False


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value, flags=re.I).strip("-")
    return value or uuid.uuid4().hex[:8]


def as_csv(data: list[dict]) -> bytes:
    return pd.DataFrame(data).to_csv(index=False).encode("utf-8-sig")


def download_button(label, data, file_name=None, mime=None, **kwargs):
    """Prépare un téléchargement non vide et évite les faux avertissements.

    Un bouton désactivé (ex. aucune sélection) ne doit jamais être traité comme
    un fichier vide. Les générateurs Excel/PDF renvoient des bytes ; les flux
    BytesIO sont lus avec getvalue(), sans dépendre de leur curseur.
    """
    try:
        disabled = bool(kwargs.get("disabled", False))
        if data is None:
            if disabled:
                st.download_button(label=label, data=b"", file_name=file_name,
                                   mime=mime or "application/octet-stream", **kwargs)
                return
            st.error(f"Le contenu de « {file_name or label} » n'a pas été généré. Relancez l'export.")
            return
        if isinstance(data, BytesIO):
            payload = data.getvalue()
        elif isinstance(data, memoryview):
            payload = data.tobytes()
        elif isinstance(data, bytearray):
            payload = bytes(data)
        elif isinstance(data, bytes):
            payload = data
        elif isinstance(data, pd.DataFrame):
            payload = data.to_csv(index=False).encode("utf-8-sig")
            mime = mime or "text/csv"
        elif isinstance(data, str):
            payload = data.encode("utf-8")
        else:
            payload = bytes(data)
        if not payload:
            if disabled:
                st.download_button(label=label, data=b"", file_name=file_name,
                                   mime=mime or "application/octet-stream", **kwargs)
            else:
                st.error(f"L'export « {file_name or label} » a produit 0 octet. La génération doit être relancée.")
            return
        st.download_button(label=label, data=payload, file_name=file_name,
                           mime=mime or "application/octet-stream", **kwargs)
    except Exception as exc:
        st.error(f"Téléchargement impossible pour « {file_name or label} » : {type(exc).__name__}: {exc}")


def two_sheet_fiche_excel(title, metadata, grid_frame, grid_title="Grille"):
    """Classeur standard à exactement deux feuilles : Présentation et Grilles."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    wb = Workbook()
    ws = wb.active
    ws.title = "Présentation"
    wg = wb.create_sheet("Grilles")
    dark, green, mint, pale, white = "16483F", "247A66", "BFE9DE", "EFF9F5", "FFFFFF"
    thin = Side(style="thin", color="9CCDBD")

    def banner(sheet, title_text, ncols):
        ncols = max(2, ncols)
        last = get_column_letter(ncols)
        for row, text, fill, size in [
            (1, "INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES — ISRA", dark, 12),
            (2, "CENTRE DE RECHERCHES AGRICOLES — SAINT-LOUIS", green, 11),
            (3, title_text, mint, 14),
            (4, f"Document scientifique · {datetime.now().strftime('%d/%m/%Y %H:%M')} · {CONTACT_EMAIL}", pale, 9),
        ]:
            sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
            c = sheet.cell(row, 1, text)
            c.fill = PatternFill("solid", fgColor=fill)
            c.font = Font(name="Aptos", size=size, bold=(row != 4), italic=(row == 4),
                          color=white if row in (1, 2) else dark)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            sheet.row_dimensions[row].height = 27 if row != 4 else 22
        sheet.sheet_view.showGridLines = False

    banner(ws, f"PRÉSENTATION — {title}", 4)
    ws.append([])
    ws.append(["Rubrique", "Valeur", "Rubrique", "Valeur"])
    for c in ws[6]:
        c.fill = PatternFill("solid", fgColor=green)
        c.font = Font(bold=True, color=white)
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    items = [(str(k).replace("_", " ").capitalize(),
              json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (dict, list, tuple)) else ("" if v is None else str(v)))
             for k, v in metadata.items() if k not in {"grid", "observations_periodiques", "headers", "observations_headers", "types", "owner_email"}]
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i+1] if i+1 < len(items) else ("", "")
        ws.append([left[0], left[1], right[0], right[1]])
        r = ws.max_row
        for c in ws[r]:
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.font = Font(name="Aptos", size=9, color=dark)
            if c.column in (1, 3):
                c.fill = PatternFill("solid", fgColor=mint)
                c.font = Font(name="Aptos", size=9, bold=True, color=dark)
            else:
                c.fill = PatternFill("solid", fgColor=pale)
        ws.row_dimensions[r].height = 30
    for col, width in {1:25, 2:48, 3:25, 4:48}.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A7"
    banner(wg, f"{grid_title.upper()} — {title}", max(2, len(grid_frame.columns)))
    frame = grid_frame.copy() if isinstance(grid_frame, pd.DataFrame) else pd.DataFrame(grid_frame)
    if len(frame.columns) == 0:
        frame = pd.DataFrame(columns=["Observation"])
    # Conserver strictement l'ordre et les noms des colonnes définies par l'utilisateur.
    for j, name in enumerate(frame.columns, 1):
        c = wg.cell(6, j, str(name))
        c.fill = PatternFill("solid", fgColor=green)
        c.font = Font(bold=True, color=white)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    if frame.empty:
        wg.cell(7, 1, "Aucune ligne de données saisie")
    else:
        for ri, vals in enumerate(frame.fillna("").itertuples(index=False, name=None), 7):
            for ci, val in enumerate(vals, 1):
                c = wg.cell(ri, ci, val.item() if hasattr(val, "item") else val)
                c.font = Font(name="Aptos", size=9, color=dark)
                c.alignment = Alignment(vertical="top", wrap_text=True)
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                if ri % 2 == 1:
                    c.fill = PatternFill("solid", fgColor=pale)
    for ci, name in enumerate(frame.columns, 1):
        vals = [str(name)] + [str(x) for x in frame.iloc[:, ci-1].head(100).tolist()]
        wg.column_dimensions[get_column_letter(ci)].width = min(34, max(14, max(map(len, vals), default=14) + 2))
    wg.freeze_panes = "A7"
    for sheet in (ws, wg):
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.page_margins = PageMargins(left=.25, right=.25, top=.45, bottom=.45, header=.2, footer=.2)
        sheet.oddFooter.center.text = "ISRA · CRA SAINT-LOUIS | YAM GROUP — YAM NUMÉRIQUE"
        sheet.print_title_rows = "1:6"
    output = BytesIO()
    wb.save(output)
    result = output.getvalue()
    if not result or not result.startswith(b"PK"):
        raise RuntimeError("Le classeur Excel n'a pas été généré correctement.")
    return result


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Exporte Excel institutionnel : en-tête ISRA/CRA, métadonnées et tableau structuré.

    Chaque module conserve une feuille unique lorsqu'un seul tableau est exporté.
    Les exports globaux gardent leurs feuilles séparées, avec la même identité visuelle.
    Mise en page A4 paysage, largeur ajustée et impression lisible sur plusieurs pages si nécessaire.
    """
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for raw_name, raw_frame in sheets.items():
            sheet_name = str(raw_name)[:31] or "Données"
            frame = raw_frame.copy() if isinstance(raw_frame, pd.DataFrame) else pd.DataFrame(raw_frame)
            if frame.empty and len(frame.columns) == 0:
                frame = pd.DataFrame([{"Information": "Aucune donnée enregistrée"}])
            frame.to_excel(writer, sheet_name=sheet_name, index=False, startrow=4)
            ws = writer.book[sheet_name]
            ncols = max(1, len(frame.columns))
            last_col = get_column_letter(ncols)

            # Bandeaux institutionnels et titre de l'export
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
            ws.cell(1, 1, "INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES — ISRA")
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
            ws.cell(2, 1, "CENTRE DE RECHERCHES AGRICOLES — SAINT-LOUIS")
            ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=ncols)
            ws.cell(3, 1, str(raw_name).upper())
            ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=ncols)
            ws.cell(4, 1, f"Export scientifique · {datetime.now().strftime('%d/%m/%Y %H:%M')} · Contact : {CONTACT_EMAIL}")

            dark = "16483F"; green = "247A66"; water = "BFE9DE"; pale = "EFF9F5"; gold = "DDB64C"
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor=dark); cell.font = Font(name="Aptos", size=12, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for cell in ws[2]:
                cell.fill = PatternFill("solid", fgColor=green); cell.font = Font(name="Aptos", size=11, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for cell in ws[3]:
                cell.fill = PatternFill("solid", fgColor=water); cell.font = Font(name="Aptos Display", size=14, bold=True, color=dark)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for cell in ws[4]:
                cell.fill = PatternFill("solid", fgColor="F4FAF7"); cell.font = Font(name="Aptos", size=9, italic=True, color=dark)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 25; ws.row_dimensions[2].height = 22
            ws.row_dimensions[3].height = 30; ws.row_dimensions[4].height = 21

            thin = Side(style="thin", color="9CCDBD")
            for cell in ws[5]:
                cell.fill = PatternFill("solid", fgColor=green)
                cell.font = Font(name="Aptos", size=10, bold=True, color="FFFFFF")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            ws.row_dimensions[5].height = 30
            for row_idx in range(6, ws.max_row + 1):
                ws.row_dimensions[row_idx].height = 24
                first_value = str(ws.cell(row_idx, 1).value or "").strip()
                second_value = str(ws.cell(row_idx, 2).value or "").strip() if ncols >= 2 else ""
                is_section = (first_value in {"INFORMATIONS DE LA FICHE"} or
                              (first_value.isupper() and bool(first_value) and
                               ("GRILLE" in first_value or "OBSERVATION" in first_value or
                                "MESURE" in first_value or "QUESTION" in first_value or
                                "RÉPONSE" in first_value or "REPONSE" in first_value or
                                "MODALITÉ" in first_value or "MODALITE" in first_value)))
                is_grid_header = first_value == "N° ligne"
                for cell in ws[row_idx]:
                    cell.font = Font(name="Aptos", size=9, color="18352A")
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                    if is_section:
                        cell.fill = PatternFill("solid", fgColor=green)
                        cell.font = Font(name="Aptos", size=9, bold=True, color="FFFFFF")
                    elif is_grid_header:
                        cell.fill = PatternFill("solid", fgColor="BFE9DE")
                        cell.font = Font(name="Aptos", size=9, bold=True, color=dark)
                    elif row_idx % 2 == 0:
                        cell.fill = PatternFill("solid", fgColor=pale)

            for col_idx in range(1, ncols + 1):
                values = [str(ws.cell(r, col_idx).value or "") for r in range(5, min(ws.max_row, 100) + 1)]
                width = min(max(max([len(v) for v in values] + [12]) + 2, 14), 34)
                ws.column_dimensions[get_column_letter(col_idx)].width = width
            ws.freeze_panes = "A6"
            ws.auto_filter.ref = f"A5:{last_col}{max(5, ws.max_row)}"
            ws.sheet_view.showGridLines = False
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.page_setup.orientation = "landscape"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.45, bottom=0.45, header=0.2, footer=0.2)
            ws.print_title_rows = "1:5"
            ws.print_area = f"A1:{last_col}{max(5, ws.max_row)}"
            ws.oddHeader.center.text = "&BISRA / CRA SAINT-LOUIS"
            ws.oddFooter.center.text = f"ISRA · CRA SAINT-LOUIS | YAM GROUP — YAM NUMÉRIQUE | {CONTACT_EMAIL}"
    result = output.getvalue()
    if not result or not result.startswith(b"PK"):
        raise RuntimeError("Le classeur Excel n'a pas été généré correctement.")
    return result


def pdf_bytes(title: str, frame: pd.DataFrame) -> bytes:
    """Rapport PDF institutionnel robuste, y compris pour les tableaux très larges."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, LongTable, TableStyle, PageBreak
        from reportlab.lib.units import mm
        from xml.sax.saxutils import escape

        out = BytesIO()
        doc = SimpleDocTemplate(
            out, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm,
            topMargin=25*mm, bottomMargin=20*mm, title=str(title),
            author="ISRA — CRA Saint-Louis | YAM Group — YAM Numérique"
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "YAMReportTitleSafe", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, alignment=TA_CENTER,
            textColor=colors.HexColor("#16483F"), spaceAfter=6
        )
        subtitle = ParagraphStyle(
            "YAMSubtitleSafe", parent=styles["Normal"], fontSize=8, leading=10,
            alignment=TA_CENTER, textColor=colors.HexColor("#6B9B8D"), spaceAfter=6
        )
        cell = ParagraphStyle(
            "YAMCellSafe", parent=styles["BodyText"], fontName="Helvetica",
            fontSize=7.5, leading=9, wordWrap="CJK", splitLongWords=1,
            spaceBefore=0, spaceAfter=0
        )
        head = ParagraphStyle(
            "YAMHeadSafe", parent=cell, fontName="Helvetica-Bold",
            textColor=colors.white
        )
        story = [
            Paragraph("INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES", subtitle),
            Paragraph("ISRA · CENTRE DE RECHERCHES AGRICOLES DE SAINT-LOUIS", subtitle),
            Paragraph(escape(str(title)), title_style),
            Paragraph("DOCUMENT SCIENTIFIQUE · COLLECTE, EXPÉRIMENTATION ET TRAÇABILITÉ", subtitle),
            Spacer(1, 4*mm)
        ]

        if frame is None or frame.empty:
            rows = [[Paragraph("Rubrique", head), Paragraph("Information", head)],
                    [Paragraph("État", cell), Paragraph("Aucune donnée enregistrée", cell)]]
        else:
            # Format vertical en deux colonnes : évite les tableaux de 20 à 30 colonnes
            # dont les cellules deviennent trop étroites et dépassent la hauteur d'une page.
            rows = [[Paragraph("Rubrique", head), Paragraph("Information", head)]]
            safe_frame = frame.fillna("").astype(str)
            for record_no, values in enumerate(safe_frame.itertuples(index=False, name=None), start=1):
                if len(safe_frame) > 1:
                    rows.append([
                        Paragraph("<b>Enregistrement " + str(record_no) + "</b>", cell),
                        Paragraph("", cell)
                    ])
                for column_name, value in zip(safe_frame.columns, values):
                    text_value = str(value).replace("\r\n", "\n").replace("\r", "\n")
                    # Fractionne les contenus très longs en plusieurs lignes PDF paginables.
                    text_value = text_value[:12000]
                    pieces = []
                    while len(text_value) > 700:
                        cut = text_value.rfind(" ", 0, 700)
                        if cut < 350:
                            cut = 700
                        pieces.append(text_value[:cut])
                        text_value = text_value[cut:].lstrip()
                    pieces.append(text_value)
                    for piece_no, piece in enumerate(pieces):
                        label = str(column_name) if piece_no == 0 else str(column_name) + " (suite)"
                        rows.append([
                            Paragraph(escape(label), cell),
                            Paragraph(escape(piece).replace("\n", "<br/>") or "—", cell)
                        ])

        table = LongTable(
            rows, colWidths=[48*mm, doc.width-48*mm], repeatRows=1,
            hAlign="LEFT", splitByRow=1
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#247A66")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,1), (0,-1), colors.HexColor("#EFF9F5")),
            ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#8BB9AA")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(table)

        def decorate(canvas, document):
            canvas.saveState()
            w, h = landscape(A4)
            canvas.setFillColor(colors.HexColor("#16483F"))
            canvas.rect(0, h-13*mm, w, 13*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(12*mm, h-8.5*mm, "ISRA  |  CRA SAINT-LOUIS")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(w-12*mm, h-8.5*mm, "RECHERCHE AGRICOLE & INNOVATION")
            canvas.setStrokeColor(colors.HexColor("#DDB64C"))
            canvas.setLineWidth(2)
            canvas.line(12*mm, 15*mm, w-12*mm, 15*mm)
            canvas.setFillColor(colors.HexColor("#16483F"))
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(12*mm, 9*mm, "YAM GROUP · YAM NUMÉRIQUE")
            canvas.setFont("Helvetica", 7)
            canvas.drawRightString(w-12*mm, 9*mm, f"Document scientifique · Page {document.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
        return out.getvalue()
    except Exception as exc:
        st.error(f"Génération PDF impossible : {exc}. Vérifiez la dépendance reportlab.")
        return b""


def _normalize_grid_rows(value: Any) -> list[dict]:
    """Normalise les grilles natives, JSON et anciens formats tabulaires."""
    if value is None:
        return []
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8-sig")
        except Exception:
            return []
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            value = json.loads(raw)
            if isinstance(value, str) and value.strip() != raw:
                return _normalize_grid_rows(value)
        except Exception:
            try:
                from io import StringIO
                value = pd.read_csv(StringIO(raw), sep=None, engine="python").to_dict(orient="records")
            except Exception:
                return [{"Valeur": value}]
    if isinstance(value, pd.DataFrame):
        return value.fillna("").to_dict(orient="records")
    if isinstance(value, dict):
        headers = value.get("headers") or value.get("columns") or value.get("colonnes")
        for key in ("rows", "data", "records", "items", "values", "grid",
                    "observations_periodiques", "payload"):
            nested = value.get(key)
            if nested is not None and nested is not value:
                parsed = _normalize_grid_rows(nested)
                if parsed:
                    if headers and isinstance(headers, (list, tuple)):
                        names = [str(h) for h in headers]
                        converted = []
                        for row in parsed:
                            if all(f"Colonne {i+1}" in row for i in range(len(names))):
                                converted.append({name:row.get(f"Colonne {i+1}","")
                                                  for i,name in enumerate(names)})
                            else:
                                converted.append({name: row.get(name, "") for name in names} |
                                                 {k:v for k,v in row.items() if k not in names})
                        return converted
                    return parsed
        # Certains anciens enregistrements stockent une grille en format
        # colonne : {"Date": [..], "Mesure": [..]}. Le format orient="records"
        # utilisé par les nouveaux formulaires est déjà traité plus bas.
        column_values = {
            str(key): item for key, item in value.items()
            if isinstance(item, (list, tuple))
        }
        if column_values and len(column_values) == len(value):
            row_count = max((len(items) for items in column_values.values()), default=0)
            if row_count:
                return [
                    {column: (items[row_index] if row_index < len(items) else "")
                     for column, items in column_values.items()}
                    for row_index in range(row_count)
                ]
        # Certains systèmes stockent la matrice sous {headers: [...], data: [[...]]}.
        if isinstance(headers, (list, tuple)):
            matrix = value.get("data") or value.get("rows") or value.get("values")
            if isinstance(matrix, (list, tuple)):
                converted = []
                for row in matrix:
                    if isinstance(row, dict):
                        converted.append({str(k): v for k, v in row.items()})
                    elif isinstance(row, (list, tuple)):
                        converted.append({str(headers[i]): row[i] if i < len(row) else ""
                                          for i in range(len(headers))})
                if converted:
                    return converted
        if all(not isinstance(v, (dict, list, tuple)) for v in value.values()):
            return [value]
        return []
    if isinstance(value, (list, tuple)):
        rows = []
        for item in value:
            if isinstance(item, str):
                try: item = json.loads(item)
                except Exception: pass
            if isinstance(item, dict):
                row = item
            elif isinstance(item, (list, tuple)):
                row = {f"Colonne {i+1}": v for i,v in enumerate(item)}
            else:
                row = {"Valeur": item}
            has_value = False
            for cell in row.values():
                if cell is None or (isinstance(cell, str) and not cell.strip()):
                    continue
                try:
                    if pd.isna(cell):
                        continue
                except Exception:
                    pass
                has_value = True
                break
            if has_value:
                rows.append(row)
        return rows
    return [{"Valeur": value}]


def _plain_export_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return "" if value is None else value


def password_hash(password: str) -> str:
    salt = uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240000).hex()
    return f"{salt}${digest}"


def password_ok(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240000).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False


# ---------------------------------------------------------------------
# FORMULAIRE PUBLIC : ?form=IDENTIFIANT
# ---------------------------------------------------------------------
def _normalise_form_id(value: Any) -> str:
    """Normalise l'identifiant transmis par le lien public."""
    return str(value or "").strip().strip("{}[]()")


def _question_options(question: dict) -> list[str]:
    raw = question.get("options", [])
    if isinstance(raw, str):
        return [x.strip() for x in raw.split("|") if x.strip()]
    if isinstance(raw, (list, tuple)):
        return [str(x).strip() for x in raw if str(x).strip()]
    return []


@st.cache_data(ttl=45, show_spinner=False)
def _load_public_questionnaire(form_id: str):
    """Cache court pour éviter de relire Supabase à chaque rerun du formulaire."""
    return DB.table("cra_forms").select("*").eq("id", form_id).limit(1).execute().data or []


def render_public_form(form_id: str) -> None:
    """Affiche un questionnaire public et enregistre une réponse liée au bon formulaire."""
    form_id = _normalise_form_id(form_id)
    heading("Réponse externe sécurisée", "Questionnaire à remplir",
            "Complétez les champs demandés puis envoyez votre réponse au CRA Saint-Louis.")
    if not form_id:
        st.error("Le lien ne contient pas d'identifiant de questionnaire.")
        st.stop()
    try:
        # Les tables métier autonomes stockent le document dans payload JSONB.
        forms = _load_public_questionnaire(form_id)
    except Exception as exc:
        st.error(f"Impossible de charger ce questionnaire depuis Supabase : {exc}")
        st.stop()
    if not forms:
        st.error("Questionnaire introuvable. Le lien peut être ancien ou l'identifiant absent de Supabase.")
        st.caption("Demandez au créateur de rouvrir le questionnaire dans « Questionnaires et réponses » et de recopier son lien public.")
        st.stop()

    form = forms[0]
    active_value = form.get("active", True)
    if active_value is False or str(active_value).strip().lower() in {"false", "0", "non", "désactivé", "desactive"}:
        st.warning("Ce questionnaire est actuellement désactivé par son créateur.")
        st.stop()
    if st.session_state.get(f"questionnaire_submitted_{form_id}"):
        st.success("Votre réponse a déjà été enregistrée. Ce questionnaire est désactivé pour cette session.")
        st.stop()
    questions = form.get("questions") or []
    if not isinstance(questions, list) or not questions:
        st.error("Ce questionnaire existe, mais aucune question exploitable n'est enregistrée. Modifiez-le ou recréez-le.")
        st.stop()

    st.markdown(f"### {form.get('title') or 'Questionnaire ISRA / CRA'}")
    if form.get("description"):
        st.write(form["description"])
    st.caption("Les champs marqués * sont obligatoires.")
    form_contact_email = str(form.get("contact_email") or CONTACT_EMAIL).strip()
    st.markdown(f"**Contact :** [{form_contact_email}](mailto:{form_contact_email})")

    # Identifiant aléatoire conservé dans la session Streamlit : empêche un second envoi
    # depuis la même session, y compris lorsque le répondant choisit l'anonymat.
    if f"questionnaire_token_{form_id}" not in st.session_state:
        st.session_state[f"questionnaire_token_{form_id}"] = uuid.uuid4().hex
    respondent_token = st.session_state[f"questionnaire_token_{form_id}"]
    answers_by_id: dict[str, Any] = {}
    answers_by_label: dict[str, Any] = {}
    question_labels: dict[str, str] = {}
    with st.form(f"public_form_{form_id}", clear_on_submit=False):
        anonymous = st.checkbox("Répondre anonymement (ne pas enregistrer mon nom ni mes coordonnées)", value=False, disabled=not form.get("allow_anonymous", True), key=f"anonymous_{form_id}")
        respondent = st.text_input("Nom / structure du répondant" + ("" if anonymous else " *"), key=f"respondent_{form_id}", disabled=anonymous)
        contact = st.text_input("Téléphone ou adresse e-mail (facultatif)", key=f"contact_{form_id}", disabled=anonymous)
        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            label = str(question.get("label") or question.get("question") or f"Question {i+1}").strip()
            qid = str(question.get("id") or f"q_{i+1}")
            qtype = str(question.get("type") or "Texte court")
            required = question.get("required", question.get("obligatoire", False))
            required = required is True or str(required).strip().lower() in {"true", "1", "oui", "yes"}
            label_ui = label + (" *" if required else "")
            widget_key = f"answer_{form_id}_{qid}_{i}"
            if qtype == "Texte long":
                value = st.text_area(label_ui, key=widget_key)
            elif qtype == "Nombre":
                value = st.number_input(label_ui, value=0.0, key=widget_key)
            elif qtype == "Date":
                value = st.date_input(label_ui, value=date.today(), key=widget_key).isoformat()
            elif qtype == "Oui / Non":
                value = st.radio(label_ui, ["Oui", "Non"], horizontal=True, key=widget_key)
            elif qtype == "Choix unique":
                options = _question_options(question)
                value = st.selectbox(label_ui, options or ["Aucune option définie"], key=widget_key)
            elif qtype == "Choix multiple":
                options = _question_options(question)
                value = st.multiselect(label_ui, options, key=widget_key)
            else:
                value = st.text_input(label_ui, key=widget_key)
            answers_by_id[qid] = value
            answers_by_label[label] = value
            question_labels[qid] = label
        send = st.form_submit_button("📨 Envoyer ma réponse", type="primary", use_container_width=True)

    if send:
        missing = []
        if not anonymous and not respondent.strip():
            missing.append("Nom / structure du répondant")
        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            label = str(question.get("label") or question.get("question") or f"Question {i+1}").strip()
            qid = str(question.get("id") or f"q_{i+1}")
            required = question.get("required", question.get("obligatoire", False))
            required = required is True or str(required).strip().lower() in {"true", "1", "oui", "yes"}
            answer = answers_by_id.get(qid)
            empty = answer is None or answer == "" or answer == []
            if required and empty:
                missing.append(label)
        if missing:
            st.error("Veuillez compléter les champs obligatoires : " + ", ".join(missing))
        else:
            payload = {
                "id": uuid.uuid4().hex,
                "form_id": form_id,
                "form_title": str(form.get("title") or "Questionnaire ISRA / CRA"),
                "anonymous": bool(anonymous),
                "respondent_token": respondent_token,
                "respondent": "" if anonymous else respondent.strip(),
                "contact": "" if anonymous else contact.strip(),
                # answers conserve le format historique pour les exports existants.
                "answers": answers_by_label,
                # answers_by_id évite les collisions si deux questions ont le même libellé.
                "answers_by_id": answers_by_id,
                "question_labels": question_labels,
                "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "owner_email": form.get("owner_email", ""),
            }
            # Contrôle côté serveur avant insertion : une seule réponse par session/répondant.
            try:
                prior = DB.table("cra_responses").select("id,respondent_token,respondent,contact").eq("form_id", form_id).execute().data or []
            except Exception as lookup_error:
                prior = None
                st.error(f"Impossible de vérifier si une réponse existe déjà : {lookup_error}")
            if prior is not None:
                duplicate = any(
                    str(row.get("respondent_token") or "") == respondent_token
                    or (not anonymous and str(row.get("respondent") or "").strip().casefold() == respondent.strip().casefold()
                        and str(row.get("contact") or "").strip().casefold() == contact.strip().casefold())
                    for row in prior
                )
                if duplicate:
                    st.warning("Une réponse a déjà été enregistrée pour ce questionnaire depuis cette session ou avec ces coordonnées. Une seule tentative est autorisée.")
                    st.session_state[f"questionnaire_submitted_{form_id}"] = True
                elif db_insert("cra_responses", payload):
                    st.session_state[f"questionnaire_submitted_{form_id}"] = True
                    _load_public_questionnaire.clear()
                    st.success("Votre réponse a bien été enregistrée. Merci pour votre participation.")
                    st.info("Cette session est maintenant désactivée pour ce questionnaire. Vous pouvez fermer cette page.")
                else:
                    st.error("La réponse n'a pas pu être enregistrée. Vérifiez votre connexion ou contactez le CRA.")
    st.markdown("---")
    st.caption(f"ISRA · CRA Saint-Louis — Collecte de données pour la recherche agricole. Contact : {CONTACT_EMAIL}")
    st.stop()


# ---------------------------------------------------------------------
# AUTHENTIFICATION ET ESPACES PERSONNELS STRICTEMENT PRIVÉS
# ---------------------------------------------------------------------
if "cra_authenticated" not in st.session_state:
    st.session_state.cra_authenticated = False

# Lien public de questionnaire : seules les réponses sont enregistrées dans l'espace
# du créateur du questionnaire ; les répondants n'accèdent pas aux autres données.
query_form = st.query_params.get("form")
if query_form:
    render_public_form(str(query_form))

if not st.session_state.cra_authenticated:
    heading("Accès sécurisé ISRA", "Connexion à votre espace personnel",
            "Chercheur · Stagiaire · Technicien — chaque compte dispose de ses propres données privées.")
    st.markdown('<div class="card"><b>Confidentialité :</b> un compte ne peut consulter, modifier ou exporter que les données qu’il a lui-même créées. Les autres comptes ne voient ni ses fiches, ni ses essais, ni ses réponses.</div>', unsafe_allow_html=True)
    st.info("Connexion centralisée Supabase PostgreSQL : les accès sont journalisés et les données sont isolées par compte.")
    with st.form("cra_login"):
        login_email = st.text_input("Identifiant / e-mail", value="")
        login_password = st.text_input("Mot de passe", type="password")
        login_submit = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
    if login_submit:
        try:
            admin_email = CRA_ADMIN_EMAIL.strip().lower()
            admin_password = CRA_ADMIN_PASSWORD
            if login_email.strip().lower() == admin_email and admin_password and hmac.compare_digest(login_password, admin_password):
                found = DB.table("cra_users").select("*").eq("email", admin_email).limit(1).execute().data or []
                if not found:
                    DB.table("cra_users").insert({"email":admin_email,"display_name":"Administration CRA","role":"Administrateur des comptes","password_hash":password_hash(admin_password),"active":True,"permissions":["*"]}).execute()
                    found = DB.table("cra_users").select("*").eq("email", admin_email).limit(1).execute().data or []
                user = found[0]
            else:
                found = DB.table("cra_users").select("*").eq("email", login_email.strip().lower()).eq("active", True).limit(1).execute().data or []
                user = found[0] if found and password_ok(login_password, found[0].get("password_hash", "")) else None
            if user:
                st.session_state.cra_authenticated = True
                st.session_state.cra_user_email = user["email"]
                st.session_state.cra_user_name = user.get("display_name") or user["email"]
                st.session_state.cra_user_role = user.get("role", "Chercheur")
                permissions = user.get("permissions", [])
                if isinstance(permissions, str):
                    try: permissions = json.loads(permissions)
                    except Exception: permissions = []
                st.session_state.cra_user_permissions = permissions
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect, ou compte désactivé.")
        except Exception as exc:
            st.error(f"Échec de connexion : {exc}")
    st.stop()

# Relecture des droits à chaque actualisation : une révocation est prise en compte
# sans attendre une nouvelle connexion de l'utilisateur.
try:
    _cached_auth=st.session_state.get("_cra_auth_check")
    if _cached_auth and _cached_auth.get("email")==st.session_state.get("cra_user_email") and time.monotonic()-_cached_auth.get("at",0)<30:
        fresh_user=[_cached_auth["user"]]
    else:
        fresh_user = DB.table("cra_users").select("*").eq("email", st.session_state.get("cra_user_email", "")).limit(1).execute().data or []
        if fresh_user:
            st.session_state["_cra_auth_check"]={"email":st.session_state.get("cra_user_email"),"at":time.monotonic(),"user":fresh_user[0]}
    if not fresh_user or not fresh_user[0].get("active", True):
        for key in ["cra_authenticated", "cra_user_email", "cra_user_name", "cra_user_role", "cra_user_permissions"]:
            st.session_state.pop(key, None)
        st.error("Ce compte est désactivé ou n'existe plus. Veuillez vous reconnecter ou contacter l'administration.")
        st.stop()
    st.session_state.cra_user_name = fresh_user[0].get("display_name") or fresh_user[0]["email"]
    st.session_state.cra_user_role = fresh_user[0].get("role", "Chercheur")
    refreshed_permissions = fresh_user[0].get("permissions", [])
    if isinstance(refreshed_permissions, str):
        try: refreshed_permissions = json.loads(refreshed_permissions)
        except Exception: refreshed_permissions = []
    st.session_state.cra_user_permissions = refreshed_permissions
except Exception as exc:
    st.error(f"Impossible de vérifier les autorisations du compte : {exc}")
    st.stop()

# Bandeau compact du compte connecté et déconnexion
u1, u2, u3 = st.columns([3, 2, 1])
u1.caption(f"👤 {st.session_state.get('cra_user_name')}  ·  {st.session_state.get('cra_user_email')}")
u2.caption(f"Profil : {st.session_state.get('cra_user_role', 'Utilisateur')}")
if u3.button("Déconnexion", use_container_width=True):
    for key in ["cra_authenticated", "cra_user_email", "cra_user_name", "cra_user_role", "cra_user_permissions"]:
        st.session_state.pop(key, None)
    st.rerun()



# ---------------------------------------------------------------------
# NAVIGATION — GRANDS ONGLET EN HAUT / SOUS-ONGLETS EN DESSOUS
# ---------------------------------------------------------------------
PAGES = [
    "Tableau de bord", "Mes dossiers", "Fiche technique", "Fiche de mesure",
    "Pointage",
    "Référentiel des cultures", "Essais expérimentaux XXL",
    "Diagnostic phytosanitaire XXL", "Créer un questionnaire",
    "Questionnaires et réponses", "Données et exports",
    "Dossiers de culture", "Collaboration", "Journal d’audit", "Gestion des comptes",
]
ADMIN_PAGES = ["Journal d’audit", "Gestion des comptes"]
USER_PAGES = [p for p in PAGES if p not in ADMIN_PAGES]

# Les droits enregistrés par l'administrateur portent sur les sous-onglets.
# Un grand onglet n'apparaît que s'il contient au moins un sous-onglet autorisé.
is_admin = st.session_state.get("cra_user_role") == "Administrateur des comptes"
if is_admin:
    allowed_pages = PAGES[:]
else:
    saved_permissions = st.session_state.get("cra_user_permissions", [])
    if isinstance(saved_permissions, str):
        try:
            saved_permissions = json.loads(saved_permissions)
        except Exception:
            saved_permissions = []
    if not isinstance(saved_permissions, (list, tuple, set)):
        saved_permissions = []

    # Le joker donne accès aux rubriques de travail, jamais à l'administration.
    if "*" in saved_permissions:
        allowed_pages = USER_PAGES[:]
    else:
        allowed_pages = [p for p in USER_PAGES if p in saved_permissions]
        # L'espace de dossiers complète l'accueil pour les comptes ayant accès
        # à au moins un module de travail, y compris les comptes déjà créés.
        if any(p in allowed_pages for p in USER_PAGES if p != "Mes dossiers"):
            if "Mes dossiers" not in allowed_pages:
                allowed_pages.insert(0, "Mes dossiers")
        # La rubrique Pointage a été ajoutée après la création de certains comptes.
        # On l'ouvre aux comptes qui ont déjà l'accès aux outils de saisie ou d'export.
        if any(p in saved_permissions for p in ("Fiche technique", "Fiche de mesure", "Données et exports")):
            if "Pointage" not in allowed_pages:
                allowed_pages.append("Pointage")

    # Aucun droit attribué = aucun module affiché. On ne réactive pas
    # silencieusement des rubriques que l'administrateur aurait désactivées.
    if not allowed_pages:
        st.warning("Aucune rubrique ne vous a été attribuée pour le moment.")
        st.info("Contactez l'administrateur de la plateforme pour demander l'ouverture des modules nécessaires.")
        st.stop()

NAV_GROUPS = {
    "🏠 ACCUEIL": ["Tableau de bord", "Mes dossiers"],
    "🧾 SAISIE SCIENTIFIQUE": ["Fiche technique", "Fiche de mesure", "Pointage"],
    "🌱 CULTURES & EXPÉRIMENTATION": [
        "Référentiel des cultures", "Essais expérimentaux XXL", "Diagnostic phytosanitaire XXL"
    ],
    "📋 QUESTIONNAIRES": ["Créer un questionnaire", "Questionnaires et réponses"],
    "📁 DOSSIERS & PARTAGE": ["Dossiers de culture", "Collaboration"],
    "📊 DONNÉES & RAPPORTS": ["Données et exports"],
    "⚙️ ADMINISTRATION": ["Journal d’audit", "Gestion des comptes"],
}

# Filtrage à deux niveaux : les grands onglets et leurs sous-onglets
# ne contiennent que les fonctionnalités autorisées au compte connecté.
visible_nav = {
    group: [page_name for page_name in pages if page_name in allowed_pages]
    for group, pages in NAV_GROUPS.items()
    if any(page_name in allowed_pages for page_name in pages)
}
nav_groups = list(visible_nav)
if not nav_groups:
    st.warning("Aucun espace de travail n'est disponible pour ce compte.")
    st.stop()

# Évite de conserver une ancienne sélection si l'administrateur vient
# de modifier les droits ou si l'utilisateur change de profil.
if st.session_state.get("cra_nav_group") not in nav_groups:
    st.session_state["cra_nav_group"] = nav_groups[0]
st.markdown('<div class="cra-mainnav-heading">GRANDS ESPACES DE TRAVAIL</div>', unsafe_allow_html=True)
selected_group = st.radio(
    "GRANDS ESPACES DE TRAVAIL",
    options=nav_groups,
    horizontal=True,
    key="cra_nav_group",
    label_visibility="collapsed",
)

page_options = visible_nav[selected_group]
if st.session_state.get("cra_nav_page") not in page_options:
    st.session_state["cra_nav_page"] = page_options[0]

PAGE_LABELS = {
    "Tableau de bord": "📌 Tableau de bord",
    "Mes dossiers": "📁 Mes dossiers",
    "Fiche technique": "📝 Fiche technique",
    "Fiche de mesure": "📏 Fiche de mesure",
    "Pointage": "🕘 Pointage du personnel",
    "Référentiel des cultures": "🌾 Référentiel des cultures",
    "Essais expérimentaux XXL": "🔬 Essais expérimentaux",
    "Diagnostic phytosanitaire XXL": "🩺 Diagnostic phytosanitaire",
    "Créer un questionnaire": "➕ Créer un questionnaire",
    "Questionnaires et réponses": "📨 Questionnaires et réponses",
    "Données et exports": "📊 Données et exports",
    "Dossiers de culture": "📁 Dossiers de culture",
    "Collaboration": "🤝 Collaboration",
    "Journal d’audit": "🛡️ Journal d’audit quotidien",
    "Gestion des comptes": "🔐 Gestion des comptes",
}

st.markdown('<div class="cra-subnav-heading">SOUS-ONGLETS DISPONIBLES</div>', unsafe_allow_html=True)
page = st.radio(
    "SOUS-ONGLETS AUTORISÉS",
    options=page_options,
    format_func=lambda value: PAGE_LABELS.get(value, value),
    horizontal=True,
    key="cra_nav_page",
    label_visibility="collapsed",
)

# Le dossier de classement est sélectionnable depuis chaque sous-onglet.
# Les formulaires existants reprennent automatiquement ce choix à l'insertion.
available_work_folders = db_rows("cra_culture_folders", 3000)
folder_choices = {"— Sans dossier —": None}
for _folder in available_work_folders:
    _folder_title = _folder.get("folder_name") or _folder.get("name") or "Dossier sans nom"
    _folder_label = f"{_folder_title} · {str(_folder.get('id', ''))[:8]}"
    folder_choices[_folder_label] = _folder
_active_folder_now = st.session_state.get("cra_active_workspace_folder") or {}
_active_folder_label = next(
    (label for label, folder in folder_choices.items() if folder and folder.get("id") == _active_folder_now.get("id")),
    "— Sans dossier —",
)
if page == "Mes dossiers" and _active_folder_label != "— Sans dossier —":
    st.session_state["cra_active_folder_global"] = _active_folder_label
elif "cra_active_folder_global" not in st.session_state:
    st.session_state["cra_active_folder_global"] = _active_folder_label
elif st.session_state.get("cra_active_folder_global") not in folder_choices:
    st.session_state["cra_active_folder_global"] = _active_folder_label
st.selectbox(
    "Dossier de classement pour les nouvelles saisies",
    list(folder_choices),
    key="cra_active_folder_global",
    help="Disponible dans tous les sous-onglets. Les nouvelles fiches et données seront classées dans le dossier choisi.",
)
_chosen_folder = folder_choices.get(st.session_state.get("cra_active_folder_global"))
if _chosen_folder:
    st.session_state["cra_active_workspace_folder"] = _chosen_folder
else:
    st.session_state.pop("cra_active_workspace_folder", None)

st.markdown("""
<style>
/* Grands onglets : bandeau supérieur, larges cartes cliquables */
.cra-mainnav-heading {
    margin: 10px 0 7px 3px;
    color: #16483F;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1.55px;
}
.cra-subnav-heading {
    margin: 13px 0 7px 3px;
    color: #16483F;
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 1.35px;
}
.st-key-cra_nav_group {
    background: linear-gradient(115deg, #F5FBF7, #FFFFFF);
    border: 1px solid #BFDCCB;
    border-top: 5px solid #DDB64C;
    border-radius: 18px;
    padding: 12px 14px 8px;
    margin: 8px 0 12px;
    box-shadow: 0 7px 20px rgba(22,72,63,.08);
}
.st-key-cra_nav_group [role="radiogroup"] {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    width: 100%;
}
.st-key-cra_nav_group label[data-baseweb="radio"] {
    flex: 1 1 145px;
    min-height: 58px;
    justify-content: center;
    padding: 10px 13px;
    color: #16483F;
    font-size: 14px;
    font-weight: 850;
    text-align: center;
    border: 1px solid #C8DDD0;
    border-radius: 14px;
    background: #FFFFFF;
    box-shadow: 0 3px 9px rgba(22,72,63,.05);
    transition: all .18s ease;
}
.st-key-cra_nav_group label[data-baseweb="radio"] > div:first-child,
.st-key-cra_nav_page label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}
.st-key-cra_nav_group label[data-baseweb="radio"]:hover {
    border-color: #247A66;
    background: #F0F8F3;
    transform: translateY(-1px);
}
.st-key-cra_nav_group label[data-baseweb="radio"]:has(input:checked) {
    background: linear-gradient(125deg, #16483F, #247A66);
    border-color: #16483F;
    box-shadow: 0 5px 13px rgba(22,72,63,.20);
}
.st-key-cra_nav_group label[data-baseweb="radio"]:has(input:checked) * {
    color: #FFFFFF !important;
    font-weight: 800 !important;
}

/* Sous-onglets : cadre distinct, plus léger que le bandeau principal */
.st-key-cra_nav_page {
    background: #FFFFFF;
    border: 1px solid #D6E7DC;
    border-left: 5px solid #247A66;
    border-radius: 16px;
    padding: 10px 13px 7px;
    margin: 0 0 14px;
    box-shadow: 0 5px 16px rgba(22,72,63,.06);
}
.st-key-cra_nav_page [role="radiogroup"] {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
}
.st-key-cra_nav_page label[data-baseweb="radio"] {
    flex: 0 1 auto;
    min-height: 43px;
    padding: 8px 13px;
    color: #16483F;
    font-size: 13px;
    font-weight: 700;
    border: 1px solid #CFE2D5;
    border-radius: 11px;
    background: #F8FCF9;
    transition: all .18s ease;
}
.st-key-cra_nav_page label[data-baseweb="radio"]:hover {
    border-color: #247A66;
    background: #EDF7F1;
}
.st-key-cra_nav_page label[data-baseweb="radio"]:has(input:checked) {
    background: #DFF0E6;
    border-color: #247A66;
    box-shadow: inset 0 0 0 1px #247A66;
}
.st-key-cra_nav_page label[data-baseweb="radio"]:has(input:checked) * {
    color: #16483F !important;
    font-weight: 800 !important;
}
@media (max-width: 700px) {
    .st-key-cra_nav_group, .st-key-cra_nav_page { padding: 9px; }
    .st-key-cra_nav_group label[data-baseweb="radio"] { flex: 1 1 100%; min-height: 47px; }
    .st-key-cra_nav_page label[data-baseweb="radio"] { flex: 1 1 100%; }
}
</style>
""", unsafe_allow_html=True)

st.caption(f"Espace ouvert : {selected_group}  ·  {len(page_options)} sous-onglet(s) autorisé(s)")
if DB_MESSAGE:
    st.caption(DB_MESSAGE)

# ---------------------------------------------------------------------
# TABLEAU DE BORD
# ---------------------------------------------------------------------
if page == "Tableau de bord":
    heading("Pilotage scientifique", "Tableau de bord",
            "Vue synthétique des fiches et des enquêtes enregistrées au CRA.")
    tech = db_rows("cra_technical_sheets")
    measures = db_rows("cra_measurement_sheets")
    forms = db_rows("cra_forms")
    responses = db_rows("cra_responses")
    trials = db_rows("cra_trials")
    diagnostics = db_rows("cra_phytosanitary_diagnostics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Fiches techniques", len(tech))
    c2.metric("Fiches de mesure", len(measures))
    c3.metric("Questionnaires", len(forms))
    c4.metric("Réponses", len(responses))
    c5.metric("Essais", len(trials))
    c6.metric("Diagnostics", len(diagnostics))
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Activité récente")
    recent = []
    for row in tech[:5]:
        recent.append({"Type": "Fiche technique", "Objet": row.get("culture", ""), "Date": row.get("created_at", "")})
    for row in measures[:5]:
        recent.append({"Type": "Fiche de mesure", "Objet": row.get("culture", ""), "Date": row.get("created_at", "")})
    for row in responses[:5]:
        recent.append({"Type": "Réponse questionnaire", "Objet": row.get("form_title", ""), "Date": row.get("submitted_at", "")})
    if recent:
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnée enregistrée pour le moment.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.info("Utilisez les modules ci-dessus pour saisir les fiches ou créer un questionnaire accessible par lien.")

elif page == "Mes dossiers":
    heading(
        "Accueil · classement général",
        "Mes dossiers de travail",
        "Créez un dossier, ouvrez-le, puis utilisez les modules habituels : les nouvelles saisies y seront automatiquement classées."
    )
    workspace_folders = db_rows("cra_culture_folders", 3000)
    with st.expander("＋ Créer un dossier de travail", expanded=not bool(workspace_folders)):
        with st.form("create_workspace_folder", clear_on_submit=True):
            wf1, wf2 = st.columns(2)
            with wf1:
                workspace_name = st.text_input("Nom du dossier *", placeholder="Ex. : Campagne riz 2026")
                workspace_culture = st.text_input("Thème / culture", placeholder="Ex. : Riz, suivi du personnel, enquête…")
            with wf2:
                workspace_campaign = st.text_input("Campagne / période", str(date.today().year))
                workspace_station = st.text_input("Site / station")
            workspace_description = st.text_area("Description / objectif")
            create_workspace = st.form_submit_button("📁 Créer le dossier", type="primary", use_container_width=True)
        if create_workspace:
            if not workspace_name.strip():
                st.error("Le nom du dossier est obligatoire.")
            else:
                created_folder = {
                    "folder_name": workspace_name.strip(),
                    "culture": workspace_culture.strip() or "Dossier général",
                    "campaign": workspace_campaign.strip(),
                    "station": workspace_station.strip(),
                    "description": workspace_description.strip(),
                    "responsible": st.session_state.get("cra_user_email", ""),
                    "owner_email": st.session_state.get("cra_user_email", ""),
                    "folder_type": "workspace",
                }
                if db_insert("cra_culture_folders", created_folder):
                    st.success("Dossier créé.")
                    st.rerun()

    workspace_folders = db_rows("cra_culture_folders", 3000)
    if not workspace_folders:
        st.info("Créez un dossier pour commencer à classer vos saisies.")
    else:
        folder_labels = {
            f"{f.get('folder_name') or f.get('name') or 'Dossier sans nom'} · {f.get('culture') or 'Général'} · {str(f.get('id',''))[:8]}": f
            for f in workspace_folders
        }
        current_folder = st.session_state.get("cra_active_workspace_folder") or {}
        default_label = next((label for label, f in folder_labels.items() if f.get("id") == current_folder.get("id")), next(iter(folder_labels)))
        selected_folder_label = st.selectbox("Choisir un dossier à ouvrir", list(folder_labels), index=list(folder_labels).index(default_label), key="cra_workspace_folder_select")
        selected_workspace_folder = folder_labels[selected_folder_label]
        if st.button("📂 Ouvrir ce dossier", type="primary", use_container_width=False):
            st.session_state["cra_active_workspace_folder"] = selected_workspace_folder
            st.rerun()
        if st.session_state.get("cra_active_workspace_folder", {}).get("id") == selected_workspace_folder.get("id"):
            st.session_state["cra_active_workspace_folder"] = selected_workspace_folder
        active_workspace_folder = st.session_state.get("cra_active_workspace_folder") or {}
        if active_workspace_folder:
            st.success(f"Dossier ouvert : {active_workspace_folder.get('folder_name') or active_workspace_folder.get('name')} · les nouvelles saisies seront classées ici.")
            st.markdown("#### 🔗 Liens et ressources du dossier")
            with st.form(f"cra_workspace_link_form_{active_workspace_folder.get('id')}", clear_on_submit=True):
                resource_name = st.text_input("Nom du fichier ou de la ressource *", placeholder="Ex. : Protocole expérimental")
                resource_url = st.text_input("Lien de partage *", placeholder="https://…")
                resource_note = st.text_input("Description (facultatif)")
                save_resource = st.form_submit_button("🔗 Ajouter le lien au dossier", type="primary")
            if save_resource:
                if not resource_name.strip() or not re.match(r"^https?://", resource_url.strip(), flags=re.I):
                    st.error("Indiquez un nom et un lien commençant par http:// ou https://.")
                else:
                    resources = list(active_workspace_folder.get("resources") or [])
                    resources.append({"name": resource_name.strip(), "url": resource_url.strip(), "note": resource_note.strip(), "added_at": datetime.utcnow().isoformat()})
                    try:
                        DB.table("cra_culture_folders").update({"resources": resources}).eq("id", active_workspace_folder.get("id")).execute()
                        st.session_state["cra_active_workspace_folder"] = {**active_workspace_folder, "resources": resources}
                        st.success("Lien ajouté au dossier.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Enregistrement du lien impossible : {exc}")

            folder_resources = active_workspace_folder.get("resources") or []
            if folder_resources:
                for resource_index, resource in enumerate(folder_resources):
                    st.markdown(f"**{resource.get('name', 'Ressource')}** · {resource.get('note', '')}")
                    st.link_button("Ouvrir la ressource", resource.get("url", "#"), key=f"cra_workspace_resource_{active_workspace_folder.get('id')}_{resource_index}")
            else:
                st.info("Aucun lien ajouté à ce dossier pour le moment.")
            st.caption("Le ZIP exporte les liens enregistrés et les données classées dans ce dossier, sans copier les fichiers hébergés ailleurs.")
            zip_buffer = BytesIO()
            try:
                with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_archive:
                    if folder_resources:
                        zip_archive.writestr("liens_et_ressources.json", json.dumps(folder_resources, ensure_ascii=False, indent=2).encode("utf-8"))
                        zip_archive.writestr("liens_et_ressources.csv", pd.DataFrame(folder_resources).to_csv(index=False).encode("utf-8-sig"))
                    archive_tables = [
                        "cra_technical_sheets", "cra_measurement_sheets", "cra_attendance",
                        "cra_trials", "cra_trial_observations", "cra_phytosanitary_diagnostics",
                        "cra_forms", "cra_responses", "cra_collaboration",
                    ]
                    for archive_table in archive_tables:
                        try:
                            archive_rows = [
                                row for row in db_rows(archive_table, 5000)
                                if str(row.get("folder_id", "")) == str(active_workspace_folder.get("id"))
                            ]
                        except Exception:
                            archive_rows = []
                        if archive_rows:
                            zip_archive.writestr(
                                f"donnees/{archive_table}.json",
                                json.dumps(archive_rows, ensure_ascii=False, indent=2, default=str).encode("utf-8")
                            )
                            zip_archive.writestr(
                                f"donnees/{archive_table}.csv",
                                pd.DataFrame(archive_rows).to_csv(index=False).encode("utf-8-sig")
                            )
                st.download_button(
                    "📦 Télécharger le dossier complet (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name=f"{slugify(active_workspace_folder.get('folder_name') or 'dossier')}_dossier.zip",
                    mime="application/zip",
                    key=f"cra_workspace_zip_{active_workspace_folder.get('id')}",
                )
            except Exception as exc:
                st.error(f"Création du ZIP impossible : {exc}")
            workspace_modules = [
                ("Fiches techniques", "cra_technical_sheets"),
                ("Fiches de mesure", "cra_measurement_sheets"),
                ("Pointages", "cra_attendance"),
                ("Essais expérimentaux", "cra_trials"),
                ("Observations d’essais", "cra_trial_observations"),
                ("Diagnostics phytosanitaires", "cra_phytosanitary_diagnostics"),
                ("Questionnaires", "cra_forms"),
                ("Réponses aux questionnaires", "cra_responses"),
                ("Collaboration", "cra_collaboration"),
            ]
            for module_label, module_table in workspace_modules:
                try:
                    module_all_rows = db_rows(module_table, 5000)
                    module_rows = [r for r in module_all_rows if str(r.get("folder_id", "")) == str(active_workspace_folder.get("id"))]
                except Exception:
                    module_all_rows = []
                    module_rows = []
                with st.expander(f"{module_label} · {len(module_rows)} élément(s)", expanded=False):
                    if module_rows:
                        summary_rows = []
                        for row in module_rows:
                            summary_rows.append({
                                "Identifiant": str(row.get("id", ""))[:12],
                                "Nom / objet": row.get("title") or row.get("name") or row.get("culture") or row.get("form_title") or row.get("record_type") or row.get("code") or "—",
                                "Date": row.get("created_at") or row.get("date") or row.get("submitted_at") or "",
                            })
                        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                    else:
                        st.caption("Aucune donnée classée dans ce module pour ce dossier.")
                    movable_rows = [r for r in module_all_rows if str(r.get("folder_id", "")) != str(active_workspace_folder.get("id"))]
                    if movable_rows:
                        st.markdown("**Classer une donnée existante dans ce dossier**")
                        movable_labels = {
                            f"{r.get('title') or r.get('name') or r.get('culture') or r.get('form_title') or r.get('record_type') or r.get('code') or 'Élément'} · {str(r.get('id',''))[:8]}": r
                            for r in movable_rows
                        }
                        move_label = st.selectbox("Donnée à classer", list(movable_labels), key=f"cra_move_{module_table}")
                        if st.button("Classer dans ce dossier", key=f"cra_move_btn_{module_table}"):
                            try:
                                DB.table(module_table).update({
                                    "folder_id": active_workspace_folder.get("id"),
                                    "folder_name": active_workspace_folder.get("folder_name") or active_workspace_folder.get("name", ""),
                                }).eq("id", movable_labels[move_label].get("id")).execute()
                                st.success("Donnée classée dans le dossier.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Classement impossible : {exc}")

# ---------------------------------------------------------------------
# FICHE TECHNIQUE
# ---------------------------------------------------------------------
elif page == "Pointage":
    heading("Gestion du personnel", "Pointage journalier", "Définissez les personnes, enregistrez leur présence chaque jour et exportez les relevés par jour ou par mois.")
    attendance_table = "cra_attendance"
    try:
        attendance_records = db_rows(attendance_table)
    except Exception as exc:
        st.error("La table de pointage n’est pas encore accessible dans Supabase. Le schéma vient d’être forcé au démarrage ; actualisez la page dans quelques secondes. Si le problème persiste après redémarrage de l’application, vérifiez l’URI PostgreSQL et les droits de SUPABASE_SERVICE_ROLE_KEY.")
        st.caption("Le détail de l’erreur est disponible dans les journaux de l’application Streamlit Cloud.")
        st.stop()
    people = [r for r in attendance_records if r.get("record_type") == "person"]
    people = sorted(people, key=lambda r: str(r.get("name", "")).casefold())

    with st.expander("👤 Définir une personne", expanded=not bool(people)):
        with st.form("attendance_person_form", clear_on_submit=True):
            p1, p2, p3 = st.columns(3)
            person_name = p1.text_input("Nom complet *")
            person_role = p2.text_input("Fonction / poste")
            person_service = p3.text_input("Service / équipe")
            person_active = st.checkbox("Personne active", value=True)
            save_person = st.form_submit_button("Enregistrer la personne", type="primary")
        if save_person:
            if not person_name.strip():
                st.error("Le nom complet est obligatoire.")
            elif db_insert(attendance_table, {"record_type":"person", "name":person_name.strip(), "role":person_role.strip(), "service":person_service.strip(), "active":person_active}):
                st.success("Personne enregistrée."); st.rerun()

    if people:
        st.markdown("#### Personnes définies")
        st.dataframe(pd.DataFrame([{"Nom":p.get("name"), "Fonction":p.get("role", ""), "Service":p.get("service", ""), "Active":p.get("active", True)} for p in people]), use_container_width=True, hide_index=True)
        delete_person_label = st.selectbox("Personne à supprimer", [f"{p.get('name')} · {p.get('id')}" for p in people], key="attendance_delete_person")
        delete_person_id = delete_person_label.split(" · ")[-1]
        if st.button("🗑️ Supprimer cette personne et ses pointages", key="attendance_delete_person_btn"):
            for r in attendance_records:
                if r.get("person_id") == delete_person_id:
                    DB.table(attendance_table).delete().eq("id", str(r.get("id"))).execute()
            DB.table(attendance_table).delete().eq("id", str(delete_person_id)).execute()
            st.success("Personne et pointages associés supprimés.")
            st.rerun()
        active_people = [p for p in people if p.get("active", True)]
        if active_people:
            st.markdown("#### Enregistrer le pointage")
            with st.form("attendance_daily_form", clear_on_submit=False):
                a1, a2, a3 = st.columns(3)
                person_options = {f"{p.get('name')} — {p.get('role') or 'Sans fonction'} · {p.get('id', '')[:8]}":p for p in active_people}
                attendance_person_label = a1.selectbox("Personne", list(person_options), key="attendance_person_select")
                attendance_day = a2.date_input("Date", value=date.today(), key="attendance_day_input")
                attendance_status = a3.selectbox("Statut", ["Présent", "Retard", "Absent", "Permission", "Congé", "Mission"])
                a4, a5, a6 = st.columns(3)
                time_in = a4.time_input("Heure d’arrivée", value=datetime.strptime("08:00", "%H:%M").time())
                time_out = a5.time_input("Heure de départ", value=datetime.strptime("17:00", "%H:%M").time())
                attendance_note = a6.text_input("Observation")
                save_attendance = st.form_submit_button("Enregistrer le pointage", type="primary")
            if save_attendance:
                attendance_person = person_options[attendance_person_label]
                existing = next((r for r in attendance_records if r.get("record_type") == "entry" and r.get("person_id") == attendance_person["id"] and r.get("day") == attendance_day.isoformat()), None)
                payload = {"record_type":"entry", "person_id":attendance_person["id"], "person_name":attendance_person.get("name"), "role":attendance_person.get("role", ""), "service":attendance_person.get("service", ""), "day":attendance_day.isoformat(), "status":attendance_status, "time_in":time_in.strftime("%H:%M"), "time_out":time_out.strftime("%H:%M"), "note":attendance_note.strip()}
                if existing:
                    if db_update(attendance_table, existing["id"], payload): st.success("Le pointage existant a été mis à jour."); st.rerun()
                elif db_insert(attendance_table, payload):
                    st.success("Pointage enregistré."); st.rerun()
        else:
            st.info("Aucune personne active. Réactivez ou ajoutez une personne pour saisir un pointage.")
    else:
        st.info("Définissez d’abord les personnes concernées pour commencer le pointage.")

    all_entries = [r for r in attendance_records if r.get("record_type") == "entry"]
    st.markdown("#### Exports journaliers et mensuels")
    export_mode = st.radio("Période", ["Journalière", "Mensuelle"], horizontal=True, key="attendance_export_mode")
    if export_mode == "Journalière":
        export_day = st.date_input("Journée à exporter", value=date.today(), key="attendance_export_day")
        filtered_entries = [r for r in all_entries if r.get("day") == export_day.isoformat()]
        period_label = export_day.strftime("%d/%m/%Y")
        export_suffix = export_day.isoformat()
    else:
        export_month = st.date_input("Mois à exporter", value=date.today().replace(day=1), key="attendance_export_month")
        month_prefix = export_month.strftime("%Y-%m")
        filtered_entries = [r for r in all_entries if str(r.get("day", "")).startswith(month_prefix)]
        period_label = export_month.strftime("%m/%Y")
        export_suffix = month_prefix

    visible_entries = sorted(filtered_entries, key=lambda r: (str(r.get("day", "")), str(r.get("person_name", "")).casefold()))
    if visible_entries:
        export_df = pd.DataFrame([{"Date":r.get("day"), "Nom":r.get("person_name"), "Fonction":r.get("role", ""), "Service":r.get("service", ""), "Statut":r.get("status"), "Arrivée":r.get("time_in"), "Départ":r.get("time_out"), "Observation":r.get("note", "")} for r in visible_entries])
        st.dataframe(export_df, use_container_width=True, hide_index=True)
        e1, e2 = st.columns(2)
        e1.download_button("📊 Exporter en Excel", excel_bytes({"Pointages": export_df}), f"pointage_{export_suffix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        e2.download_button("📄 Exporter en PDF", pdf_bytes(f"Pointage {period_label}", export_df), f"pointage_{export_suffix}.pdf", "application/pdf", use_container_width=True)
    else:
        st.info(f"Aucun pointage enregistré pour la période {period_label}.")

elif page == "Fiche technique":
    heading("Recherche agronomique · ISRA / CRA", "FICHE TECHNIQUE D'ESSAI AGRONOMIQUE",
            "Identification, protocole expérimental, calendrier cultural, observations périodiques et validation scientifique.")
    st.markdown('<div class="card"><b>Classement et traçabilité :</b> créez d’abord un dossier dans « Dossiers de culture », puis rattachez chaque fiche technique à ce dossier. Vous pourrez retrouver et exporter toutes les versions à tout moment.</div>', unsafe_allow_html=True)
    tech_folders = db_rows("cra_culture_folders", 2000)
    tf_options = {"Sans dossier (enregistrement personnel)": ""}
    for folder in tech_folders:
        label = f"{folder.get('culture','Culture')} · {folder.get('folder_name','Dossier')} · {folder.get('folder_code','')}"
        tf_options[label] = folder.get("id", "")
    # Streamlit interdit de modifier la valeur d'un widget dans session_state
    # après que ce widget a été instancié. On applique donc la sélection en attente
    # ici, avant la création du selectbox.
    pending_tech_folder = st.session_state.pop("_pending_technical_folder_preselect", None)
    if pending_tech_folder in tf_options:
        st.session_state["technical_folder_preselect"] = pending_tech_folder
    elif st.session_state.get("technical_folder_preselect") not in tf_options:
        st.session_state["technical_folder_preselect"] = next(iter(tf_options))
    st.markdown("#### 📁 Classement préalable (facultatif mais recommandé)")
    preselected_tech_folder = st.selectbox("Définir le dossier avant de commencer la fiche", list(tf_options), key="technical_folder_preselect")
    preselected_tech_id = tf_options[preselected_tech_folder]
    with st.expander("＋ Créer rapidement un dossier avant la saisie"):
        with st.form("quick_folder_from_technical"):
            qname=st.text_input("Nom du dossier", placeholder="Riz — Essai 2026")
            qculture=st.text_input("Culture étudiée")
            qcampaign=st.text_input("Campagne / année", str(date.today().year))
            qstation=st.text_input("Station")
            qcreate=st.form_submit_button("Créer le dossier")
        if qcreate:
            if qname.strip() and qculture.strip():
                qid=str(uuid.uuid4())
                if db_insert("cra_culture_folders", {"id":qid,"folder_code":f"DC-{uuid.uuid4().hex[:8].upper()}","folder_name":qname.strip(),"culture":qculture.strip(),"campaign":qcampaign,"station":qstation,"responsible":st.session_state.get("cra_user_name",""),"description":"Dossier créé depuis la fiche technique","created_at":datetime.now().isoformat(timespec="seconds")}):
                    # Mémoriser la sélection pour le prochain rerun, sans modifier
                    # l'état du selectbox déjà instancié pendant ce run.
                    created_folder_label = next((f"{x.get('culture','')} · {x.get('folder_name','')} · {x.get('folder_code','')}" for x in db_rows('cra_culture_folders',3000) if str(x.get('id')) == qid), None)
                    if created_folder_label:
                        st.session_state["_pending_technical_folder_preselect"] = created_folder_label
                    st.success("Dossier créé et sélectionné."); st.rerun()
            else: st.error("Le nom du dossier et la culture sont obligatoires.")
    with st.form("technical_sheet_xxl", clear_on_submit=True):
        st.markdown("#### 1. En-tête d'identification")
        a,b,c = st.columns(3)
        with a:
            institution = st.text_input("Institution", "ISRA / CRA Saint-Louis")
            station = st.text_input("Station")
            code = st.text_input("Code de l'essai / fiche")
        with b:
            annee_essai = st.number_input("Année", min_value=1900, max_value=2100, value=date.today().year, step=1)
            responsables = st.text_input("Responsable(s)")
            culture = choose_culture("Culture étudiée", "technical_culture_xxl")
        with c:
            variete = st.text_input("Variété / matériel végétal")
            date_collecte = st.date_input("Date de rédaction / collecte", date.today())
            st.caption("Dossier sélectionné avant la saisie : " + (preselected_tech_folder or "Sans dossier"))
        dossier_id = preselected_tech_id
        dossier_nom = preselected_tech_folder if dossier_id else ""

        st.markdown("#### 2. Contexte et paramètres du dispositif")
        objectif = st.text_area("Objectif de l'essai", height=75)
        hypothese = st.text_area("Hypothèse / question scientifique", height=65)
        d1,d2,d3 = st.columns(3)
        with d1:
            dispositif = st.selectbox("Type de dispositif expérimental", ["Blocs complets randomisés", "Carré latin", "Complètement randomisé", "Split-plot", "Essai multilocal", "Parcelle paysanne / démonstration", "Autre"])
            nb_blocs = st.number_input("Nombre de blocs / répétitions", min_value=0, max_value=500, value=3)
        with d2:
            nb_traitements = st.number_input("Nombre de traitements / modalités", min_value=0, max_value=500, value=0)
            surface_unitaire = st.number_input("Surface unitaire (m²)", min_value=0.0, step=0.1)
        with d3:
            site = st.text_input("Site / localité")
            parcelle = st.text_input("Code de parcelle / unité expérimentale")
        traitements_modalites = st.text_area("Liste des traitements, variétés ou modalités (une par ligne)", height=90)

        st.markdown("#### 3. Calendrier cultural — Dates clés et apports")
        calendar_labels = ["Semis", "Levée", "Tallage", "Floraison", "Maturité", "Récolte"]
        calendar_values = {}
        cal_cols = st.columns(3)
        for i, label in enumerate(calendar_labels):
            with cal_cols[i % 3]:
                calendar_values["date_" + slugify(label)] = st.date_input(f"Date : {label}", value=None, key=f"tech_date_{slugify(label)}")
        apports = st.text_area("Apports et interventions (engrais, doses, traitements, dates)", height=100)

        st.markdown("#### 4. Grille dynamique des observations expérimentales")
        g1,g2,g3 = st.columns(3)
        with g1:
            obs_ncols = st.number_input("Nombre de colonnes", min_value=1, max_value=25, value=9, key="tech_obs_ncols")
        with g2:
            obs_nrows = st.number_input("Nombre de lignes d'observation", min_value=1, max_value=300, value=20, key="tech_obs_nrows")
        with g3:
            st.caption("Définissez chaque intitulé, puis saisissez directement les observations dans la grille.")
        default_obs_headers = ["Date", "Bloc", "Modalité", "Parcelle", "Stade", "Hauteur (cm)", "Note sanitaire", "Croissance", "Observateur"]
        obs_cols = []
        obs_header_cols = st.columns(min(int(obs_ncols), 5))
        for oi in range(int(obs_ncols)):
            with obs_header_cols[oi % len(obs_header_cols)]:
                default_name = default_obs_headers[oi] if oi < len(default_obs_headers) else f"Colonne {oi+1}"
                obs_cols.append(st.text_input(f"Nom de la colonne {oi+1}", value=default_name, key=f"tech_obs_header_{oi}").strip() or f"Colonne {oi+1}")
        # Évite les intitulés identiques qui écraseraient des valeurs à l'export.
        unique_cols=[]
        for oi, name in enumerate(obs_cols, 1):
            candidate=name; suffix=2
            while candidate in unique_cols:
                candidate=f"{name} ({suffix})"; suffix+=1
            unique_cols.append(candidate)
        obs_cols=unique_cols
        obs_frame = pd.DataFrame([{col: "" for col in obs_cols} for _ in range(int(obs_nrows))], columns=obs_cols)
        obs_grid = st.data_editor(obs_frame, key="technical_observations_grid", num_rows="dynamic", use_container_width=True, hide_index=True, height=min(600, 38*(int(obs_nrows)+1)))

        st.markdown("#### 5. Observations qualitatives et validation")
        observations = st.text_area("Remarques, résultats qualitatifs et recommandations", height=110)
        signature = st.text_input("Signature numérique (nom complet / visa du responsable)")
        lien_reference = st.text_input("Lien externe vers protocole, dossier partagé ou référence (facultatif)")
        submitted = st.form_submit_button("💾 Enregistrer et déposer dans le dossier", type="primary", use_container_width=True)

    tech_payload = {
        "institution": institution, "station": station, "code": code.strip() or f"FT-{uuid.uuid4().hex[:10].upper()}",
        "annee": int(annee_essai), "responsables": responsables, "culture": culture, "variete": variete,
        "date_collecte": date_collecte.isoformat(), "site": site, "parcelle": parcelle,
        "objectif": objectif, "hypothese": hypothese, "dispositif": dispositif, "nb_blocs": int(nb_blocs),
        "nb_traitements": int(nb_traitements), "surface_unitaire_m2": surface_unitaire,
        "traitements_modalites": traitements_modalites,
        "calendrier": {k: v.isoformat() if v else "" for k,v in calendar_values.items()},
        "apports_interventions": apports, "observations_periodiques": obs_grid.fillna("").to_dict(orient="records"),
        "observations_headers": [str(c) for c in obs_grid.columns], "observations_ncols": len(obs_grid.columns),
        "observations": observations, "signature_numerique": signature, "lien_reference": lien_reference.strip(),
        "folder_id": dossier_id, "folder_name": dossier_nom,
    }
    # Ne pas exporter les lignes vides du gabarit : seules les observations réellement
    # renseignées apparaissent dans Excel, PDF et CSV. Les valeurs 0 et False restent valides.
    def _is_filled_observation(row):
        for value in row.values():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            return True
        return False

    saved_observations = [row for row in tech_payload["observations_periodiques"] if _is_filled_observation(row)]
    tech_frame = pd.DataFrame([{"N°": i+1, **row} for i,row in enumerate(saved_observations)],
                              columns=["N°"] + list(obs_cols))
    if tech_frame.empty:
        tech_frame = pd.DataFrame(columns=["N°"] + list(obs_cols))
    tech_meta = {k:v for k,v in tech_payload.items() if k != "observations_periodiques"}
    tech_meta_frame = pd.DataFrame([{"Champ": k, "Valeur": json.dumps(v, ensure_ascii=False) if isinstance(v,(dict,list)) else v} for k,v in tech_meta.items()])
    def technical_excel_one_sheet(meta, frame):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.page import PageMargins
        output=BytesIO(); wb=Workbook(); ws=wb.active; ws.title="Fiche technique"
        deep="16483F"; mint="BFE9DE"; pale="EFF9F5"; white="FFFFFF"
        thin=Side(style="thin", color="80A99B"); medium=Side(style="medium", color=deep)
        ws.merge_cells("A1:J1"); ws["A1"]="INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES (ISRA) — CRA SAINT-LOUIS"
        ws["A1"].font=Font(name="Arial",size=13,bold=True,color=white); ws["A1"].fill=PatternFill("solid",fgColor=deep); ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=28
        ws.merge_cells("A2:J2"); ws["A2"]="FICHE TECHNIQUE D'ESSAI AGRONOMIQUE"; ws["A2"].font=Font(name="Arial",size=16,bold=True,color=deep); ws["A2"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[2].height=30
        ws.merge_cells("A3:J3"); ws["A3"]="IDENTIFICATION · DISPOSITIF · CALENDRIER CULTURAL · SUIVI EXPÉRIMENTAL"; ws["A3"].font=Font(name="Arial",size=10,bold=True,color=deep); ws["A3"].fill=PatternFill("solid",fgColor=mint); ws["A3"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[3].height=22
        fields=[("Institution",meta.get("institution","ISRA / CRA Saint-Louis")),("Station",meta.get("station","")),("Code de l'essai",meta.get("code","")),("Année",meta.get("annee","")),("Responsable(s)",meta.get("responsables","")),("Culture étudiée",meta.get("culture","")),("Variété / matériel végétal",meta.get("variete","")),("Dossier",meta.get("folder_name","")),("Objectif",meta.get("objectif","")),("Hypothèse",meta.get("hypothese","")),("Dispositif",meta.get("dispositif","")),("Blocs / répétitions",meta.get("nb_blocs","")),("Traitements / modalités",meta.get("traitements_modalites","")),("Nombre de traitements",meta.get("nb_traitements","")),("Surface unitaire (m²)",meta.get("surface_unitaire_m2","")),("Site",meta.get("site","")),("Parcelle",meta.get("parcelle","")),("Apports / interventions",meta.get("apports_interventions","")),("Calendrier cultural",json.dumps(meta.get("calendrier",{}),ensure_ascii=False)),("Observations qualitatives",meta.get("observations","")),("Signature / visa",meta.get("signature_numerique","")),("Lien de référence",meta.get("lien_reference",""))]
        row=4
        for i in range(0,len(fields),2):
            for start,pair in ((1,fields[i]),(6,fields[i+1] if i+1<len(fields) else ("",""))):
                for col,val in ((start,pair[0]),(start+1,pair[1])):
                    cell=ws.cell(row,col,val); cell.alignment=Alignment(vertical="center",wrap_text=True); cell.border=Border(left=thin,right=thin,top=thin,bottom=thin)
                    if col==start: cell.font=Font(name="Arial",size=9,bold=True,color=deep); cell.fill=PatternFill("solid",fgColor=mint)
                    else: cell.font=Font(name="Arial",size=9,color="20352E"); cell.fill=PatternFill("solid",fgColor=pale)
            ws.row_dimensions[row].height=32 if len(str(fields[i][1]))>45 or (i+1<len(fields) and len(str(fields[i+1][1]))>45) else 24
            row+=1
        row+=1
        width=max(1,len(frame.columns),10)
        ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=width); c=ws.cell(row,1,"GRILLE DES OBSERVATIONS EXPÉRIMENTALES"); c.font=Font(name="Arial",size=10,bold=True,color=white); c.fill=PatternFill("solid",fgColor=deep); row+=1
        for ci,name in enumerate(frame.columns,start=1):
            c=ws.cell(row,ci,str(name)); c.font=Font(name="Arial",size=9,bold=True,color=deep); c.fill=PatternFill("solid",fgColor=mint); c.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); c.border=Border(left=thin,right=thin,top=medium,bottom=medium)
        ws.row_dimensions[row].height=30; row+=1
        for vals in frame.fillna("").itertuples(index=False,name=None):
            for ci,val in enumerate(vals,start=1):
                c=ws.cell(row,ci,val); c.font=Font(name="Arial",size=9); c.alignment=Alignment(vertical="center",wrap_text=True); c.border=Border(left=thin,right=thin,top=thin,bottom=thin)
            ws.row_dimensions[row].height=22; row+=1
        for col in range(1,width+1): ws.column_dimensions[get_column_letter(col)].width=20 if col in (1,6) else (26 if col in (2,7) else 16)
        ws.freeze_panes="A28"; ws.sheet_view.showGridLines=False; ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.orientation="landscape"; ws.page_setup.paperSize=ws.PAPERSIZE_A4; ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=1
        ws.page_margins=PageMargins(left=.25,right=.25,top=.45,bottom=.45,header=.2,footer=.2); ws.print_area=f"A1:{get_column_letter(width)}{row-1}"
        ws.oddHeader.center.text="&BISRA / CRA SAINT-LOUIS — FICHE TECHNIQUE"; ws.oddFooter.center.text="ISRA · CRA SAINT-LOUIS | YAM GROUP — YAM NUMÉRIQUE"
        wb.save(output); return output.getvalue()
    tech_excel = two_sheet_fiche_excel("Fiche technique d’essai agronomique", tech_meta, tech_frame, "Grille des observations")
    tech_csv = tech_frame.to_csv(index=False).encode("utf-8-sig")
    def technical_sheet_pdf(meta, observations_frame):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import mm
        from xml.sax.saxutils import escape
        out = BytesIO()
        doc = SimpleDocTemplate(out, pagesize=landscape(A4), rightMargin=9*mm, leftMargin=9*mm, topMargin=18*mm, bottomMargin=18*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("TechTitle", parent=styles["Title"], fontSize=15, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#16483F"))
        cell_style = ParagraphStyle("TechCell", parent=styles["BodyText"], fontSize=7, leading=9)
        story = [Paragraph("INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES — ISRA", styles["Heading2"]),
                 Paragraph("CENTRE DE RECHERCHES AGRICOLES — SAINT-LOUIS", styles["Heading3"]),
                 Spacer(1, 2*mm), Paragraph("FICHE TECHNIQUE D'ESSAI AGRONOMIQUE", title_style),
                 Paragraph("DOCUMENT OFFICIEL DE RECHERCHE · SUIVI EXPÉRIMENTAL ET TRAÇABILITÉ", styles["Italic"]), Spacer(1, 4*mm)]
        metadata_rows = [[Paragraph("<b>Rubrique</b>", cell_style), Paragraph("<b>Information renseignée</b>", cell_style)]]
        for key, value in meta.items():
            metadata_rows.append([Paragraph(escape(str(key).replace("_", " ").title()), cell_style),
                                  Paragraph(escape(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict,list)) else str(value or "")), cell_style)])
        mt = Table(metadata_rows, colWidths=[55*mm, doc.width-55*mm], repeatRows=1)
        mt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#247A66")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#8BB9AA")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#EFF9F5")]),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5)]))
        story += [Paragraph("1. IDENTIFICATION, CONTEXTE ET CALENDRIER", styles["Heading3"]), mt, Spacer(1,4*mm),
                  Paragraph("2. GRILLE DES OBSERVATIONS EXPÉRIMENTALES", styles["Heading3"])]
        headers = list(observations_frame.columns) or list(meta.get("observations_headers", [])) or ["Observation"]
        observations_frame = observations_frame.reindex(columns=headers, fill_value="")
        for offset in range(0, len(headers), 8):
            group = headers[offset:offset+8]
            table_data = [[Paragraph("<b>"+escape(str(h))+"</b>", cell_style) for h in group]]
            for vals in observations_frame.fillna("").astype(str).itertuples(index=False, name=None):
                table_data.append([Paragraph(escape(str(v)), cell_style) for v in vals[offset:offset+8]])
            if len(table_data) == 1:
                table_data.append([Paragraph("Aucune observation saisie", cell_style)] + [""] * max(0,len(group)-1))
            obs_table = Table(table_data, colWidths=[doc.width/max(1,len(group))]*len(group), repeatRows=1)
            obs_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#BFE9DE")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#8BB9AA")),
                ("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),6)]))
            story.append(obs_table)
        story += [Spacer(1,5*mm), Paragraph("3. OBSERVATIONS QUALITATIVES", styles["Heading3"]),
                  Paragraph(escape(str(meta.get("observations", ""))).replace("\n", "<br/>") or "—", cell_style), Spacer(1,8*mm),
                  Paragraph("Signature / visa du responsable : " + escape(str(meta.get("signature_numerique", ""))), cell_style)]
        def tech_page_brand(canvas, document):
            from reportlab.lib.pagesizes import A4, landscape
            canvas.saveState(); w, h = landscape(A4)
            canvas.setFillColor(colors.HexColor("#BFE9DE")); canvas.rect(0, h-12*mm, w, 12*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(9*mm, h-8*mm, "ISRA · CRA SAINT-LOUIS")
            canvas.setFont("Helvetica", 7); canvas.drawRightString(w-9*mm, h-8*mm, "FICHE TECHNIQUE D'ESSAI AGRONOMIQUE")
            canvas.setStrokeColor(colors.HexColor("#DDB64C")); canvas.setLineWidth(2); canvas.line(9*mm, 13*mm, w-9*mm, 13*mm)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(9*mm, 7*mm, "YAM GROUP · YAM NUMÉRIQUE")
            canvas.setFont("Helvetica", 7); canvas.drawRightString(w-9*mm, 7*mm, f"Page {document.page}")
            canvas.restoreState()
        doc.build(story, onFirstPage=tech_page_brand, onLaterPages=tech_page_brand)
        return out.getvalue()

    tech_pdf = technical_sheet_pdf(tech_meta, tech_frame)
    ex1,ex2,ex3 = st.columns(3)
    download_button("📊 Excel de la fiche technique", tech_excel, f"FICHE_TECHNIQUE_{slugify(tech_payload['code'])}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    download_button("📄 PDF officiel", tech_pdf, f"FICHE_TECHNIQUE_{slugify(tech_payload['code'])}.pdf", "application/pdf", use_container_width=True)
    download_button("📑 CSV observations", tech_csv, f"OBSERVATIONS_{slugify(tech_payload['code'])}.csv", "text/csv", use_container_width=True)
    if submitted:
        tech_payload["created_at"] = datetime.now().isoformat(timespec="seconds")
        if db_insert("cra_technical_sheets", tech_payload):
            st.success(f"Fiche technique enregistrée. Code : {tech_payload['code']} · Dossier : {dossier_nom or 'Non classé'}")
            st.session_state["last_technical_saved"] = tech_payload

    st.markdown("#### Dernières fiches techniques enregistrées")
    saved_tech = db_rows("cra_technical_sheets", 500)
    if saved_tech:
        display = [{"Code":r.get("code"),"Culture":r.get("culture"),"Station":r.get("station"),"Année":r.get("annee"),"Dossier":r.get("folder_name"),"Date":r.get("date_collecte")} for r in saved_tech[:30]]
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune fiche technique enregistrée pour le moment.")

# ---------------------------------------------------------------------
# FICHE DE MESURE — MODÈLE ISRA / SAINT-LOUIS
# ---------------------------------------------------------------------
elif page == "Fiche de mesure":
    heading("Collecte scientifique · ISRA / Saint-Louis", "FICHE DE MESURES",
            "Formulaire matriciel pour les mesures au champ et au laboratoire. Brouillon enregistré automatiquement sur cet ordinateur.")

    st.markdown("""
    <style>
    @media print {
      header, footer, [data-testid="stSidebar"], [data-testid="stHeader"],
      .stButton, .stDownloadButton, [data-testid="stRadio"], [data-testid="stSelectbox"] {display:none!important;}
      .block-container {max-width:100%!important;padding:0!important;}
      .measure-paper {border:1px solid #333!important;box-shadow:none!important;}
    }
    .measure-paper {background:white;border:1px solid #b9c9bd;border-radius:12px;padding:20px;margin:12px 0 18px;}
    .measure-paper h3 {text-align:center;color:#103f2d;margin:0 0 4px;letter-spacing:1px;}
    .measure-paper .sub {text-align:center;color:#52665a;font-weight:700;margin-bottom:16px;}
    .measure-label {font-weight:800;color:#103f2d;}
    </style>
    """, unsafe_allow_html=True)

    # Identifiant stable du brouillon de chaque compte. SQLite assure la conservation
    # locale même si le navigateur est fermé ou si la connexion Internet est coupée.
    draft_key = f"measure_draft_id_{st.session_state.get('cra_user_email','guest')}"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = f"DRAFT-{uuid.uuid4().hex[:12].upper()}"
    draft_id = st.session_state[draft_key]

    existing_draft = next((r for r in db_rows("cra_measurement_drafts", 1000) if r.get("id") == draft_id), None)
    if existing_draft and "measure_restore_done" not in st.session_state:
        saved = existing_draft.get("draft_data", {})
        if isinstance(saved, str):
            try: saved = json.loads(saved)
            except Exception: saved = {}
        st.session_state["measure_restore_data"] = saved if isinstance(saved, dict) else {}
        st.session_state["measure_restore_done"] = True
    restore = st.session_state.get("measure_restore_data", {})

    st.markdown('<div class="measure-paper"><h3>FICHE DE MESURES</h3><div class="sub">ISRA / Saint-Louis</div><div class="measure-label">1. CONTEXTE ET OBJECTIFS</div><p>Collecte et numérisation des données de terrain et de laboratoire pour les activités de recherche agronomique.</p></div>', unsafe_allow_html=True)

    # Le dossier peut être défini avant la saisie de la fiche ; le classement reste facultatif.
    measure_folders = db_rows("cra_culture_folders", 2000)
    mf_options = {"Sans dossier (enregistrement personnel)": ""}
    for folder in measure_folders:
        label = f"{folder.get('culture','Culture')} · {folder.get('folder_name','Dossier')} · {folder.get('folder_code','')}"
        mf_options[label] = folder.get("id", "")
    mf_labels = list(mf_options)
    mf_default = 0
    measure_folder_label = st.selectbox("📁 Définir le dossier avant de commencer la fiche", mf_labels, index=mf_default, key="measurement_folder_select")
    measure_folder_id = mf_options[measure_folder_label]
    measure_folder_name = measure_folder_label if measure_folder_id else ""
    with st.expander("＋ Créer rapidement un dossier avant la saisie de mesures"):
        with st.form("quick_folder_from_measure"):
            qm_name=st.text_input("Nom du dossier",placeholder="Tomate — Essai 2026")
            qm_crop=st.text_input("Culture étudiée")
            qm_campaign=st.text_input("Campagne / année",str(date.today().year))
            qm_station=st.text_input("Station")
            qm_create=st.form_submit_button("Créer le dossier")
        if qm_create:
            if qm_name.strip() and qm_crop.strip():
                qmid=str(uuid.uuid4())
                if db_insert("cra_culture_folders",{"id":qmid,"folder_code":f"DC-{uuid.uuid4().hex[:8].upper()}","folder_name":qm_name.strip(),"culture":qm_crop.strip(),"campaign":qm_campaign,"station":qm_station,"responsible":st.session_state.get("cra_user_name",""),"description":"Dossier créé depuis la fiche de mesures","created_at":datetime.now().isoformat(timespec="seconds")}):
                    st.success("Dossier créé. Actualisez la sélection pour le choisir."); st.rerun()
            else: st.error("Le nom du dossier et la culture sont obligatoires.")

    st.markdown("### A. Métadonnées de l'essai — En-tête")
    a,b,c = st.columns(3)
    with a:
        centre = st.text_input("Centre", value=restore.get("centre", "ISRA / Saint-Louis"), key="m_centre")
        essai = st.text_input("Essai", value=restore.get("essai", ""), key="m_essai")
        mesure_culture = choose_culture("Culture étudiée", "measurement_culture")
        station = st.text_input("Station", value=restore.get("station", ""), key="m_station")
        annee = st.number_input("Année", min_value=1900, max_value=2100, value=int(restore.get("annee", date.today().year) or date.today().year), step=1, key="m_annee")
    with b:
        responsables = st.text_input("Responsable(s)", value=restore.get("responsables", ""), key="m_responsables")
        parametres_text = st.text_input("Paramètres mesurés (séparer par des virgules)", value=restore.get("parametres", ""), key="m_parametres")
        date_semis = st.date_input("Date de semis", value=date.fromisoformat(restore["date_semis"]) if restore.get("date_semis") else None, key="m_date_semis")
        date_levee = st.date_input("Date de levée", value=date.fromisoformat(restore["date_levee"]) if restore.get("date_levee") else None, key="m_date_levee")
    with c:
        date_mesure = st.date_input("Date de mesure", value=date.fromisoformat(restore["date_mesure"]) if restore.get("date_mesure") else date.today(), key="m_date_mesure")
        autre = st.text_area("Autre(s)", value=restore.get("autres", ""), height=105, key="m_autres")
        st.caption("Le centre est prérempli et reste modifiable.")



    st.markdown("### B. Grille de mesures — Tableau dynamique")
    cfg1,cfg2,cfg3 = st.columns([1,1,2])
    with cfg1:
        ncols = st.number_input("Nombre de colonnes", min_value=1, max_value=20, value=int(restore.get("ncols", 10)), step=1, key="m_ncols")
    with cfg2:
        nrows = st.number_input("Nombre de lignes", min_value=1, max_value=200, value=int(restore.get("nrows", 20)), step=1, key="m_nrows")
    with cfg3:
        st.caption("Format initial : 10 colonnes × 20 lignes. Les en-têtes et types de colonnes sont personnalisables.")

    previous_headers = restore.get("headers", [])
    previous_types = restore.get("types", {})
    headers=[]
    type_map={}
    type_options=["Numérique", "Texte", "Date"]
    type_cols=st.columns(min(int(ncols),5))
    for i in range(int(ncols)):
        default_header = previous_headers[i] if i < len(previous_headers) and previous_headers[i] else ("N°" if i==0 else f"Paramètre {i}")
        with type_cols[i % len(type_cols)]:
            raw_header = st.text_input(f"En-tête {i+1}", value=default_header, key=f"m_header_{i}").strip() or f"Colonne {i+1}"
            final_header = raw_header
            suffix = 2
            while final_header in headers:
                final_header = f"{raw_header} ({suffix})"
                suffix += 1
            headers.append(final_header)
            type_map[final_header] = st.selectbox(f"Type {i+1}", type_options,
                index=type_options.index(previous_types.get(default_header,"Numérique")) if previous_types.get(default_header,"Numérique") in type_options else 0,
                key=f"m_type_{i}")

    old_grid=restore.get("grid", [])
    grid_rows=[]
    for ri in range(int(nrows)):
        old=old_grid[ri] if ri < len(old_grid) and isinstance(old_grid[ri],dict) else {}
        row={}
        for ci,h in enumerate(headers):
            key=h.strip() or f"Colonne {ci+1}"
            value=old.get(key, "")
            if type_map.get(key)=="Numérique":
                try: value=float(value) if value not in (None,"") else None
                except Exception: value=None
            row[key]=value
        grid_rows.append(row)
    grid_df=pd.DataFrame(grid_rows, columns=[h.strip() or f"Colonne {i+1}" for i,h in enumerate(headers)])
    col_config={}
    for col in grid_df.columns:
        typ=type_map.get(col,"Numérique")
        if typ=="Numérique": col_config[col]=st.column_config.NumberColumn(col, help="Valeur numérique", format="%.4f")
        elif typ=="Date": col_config[col]=st.column_config.TextColumn(col, help="Saisir une date au format AAAA-MM-JJ")
        else: col_config[col]=st.column_config.TextColumn(col)
    edited_grid=st.data_editor(grid_df, key="m_grid_editor", num_rows="fixed", use_container_width=True,
        hide_index=True, height=min(680, 38*(int(nrows)+1)), column_config=col_config)

    st.markdown("### C. Remarques et observations")
    observations=st.text_area("Observations", value=restore.get("observations",""), height=130, key="m_observations")

    metadata={"centre":centre,"essai":essai,"culture":mesure_culture,"station":station,"annee":int(annee),"responsables":responsables,
              "folder_id":measure_folder_id,"folder_name":measure_folder_name,
              "parametres":parametres_text,"date_semis":date_semis.isoformat() if date_semis else "",
              "date_levee":date_levee.isoformat() if date_levee else "","date_mesure":date_mesure.isoformat(),
              "autres":autre,"observations":observations,"ncols":int(ncols),"nrows":int(nrows),
              "headers":headers,"types":type_map,"grid":edited_grid.fillna("").to_dict(orient="records")}

    # Brouillon autosauvegardé à chaque interaction Streamlit.
    try:
        if existing_draft:
            DB.table("cra_measurement_drafts").update({"draft_data":metadata,"updated_at":datetime.utcnow().isoformat()}).eq("id",draft_id).execute()
        else:
            db_insert("cra_measurement_drafts", {"id":draft_id,"draft_data":metadata,"updated_at":datetime.utcnow().isoformat()})
        st.caption("🟢 Brouillon sauvegardé automatiquement sur cet ordinateur · Mode local utilisable sans Internet.")
    except Exception:
        st.warning("Le brouillon n'a pas pu être sauvegardé automatiquement. Utilisez le bouton d'enregistrement ci-dessous.")

    st.markdown("### Enregistrement et exports")
    measure_cols=st.columns(4)
    with measure_cols[0]:
        save_measure=st.button("💾 Enregistrer la fiche", type="primary", use_container_width=True)
    with measure_cols[1]:
        blank_pdf=st.button("📄 PDF vierge", use_container_width=True)
    with measure_cols[2]:
        filled_pdf=st.button("📄 PDF rempli", use_container_width=True)
    with measure_cols[3]:
        def measurement_excel_one_sheet(meta, frame):
            """Classeur de la fiche de mesures sur une seule feuille : en-tête, métadonnées et matrice."""
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
            from openpyxl.utils import get_column_letter
            from openpyxl.worksheet.page import PageMargins

            output = BytesIO()
            wb = Workbook()
            ws = wb.active
            ws.title = "Fiche de mesures"
            green = "174D35"
            light_green = "E2EEE6"
            pale = "F4F8F5"
            white = "FFFFFF"
            thin_green = Side(style="thin", color="789484")
            medium_green = Side(style="medium", color=green)

            # Titre institutionnel
            ws.merge_cells("A1:J1")
            ws["A1"] = "INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES (ISRA) — SAINT-LOUIS"
            ws["A1"].font = Font(name="Arial", size=13, bold=True, color=white)
            ws["A1"].fill = PatternFill("solid", fgColor=green)
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 26
            ws.merge_cells("A2:J2")
            ws["A2"] = "FICHE DE MESURES"
            ws["A2"].font = Font(name="Arial", size=16, bold=True, color=green)
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[2].height = 28
            ws.merge_cells("A3:J3")
            ws["A3"] = "CONTEXTE ET MÉTADONNÉES DE L'ESSAI — compléter les champs de l'en-tête"
            ws["A3"].font = Font(name="Arial", size=10, bold=True, color=green)
            ws["A3"].fill = PatternFill("solid", fgColor=light_green)
            ws["A3"].alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[3].height = 22

            # Deux couples Libellé / Valeur par ligne pour un en-tête imprimable et facile à renseigner.
            fields = [
                ("Centre", meta.get("centre", "ISRA / Saint-Louis")),
                ("Essai", meta.get("essai", "")),
                ("Station", meta.get("station", "")),
                ("Culture", meta.get("culture", "")),
                ("Année", meta.get("annee", "")),
                ("Responsable(s)", meta.get("responsables", "")),
                ("Paramètres mesurés", meta.get("parametres", "")),
                ("Date de semis", meta.get("date_semis", "")),
                ("Date de levée", meta.get("date_levee", "")),
                ("Date de mesure", meta.get("date_mesure", "")),
                ("Autre(s)", meta.get("autres", "")),
            ]
            row = 4
            for i in range(0, len(fields), 2):
                left = fields[i]
                right = fields[i + 1] if i + 1 < len(fields) else ("", "")
                for col, pair in ((1, left), (6, right)):
                    label_col, value_col = col, col + 1
                    ws.cell(row, label_col, pair[0])
                    ws.cell(row, value_col, pair[1])
                    ws.cell(row, label_col).font = Font(name="Arial", size=9, bold=True, color=green)
                    ws.cell(row, label_col).fill = PatternFill("solid", fgColor=light_green)
                    ws.cell(row, value_col).font = Font(name="Arial", size=9, color="202820")
                    ws.cell(row, value_col).fill = PatternFill("solid", fgColor=pale)
                    for c in (label_col, value_col):
                        ws.cell(row, c).border = Border(bottom=thin_green, top=thin_green,
                                                       left=thin_green, right=thin_green)
                        ws.cell(row, c).alignment = Alignment(vertical="center", wrap_text=True)
                row += 1

            # Observations sur toute la largeur de la fiche.
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
            ws.cell(row, 1, "OBSERVATIONS / REMARQUES")
            ws.cell(row, 1).font = Font(name="Arial", size=9, bold=True, color=white)
            ws.cell(row, 1).fill = PatternFill("solid", fgColor=green)
            row += 1
            ws.merge_cells(start_row=row, start_column=1, end_row=row + 1, end_column=10)
            ws.cell(row, 1, meta.get("observations", ""))
            ws.cell(row, 1).font = Font(name="Arial", size=9)
            ws.cell(row, 1).alignment = Alignment(vertical="top", wrap_text=True)
            ws.cell(row, 1).fill = PatternFill("solid", fgColor=pale)
            ws.cell(row, 1).border = Border(left=thin_green, right=thin_green,
                                           top=thin_green, bottom=thin_green)
            ws.row_dimensions[row].height = 25
            ws.row_dimensions[row + 1].height = 20
            row += 3

            # Matrice de mesures sur la même feuille Excel.
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max(1, len(frame.columns)))
            ws.cell(row, 1, "GRILLE DE MESURES")
            ws.cell(row, 1).font = Font(name="Arial", size=10, bold=True, color=white)
            ws.cell(row, 1).fill = PatternFill("solid", fgColor=green)
            row += 1
            for ci, name in enumerate(frame.columns, start=1):
                cell = ws.cell(row, ci, str(name))
                cell.font = Font(name="Arial", size=9, bold=True, color=green)
                cell.fill = PatternFill("solid", fgColor=light_green)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = Border(left=thin_green, right=thin_green, top=medium_green, bottom=medium_green)
            ws.row_dimensions[row].height = 30
            row += 1
            for values in frame.fillna("").itertuples(index=False, name=None):
                for ci, value in enumerate(values, start=1):
                    cell = ws.cell(row, ci, value)
                    cell.font = Font(name="Arial", size=9)
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    cell.border = Border(left=thin_green, right=thin_green, top=thin_green, bottom=thin_green)
                ws.row_dimensions[row].height = 22
                row += 1

            # Dimensions, impression et navigation : une seule feuille, largeur ajustée à une page.
            for col in range(1, max(10, len(frame.columns)) + 1):
                if col in (1, 6):
                    width = 20
                elif col in (2, 7):
                    width = 22
                else:
                    width = 15
                ws.column_dimensions[get_column_letter(col)].width = width
            ws.freeze_panes = "A18"
            ws.sheet_view.showGridLines = False
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.page_setup.orientation = "landscape"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1
            ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.45, bottom=0.45, header=0.2, footer=0.2)
            ws.print_title_rows = "1:3"
            ws.print_area = f"A1:{get_column_letter(max(10, len(frame.columns)))}{row-1}"
            ws.oddHeader.center.text = "&BISRA / CRA SAINT-LOUIS — FICHE DE MESURES"
            ws.oddFooter.center.text = "ISRA / CRA SAINT-LOUIS  |  YAM GROUP — YAM NUMÉRIQUE"
            wb.save(output)
            return output.getvalue()

        download_button("⬇️ Excel (.xlsx) — présentation + grilles",
            two_sheet_fiche_excel("Fiche de mesures", metadata, edited_grid, "Grille de mesures"),
            f"FICHE_MESURES_{slugify(essai or 'ISRA_CRA')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    csv_frame=edited_grid.copy()
    csv_header = "# FICHE DE MESURES — ISRA / Saint-Louis\n" + "\n".join(
        f"# {k}: {v}" for k, v in metadata.items() if k not in ("grid", "headers", "types")) + "\n\n"
    csv_data=(csv_header + csv_frame.to_csv(index=False)).encode("utf-8-sig")
    download_button("⬇️ Télécharger la grille CSV", csv_data,
        f"FICHE_MESURES_{slugify(essai or 'ISRA_CRA')}.csv", "text/csv", use_container_width=True)

    def measurement_pdf(meta, frame, blank=False):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, LongTable, TableStyle, PageBreak
        from reportlab.lib.units import mm
        from xml.sax.saxutils import escape
        out=BytesIO()
        doc=SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=9*mm,leftMargin=9*mm,topMargin=18*mm,bottomMargin=18*mm)
        styles=getSampleStyleSheet()
        title=ParagraphStyle("FicheTitle",parent=styles["Title"],fontSize=15,leading=18,alignment=TA_CENTER,textColor=colors.HexColor("#16483F"))
        small=ParagraphStyle("SmallCell",parent=styles["BodyText"],fontSize=6.5,leading=8)
        story=[Paragraph("INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES — ISRA",styles["Heading2"]),
               Paragraph("CENTRE DE RECHERCHES AGRICOLES — SAINT-LOUIS",styles["Heading3"]),
               Paragraph("FICHE DE MESURES",title),
               Paragraph("DOCUMENT SCIENTIFIQUE · SAISIE ET TRAÇABILITÉ DES MESURES",styles["Italic"]),Spacer(1,5*mm)]
        fields=[("Centre",meta.get("centre","ISRA / Saint-Louis")),("Essai",meta.get("essai","")),("Culture",meta.get("culture","")),("Station",meta.get("station","")),("Année",meta.get("annee","")),
                ("Responsable(s)",meta.get("responsables","")),("Paramètres mesurés",meta.get("parametres","")),("Date de semis",meta.get("date_semis","")),
                ("Date de levée",meta.get("date_levee","")),("Date de mesure",meta.get("date_mesure","")),("Autre(s)",meta.get("autres",""))]
        field_rows=[]
        for i in range(0,len(fields),2):
            left=fields[i]; right=fields[i+1] if i+1<len(fields) else ("","")
            field_rows.append([Paragraph(f"<b>{escape(str(left[0]))}</b><br/>{escape(str(left[1]))}",small),Paragraph(f"<b>{escape(str(right[0]))}</b><br/>{escape(str(right[1]))}",small)])
        ft=Table(field_rows,colWidths=[doc.width/2,doc.width/2],rowHeights=13*mm)
        ft.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.HexColor("#6B9B8D")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#EFF9F5")),("LEFTPADDING",(0,0),(-1,-1),5)]))
        story += [ft,Spacer(1,4*mm),Paragraph("GRILLE DE MESURES",styles["Heading3"])]
        cols=list(frame.columns) or list(meta.get("headers", [])) or ["Observation"]
        frame = frame.reindex(columns=cols, fill_value="")
        max_cols=8
        for offset in range(0, len(cols), max_cols):
            group=cols[offset:offset+max_cols]
            data=[[Paragraph(f"<b>{escape(str(c))}</b>",small) for c in group]]
            if blank:
                for _ in range(int(meta.get("nrows",20))): data.append([""]*len(group))
            else:
                for row in frame.fillna("").astype(str).itertuples(index=False,name=None):
                    data.append([Paragraph(escape(str(v)),small) for v in row[offset:offset+max_cols]])
            widths=[doc.width/max(1,len(group))]*len(group)
            gt=LongTable(data,colWidths=widths,repeatRows=1,splitByRow=1)
            gt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.45,colors.HexColor("#6B9B8D")),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#BFE9DE")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#16483F")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3)]))
            story.append(gt)
            if offset + max_cols < len(cols): story.append(Paragraph(f"Suite de la grille — colonnes {offset+max_cols+1} à {min(offset+2*max_cols,len(cols))}",small))
        story += [Spacer(1,4*mm),Paragraph("OBSERVATIONS",styles["Heading3"]),Paragraph(escape("" if blank else str(meta.get("observations",""))).replace("\n","<br/>") or "<br/><br/><br/>",small)]
        def measure_page_brand(canvas, document):
            canvas.saveState(); w, h = landscape(A4)
            canvas.setFillColor(colors.HexColor("#BFE9DE")); canvas.rect(0, h-12*mm, w, 12*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(9*mm, h-8*mm, "ISRA · CRA SAINT-LOUIS")
            canvas.setFont("Helvetica", 7); canvas.drawRightString(w-9*mm, h-8*mm, "FICHE DE MESURES")
            canvas.setStrokeColor(colors.HexColor("#DDB64C")); canvas.setLineWidth(2); canvas.line(9*mm, 13*mm, w-9*mm, 13*mm)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(9*mm, 7*mm, "YAM GROUP · YAM NUMÉRIQUE")
            canvas.setFont("Helvetica", 7); canvas.drawRightString(w-9*mm, 7*mm, f"Page {document.page}")
            canvas.restoreState()
        doc.build(story, onFirstPage=measure_page_brand, onLaterPages=measure_page_brand)
        return out.getvalue()

    if save_measure:
        final_payload=dict(metadata)
        # Copie explicite de la grille éditée : les cellules du data_editor deviennent
        # une liste de dictionnaires JSONB attachée à CETTE fiche, pas au brouillon partagé.
        final_payload["grid"] = edited_grid.fillna("").to_dict(orient="records")
        final_payload["headers"] = [str(c) for c in edited_grid.columns]
        final_payload["ncols"] = len(edited_grid.columns)
        final_payload["nrows"] = len(edited_grid.index)
        final_payload["fiche_code"]=f"FM-{uuid.uuid4().hex[:10].upper()}"
        final_payload["folder_id"]=measure_folder_id
        final_payload["folder_name"]=measure_folder_name
        if db_insert("cra_measurement_sheets",final_payload):
            st.success("Fiche de mesures enregistrée dans votre espace personnel ISRA / CRA Saint-Louis.")
    if blank_pdf:
        blank_meta=dict(metadata); blank_meta["observations"]=""
        download_button("📥 Télécharger le modèle PDF vierge",measurement_pdf(blank_meta,edited_grid.iloc[0:0],True),
            "ISRA_CRA_FICHE_MESURES_VIERGE.pdf","application/pdf")
    if filled_pdf:
        download_button("📥 Télécharger la fiche PDF remplie",measurement_pdf(metadata,edited_grid,False),
            f"ISRA_CRA_FICHE_MESURES_{slugify(essai or 'essai')}.pdf","application/pdf")

    st.markdown("#### Impression directe")
    st.caption("Utilisez Ctrl + P dans votre navigateur : les éléments de navigation et les boutons sont masqués dans la vue imprimée.")

    st.markdown("#### Mes fiches de mesures enregistrées")
    my_measurements=db_rows("cra_measurement_sheets",2000)
    if my_measurements:
        rows=[]
        for item in my_measurements:
            rows.append({"Code":item.get("fiche_code",""),"Culture":item.get("culture",""),"Essai":item.get("essai",""),"Dossier":item.get("folder_name",""),"Station":item.get("station",""),"Année":item.get("annee",""),"Date de mesure":item.get("date_mesure",""),"Centre":item.get("centre","")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        measure_presentation_rows = []
        measure_grid_rows = []
        for rec_no, rec in enumerate(my_measurements, 1):
            grid_rows = _normalize_grid_rows(rec.get("grid"))
            headers_saved = rec.get("headers") or []
            if isinstance(headers_saved, str):
                try: headers_saved = json.loads(headers_saved)
                except Exception: headers_saved = []
            columns_saved = list(dict.fromkeys([str(c) for c in headers_saved] +
                                                [str(k) for row in grid_rows for k in row.keys()]))
            code = rec.get("fiche_code") or f"Fiche_{rec_no}"
            measure_presentation_rows.append({"N° fiche":rec_no, "Code fiche":code,
                **{str(k).replace("_", " ").capitalize():_plain_export_value(v)
                   for k,v in rec.items() if k not in {"grid","owner_email","id"}
                   and not isinstance(v,(dict,list,tuple))}})
            if not columns_saved: columns_saved = ["Observation"]
            for n, gr in enumerate(grid_rows,1):
                measure_grid_rows.append({"N° fiche":rec_no,"Code fiche":code,"N° ligne":n,
                                          **{c:_plain_export_value(gr.get(c,"")) for c in columns_saved}})
            if not grid_rows:
                measure_grid_rows.append({"N° fiche":rec_no,"Code fiche":code,"N° ligne":"",
                                          **{c:"" for c in columns_saved}})
        saved_measure_excel = two_sheet_fiche_excel(
            "Toutes les fiches de mesures enregistrées",
            {"Nombre de fiches":len(my_measurements), "Centre":"ISRA / CRA Saint-Louis",
             "Date d’export":datetime.now().strftime("%d/%m/%Y %H:%M")},
            pd.DataFrame(measure_grid_rows), "Grilles de mesures")
        # Remplace la feuille de présentation générique par une vue récapitulative de chaque fiche.
        from openpyxl import load_workbook
        _wb = load_workbook(BytesIO(saved_measure_excel))
        _ws = _wb["Présentation"]
        _ws.delete_rows(6, _ws.max_row)
        _ws.cell(6,1,"N° fiche"); _ws.cell(6,2,"Code fiche"); _ws.cell(6,3,"Culture"); _ws.cell(6,4,"Essai")
        for _i, _row in enumerate(measure_presentation_rows,7):
            _ws.cell(_i,1,_row.get("N° fiche")); _ws.cell(_i,2,_row.get("Code fiche"))
            _ws.cell(_i,3,_row.get("Culture","")); _ws.cell(_i,4,_row.get("Essai",""))
        _buffer=BytesIO(); _wb.save(_buffer); saved_measure_excel=_buffer.getvalue()
        download_button("📊 Exporter toutes mes fiches de mesures en Excel",
            saved_measure_excel, "MES_FICHES_MESURES_ISRA_CRA.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Aucune fiche de mesures finale enregistrée pour le moment.")

    # Reprendre une fiche déjà enregistrée : corriger ses métadonnées, sa grille et son dossier.
    if my_measurements:
        with st.expander("✏️ Modifier une fiche de mesures déjà enregistrée ou la classer dans un dossier", expanded=False):
            def _saved_measure_label(r):
                return f"{r.get('fiche_code','Fiche')} · {r.get('culture','')} · {r.get('essai','')} · {str(r.get('id',''))[:8]}"
            saved_map = {_saved_measure_label(r): r for r in my_measurements}
            chosen_saved_label = st.selectbox("Fiche à reprendre", list(saved_map), key="saved_measure_to_edit")
            saved_measure = saved_map[chosen_saved_label]
            saved_grid = saved_measure.get("grid") or []
            if isinstance(saved_grid, str):
                try: saved_grid = json.loads(saved_grid)
                except Exception: saved_grid = []
            saved_grid_rows = _normalize_grid_rows(saved_grid)
            saved_headers = saved_measure.get("headers") or []
            if isinstance(saved_headers, str):
                try: saved_headers = json.loads(saved_headers)
                except Exception: saved_headers = []
            saved_columns = list(dict.fromkeys([str(c) for c in saved_headers] +
                                                [str(k) for row in saved_grid_rows for k in row.keys()]))
            saved_grid_df = pd.DataFrame(saved_grid_rows, columns=saved_columns or None).fillna("")
            folder_rows = db_rows("cra_culture_folders", 3000)
            folder_map = {"Sans dossier": ""}
            for f in folder_rows:
                folder_map[f"{f.get('culture','')} · {f.get('folder_name','')} · {f.get('folder_code','')}"] = f.get("id", "")
            current_folder_id = saved_measure.get("folder_id", "")
            folder_labels = list(folder_map)
            current_folder_label = next((k for k,v in folder_map.items() if v == current_folder_id), "Sans dossier")
            with st.form(f"edit_saved_measure_{saved_measure.get('id')}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    edit_essai = st.text_input("Essai", value=saved_measure.get("essai", ""))
                    edit_culture = st.text_input("Culture", value=saved_measure.get("culture", ""))
                    edit_station = st.text_input("Station", value=saved_measure.get("station", ""))
                    edit_year = st.text_input("Année", value=str(saved_measure.get("annee", "")))
                with ec2:
                    edit_responsables = st.text_input("Responsable(s)", value=saved_measure.get("responsables", ""))
                    edit_params = st.text_input("Paramètres mesurés", value=saved_measure.get("parametres", ""))
                    edit_date = st.text_input("Date de mesure", value=str(saved_measure.get("date_mesure", "")))
                    edit_folder_label = st.selectbox("Dossier de classement", folder_labels, index=folder_labels.index(current_folder_label))
                edit_observations = st.text_area("Observations", value=saved_measure.get("observations", ""))
                st.caption("Grille de mesures : modifiez directement les cellules ci-dessous.")
                edit_grid = st.data_editor(saved_grid_df, key=f"edit_saved_grid_{saved_measure.get('id')}", num_rows="dynamic", use_container_width=True, hide_index=True)
                save_saved_measure = st.form_submit_button("💾 Enregistrer les modifications et le classement", type="primary", use_container_width=True)
            if save_saved_measure:
                selected_folder_id_edit = folder_map[edit_folder_label]
                selected_folder = next((f for f in folder_rows if f.get("id") == selected_folder_id_edit), {})
                changes = {"essai":edit_essai, "culture":edit_culture, "station":edit_station,
                           "annee":edit_year, "responsables":edit_responsables, "parametres":edit_params,
                           "date_mesure":edit_date, "observations":edit_observations,
                           "grid":edit_grid.fillna("").to_dict(orient="records"),
                           "headers":[str(c) for c in edit_grid.columns],
                           "ncols":len(edit_grid.columns),"nrows":len(edit_grid.index),
                           "folder_id":selected_folder_id_edit,
                           "folder_name":f"{selected_folder.get('culture','')} · {selected_folder.get('folder_name','')}" if selected_folder_id_edit else ""}
                if db_update("cra_measurement_sheets", saved_measure.get("id"), changes):
                    st.success("Fiche mise à jour : les métadonnées, la grille et le dossier ont été enregistrés.")
                    st.rerun()

# ---------------------------------------------------------------------
# DOSSIERS DE CULTURE — CLASSEMENT SIMPLIFIÉ
# ---------------------------------------------------------------------
elif page == "Dossiers de culture":
    heading(
        "Classement scientifique · ISRA / CRA",
        "MES DOSSIERS DE CULTURE",
        "Un dossier rassemble les fiches techniques et les mesures d'une culture, d'une campagne ou d'un essai."
    )
    st.info(
        "Mode d'emploi : 1) choisissez un dossier, 2) consultez ses fiches, "
        "3) classez les anciennes fiches si nécessaire, 4) téléchargez les archives."
    )

    folders = db_rows("cra_culture_folders", 3000)
    all_tech = db_rows("cra_technical_sheets", 5000)
    all_measures = db_rows("cra_measurement_sheets", 5000)

    # Le formulaire de création reste disponible même lorsque la base est vide.
    with st.expander("＋ Créer un nouveau dossier", expanded=not bool(folders)):
        with st.form("create_culture_folder", clear_on_submit=True):
            folder_name = st.text_input(
                "Nom du dossier *",
                placeholder="Ex. : Riz — Essai variétal 2026"
            )
            folder_culture = choose_culture("Culture *", "folder_create_culture")
            col_a, col_b = st.columns(2)
            with col_a:
                folder_campaign = st.text_input("Campagne / année", str(date.today().year))
                folder_station = st.text_input("Station / site")
            with col_b:
                folder_responsible = st.text_input("Responsable du dossier")
                folder_description = st.text_area("Objet / description", height=80)
            create_folder = st.form_submit_button(
                "📁 Créer le dossier",
                type="primary",
                use_container_width=True
            )
        if create_folder:
            if not folder_name.strip() or not folder_culture.strip():
                st.error("Le nom du dossier et la culture sont obligatoires.")
            else:
                folder_id = str(uuid.uuid4())
                folder_payload = {
                    "id": folder_id,
                    "folder_code": f"DC-{uuid.uuid4().hex[:8].upper()}",
                    "folder_name": folder_name.strip(),
                    "culture": folder_culture,
                    "campaign": folder_campaign,
                    "station": folder_station,
                    "responsible": folder_responsible,
                    "description": folder_description,
                    "created_at": datetime.now().isoformat(timespec="seconds")
                }
                if db_insert("cra_culture_folders", folder_payload):
                    st.session_state["selected_cra_folder"] = folder_id
                    st.session_state["cra_active_folder"] = folder_id
                    st.success("Dossier créé. Il est maintenant sélectionné.")
                    st.rerun()

    folders = db_rows("cra_culture_folders", 3000)
    if not folders:
        st.info("Aucun dossier pour le moment. Créez votre premier dossier ci-dessus.")
    else:
        folder_lookup = {str(f.get("id")): f for f in folders if f.get("id")}
        folder_ids = list(folder_lookup)
        preferred_folder = st.session_state.get("selected_cra_folder")
        active_folder = st.session_state.get("cra_active_folder")
        if preferred_folder in folder_ids:
            initial_folder = preferred_folder
        elif active_folder in folder_ids:
            initial_folder = active_folder
        else:
            initial_folder = folder_ids[0]
        if st.session_state.get("cra_active_folder") != initial_folder:
            st.session_state["cra_active_folder"] = initial_folder

        folder_labels = {
            fid: (
                f"{folder_lookup[fid].get('culture', 'Culture non précisée')} — "
                f"{folder_lookup[fid].get('folder_name', 'Dossier sans nom')} "
                f"· {folder_lookup[fid].get('campaign', '')} "
                f"[{folder_lookup[fid].get('folder_code', '')}]"
            )
            for fid in folder_ids
        }
        selected_folder_id = st.selectbox(
            "📂 Dossier à ouvrir",
            options=folder_ids,
            format_func=lambda fid: folder_labels[fid],
            key="cra_active_folder"
        )
        st.session_state["selected_cra_folder"] = selected_folder_id
        folder = folder_lookup[selected_folder_id]
        folder_name_display = str(folder.get("folder_name") or "Dossier")

        folder_tech = [r for r in all_tech if r.get("folder_id") == selected_folder_id]
        folder_measures = [r for r in all_measures if r.get("folder_id") == selected_folder_id]

        st.markdown(f"### 📁 {folder_name_display}")
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        detail_col1.caption(f"Culture : **{folder.get('culture', '—')}**")
        detail_col2.caption(f"Campagne : **{folder.get('campaign', '—')}**")
        detail_col3.caption(f"Code : **{folder.get('folder_code', '—')}**")
        if folder.get("station") or folder.get("responsible"):
            st.caption(
                f"Station : {folder.get('station') or '—'}  ·  "
                f"Responsable : {folder.get('responsible') or '—'}"
            )
        if folder.get("description"):
            st.write(folder.get("description"))

        metric_a, metric_b, metric_c = st.columns(3)
        metric_a.metric("Fiches techniques", len(folder_tech))
        metric_b.metric("Fiches de mesures", len(folder_measures))
        metric_c.metric("Total des fiches", len(folder_tech) + len(folder_measures))

        tab_content, tab_classify, tab_download = st.tabs([
            "📄 Contenu du dossier",
            "🗂️ Classer des fiches",
            "⬇️ Télécharger le dossier"
        ])

        with tab_content:
            if folder_tech:
                st.markdown("#### Fiches techniques")
                tech_view = [{
                    "Code": r.get("code"),
                    "Année": r.get("annee"),
                    "Station": r.get("station"),
                    "Responsables": r.get("responsables"),
                    "Date": r.get("date_collecte")
                } for r in folder_tech]
                st.dataframe(pd.DataFrame(tech_view), use_container_width=True, hide_index=True)
            if folder_measures:
                st.markdown("#### Fiches de mesures")
                measure_view = [{
                    "Code": r.get("fiche_code"),
                    "Essai": r.get("essai"),
                    "Année": r.get("annee"),
                    "Date de mesure": r.get("date_mesure"),
                    "Paramètres": r.get("parametres")
                } for r in folder_measures]
                st.dataframe(pd.DataFrame(measure_view), use_container_width=True, hide_index=True)
            if not folder_tech and not folder_measures:
                st.info(
                    "Ce dossier est vide. Pour ajouter une fiche, ouvrez « Fiche technique » "
                    "ou « Fiche de mesure » et choisissez ce dossier dans le champ de classement."
                )

        with tab_classify:
            st.write(
                "Cette fonction sert à ranger ici des fiches déjà enregistrées, "
                "sans avoir à les ressaisir. Vous pouvez aussi déplacer une fiche d'un autre dossier."
            )
            tech_choices = {}
            for r in all_tech:
                record_id = str(r.get("id") or "")
                if not record_id:
                    continue
                label = (
                    f"Fiche technique — {r.get('culture', 'Culture')} — "
                    f"{r.get('code') or 'Sans code'} — dossier actuel : "
                    f"{r.get('folder_name') or 'Aucun'} — {record_id[:8]}"
                )
                tech_choices[label] = ("cra_technical_sheets", record_id)
            measure_choices = {}
            for r in all_measures:
                record_id = str(r.get("id") or "")
                if not record_id:
                    continue
                label = (
                    f"Fiche de mesure — {r.get('culture', 'Culture')} — "
                    f"{r.get('fiche_code') or 'Sans code'} — dossier actuel : "
                    f"{r.get('folder_name') or 'Aucun'} — {record_id[:8]}"
                )
                measure_choices[label] = ("cra_measurement_sheets", record_id)
            all_choices = {**tech_choices, **measure_choices}
            if all_choices:
                selected_to_file = st.multiselect(
                    "Sélectionner une ou plusieurs fiches",
                    options=list(all_choices),
                    key=f"file_existing_{selected_folder_id}"
                )
                if st.button(
                    "📂 Ranger les fiches dans ce dossier",
                    key=f"attach_existing_{selected_folder_id}",
                    type="primary",
                    disabled=not selected_to_file,
                    use_container_width=True
                ):
                    moved = 0
                    for label in selected_to_file:
                        table_name, record_id = all_choices[label]
                        if db_update(table_name, record_id, {
                            "folder_id": selected_folder_id,
                            "folder_name": f"{folder.get('culture', '')} · {folder_name_display}"
                        }):
                            moved += 1
                    st.success(f"{moved} fiche(s) classée(s) ou déplacée(s).")
                    st.rerun()
            else:
                st.info("Aucune fiche enregistrée à classer pour le moment.")

        with tab_download:
            # Les tableaux d'observations sont conservés dans les exports séparés.
            tech_meta_rows = []
            tech_obs_rows = []
            measure_meta_rows = []
            measure_grid_rows = []
            for r in folder_tech:
                tech_meta_rows.append({
                    k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                    for k, v in r.items() if k != "observations_periodiques"
                })
                for idx, obs in enumerate(_normalize_grid_rows(r.get("observations_periodiques")), start=1):
                    tech_obs_rows.append({
                        "Code fiche": r.get("code"),
                        "Culture": r.get("culture"),
                        "N° observation": idx,
                        **obs
                    })
            for r in folder_measures:
                measure_meta_rows.append({
                    k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                    for k, v in r.items() if k != "grid"
                })
                grid = _normalize_grid_rows(r.get("grid"))
                for idx, obs in enumerate(grid, start=1):
                    if isinstance(obs, dict):
                        measure_grid_rows.append({
                            "Code fiche": r.get("fiche_code"),
                            "Culture": r.get("culture"),
                            "Essai": r.get("essai"),
                            "N° ligne": idx,
                            **obs
                        })

            folder_excel = excel_bytes({
                "Dossier": pd.DataFrame([{
                    "Code dossier": folder.get("folder_code"),
                    "Dossier": folder.get("folder_name"),
                    "Culture": folder.get("culture"),
                    "Campagne": folder.get("campaign"),
                    "Station": folder.get("station"),
                    "Responsable": folder.get("responsible"),
                    "Description": folder.get("description")
                }]),
                "Fiches_techniques": pd.DataFrame(tech_meta_rows),
                "Observations_tech": pd.DataFrame(tech_obs_rows),
                "Fiches_mesures": pd.DataFrame(measure_meta_rows),
                "Grilles_mesures": pd.DataFrame(measure_grid_rows)
            })
            combined_rows = (
                [{
                    "Type": "Fiche technique",
                    "Code": r.get("code"),
                    "Culture": r.get("culture"),
                    "Date": r.get("date_collecte"),
                    "Résumé": r.get("objectif", "")
                } for r in folder_tech]
                + [{
                    "Type": "Fiche de mesures",
                    "Code": r.get("fiche_code"),
                    "Culture": r.get("culture"),
                    "Date": r.get("date_mesure"),
                    "Résumé": r.get("parametres", "")
                } for r in folder_measures]
            )
            pdf_payload = pdf_bytes(
                "DOSSIER DE CULTURE — " + folder_name_display,
                pd.DataFrame(combined_rows or [{"Information": "Aucune fiche déposée"}])
            )

            csv_zip_io = BytesIO()
            with zipfile.ZipFile(csv_zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "fiches_techniques.csv",
                    pd.DataFrame(tech_meta_rows).to_csv(index=False).encode("utf-8-sig")
                )
                zf.writestr(
                    "observations_techniques.csv",
                    pd.DataFrame(tech_obs_rows).to_csv(index=False).encode("utf-8-sig")
                )
                zf.writestr(
                    "fiches_mesures.csv",
                    pd.DataFrame(measure_meta_rows).to_csv(index=False).encode("utf-8-sig")
                )
                zf.writestr(
                    "grilles_mesures.csv",
                    pd.DataFrame(measure_grid_rows).to_csv(index=False).encode("utf-8-sig")
                )

            st.write("Téléchargez le dossier dans le format qui vous convient :")
            dl_a, dl_b, dl_c = st.columns(3)
            with dl_a:
                download_button(
                    "📊 Classeur Excel complet",
                    folder_excel,
                    f"DOSSIER_{slugify(folder_name_display)}_ISRA.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with dl_b:
                download_button(
                    "📄 Rapport PDF",
                    pdf_payload,
                    f"RAPPORT_{slugify(folder_name_display)}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            with dl_c:
                download_button(
                    "📦 Archives CSV (ZIP)",
                    csv_zip_io.getvalue(),
                    f"CSV_{slugify(folder_name_display)}.zip",
                    "application/zip",
                    use_container_width=True
                )

# ---------------------------------------------------------------------
# COLLABORATION — PARTAGE ET CONTINUITE DES TRAVAUX
# ---------------------------------------------------------------------
elif page == "Collaboration":
    heading("Travail scientifique partagé · ISRA / CRA", "ESPACE COLLABORATION",
            "Publiez un dossier ou une fiche pour permettre à des collègues autorisés de consulter, reprendre et poursuivre le travail.")
    st.markdown("""<div class='card'><b>Principe :</b> le partage est facultatif. Les dossiers non publiés restent privés. Lorsqu'un dossier est partagé, ses fiches techniques et fiches de mesures deviennent accessibles aux personnes sélectionnées. Les modifications sont enregistrées dans la base locale commune.</div>""", unsafe_allow_html=True)
    try:
        users = DB.table("cra_users").select("email,display_name,role,active").execute().data or []
    except Exception:
        users = []
    colleagues = [u for u in users if u.get("email") != st.session_state.get("cra_user_email") and u.get("active", True)]
    colleague_map = {f"{u.get('display_name') or u.get('email')} · {u.get('role','')} ({u.get('email')})":u.get("email") for u in colleagues}
    my_folders = [f for f in db_rows("cra_culture_folders", 3000) if f.get("owner_email") == st.session_state.get("cra_user_email")]
    my_tech = [r for r in db_rows("cra_technical_sheets", 3000) if r.get("owner_email") == st.session_state.get("cra_user_email")]
    my_measures = [r for r in db_rows("cra_measurement_sheets", 3000) if r.get("owner_email") == st.session_state.get("cra_user_email")]
    st.markdown("### 1. Publier un dossier ou une fiche")
    share_kind = st.radio("Élément à partager", ["Dossier complet", "Fiche technique", "Fiche de mesures"], horizontal=True, key="collab_kind")
    target_options = {}
    if share_kind == "Dossier complet":
        target_options = {f"{x.get('culture','')} · {x.get('folder_name','')} · {x.get('folder_code','')}":x.get("id") for x in my_folders}
    elif share_kind == "Fiche technique":
        target_options = {f"{x.get('culture','')} · {x.get('code','')} · {x.get('station','')}":x.get("id") for x in my_tech}
    else:
        target_options = {f"{x.get('culture','')} · {x.get('fiche_code','')} · {x.get('essai','')}":x.get("id") for x in my_measures}
    with st.form("cra_publish_collaboration"):
        if target_options:
            target_label = st.selectbox("Choisir l'élément", list(target_options))
        else:
            target_label = None
            st.info("Aucun élément personnel de ce type à publier pour le moment.")
        recipients_labels = st.multiselect("Donner accès à ces personnes", list(colleague_map), help="Les personnes choisies pourront consulter et modifier les données partagées.")
        share_note = st.text_area("Consigne de travail / message aux collaborateurs", height=70)
        publish = st.form_submit_button("🤝 Publier et partager", type="primary", disabled=not bool(target_options))
    if publish and target_label:
        recipients = [colleague_map[x] for x in recipients_labels]
        if not recipients:
            st.error("Sélectionnez au moins un collaborateur.")
        else:
            target_id = target_options[target_label]
            target_table = {"Dossier complet":"cra_culture_folders", "Fiche technique":"cra_technical_sheets", "Fiche de mesures":"cra_measurement_sheets"}[share_kind]
            item = {"id":str(uuid.uuid4()), "target_type":"folder" if share_kind == "Dossier complet" else "record",
                    "target_table":target_table, "target_id":target_id, "target_label":target_label,
                    "shared_with":recipients, "note":share_note, "status":"active",
                    "created_by":st.session_state.get("cra_user_email"), "created_at":datetime.now().isoformat(timespec="seconds")}
            if db_insert("cra_collaboration", item):
                st.success("Publication effectuée. Les collaborateurs sélectionnés voient maintenant cet élément dans leur espace Collaboration et dans les dossiers partagés.")
                st.rerun()
    st.markdown("### 2. Éléments partagés avec moi")
    shared_records, shared_folders = collaboration_permissions()
    try:
        all_collabs = db_rows("cra_collaboration", 10000)
        active_shares=[x for x in all_collabs if st.session_state.get("cra_user_email") in (x.get("shared_with") or []) and x.get("status","active")=="active"]
    except Exception:
        active_shares=[]
    if active_shares:
        for share in active_shares:
            with st.expander(f"🤝 {share.get('target_label','Élément partagé')} · publié par {share.get('created_by','')}"):
                st.write(share.get("note") or "Aucune consigne particulière.")
                target_table=share.get("target_table"); target_id=share.get("target_id")
                target_rows = db_rows(target_table, 5000) if target_table else []
                target = next((r for r in target_rows if r.get("id")==target_id), None)
                if target:
                    st.caption("Espace de reprise collaborative : les champs et tableaux ci-dessous peuvent être complétés par les personnes autorisées.")
                    if target_table == "cra_technical_sheets":
                        with st.form(f"collab_tech_form_{share.get('id')}"):
                            e_objectif=st.text_area("Objectif de l'essai",target.get("objectif", ""),key=f"co_{share.get('id')}")
                            e_hypothese=st.text_area("Hypothèse scientifique",target.get("hypothese", ""),key=f"ch_{share.get('id')}")
                            e_apports=st.text_area("Apports et interventions",target.get("apports_interventions", ""),key=f"ca_{share.get('id')}")
                            e_observations=st.text_area("Observations qualitatives",target.get("observations", ""),key=f"cv_{share.get('id')}")
                            old_obs=_normalize_grid_rows(target.get("observations_periodiques"))
                            obs_editor=st.data_editor(pd.DataFrame(old_obs),key=f"cg_{share.get('id')}",num_rows="dynamic",use_container_width=True,hide_index=True)
                            e_signature=st.text_input("Signature / visa",target.get("signature_numerique", ""),key=f"cs_{share.get('id')}")
                            save_shared=st.form_submit_button("💾 Enregistrer et poursuivre le travail",type="primary",use_container_width=True)
                        if save_shared:
                            changes={"objectif":e_objectif,"hypothese":e_hypothese,"apports_interventions":e_apports,"observations":e_observations,"observations_periodiques":obs_editor.fillna("").to_dict(orient="records"),"observations_headers":[str(c) for c in obs_editor.columns],"observations_ncols":len(obs_editor.columns),"signature_numerique":e_signature,"last_collaborative_edit_by":st.session_state.get("cra_user_email"),"last_collaborative_edit_at":datetime.now().isoformat(timespec="seconds")}
                            if db_update(target_table,target_id,changes): st.success("Fiche technique mise à jour pour tous les collaborateurs."); st.rerun()
                    elif target_table == "cra_measurement_sheets":
                        with st.form(f"collab_measure_form_{share.get('id')}"):
                            e_params=st.text_input("Paramètres mesurés",target.get("parametres", ""),key=f"mp_{share.get('id')}")
                            e_other=st.text_area("Autre(s)",target.get("autres", ""),key=f"mo_{share.get('id')}")
                            e_obs=st.text_area("Observations",target.get("observations", ""),key=f"mv_{share.get('id')}")
                            old_grid=_normalize_grid_rows(target.get("grid"))
                            grid_editor=st.data_editor(pd.DataFrame(old_grid),key=f"mg_{share.get('id')}",num_rows="dynamic",use_container_width=True,hide_index=True)
                            save_shared=st.form_submit_button("💾 Enregistrer et poursuivre le travail",type="primary",use_container_width=True)
                        if save_shared:
                            changes={"parametres":e_params,"autres":e_other,"observations":e_obs,"grid":grid_editor.fillna("").to_dict(orient="records"),"last_collaborative_edit_by":st.session_state.get("cra_user_email"),"last_collaborative_edit_at":datetime.now().isoformat(timespec="seconds")}
                            if db_update(target_table,target_id,changes): st.success("Fiche de mesures mise à jour pour tous les collaborateurs."); st.rerun()
                    else:
                        with st.form(f"collab_folder_form_{share.get('id')}"):
                            e_campaign=st.text_input("Campagne / année",target.get("campaign", ""),key=f"fc_{share.get('id')}")
                            e_station=st.text_input("Station",target.get("station", ""),key=f"fs_{share.get('id')}")
                            e_responsible=st.text_input("Responsable",target.get("responsible", ""),key=f"fr_{share.get('id')}")
                            e_description=st.text_area("Description du dossier",target.get("description", ""),key=f"fd_{share.get('id')}")
                            save_shared=st.form_submit_button("💾 Mettre à jour le dossier",type="primary",use_container_width=True)
                        if save_shared:
                            changes={"campaign":e_campaign,"station":e_station,"responsible":e_responsible,"description":e_description,"last_collaborative_edit_by":st.session_state.get("cra_user_email"),"last_collaborative_edit_at":datetime.now().isoformat(timespec="seconds")}
                            if db_update(target_table,target_id,changes): st.success("Dossier mis à jour pour tous les collaborateurs."); st.rerun()
                else:
                    st.warning("L'élément n'est plus accessible ou a été archivé.")
    else:
        st.info("Aucun dossier ou fiche ne vous a encore été partagé.")
    st.markdown("### 3. Publications que j'ai créées")
    own_shares=[x for x in db_rows("cra_collaboration", 3000) if x.get("created_by")==st.session_state.get("cra_user_email")]
    if own_shares:
        for share in own_shares:
            with st.expander(f"{share.get('target_label','Élément')} · {share.get('status','active')}"):
                st.write("Accès accordé à : " + ", ".join(share.get("shared_with", [])))
                if st.button("Révoquer le partage", key=f"revoke_{share.get('id')}"):
                    db_update("cra_collaboration", share.get("id"), {"status":"revoked"})
                    st.success("Accès révoqué."); st.rerun()
    else:
        st.caption("Vous n'avez encore publié aucun élément.")

# ---------------------------------------------------------------------
# REFERENTIEL CULTURES
# ---------------------------------------------------------------------
elif page == "Référentiel des cultures":
    heading("Base agronomique", "Référentiel des cultures",
            "Ajoutez les cultures étudiées par le CRA : elles seront proposées dans les fiches techniques et les fiches de mesure.")
    with st.form("add_crop_catalogue", clear_on_submit=True):
        a, b, c = st.columns(3)
        with a:
            crop_name = st.text_input("Nom de la culture *", placeholder="Ex. : Sorgho")
            crop_scientific = st.text_input("Nom scientifique", placeholder="Ex. : Sorghum bicolor")
        with b:
            crop_family = st.text_input("Famille botanique", placeholder="Ex. : Poaceae")
            crop_cycle = st.text_input("Cycle indicatif", placeholder="Ex. : 90 à 120 jours")
        with c:
            crop_group = st.selectbox("Groupe", ["Céréale", "Légumineuse", "Culture maraîchère", "Culture industrielle", "Fruit", "Fourragère", "Autre"])
            crop_notes = st.text_input("Remarque / usage")
        add_crop = st.form_submit_button("Ajouter cette culture", type="primary", use_container_width=True)
    if add_crop:
        if not crop_name.strip():
            st.error("Le nom de la culture est obligatoire.")
        elif any(x.get("name", "").lower() == crop_name.strip().lower() for x in db_rows("cra_cultures", 2000)):
            st.warning("Cette culture existe déjà dans le référentiel.")
        elif db_insert("cra_cultures", {"name": crop_name.strip(), "scientific_name": crop_scientific,
                                         "family": crop_family, "cycle": crop_cycle,
                                         "group_name": crop_group, "notes": crop_notes}):
            st.success("Culture ajoutée. Elle est maintenant disponible dans les fiches.")
            st.rerun()
    crops = db_rows("cra_cultures", 2000)
    st.markdown("#### Cultures enregistrées")
    if crops:
        crop_df = pd.DataFrame(crops)
        st.dataframe(crop_df, use_container_width=True, hide_index=True)
        download_button("Exporter le référentiel des cultures en Excel", excel_bytes({"Cultures": crop_df}),
            "ISRA_CRA_referentiel_cultures.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        crop_to_remove = st.selectbox("Culture à retirer du catalogue", [x.get("name", "") for x in crops])
        st.caption("La suppression du catalogue ne supprime pas les anciennes fiches qui utilisent cette culture.")
        if st.button("Retirer la culture sélectionnée", type="secondary"):
            try:
                DB.table("cra_cultures").delete().eq("name", crop_to_remove).execute()
                st.success("Culture retirée du référentiel.")
                st.rerun()
            except Exception as exc:
                st.error(f"Suppression impossible : {exc}")
    else:
        st.info("Aucune culture personnalisée enregistrée. Les cultures standards restent proposées.")

# ---------------------------------------------------------------------
# FONCTIONNALITE XXL 1 : GESTION DES ESSAIS EXPERIMENTAUX
# ---------------------------------------------------------------------
elif page == "Essais expérimentaux XXL":
    heading("Recherche expérimentale", "Gestion des essais agronomiques XXL",
            "Structurez les protocoles, modalités, répétitions, blocs et parcelles élémentaires ; gardez une trace exploitable de chaque essai.")
    with st.form("trial_builder", clear_on_submit=True):
        st.markdown("#### A. Identification du protocole")
        a, b, c = st.columns(3)
        with a:
            trial_title = st.text_input("Intitulé de l'essai *", placeholder="Ex. : Évaluation variétale du riz")
            trial_code = st.text_input("Code de l'essai", value=f"ESS-{date.today().year}-{uuid.uuid4().hex[:4].upper()}")
        with b:
            trial_culture = choose_culture("Culture de l'essai", "trial_culture")
            trial_variety = st.text_input("Variété(s) / matériel végétal")
        with c:
            trial_site = st.text_input("Site expérimental")
            trial_lead = st.text_input("Responsable scientifique / équipe")
        trial_objective = st.text_area("Objectif scientifique et hypothèse")
        st.markdown("#### B. Dispositif expérimental")
        a, b, c = st.columns(3)
        with a:
            design = st.selectbox("Type de dispositif", ["Blocs complets randomisés", "Carré latin", "Complètement randomisé", "Split-plot", "Essai multilocal", "Observation / démonstration", "Autre"])
            blocks = st.number_input("Nombre de blocs / répétitions", min_value=1, max_value=100, value=3)
        with b:
            treatments_text = st.text_area("Modalités / traitements (une modalité par ligne)", placeholder="T0 - Témoin\nT1 - Dose 1\nT2 - Dose 2")
            plot_area = st.number_input("Surface d'une parcelle élémentaire (m²)", min_value=0.0, value=20.0, step=1.0)
        with c:
            spacing = st.text_input("Écartements / dimensions", placeholder="Ex. : 20 × 20 cm")
            buffer = st.number_input("Allées / bordures (m)", min_value=0.0, value=0.5, step=0.1)
        start_date = st.date_input("Date de mise en place", date.today())
        protocol = st.text_area("Protocole, interventions et calendrier prévisionnel")
        create_trial = st.form_submit_button("Créer et enregistrer le protocole", type="primary", use_container_width=True)
    if create_trial:
        modalities = [x.strip() for x in treatments_text.splitlines() if x.strip()]
        if not trial_title.strip() or not trial_culture:
            st.error("L'intitulé et la culture sont obligatoires.")
        elif not modalities:
            st.error("Renseignez au moins une modalité ou un traitement.")
        else:
            trial_payload = {"code": trial_code, "title": trial_title, "culture": trial_culture,
                "varieties": trial_variety, "site": trial_site, "scientific_lead": trial_lead,
                "objective": trial_objective, "design": design, "blocks": int(blocks),
                "modalities": modalities, "plot_area_m2": plot_area, "spacing": spacing,
                "buffer_m": buffer, "start_date": start_date.isoformat(), "protocol": protocol}
            if db_insert("cra_trials", trial_payload):
                st.success("Protocole expérimental enregistré avec succès.")
    st.markdown("---")
    st.markdown("#### C. Registre des essais et suivi des observations")
    trials = db_rows("cra_trials", 2000)
    if trials:
        trials_df = pd.DataFrame(trials)
        download_button("Exporter tous mes essais en Excel", excel_bytes({"Essais": trials_df}),
            "ISRA_CRA_essais.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        trial_options = {f"{t.get('code')} — {t.get('title')}": t for t in trials}
        chosen_label = st.selectbox("Sélectionner un essai", list(trial_options))
        chosen_trial = trial_options[chosen_label]
        st.write(f"**Culture :** {chosen_trial.get('culture')} · **Site :** {chosen_trial.get('site')} · **Dispositif :** {chosen_trial.get('design')}")
        with st.form("trial_observation"):
            oa, ob, oc = st.columns(3)
            with oa:
                obs_date = st.date_input("Date d'observation", date.today())
                obs_block = st.number_input("Bloc / répétition", min_value=1, value=1)
            with ob:
                obs_modality = st.selectbox("Modalité", chosen_trial.get("modalities") or ["Non précisée"])
                obs_plot = st.text_input("Numéro de parcelle élémentaire")
            with oc:
                obs_stage = st.text_input("Stade phénologique")
                obs_agent = st.text_input("Observateur")
            obs_values = st.text_area("Résultats / variables observées", placeholder="Hauteur, vigueur, nombre de talles, rendement, etc.")
            obs_notes = st.text_area("Incidents, conditions et commentaires")
            save_obs = st.form_submit_button("Enregistrer l'observation", type="primary")
        if save_obs:
            observation = {"trial_id": chosen_trial.get("id"), "trial_code": chosen_trial.get("code"),
                "trial_title": chosen_trial.get("title"), "date_observation": obs_date.isoformat(),
                "block_number": int(obs_block), "modality": obs_modality, "plot_number": obs_plot,
                "stage": obs_stage, "observer": obs_agent, "results": obs_values, "notes": obs_notes}
            if db_insert("cra_trial_observations", observation):
                st.success("Observation ajoutée à l'essai.")
        observations = [x for x in db_rows("cra_trial_observations", 5000) if x.get("trial_id") == chosen_trial.get("id")]
        st.dataframe(pd.DataFrame(observations), use_container_width=True, hide_index=True)
        if observations:
            obs_df = pd.DataFrame(observations)
            download_button("📊 Télécharger Excel (.xlsx)", excel_bytes({"Observations": obs_df}),
                f"Observations_{slugify(str(chosen_trial.get('code')))}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            download_button("📄 Télécharger PDF", pdf_bytes("Observations de l'essai", obs_df),
                f"Observations_{slugify(str(chosen_trial.get('code')))}.pdf", "application/pdf")
    else:
        st.info("Créez votre premier protocole pour activer le registre des observations.")

# ---------------------------------------------------------------------
# FONCTIONNALITE XXL 2 : DIAGNOSTIC PHYTOSANITAIRE
# ---------------------------------------------------------------------
elif page == "Diagnostic phytosanitaire XXL":
    heading("Surveillance sanitaire", "Diagnostic phytosanitaire et alertes XXL",
            "Documentez les symptômes, l'incidence, la sévérité, les facteurs favorisants et les mesures de gestion sur le terrain.")
    with st.form("plant_health_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        with a:
            diag_date = st.date_input("Date du diagnostic", date.today())
            diag_site = st.text_input("Site / localité")
            diag_plot = st.text_input("Parcelle / essai")
        with b:
            diag_crop = choose_culture("Culture diagnostiquée", "diagnostic_culture")
            diag_variety = st.text_input("Variété")
            diag_stage = st.text_input("Stade de la culture")
        with c:
            diag_agent = st.text_input("Agent / diagnostiqueur")
            diag_problem = st.selectbox("Nature du problème", ["Maladie", "Ravageur", "Adventice", "Carence", "Stress hydrique", "Autre désordre"])
            diag_name = st.text_input("Organisme / problème suspecté")
        symptoms = st.text_area("Symptômes et description détaillée", placeholder="Taches, nécroses, flétrissement, pourriture, décoloration…")
        a, b, c = st.columns(3)
        with a:
            incidence = st.number_input("Incidence estimée (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        with b:
            severity = st.select_slider("Sévérité", options=["0 - Absente", "1 - Très faible", "2 - Faible", "3 - Modérée", "4 - Forte", "5 - Très forte"])
        with c:
            urgency = st.selectbox("Niveau d'alerte", ["Information", "Surveillance", "Intervention à planifier", "Urgent"])
        distribution = st.selectbox("Répartition dans la parcelle", ["En foyers", "Homogène", "En bordure", "Aléatoire", "Non déterminée"])
        weather = st.text_input("Conditions récentes (pluie, humidité, température, vent)")
        management = st.text_area("Mesures déjà prises / recommandations proposées")
        sample_ref = st.text_input("Référence d'échantillon envoyé au laboratoire")
        diag_link = st.text_input("Lien externe vers les images / résultats / dossier laboratoire")
        save_diag = st.form_submit_button("Enregistrer le diagnostic", type="primary", use_container_width=True)
    if save_diag:
        diag = {"diagnostic_date": diag_date.isoformat(), "site": diag_site, "plot": diag_plot,
            "culture": diag_crop, "variety": diag_variety, "stage": diag_stage, "agent": diag_agent,
            "problem_type": diag_problem, "suspected_cause": diag_name, "symptoms": symptoms,
            "incidence_percent": incidence, "severity": severity, "alert_level": urgency,
            "distribution": distribution, "weather_conditions": weather, "management": management,
            "sample_reference": sample_ref, "reference_link": diag_link.strip()}
        if db_insert("cra_phytosanitary_diagnostics", diag):
            st.success("Diagnostic enregistré dans le registre phytosanitaire.")
            if urgency == "Urgent":
                st.error("ALERTE URGENTE : transmettez rapidement ce diagnostic au responsable scientifique pour validation.")
    st.markdown("---")
    st.markdown("#### Registre sanitaire et alertes")
    diagnostics = db_rows("cra_phytosanitary_diagnostics", 5000)
    if diagnostics:
        diag_df = pd.DataFrame(diagnostics)
        if "alert_level" in diag_df:
            urgent_df = diag_df[diag_df["alert_level"].isin(["Urgent", "Intervention à planifier"])]
            st.metric("Diagnostics nécessitant une attention", len(urgent_df))
        st.dataframe(diag_df, use_container_width=True, hide_index=True)
        download_button("📊 Télécharger le registre Excel (.xlsx)", excel_bytes({"Diagnostics": diag_df}),
            "CRA_registre_phytosanitaire.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        download_button("📄 Télécharger le registre PDF", pdf_bytes("Registre phytosanitaire", diag_df),
            "CRA_registre_phytosanitaire.pdf", "application/pdf")
    else:
        st.info("Aucun diagnostic phytosanitaire enregistré.")

# ---------------------------------------------------------------------
# CRÉATION DE QUESTIONNAIRE DYNAMIQUE
# ---------------------------------------------------------------------
elif page == "Créer un questionnaire":
    heading("Concepteur de formulaires", "Créer et partager un questionnaire",
            "Définissez vous-même les questions, leur type, les choix possibles et les champs obligatoires.")
    st.caption(f"Contact par défaut des questionnaires : {CONTACT_EMAIL}. Vous pouvez définir une adresse propre à chaque questionnaire ci-dessous.")
    with st.form("create_form"):
        title = st.text_input("Titre du questionnaire *", placeholder="Ex. : Enquête sur les pratiques culturales")
        description = st.text_area("Description / consignes à afficher aux répondants")
        st.markdown("#### Définition des questions")
        st.caption("Ajoutez une ligne par question. Pour les choix, séparez les options par le caractère | (ex. Oui|Non|Ne sait pas).")
        question_template = pd.DataFrame([
            {"Question": "Quelle est votre principale culture ?", "Type": "Texte court", "Obligatoire": True, "Options (séparées par |)": ""},
            {"Question": "Quelle difficulté rencontrez-vous ?", "Type": "Texte long", "Obligatoire": False, "Options (séparées par |)": ""},
        ])
        question_table = st.data_editor(
            question_template, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Question": st.column_config.TextColumn(required=True),
                "Type": st.column_config.SelectboxColumn(options=[
                    "Texte court", "Texte long", "Nombre", "Date", "Oui / Non",
                    "Choix unique", "Choix multiple",
                ], required=True),
                "Obligatoire": st.column_config.CheckboxColumn(),
                "Options (séparées par |)": st.column_config.TextColumn(),
            }, key="question_builder",
        )
        active = st.checkbox("Activer immédiatement le questionnaire", value=True)
        allow_anonymous = st.checkbox("Autoriser les réponses anonymes (option au répondant)", value=True, help="Le répondant pourra choisir de ne pas transmettre son nom ni ses coordonnées.")
        contact_email = st.text_input("E-mail de contact du questionnaire", value=st.session_state.get("questionnaire_contact_email", CONTACT_EMAIL), help="Cette adresse sera affichée aux répondants pour toute question sur le questionnaire.").strip()
        create = st.form_submit_button("Créer le questionnaire et générer son lien", type="primary", use_container_width=True)
    if create:
        qlist = []
        for _, row in question_table.iterrows():
            label = str(row.get("Question", "")).strip()
            if label:
                qtype = str(row.get("Type", "Texte court") or "Texte court")
                options_raw = row.get("Options (séparées par |)", "")
                options = str(options_raw or "").strip()
                qlist.append({
                    "id": uuid.uuid4().hex,
                    "label": label,
                    "type": qtype,
                    "required": bool(row.get("Obligatoire", False)),
                    "options": options,
                })
        if not title.strip():
            st.error("Donnez un titre au questionnaire.")
        elif not qlist:
            st.error("Ajoutez au moins une question.")
        elif any(q["type"].startswith("Choix") and not q["options"].strip() for q in qlist):
            st.error("Chaque question à choix doit avoir des options séparées par |.")
        else:
            fid = uuid.uuid4().hex
            payload = {"id": fid, "title": title.strip(), "description": description,
                       "questions": qlist, "active": active, "allow_anonymous": allow_anonymous, "contact_email": contact_email}
            if db_insert("cra_forms", payload):
                _cached_questionnaire_rows.clear()
                st.session_state["last_created_form"] = fid
                st.success("Questionnaire créé avec succès.")
                st.rerun()

    fid = st.session_state.get("last_created_form")
    if fid:
        st.markdown("#### Lien de partage")
        st.info("Copiez ce lien et envoyez-le aux producteurs, techniciens, partenaires ou répondants. Ils pourront remplir le formulaire sans accéder à l'administration.")
        base = st.text_input("Adresse publique de l'application (URL Streamlit)",
                             value=st.session_state.get("public_base", ""),
                             placeholder="https://nom-de-votre-application.streamlit.app",
                             help="L'adresse e-mail sert de contact. Pour fabriquer un lien cliquable, il faut aussi l'URL publique de l'application.")
        st.session_state["public_base"] = base.strip().rstrip("/")
        st.info(f"Adresse de contact officielle pour les questionnaires : {CONTACT_EMAIL}")
        if base.strip():
            base_clean = base.strip().rstrip("/")
            if not base_clean.startswith(("https://", "http://")):
                st.error("L'URL publique doit commencer par https:// (ou http:// en test local).")
                st.stop()
            link = f"{base_clean}/?form={fid}"
            st.text_input("Lien public du questionnaire", value=link, disabled=True, key=f"generated_link_{fid}")
            st.link_button("Ouvrir le questionnaire", link)
            try:
                import qrcode
                from qrcode.constants import ERROR_CORRECT_M
                qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=10, border=4)
                qr.add_data(link)
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="black", back_color="white")
                qr_buffer = BytesIO()
                qr_image.save(qr_buffer, format="PNG")
                qr_bytes = qr_buffer.getvalue()
                st.markdown("#### QR code du questionnaire")
                st.image(qr_bytes, caption="Scannez ce code avec l'appareil photo du téléphone.", width=260)
                download_button(
                    "📥 Télécharger le QR code (PNG)", qr_bytes,
                    file_name=f"QR_QUESTIONNAIRE_{fid}.png",
                    mime="image/png", use_container_width=True,
                )
                st.caption("Le QR code encode exactement le lien affiché ci-dessus. Testez-le avec un téléphone déconnecté du compte administrateur.")
            except Exception as qr_exc:
                st.error(f"Génération du QR code impossible : {type(qr_exc).__name__}: {qr_exc}")
                st.info("Vérifiez que requirements.txt est à la racine du dépôt et contient qrcode[pil]>=7.4 et Pillow>=10.0.")
            from urllib.parse import quote
            mail_subject = quote(f"Questionnaire ISRA / CRA Saint-Louis : {title.strip()}")
            mail_body = quote(f"Bonjour,\n\nMerci de renseigner le questionnaire suivant :\n{link}\n\nContact ISRA / CRA Saint-Louis : {CONTACT_EMAIL}")
            st.link_button("✉️ Préparer un e-mail avec le lien", f"mailto:?subject={mail_subject}&body={mail_body}")
            st.caption(f"Contact pour les liens et les réponses : {CONTACT_EMAIL}")
        else:
            st.warning("Saisissez l'URL publique de votre application pour générer le lien complet. L'adresse e-mail ne remplace pas l'URL du site.")

# ---------------------------------------------------------------------
# LISTE FORMULAIRES ET RÉPONSES
# ---------------------------------------------------------------------
elif page == "Questionnaires et réponses":
    heading("Administration des enquêtes", "Questionnaires et réponses reçues",
            "Consultez les formulaires créés, activez ou désactivez les liens et exportez les réponses.")
    current_owner = str(st.session_state.get("cra_user_email", ""))
    forms = _cached_questionnaire_rows("cra_forms", current_owner, 1000)
    responses = _cached_questionnaire_rows("cra_responses", current_owner, 3000)
    public_base = st.text_input(
        "URL publique de cette application",
        value=st.session_state.get("public_base", ""),
        placeholder="https://votre-application.streamlit.app",
        key="questionnaire_admin_public_base",
        help="Cette URL sert à reconstruire les liens et QR codes des questionnaires déjà créés."
    ).strip().rstrip("/")
    st.session_state["public_base"] = public_base
    if not forms:
        st.info("Aucun questionnaire créé.")
    else:
        for form in forms:
            fid = str(form.get("id") or "")
            with st.expander(f"📝 {form.get('title', 'Questionnaire')} · {'Actif' if form.get('active') else 'Désactivé'}"):
                st.write(form.get("description", ""))
                st.write(f"**Nombre de questions :** {len(form.get('questions') or [])}")
                for question_index, question in enumerate(form.get("questions") or [], start=1):
                    if isinstance(question, dict):
                        question_label = question.get("label") or question.get("question") or question.get("title") or f"Question {question_index}"
                        question_type = question.get("type", "")
                        st.markdown(f"**{question_index}. {question_label}**" + (f" _({question_type})_" if question_type else ""))
                    else:
                        st.markdown(f"**{question_index}. {question}**")
                if public_base and fid:
                    public_link = f"{public_base}/?form={fid}"
                    st.text_input("Lien public du questionnaire", value=public_link, disabled=True, key=f"public_link_display_{fid}")
                    st.link_button("Ouvrir le questionnaire public", public_link, use_container_width=True)
                    if st.checkbox("Afficher le QR code", value=False, key=f"show_qr_{fid}"):
                        try:
                            import qrcode
                            qr_obj = qrcode.QRCode(box_size=6, border=3)
                            qr_obj.add_data(public_link)
                            qr_obj.make(fit=True)
                            qr_img = qr_obj.make_image(fill_color="black", back_color="white")
                            qr_io = BytesIO(); qr_img.save(qr_io, format="PNG")
                            qr_data = qr_io.getvalue()
                            st.image(qr_data, width=170, caption="QR code du lien public")
                            download_button("Télécharger le QR code", qr_data,
                                file_name=f"QR_QUESTIONNAIRE_{fid}.png", mime="image/png",
                                key=f"qr_existing_{fid}", use_container_width=True)
                        except Exception as qr_error:
                            st.error(f"QR code indisponible : {type(qr_error).__name__}: {qr_error}")
                elif fid:
                    st.info("Renseignez l'URL publique ci-dessus pour afficher le lien et le QR code de ce questionnaire.")
                col1, col2 = st.columns(2)
                with col1:
                    if form.get("active"):
                        if st.button("Désactiver le lien", key=f"deactivate_{fid}"):
                            db_update("cra_forms", fid, {"active": False})
                            _cached_questionnaire_rows.clear()
                            st.rerun()
                    else:
                        if st.button("Réactiver le lien", key=f"activate_{fid}"):
                            db_update("cra_forms", fid, {"active": True})
                            _cached_questionnaire_rows.clear()
                            st.rerun()
                with col2:
                    n = sum(1 for r in responses if r.get("form_id") == fid)
                    st.metric("Réponses", n)
    st.markdown("---")
    st.markdown("### Réponses reçues")
    form_options = {"Tous": None}
    for item in forms:
        item_id = str(item.get("id") or "")
        display_name = f"{item.get('title', 'Questionnaire')} · {item_id[:8]}"
        form_options[display_name] = item_id
    selected_form = st.selectbox("Filtrer par questionnaire", list(form_options.keys()))
    selected_form_id = form_options[selected_form]
    filtered = responses if selected_form_id is None else [r for r in responses if str(r.get("form_id")) == str(selected_form_id)]
    if filtered:
        display = []
        for r in filtered:
            row = {"Questionnaire": r.get("form_title"), "Répondant": r.get("respondent"),
                   "Contact": r.get("contact"), "Date": r.get("submitted_at")}
            answer_values = r.get("answers") or {}
            if not answer_values and r.get("answers_by_id"):
                labels = r.get("question_labels") or {}
                answer_values = {labels.get(k, k): v for k, v in r.get("answers_by_id", {}).items()}
            row.update(answer_values)
            display.append(row)
        df = pd.DataFrame(display)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("### Analyse du questionnaire sélectionné")
        st.metric("Nombre de réponses", len(filtered))
        answer_columns = [c for c in df.columns if c not in {"Questionnaire", "Répondant", "Contact", "Date"}]
        for question_col in answer_columns:
            series = df[question_col].dropna().astype(str)
            series = series[series.str.strip() != ""]
            if not series.empty:
                st.markdown(f"**{question_col}**")
                counts = series.value_counts().rename_axis("Réponse").reset_index(name="Effectif")
                # Éviter les graphiques Vega-Lite qui peuvent déclencher le chargement
                # du module frontend ArrowVegaLiteChart (échec dynamique sur certains déploiements).
                # Le tableau de fréquences reste disponible sans dépendance à ce module.
                st.dataframe(counts.head(20), use_container_width=True, hide_index=True)
        download_button("Télécharger les réponses (.xlsx)",
            excel_bytes({"Réponses": df}), "CRA_reponses_questionnaires.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        download_button("Télécharger les réponses (.csv)", as_csv(display),
            "CRA_reponses_questionnaires.csv", "text/csv")
        download_button("Télécharger les réponses (.pdf)", pdf_bytes("Réponses aux questionnaires", df),
            "CRA_reponses_questionnaires.pdf", "application/pdf")
    else:
        st.info("Aucune réponse ne correspond à ce filtre.")

# ---------------------------------------------------------------------
# DONNÉES ET EXPORTS
# ---------------------------------------------------------------------
elif page == "Données et exports":
    heading("Archivage scientifique", "Données et exports",
            "Sélectionnez les fiches à exporter, retrouvez leurs grilles, modifiez-les et classez-les dans les dossiers.")
    tech = db_rows("cra_technical_sheets")
    measures = db_rows("cra_measurement_sheets")
    responses = db_rows("cra_responses")
    cultures = db_rows("cra_cultures")
    trials = db_rows("cra_trials")
    trial_obs = db_rows("cra_trial_observations")
    diagnostics = db_rows("cra_phytosanitary_diagnostics")
    forms = db_rows("cra_forms")
    folders_export = db_rows("cra_culture_folders")

    # Petite animation d'apparition et transitions discrètes : aucun effet lourd côté navigateur.
    st.markdown("""<style>
    @media (prefers-reduced-motion: no-preference) {
      [data-testid='stVerticalBlock'] > div { animation: israIn .22s ease-out both; }
      [data-testid='stDownloadButton'] button, .stButton button { transition: transform .12s ease, box-shadow .12s ease; }
      [data-testid='stDownloadButton'] button:hover, .stButton button:hover { transform: translateY(-1px); }
      @keyframes israIn { from {opacity:.82; transform:translateY(3px)} to {opacity:1; transform:translateY(0)} }
    }
    </style>""", unsafe_allow_html=True)

    def _as_rows(value):
        return _normalize_grid_rows(value)

    def _record_grid(record, field):
        """Récupère une grille depuis une fiche, un brouillon ou un payload historique."""
        aliases = {
            "observations_periodiques": ("observations_periodiques", "observations_periodiques_json",
                                         "technical_grid", "technical_observations", "grid", "rows"),
            "grid": ("grid", "measurement_grid", "measurement_rows", "measurements", "grille", "mesures", "rows", "data"),
        }
        candidates = [field] + [x for x in aliases.get(field, ()) if x != field]
        # Les versions précédentes ont parfois enveloppé les valeurs dans
        # payload, draft_data, metadata ou form_data. Parcours borné pour ne
        # pas interpréter les cellules arbitraires comme des grilles.
        sources = []
        queue = [(record, 0)]
        seen = set()
        while queue:
            source, depth = queue.pop(0)
            if not isinstance(source, dict) or id(source) in seen:
                continue
            seen.add(id(source))
            sources.append(source)
            if depth >= 4:
                continue
            for nested_key in ("payload", "draft_data", "metadata", "form_data", "data"):
                nested = source.get(nested_key)
                if isinstance(nested, str):
                    try:
                        nested = json.loads(nested)
                    except Exception:
                        continue
                if isinstance(nested, dict):
                    queue.append((nested, depth + 1))
        for source in sources:
            for key in candidates:
                value = source.get(key) if isinstance(source, dict) else None
                if value is not None and not (isinstance(value, str) and not value.strip()):
                    rows = _as_rows(value)
                    if rows:
                        return rows
                    headers = source.get("headers") or source.get("columns")
                    if headers and isinstance(headers, (list, tuple)):
                        return [{str(h): "" for h in headers}]
        return []

    def _is_structured_grid(value):
        """Détecte les grilles natives et JSON, sans confondre un texte libre."""
        if isinstance(value, (list, tuple, pd.DataFrame, dict)):
            return True
        if isinstance(value, str) and value.strip().startswith(("[", "{")):
            try: return isinstance(json.loads(value), (list, dict))
            except Exception: return False
        return False

    def _plain(value):
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        if value is None:
            return ""
        return value

    def _clean(row):
        return {k: _plain(v) for k, v in row.items() if k not in {"owner_email"}}

    def _safe_sheet_name(name, used):
        base = re.sub(r"[\[\]:*?/\\]", "_", str(name)).strip()[:31] or "Données"
        candidate, n = base, 2
        while candidate in used:
            suffix = f"_{n}"
            candidate = base[:31-len(suffix)] + suffix
            n += 1
        used.add(candidate)
        return candidate

    def _export_parts(records, module_label, nested_grid_fields=None):
        """Produit deux tables logiques : présentation des fiches et grilles fidèles."""
        nested_grid_fields = nested_grid_fields or {}
        presentation_rows = []
        grid_rows = []
        for rec_no, record in enumerate(records, 1):
            identity = (record.get("code") or record.get("fiche_code") or
                        record.get("folder_code") or record.get("title") or
                        record.get("form_title") or record.get("id") or f"Fiche_{rec_no}")
            presentation_rows.append({"N° fiche": rec_no, "Code fiche": str(identity),
                                      **{str(k).replace("_", " ").capitalize(): _plain(v)
                                         for k, v in record.items()
                                         if k not in {"id", "owner_email", "grid", "observations_periodiques",
                                                      "observations_periodiques_json", "technical_grid", "measurement_grid",
                                                      "grille", "mesures", "rows", "data", "payload"}
                                         and not isinstance(v, (dict, list, tuple))}})
            payload = record.get("payload")
            if isinstance(payload, str):
                try: payload = json.loads(payload)
                except Exception: payload = {}
            for field, grid_title in nested_grid_fields.items():
                grid = _record_grid(record, field)
                header_key = "observations_headers" if field == "observations_periodiques" else "headers"
                saved_headers = record.get(header_key) or record.get("headers") or []
                if not saved_headers and isinstance(payload, dict):
                    saved_headers = payload.get(header_key) or payload.get("headers") or []
                if isinstance(saved_headers, str):
                    try: saved_headers = json.loads(saved_headers)
                    except Exception: saved_headers = []
                columns = [str(x) for x in saved_headers] if isinstance(saved_headers, (list, tuple)) else []
                for row in grid:
                    for col in row:
                        if str(col) not in columns: columns.append(str(col))
                if not columns:
                    columns = ["Observation"]
                for line_no, row in enumerate(grid, 1):
                    grid_rows.append({"N° fiche": rec_no, "Code fiche": str(identity),
                                      "Type de grille": grid_title, "N° ligne": line_no,
                                      **{col: _plain(row.get(col, "")) for col in columns}})
                if not grid:
                    grid_rows.append({"N° fiche": rec_no, "Code fiche": str(identity),
                                      "Type de grille": grid_title, "N° ligne": "",
                                      **{col: "" for col in columns}})
        presentation = pd.DataFrame(presentation_rows or [{"Information": "Aucun enregistrement sélectionné."}]).fillna("")
        grids = pd.DataFrame(grid_rows).fillna("") if grid_rows else pd.DataFrame(columns=["N° fiche", "Code fiche", "Type de grille", "N° ligne"])
        return {"Présentation": presentation, "Grilles": grids}, None

    def _records_pdf_bytes(title, records, nested_grid_fields=None):
        """PDF fidèle avec les champs de la fiche puis les grilles en tableaux paginables."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, LongTable, TableStyle, KeepTogether
        from xml.sax.saxutils import escape

        out = BytesIO()
        doc = SimpleDocTemplate(out, pagesize=landscape(A4), rightMargin=10*mm, leftMargin=10*mm,
                                topMargin=22*mm, bottomMargin=18*mm, title=str(title),
                                author="ISRA — CRA Saint-Louis")
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("ExportTitle", parent=styles["Title"], fontSize=16, leading=19,
                                     alignment=TA_CENTER, textColor=colors.HexColor("#16483F"), spaceAfter=5)
        small = ParagraphStyle("ExportCell", parent=styles["BodyText"], fontSize=7, leading=8.5,
                               wordWrap="CJK", splitLongWords=1, spaceAfter=0)
        head = ParagraphStyle("ExportHead", parent=small, fontName="Helvetica-Bold", textColor=colors.white)
        story = [Paragraph("INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES — ISRA", styles["Heading3"]),
                 Paragraph("CENTRE DE RECHERCHES AGRICOLES — SAINT-LOUIS", styles["Heading3"]),
                 Paragraph(escape(str(title)), title_style),
                 Paragraph(f"Export du {datetime.now().strftime('%d/%m/%Y à %H:%M')}", small), Spacer(1, 5*mm)]
        nested_grid_fields = nested_grid_fields or {}
        if not records:
            records = []
            story.append(Paragraph("Aucun enregistrement sélectionné.", styles["BodyText"]))
        for rec_no, rec in enumerate(records, 1):
            ref = rec.get("code") or rec.get("fiche_code") or rec.get("folder_code") or rec.get("title") or rec.get("id") or rec_no
            story.append(Paragraph(f"<b>{escape(str(ref))}</b> — {escape(str(rec.get('culture') or ''))}", styles["Heading2"]))
            fields = [[Paragraph("Champ", head), Paragraph("Valeur", head)]]
            parsed_grids = {field: _record_grid(rec, field) for field in nested_grid_fields}
            for key, value in rec.items():
                if key == "owner_email" or (key in nested_grid_fields and
                    (parsed_grids.get(key) or _is_structured_grid(value))):
                    continue
                val = _plain(value)
                val_text = escape(str(val)).replace("\n", "<br/>")
                fields.append([Paragraph(escape(str(key).replace("_", " ")), small),
                               Paragraph(val_text or "—", small)])
            if len(fields) > 1:
                t = LongTable(fields, colWidths=[48*mm, doc.width-48*mm], repeatRows=1, splitByRow=1)
                t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#247A66")),
                                       ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#9CCDBD")),
                                       ("BACKGROUND",(0,1),(0,-1),colors.HexColor("#EFF9F5")),
                                       ("VALIGN",(0,0),(-1,-1),"TOP"),
                                       ("LEFTPADDING",(0,0),(-1,-1),4), ("RIGHTPADDING",(0,0),(-1,-1),4)]))
                story.append(t)
            for field, grid_title in nested_grid_fields.items():
                grid = parsed_grids.get(field) or []
                story.extend([Spacer(1, 3*mm), Paragraph(f"<b>{escape(str(grid_title))}</b> — {len(grid)} ligne(s) renseignée(s)", styles["Heading3"])])
                if not grid:
                    story.append(Paragraph("Grille non renseignée dans cette fiche.", small))
                    continue
                columns = list(dict.fromkeys(k for row in grid for k in row.keys()))
                saved_headers = (rec.get("observations_headers") if field == "observations_periodiques" else rec.get("headers")) or rec.get("headers") or []
                if isinstance(saved_headers, str):
                    try: saved_headers = json.loads(saved_headers)
                    except Exception: saved_headers = []
                if isinstance(saved_headers, (list, tuple)):
                    columns = list(dict.fromkeys([str(c) for c in saved_headers] + columns))
                if not columns:
                    story.append(Paragraph("Aucune colonne définie.", small))
                    continue
                # Un PDF paysage ne peut pas rendre lisiblement 15 à 30 colonnes
                # sur une seule largeur : toutes les colonnes sont donc imprimées
                # par groupes successifs, avec le numéro de ligne conservé.
                max_cols_per_table = 8
                for offset in range(0, len(columns), max_cols_per_table):
                    group = columns[offset:offset + max_cols_per_table]
                    matrix = [[Paragraph(escape(str(c)), head) for c in group]]
                    for row in grid:
                        matrix.append([Paragraph(escape(str(_plain(row.get(c, "")))), small) for c in group])
                    widths = [doc.width / max(1, len(group))] * len(group)
                    gt = LongTable(matrix, colWidths=widths, repeatRows=1, splitByRow=1)
                    gt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#247A66")),
                                            ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#9CCDBD")),
                                            ("VALIGN",(0,0),(-1,-1),"TOP"),
                                            ("LEFTPADDING",(0,0),(-1,-1),3), ("RIGHTPADDING",(0,0),(-1,-1),3)]))
                    story.append(gt)
                    if offset + max_cols_per_table < len(columns):
                        story.append(Paragraph(
                            f"Suite des colonnes : {offset + max_cols_per_table + 1} à {min(offset + 2*max_cols_per_table, len(columns))}",
                            small))

            story.append(Spacer(1, 6*mm))

        def decorate(canvas, document):
            canvas.saveState(); w, h = landscape(A4)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.rect(0, h-12*mm, w, 12*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(10*mm, h-8*mm, "ISRA | CRA SAINT-LOUIS")
            canvas.setStrokeColor(colors.HexColor("#DDB64C")); canvas.line(10*mm, 13*mm, w-10*mm, 13*mm)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica", 7)
            canvas.drawString(10*mm, 7*mm, "YAM GROUP — YAM NUMÉRIQUE")
            canvas.drawRightString(w-10*mm, 7*mm, f"Page {document.page}")
            canvas.restoreState()
        doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
        data = out.getvalue()
        if not data.startswith(b"%PDF"):
            raise ValueError("Le PDF généré est vide ou invalide.")
        return data

    def _module_controls(label, table, records, key, prefix, nested_grid_fields=None, folder_mode=False):
        """Affichage, sélection partielle, exports et modification au bas de chaque onglet."""
        nested_grid_fields = nested_grid_fields or {}
        st.markdown("#### Enregistrements disponibles")
        search = st.text_input("Rechercher dans cet onglet", key=f"{key}_search", placeholder="Code, culture, titre, dossier…")
        visible = records
        if search.strip():
            q = search.casefold()
            visible = [r for r in records if q in json.dumps(r, ensure_ascii=False, default=str).casefold()]
        if not visible:
            st.info("Aucun enregistrement ne correspond à cette recherche.")
            return
        display_rows = [{k:_plain(v) for k,v in r.items() if k not in {"owner_email"} and not isinstance(v, (dict,list))} for r in visible]
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
        def _label(r):
            title = r.get("code") or r.get("fiche_code") or r.get("folder_code") or r.get("folder_name") or r.get("trial_name") or r.get("title") or r.get("form_title") or r.get("respondent") or r.get("name") or str(r.get("id",""))
            return f"{title} · {str(r.get('culture',''))} · {str(r.get('id',''))[:8]}"
        by_label = {_label(r):r for r in visible}
        selected_labels = st.multiselect(
            "Téléchargement — sélectionnez des éléments ou laissez vide pour tout exporter",
            list(by_label), key=f"{key}_partial"
        )
        # Par défaut, l'absence de sélection signifie « toutes les fiches visibles ».
        # Cela évite de générer deux exports vides alors que des fiches sont enregistrées.
        selected_records = [by_label[x] for x in selected_labels] if selected_labels else list(visible)

        # Pour un dossier, les exports contiennent le dossier, ses fiches et toutes les grilles liées.
        if folder_mode and selected_records:
            expanded = []
            for folder in selected_records:
                fid = folder.get("id")
                child_tech = [r for r in tech if r.get("folder_id") == fid]
                child_measure = [r for r in measures if r.get("folder_id") == fid]
                expanded.extend(child_tech + child_measure)
            folder_sheets = {"Dossiers":pd.DataFrame([_clean(x) for x in selected_records])}
            for rec in expanded:
                kind = "Fiches techniques" if rec in tech else "Fiches de mesure"
                nested = {"observations_periodiques":"Grilles techniques"} if kind == "Fiches techniques" else {"grid":"Grilles de mesures"}
                sub_sheets, _ = _export_parts([rec], kind, nested)
                for nm, frame in sub_sheets.items():
                    if nm in folder_sheets: folder_sheets[nm] = pd.concat([folder_sheets[nm], frame], ignore_index=True)
                    else: folder_sheets[nm] = frame
            pdf_records = []
            pdf_grid_fields = {"observations_periodiques":"Grilles techniques", "grid":"Grilles de mesures"}
            for f in selected_records:
                pdf_records.append({"Type":"DOSSIER", **f})
                fid = f.get("id")
                for r in [x for x in tech if x.get("folder_id") == fid]:
                    pdf_records.append({"Type":"Fiche technique", **r})
                for r in [x for x in measures if x.get("folder_id") == fid]:
                    pdf_records.append({"Type":"Fiche de mesure", **r})
            xlsx_payload = excel_bytes(folder_sheets)
            pdf_payload = _records_pdf_bytes("Dossiers de culture sélectionnés", pdf_records, pdf_grid_fields)
        elif selected_records:
            xlsx_sheets, _ = _export_parts(selected_records, label, nested_grid_fields)
            xlsx_payload = excel_bytes(xlsx_sheets)
            pdf_payload = _records_pdf_bytes(label + " — sélection", selected_records, nested_grid_fields)
        else:
            # Relecture immédiate de la table : certaines sessions Streamlit gardent
            # une ancienne liste en mémoire après l'enregistrement d'une fiche.
            try:
                fresh_records = db_rows(table, 5000)
            except Exception:
                fresh_records = []
            if fresh_records:
                visible = fresh_records
                selected_records = list(fresh_records)
                xlsx_sheets, _ = _export_parts(selected_records, label, nested_grid_fields)
                xlsx_payload = excel_bytes(xlsx_sheets)
                pdf_payload = _records_pdf_bytes(label + " — toutes les fiches", selected_records, nested_grid_fields)
            else:
                xlsx_payload = pdf_payload = None
                st.caption("Aucune fiche enregistrée dans cette rubrique : les exports seront disponibles dès le premier enregistrement.")

        # Dernier contrôle : ne jamais transmettre un buffer vide à Streamlit.
        # Si des fiches existent, on reconstruit les deux fichiers directement
        # depuis les enregistrements bruts, sans dépendre du filtre de sélection.
        if selected_records:
            if not xlsx_payload:
                fallback_sheets, _ = _export_parts(selected_records, label, nested_grid_fields)
                xlsx_payload = excel_bytes(fallback_sheets)
            if not pdf_payload:
                pdf_payload = _records_pdf_bytes(label + " — export complet", selected_records, nested_grid_fields)
            if not xlsx_payload or not bytes(xlsx_payload).startswith(b"PK"):
                raise RuntimeError(f"Échec de génération Excel pour {label} : fichier XLSX invalide.")
            if not pdf_payload or not bytes(pdf_payload).startswith(b"%PDF"):
                raise RuntimeError(f"Échec de génération PDF pour {label} : fichier PDF invalide.")

        st.markdown("#### Modifier / classer une fiche")
        editable_records = [r for r in visible if r.get("owner_email") == st.session_state.get("cra_user_email") or r.get("created_by") == st.session_state.get("cra_user_email")]
        if editable_records:
            edit_map = {_label(r):r for r in editable_records}
            edit_label = st.selectbox("Fiche à modifier", list(edit_map), key=f"{key}_edit_choice")
            edit_record = edit_map[edit_label]
            editable_fields = {k:v for k,v in edit_record.items() if k not in {"id","owner_email","created_at"}}
            edits = {}
            with st.form(f"{key}_edit_form_{edit_record.get('id')}"):
                st.caption("Les champs imbriqués (grilles, réponses, questions) sont modifiables au format JSON ; les autres champs utilisent des contrôles simples.")
                for field, old in editable_fields.items():
                    label_field = field.replace("_", " ").capitalize()
                    widget_key = f"{key}_edit_{edit_record.get('id')}_{field}"
                    if isinstance(old, bool): edits[field] = st.checkbox(label_field, value=old, key=widget_key)
                    elif isinstance(old, (int,float)) and not isinstance(old,bool): edits[field] = st.number_input(label_field, value=old, key=widget_key)
                    elif field in nested_grid_fields and _is_structured_grid(old):
                        # Grille éditable visuellement : colonnes renommables, ajoutables,
                        # supprimables, lignes ajoutables/supprimables. Pas besoin de JSON.
                        grid_rows = _as_rows(old)
                        if isinstance(old, str) and old.strip():
                            try:
                                parsed_old = json.loads(old)
                                grid_rows = _as_rows(parsed_old)
                            except Exception:
                                grid_rows = []
                        grid_cols = list(dict.fromkeys(
                            str(col) for row in grid_rows for col in row.keys()
                        ))
                        if not grid_cols and grid_rows:
                            grid_cols = list(grid_rows[0].keys())
                        col_text = st.text_input(
                            f"Colonnes de la grille — {label_field} (séparées par des virgules)",
                            value=", ".join(grid_cols), key=widget_key + "_columns"
                        )
                        new_cols = list(dict.fromkeys(x.strip() for x in col_text.split(",") if x.strip()))
                        if not new_cols:
                            st.warning("Définissez au moins une colonne pour conserver cette grille.")
                            new_cols = grid_cols or ["Observation"]
                        base_rows = [{col: row.get(col, "") for col in new_cols} for row in grid_rows]
                        grid_df = pd.DataFrame(base_rows, columns=new_cols)
                        st.caption("Modifiez les cellules, ajoutez/supprimez des lignes avec le contrôle du tableau. Pour ajouter, renommer ou supprimer des colonnes, modifiez la liste ci-dessus.")
                        edited_df = st.data_editor(
                            grid_df, key=widget_key + "_grid_editor", num_rows="dynamic",
                            use_container_width=True, hide_index=True
                        )
                        edits[field] = edited_df.fillna("").to_dict(orient="records")
                    elif isinstance(old, (dict,list)):
                        raw = json.dumps(old, ensure_ascii=False, indent=2, default=str)
                        edited = st.text_area(label_field + " (JSON)", value=raw, key=widget_key, height=140)
                        try: edits[field] = json.loads(edited)
                        except Exception: edits[field] = old; st.warning(f"Le JSON du champ « {label_field} » est invalide : ancienne valeur conservée.")
                    else:
                        text = "" if old is None else str(old)
                        if len(text)>100 or "\n" in text: edits[field]=st.text_area(label_field, value=text, key=widget_key, height=90)
                        else: edits[field]=st.text_input(label_field, value=text, key=widget_key)
                if table in {"cra_technical_sheets","cra_measurement_sheets"} and folders_export:
                    folder_opts = {"— Sans dossier —":None}
                    folder_opts.update({f"{f.get('folder_code','')} · {f.get('culture','')} · {f.get('folder_name','Dossier')}":f.get("id") for f in folders_export})
                    current_id = edit_record.get("folder_id")
                    labels = list(folder_opts)
                    default_idx = next((i for i,(nm,fid) in enumerate(folder_opts.items()) if fid==current_id),0)
                    chosen_folder_label = st.selectbox("Classer / déplacer dans le dossier", labels, index=default_idx, key=f"{key}_folder_{edit_record.get('id')}")
                    edits["folder_id"] = folder_opts[chosen_folder_label]
                    edits["folder_name"] = next((f.get("folder_name") for f in folders_export if f.get("id")==edits["folder_id"]), None)
                save = st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True)
            if save:
                if db_update(table, str(edit_record.get("id")), edits):
                    st.success("Fiche modifiée et classement enregistré.")
                    st.rerun()

            # Suppression définitive encadrée : propriétaire uniquement,
            # sauvegarde téléchargeable, confirmation explicite et motif obligatoire.
            with st.expander("🗑️ Suppression définitive d’une donnée", expanded=False):
                record_id = str(edit_record.get("id", ""))
                short_id = record_id[-6:] if record_id else ""
                st.warning(
                    "Cette opération efface définitivement l’enregistrement de la base active. "
                    "Elle ne doit être utilisée qu’en cas d’erreur ou de doublon avéré. "
                    "Le journal d’audit conserve une trace de l’opération, mais ne remplace pas une sauvegarde."
                )
                st.write(f"**Rubrique :** {label}  ·  **Identifiant :** `{record_id}`")
                st.write("**Donnée sélectionnée :** " + _label(edit_record))
                backup_bytes = json.dumps(edit_record, ensure_ascii=False, indent=2, default=str).encode("utf-8")
                st.download_button(
                    "⬇️ Télécharger une copie de sauvegarde avant suppression (.json)",
                    data=backup_bytes,
                    file_name=f"SAUVEGARDE_AVANT_SUPPRESSION_{table}_{short_id}.json",
                    mime="application/json",
                    key=f"{key}_delete_backup_{short_id}",
                    use_container_width=True,
                )
                st.caption(
                    "Protocole : 1) téléchargez la sauvegarde ; 2) vérifiez la fiche et son identifiant ; "
                    "3) indiquez le motif ; 4) saisissez le code de confirmation ; 5) confirmez."
                )
                reason = st.text_area(
                    "Motif obligatoire de la suppression (15 caractères minimum)",
                    key=f"{key}_delete_reason_{short_id}",
                    placeholder="Ex. : doublon confirmé après vérification avec le responsable scientifique…",
                )
                confirmation_code = st.text_input(
                    f"Pour confirmer, saisissez exactement : SUPPRIMER {short_id}",
                    key=f"{key}_delete_code_{short_id}",
                )
                backup_ack = st.checkbox(
                    "J’ai téléchargé la sauvegarde et vérifié qu’il s’agit bien de la donnée à supprimer.",
                    key=f"{key}_delete_backup_ack_{short_id}",
                )
                if st.button(
                    "⚠️ CONFIRMER LA SUPPRESSION DÉFINITIVE",
                    key=f"{key}_delete_confirm_{short_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    current_email = st.session_state.get("cra_user_email", "")
                    if not current_email:
                        st.error("Session invalide : reconnectez-vous avant toute suppression.")
                    elif not backup_ack:
                        st.error("Téléchargez et vérifiez d’abord la sauvegarde, puis cochez la confirmation.")
                    elif len(reason.strip()) < 15:
                        st.error("Le motif est obligatoire et doit contenir au moins 15 caractères.")
                    elif confirmation_code.strip() != f"SUPPRIMER {short_id}":
                        st.error("Code de confirmation incorrect. Aucune donnée n’a été supprimée.")
                    else:
                        try:
                            # Relecture directe juste avant l'action : ne pas se fier au cache Streamlit.
                            fresh = (_SUPABASE.table(table).select("id,owner_email,payload,created_at")
                                     .eq("id", record_id).limit(1).execute().data or [])
                            if not fresh:
                                st.error("Cette donnée n’existe déjà plus. Actualisez la page.")
                            else:
                                stored = fresh[0]
                                payload_now = stored.get("payload") or {}
                                if isinstance(payload_now, str):
                                    try: payload_now = json.loads(payload_now)
                                    except Exception: payload_now = {}
                                is_owner = (stored.get("owner_email") == current_email or
                                            payload_now.get("owner_email") == current_email or
                                            payload_now.get("created_by") == current_email)
                                if not is_owner:
                                    st.error("Suppression refusée : vous n’êtes pas propriétaire de cet enregistrement.")
                                else:
                                    # Empêcher la suppression d'un parent qui possède encore des données liées.
                                    dependencies = []
                                    if table == "cra_culture_folders":
                                        for child_table in ("cra_technical_sheets", "cra_measurement_sheets"):
                                            child = (_SUPABASE.table(child_table).select("id")
                                                     .filter("payload->>folder_id", "eq", record_id).limit(1).execute().data or [])
                                            if child: dependencies.append(child_table)
                                    elif table == "cra_forms":
                                        child = (_SUPABASE.table("cra_responses").select("id")
                                                 .filter("payload->>form_id", "eq", record_id).limit(1).execute().data or [])
                                        if child: dependencies.append("cra_responses")
                                    elif table == "cra_trials":
                                        child = (_SUPABASE.table("cra_trial_observations").select("id")
                                                 .filter("payload->>trial_id", "eq", record_id).limit(1).execute().data or [])
                                        if child: dependencies.append("cra_trial_observations")
                                    if dependencies:
                                        st.error(
                                            "Suppression bloquée : cette donnée possède encore des éléments liés "
                                            "(" + ", ".join(dependencies) + "). Traitez d’abord ces éléments pour éviter des données orphelines."
                                        )
                                    else:
                                        # Le trigger PostgreSQL écrit l'instantané de suppression dans cra_audit_log.
                                        _SUPABASE.table(table).delete().eq("id", record_id).execute()
                                        remaining = (_SUPABASE.table(table).select("id")
                                                     .eq("id", record_id).limit(1).execute().data or [])
                                        if remaining:
                                            st.error("La suppression n’a pas pu être vérifiée. Contactez l’administrateur ; ne répétez pas l’opération sans contrôle.")
                                        else:
                                            _SUPABASE.table("cra_audit_log").insert({
                                                "actor_email": current_email,
                                                "action": "DELETE_PERMANENT_CONFIRMED",
                                                "table_name": table,
                                                "record_id": record_id,
                                                "before_data": {
                                                    "label": _label(edit_record),
                                                    "reason": reason.strip(),
                                                    "protocol": "backup_downloaded_and_explicit_confirmation",
                                                },
                                                "after_data": None,
                                                "event_at": datetime.utcnow().isoformat(),
                                            }).execute()
                                            st.success("Suppression définitive effectuée. L’opération est inscrite au journal d’audit.")
                                            st.rerun()
                        except Exception as exc:
                            st.error(f"Suppression non effectuée ou non vérifiable : {type(exc).__name__}: {exc}")
        else:
            st.info("Aucune fiche modifiable dans cette sélection : seuls les enregistrements dont vous êtes propriétaire sont modifiables.")

        st.markdown("#### Télécharger la sélection")
        c1,c2 = st.columns(2)
        with c1:
            if selected_records and xlsx_payload:
                st.download_button("📊 Excel — sélection + grilles", data=bytes(xlsx_payload),
                    file_name=f"{prefix}_SELECTION.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"{key}_xlsx_direct", use_container_width=True)
            else:
                st.button("📊 Excel — aucune fiche disponible", key=f"{key}_xlsx_empty", disabled=True, use_container_width=True)
        with c2:
            if selected_records and pdf_payload:
                st.download_button("📄 PDF — sélection + grilles", data=bytes(pdf_payload),
                    file_name=f"{prefix}_SELECTION.pdf", mime="application/pdf",
                    key=f"{key}_pdf_direct", use_container_width=True)
            else:
                st.button("📄 PDF — aucune fiche disponible", key=f"{key}_pdf_empty", disabled=True, use_container_width=True)

    st.markdown("### 📦 Export intégral (facultatif)")
    all_measure_grid_rows=[]
    for mr in measures:
        for gi, gr in enumerate(_record_grid(mr, "grid"),1):
            if isinstance(gr,dict): all_measure_grid_rows.append({"Code fiche":mr.get("fiche_code"),"Culture":mr.get("culture"),"N° ligne":gi,**gr})
    all_tech_grid_rows=[]
    for tr in tech:
        for gi, gr in enumerate(_record_grid(tr, "observations_periodiques"),1):
            if isinstance(gr,dict): all_tech_grid_rows.append({"Code fiche":tr.get("code"),"Culture":tr.get("culture"),"N° ligne":gi,**gr})
    all_sheets={
        "Fiches techniques":pd.DataFrame([_clean({k:v for k,v in r.items() if k!="observations_periodiques"}) for r in tech]),
        "Grilles techniques":pd.DataFrame(all_tech_grid_rows),
        "Fiches de mesure":pd.DataFrame([_clean({k:v for k,v in r.items() if k!="grid"}) for r in measures]),
        "Grilles de mesures":pd.DataFrame(all_measure_grid_rows),
        "Dossiers":pd.DataFrame([_clean(x) for x in folders_export]),
        "Essais":pd.DataFrame([_clean(x) for x in trials]),
        "Observations essais":pd.DataFrame([_clean(x) for x in trial_obs]),
        "Diagnostics":pd.DataFrame([_clean(x) for x in diagnostics]),
        "Questionnaires":pd.DataFrame([_clean(x) for x in forms]),
        "Réponses":pd.DataFrame([_clean(x) for x in responses]),
        "Cultures":pd.DataFrame([_clean(x) for x in cultures]),
    }
    download_button("📚 Télécharger l'espace complet (Excel)", excel_bytes(all_sheets), "ISRA_CRA_ESPACE_COMPLET.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    export_tabs=st.tabs(["Fiches techniques", "Fiches de mesure", "Dossiers de culture", "Essais", "Observations d’essais", "Diagnostics", "Questionnaires", "Réponses aux questionnaires"])
    with export_tabs[0]:
        _module_controls("Fiches techniques", "cra_technical_sheets", tech, "tab_tech", "FICHES_TECHNIQUES", {"observations_periodiques":"Grilles techniques"})
    with export_tabs[1]:
        _module_controls("Fiches de mesure", "cra_measurement_sheets", measures, "tab_measure", "FICHES_MESURE", {"grid":"Grilles de mesures"})
    with export_tabs[2]:
        st.info("Un dossier regroupe ses fiches techniques et ses fiches de mesure. Sélectionnez le dossier : l'export récupère automatiquement les fiches classées et leurs grilles.")
        _module_controls("Dossiers de culture", "cra_culture_folders", folders_export, "tab_folders", "DOSSIERS_CULTURE", folder_mode=True)
    with export_tabs[3]:
        _module_controls("Essais expérimentaux", "cra_trials", trials, "tab_trials", "ESSAIS", {"modalities":"Grille des modalités","observations":"Grilles observations","grid":"Grilles essais"})
    with export_tabs[4]:
        _module_controls("Observations d’essais", "cra_trial_observations", trial_obs, "tab_trial_obs", "OBSERVATIONS_ESSAIS", {"grid":"Grilles observations","measurements":"Grilles mesures"})
    with export_tabs[5]:
        _module_controls("Diagnostics phytosanitaires", "cra_phytosanitary_diagnostics", diagnostics, "tab_diagnostics", "DIAGNOSTICS", {"observations":"Grilles observations","symptoms":"Symptômes détaillés","grid":"Grille diagnostic"})
    with export_tabs[6]:
        _module_controls("Questionnaires", "cra_forms", forms, "tab_forms", "QUESTIONNAIRES", {"questions":"Grilles questions"})
    with export_tabs[7]:
        response_records=[]
        for r in responses:
            answers=r.get("answers") or {}
            if not answers and r.get("answers_by_id"):
                labels=r.get("question_labels") or {}
                answers={labels.get(k,k):v for k,v in r.get("answers_by_id",{}).items()}
            response_records.append({**r,"answers":answers})
        _module_controls("Réponses aux questionnaires", "cra_responses", response_records, "tab_responses", "REPONSES_QUESTIONNAIRES", {"answers":"Grilles réponses","answers_by_id":"Réponses par identifiant"})

# ---------------------------------------------------------------------
# JOURNAL D’AUDIT QUOTIDIEN — ADMINISTRATEUR UNIQUEMENT
# ---------------------------------------------------------------------
elif page == "Journal d’audit":
    heading(
        "Journal d’audit quotidien",
        "Traçabilité active des opérations réalisées sur la plateforme",
        "Consultation réservée exclusivement à l’administrateur. Les événements sont lus depuis le journal append-only cra_audit_log."
    )
    if st.session_state.get("cra_user_role") != "Administrateur des comptes":
        st.error("Accès refusé : le journal d’audit est strictement réservé à l’administrateur.")
        st.stop()

    audit_top1, audit_top2, audit_top3 = st.columns([2, 2, 1])
    with audit_top1:
        audit_day = st.date_input("Journée à consulter", value=date.today(), key="cra_audit_day")
    with audit_top2:
        audit_search = st.text_input("Recherche (utilisateur, action, table ou identifiant)", key="cra_audit_search")
    with audit_top3:
        st.write("")
        if st.button("🔄 Actualiser le journal", type="primary", use_container_width=True, key="cra_audit_refresh"):
            st.rerun()

    try:
        audit_response = _SUPABASE.table("cra_audit_log").select(
            "id,actor_email,action,table_name,record_id,before_data,after_data,event_at"
        ).order("event_at", desc=True).limit(3000).execute()
        audit_rows = audit_response.data or []
        audit_df = pd.DataFrame(audit_rows)
        if not audit_df.empty:
            audit_df["event_at"] = pd.to_datetime(audit_df["event_at"], errors="coerce", utc=True)
            # La date affichée est la date du serveur (UTC), cohérente avec event_at.
            audit_df["jour_utc"] = audit_df["event_at"].dt.date
            daily_df = audit_df[audit_df["jour_utc"] == audit_day].copy()
            if audit_search.strip():
                search_cols = [c for c in ["actor_email", "action", "table_name", "record_id"] if c in daily_df.columns]
                mask = daily_df[search_cols].fillna("").astype(str).apply(
                    lambda col: col.str.contains(audit_search.strip(), case=False, regex=False)
                ).any(axis=1) if search_cols else pd.Series(False, index=daily_df.index)
                daily_df = daily_df[mask]

            total_day = int((audit_df["jour_utc"] == audit_day).sum())
            inserts_day = int(((audit_df["jour_utc"] == audit_day) & audit_df["action"].astype(str).str.upper().str.contains("INSERT|CREATE", regex=True)).sum())
            updates_day = int(((audit_df["jour_utc"] == audit_day) & audit_df["action"].astype(str).str.upper().str.contains("UPDATE|MODIF", regex=True)).sum())
            deletes_day = int(((audit_df["jour_utc"] == audit_day) & audit_df["action"].astype(str).str.upper().str.contains("DELETE|SUPPRESS", regex=True)).sum())
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Événements du jour", total_day)
            m2.metric("Créations", inserts_day)
            m3.metric("Modifications", updates_day)
            m4.metric("Suppressions", deletes_day)

            st.markdown(f"### Activité du {audit_day.strftime('%d/%m/%Y')} (UTC)")
            st.caption(f"{len(daily_df)} événement(s) affiché(s) après filtrage · {len(audit_rows)} événement(s) chargés (maximum 3 000).")
            if daily_df.empty:
                st.info("Aucun événement enregistré pour cette journée ou cette recherche.")
            else:
                display_df = daily_df.copy()
                display_df["event_at"] = display_df["event_at"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                display_df["before_data"] = display_df["before_data"].apply(
                    lambda v: json.dumps(v, ensure_ascii=False, default=str) if v is not None else ""
                )
                display_df["after_data"] = display_df["after_data"].apply(
                    lambda v: json.dumps(v, ensure_ascii=False, default=str) if v is not None else ""
                )
                columns_order = [c for c in ["event_at", "actor_email", "action", "table_name", "record_id"] if c in display_df.columns]
                st.dataframe(
                    display_df[columns_order].rename(columns={
                        "event_at": "Date / heure (UTC)", "actor_email": "Utilisateur",
                        "action": "Opération", "table_name": "Table", "record_id": "Identifiant"
                    }),
                    use_container_width=True, hide_index=True
                )
                st.markdown("#### 🔎 Détail d’un événement")
                event_options = daily_df.to_dict("records")
                selected_event_id = st.selectbox(
                    "Sélectionner un événement",
                    options=list(range(len(event_options))),
                    format_func=lambda i: (
                        f"#{event_options[i].get('id')} · {event_options[i].get('action')} · "
                        f"{event_options[i].get('table_name')} · {event_options[i].get('actor_email')}"
                    ),
                    key="cra_audit_selected_event"
                )
                chosen_event = event_options[selected_event_id]
                with st.expander("Afficher les données avant / après l’opération", expanded=True):
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**État avant**")
                        st.json(chosen_event.get("before_data") or {}, expanded=False)
                    with right:
                        st.markdown("**État après**")
                        st.json(chosen_event.get("after_data") or {}, expanded=False)
                    st.caption(f"Événement n° {chosen_event.get('id')} · {chosen_event.get('event_at')} · {chosen_event.get('record_id')}")

                export_rows = daily_df.copy()
                export_rows["event_at"] = export_rows["event_at"].astype(str)
                csv_data = export_rows.drop(columns=["jour_utc"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
                json_data = json.dumps(
                    export_rows.drop(columns=["jour_utc"], errors="ignore").to_dict("records"),
                    ensure_ascii=False, indent=2, default=str
                ).encode("utf-8")
                ex1, ex2 = st.columns(2)
                ex1.download_button("⬇️ Exporter le journal du jour (CSV)", csv_data,
                    file_name=f"journal_audit_{audit_day.isoformat()}.csv", mime="text/csv", use_container_width=True)
                ex2.download_button("⬇️ Exporter le journal du jour (JSON)", json_data,
                    file_name=f"journal_audit_{audit_day.isoformat()}.json", mime="application/json", use_container_width=True)
        else:
            st.info("Le journal d’audit ne contient encore aucun événement.")
    except Exception as audit_exc:
        st.error(f"Impossible de charger le journal d’audit : {audit_exc}")
        st.info("Vérifiez que la table cra_audit_log existe et que la connexion Supabase côté serveur dispose des droits de lecture.")

# ---------------------------------------------------------------------
# GESTION DES COMPTES
# ---------------------------------------------------------------------
elif page == "Gestion des comptes":
    heading("Administration des accès", "Comptes chercheurs, stagiaires et techniciens",
            "Créez des espaces séparés. Aucun compte ne peut consulter les données privées d'un autre compte.")
    if st.session_state.get("cra_user_role") != "Administrateur des comptes":
        st.warning("Cette rubrique est réservée au compte d'administration des accès.")
    else:
        with st.form("create_cra_user", clear_on_submit=True):
            a,b,c = st.columns(3)
            with a:
                new_name = st.text_input("Nom complet")
                new_email = st.text_input("Identifiant / e-mail")
            with b:
                new_role = st.selectbox("Profil", ["Chercheur", "Stagiaire", "Technicien"])
                new_password = st.text_input("Mot de passe initial", type="password")
            with c:
                new_password2 = st.text_input("Confirmer le mot de passe", type="password")
                new_active = st.checkbox("Compte actif", value=True)
            role_defaults = {
                "Chercheur": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Pointage", "Référentiel des cultures", "Essais expérimentaux XXL", "Diagnostic phytosanitaire XXL", "Créer un questionnaire", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
                "Stagiaire": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Pointage", "Diagnostic phytosanitaire XXL", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
                "Technicien": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Pointage", "Référentiel des cultures", "Diagnostic phytosanitaire XXL", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
            }
            # Streamlit exige que chaque valeur de « default » existe dans « options ».
            # On filtre les droits par sécurité et on conserve Collaboration dans les choix.
            default_permissions = [p for p in role_defaults.get(new_role, []) if p in USER_PAGES]
            new_permissions = st.multiselect(
                "Onglets autorisés pour cette personne",
                options=USER_PAGES,
                default=default_permissions,
                help="Seuls les onglets sélectionnés apparaîtront dans sa barre de navigation. La gestion des comptes reste réservée à l'administration."
            )
            create_user = st.form_submit_button("Créer l'espace personnel", type="primary")
        if create_user:
            if not new_name.strip() or not new_email.strip() or len(new_password) < 8:
                st.error("Nom, identifiant et mot de passe d'au moins 8 caractères sont obligatoires.")
            elif new_password != new_password2:
                st.error("Les deux mots de passe ne correspondent pas.")
            else:
                try:
                    DB.table("cra_users").insert({"email":new_email.strip().lower(), "display_name":new_name.strip(),
                        "role":new_role, "password_hash":password_hash(new_password), "active":new_active,
                        "permissions":new_permissions}).execute()
                    st.success("Compte créé. L'utilisateur peut maintenant se connecter.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Création impossible : {exc}. Vérifiez que l'identifiant n'existe pas déjà.")
        try:
            users = DB.table("cra_users").select("id,email,display_name,role,active,created_at,permissions").order("created_at", desc=True).execute().data or []
            if users:
                view_users = [{"Nom":u.get("display_name"), "Identifiant":u.get("email"), "Profil":u.get("role"), "Actif":u.get("active"), "Nombre d'onglets":len(u.get("permissions") or [])} for u in users]
                st.dataframe(pd.DataFrame(view_users), use_container_width=True, hide_index=True)
                manageable_users = [x for x in users if x["role"] != "Administrateur des comptes"]
                if not manageable_users:
                    st.info("Créez d'abord un compte chercheur, stagiaire ou technicien pour définir ses autorisations.")
                else:
                    target = st.selectbox("Personne à gérer", [x["email"] for x in manageable_users])
                    target_user = next(x for x in manageable_users if x["email"] == target)
                    current_permissions = target_user.get("permissions") or []
                    if isinstance(current_permissions, str):
                        try: current_permissions = json.loads(current_permissions)
                        except Exception: current_permissions = []
                    with st.form("edit_user_permissions"):
                        st.markdown(f"**Droits de navigation de {target_user.get('display_name', target)}**")
                        # Les droits enregistrés sont également filtrés pour éviter
                        # toute valeur absente des options proposées par Streamlit.
                        current_permissions = current_permissions if isinstance(current_permissions, list) else []
                        revised_permissions = st.multiselect(
                            "Onglets visibles dans son espace",
                            options=USER_PAGES,
                            default=[x for x in current_permissions if x in USER_PAGES]
                        )
                        save_permissions = st.form_submit_button("Enregistrer les autorisations", type="primary")
                    if save_permissions:
                        DB.table("cra_users").update({"permissions":revised_permissions}).eq("email", target).execute()
                        st.success("Les autorisations ont été mises à jour.")
                        st.rerun()
                    if target_user.get("active"):
                        if st.button("Désactiver ce compte"):
                            DB.table("cra_users").update({"active":False}).eq("email", target).execute(); st.rerun()
                    else:
                        if st.button("Réactiver ce compte"):
                            DB.table("cra_users").update({"active":True}).eq("email", target).execute(); st.rerun()
        except Exception as exc:
            st.error(f"Gestion des comptes indisponible : {exc}")

# ---------------------------------------------------------------------
# PIED DE PAGE INSTITUTIONNEL — ISRA / CRA / YAM
# ---------------------------------------------------------------------
st.markdown(f"""
<style>
.cra-footer {{margin-top:42px;background:linear-gradient(125deg,#103F2D,#176B45);color:#fff;border-radius:20px;padding:30px 30px 22px;border-top:6px solid {GOLD};box-shadow:0 14px 32px #103f2d22;}}
.cra-footer h2,.cra-footer h3 {{color:#fff!important;}}
.cra-footer p,.cra-footer li {{color:#e9f4ed!important;line-height:1.65;}}
.cra-footer strong {{color:#fff;}}
.footer-brands {{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;border-bottom:1px solid #ffffff35;padding-bottom:18px;margin-bottom:20px;}}
.footer-brand {{flex:1;min-width:230px;background:#ffffff12;border:1px solid #ffffff30;border-radius:13px;padding:14px 17px;}}
.footer-brand .brand-name {{font-size:20px;font-weight:900;letter-spacing:.8px;}}
.footer-brand small {{color:#dceee2;display:block;margin-top:5px;}}
.footer-bottom {{border-top:1px solid #ffffff35;margin-top:22px;padding-top:14px;font-size:11px;color:#d9e9de;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;}}
</style>
<section class="cra-footer" id="cra-saint-louis">
  <div class="footer-brands">
    <div class="footer-brand"><div class="brand-name">ISRA · CRA SAINT-LOUIS</div><small>Institution scientifique de rattachement · Recherche agricole, expérimentation et innovation au service du développement rural.</small></div>
    <div class="footer-brand"><div class="brand-name">YAM GROUP</div><small>Groupe porteur de solutions et d'initiatives numériques · Valorisation, innovation et accompagnement.</small><div class="brand-name" style="font-size:16px;margin-top:10px">YAM NUMÉRIQUE</div><small>Filiale de YAM Group · Conception, développement et maintenance de la plateforme numérique ISRA / CRA.</small></div>
  </div>
  <h2>Le Centre de Recherches Agricoles (CRA) de Saint-Louis</h2>
  <p>Rattaché à l'Institut Sénégalais de Recherches Agricoles (ISRA), le CRA de Saint-Louis est le pôle majeur de recherche et d'innovation agronomique au cœur de la Vallée du fleuve Sénégal. Le centre œuvre au quotidien pour le développement rural, la sécurité alimentaire et l'adaptation du secteur agricole aux enjeux agro-écologiques régionaux.</p>
  <h3>Nos missions principales :</h3>
  <ul>
    <li><strong>Intensification de la riziculture :</strong> Amélioration de la productivité du riz, création de variétés tolérantes aux contraintes locales (salinité, climat) et optimisation de la gestion de l'eau.</li>
    <li><strong>Diversification des systèmes de production :</strong> Développement des cultures horticoles, de l'arboriculture et de cultures émergentes pour renforcer la résilience des exploitations agricoles.</li>
    <li><strong>Production de semences de qualité :</strong> Recherche, conservation et multiplication du capital semencier (riz, niébé, arachide, cultures maraîchères) sur nos stations expérimentales.</li>
    <li><strong>Gestion durable des ressources :</strong> Promotion des pratiques agro-écologiques, préservation des sols et valorisation des écosystèmes locaux.</li>
    <li><strong>Accompagnement et aide à la décision :</strong> Production de connaissances scientifiques et socio-économiques pour guider les décideurs, les organisations paysannes et les acteurs agro-industriels.</li>
  </ul>
  <div class="footer-bottom"><span><strong>ISRA — CRA Saint-Louis</strong> · Supervision scientifique : M. Keita</span><span><strong>YAM GROUP</strong> · <strong>YAM NUMÉRIQUE</strong>, filiale dédiée aux solutions numériques · <a style="color:#fff" href="mailto:issayoume1801@gmail.com">issayoume1801@gmail.com</a></span></div>
</section>
""", unsafe_allow_html=True)
