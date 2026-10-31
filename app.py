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
    'cra_trial_observations','cra_trials'
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
def _bootstrap_supabase_schema_once(db_url: str):
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
    _bootstrap_supabase_schema_once(SUPABASE_DB_URL)
    _SUPABASE: Client = _get_supabase_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except Exception as exc:
    st.error(f"Initialisation Supabase impossible : {exc}")
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
                for cell in ws[row_idx]:
                    cell.font = Font(name="Aptos", size=9, color="18352A")
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
                    if row_idx % 2 == 0:
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
    return output.getvalue()


def pdf_bytes(title: str, frame: pd.DataFrame) -> bytes:
    """Rapport PDF institutionnel avec identité ISRA/CRA et signature YAM Group."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        from reportlab.lib.units import mm
        from xml.sax.saxutils import escape
        out = BytesIO()
        doc = SimpleDocTemplate(out, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm,
                                topMargin=25*mm, bottomMargin=20*mm, title=str(title),
                                author="ISRA — CRA Saint-Louis | YAM Group — YAM Numérique")
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("YAMReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=19, leading=23, alignment=TA_CENTER, textColor=colors.HexColor("#16483F"), spaceAfter=5)
        subtitle = ParagraphStyle("YAMSubtitle", parent=styles["Normal"], fontSize=9, leading=12,
            alignment=TA_CENTER, textColor=colors.HexColor("#6B9B8D"), spaceAfter=10)
        cell = ParagraphStyle("YAMCell", parent=styles["BodyText"], fontSize=7.5, leading=9)
        head = ParagraphStyle("YAMHead", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
        story = [Paragraph("INSTITUT SÉNÉGALAIS DE RECHERCHES AGRICOLES", subtitle),
                 Paragraph("ISRA · CENTRE DE RECHERCHES AGRICOLES DE SAINT-LOUIS", subtitle),
                 Paragraph(escape(str(title)), title_style),
                 Paragraph("DOCUMENT SCIENTIFIQUE · COLLECTE, EXPÉRIMENTATION ET TRAÇABILITÉ", subtitle),
                 Spacer(1, 5*mm)]
        if frame is None or frame.empty:
            data = [[Paragraph("Information", head)], [Paragraph("Aucune donnée enregistrée", cell)]]
        else:
            data = [[Paragraph(escape(str(c)), head) for c in frame.columns]]
            for row in frame.fillna("").astype(str).itertuples(index=False, name=None):
                data.append([Paragraph(escape(str(v)[:1200]).replace("\n", "<br/>"), cell) for v in row])
        available = doc.width
        widths = [available/max(1, len(data[0]))] * max(1, len(data[0]))
        table = Table(data, repeatRows=1, colWidths=widths, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,0), colors.HexColor("#247A66")),
            ("TEXTCOLOR", (0,0),(-1,0), colors.white),
            ("GRID", (0,0),(-1,-1), .45, colors.HexColor("#8BB9AA")),
            ("VALIGN", (0,0),(-1,-1), "TOP"), ("FONTSIZE", (0,0),(-1,-1), 7),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.white, colors.HexColor("#F1F6F2")]),
            ("LEFTPADDING", (0,0),(-1,-1), 5), ("RIGHTPADDING", (0,0),(-1,-1), 5),
            ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ]))
        story.append(table)
        def decorate(canvas, document):
            canvas.saveState()
            w, h = landscape(A4)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.rect(0, h-13*mm, w, 13*mm, fill=1, stroke=0)
            canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(12*mm, h-8.5*mm, "ISRA  |  CRA SAINT-LOUIS")
            canvas.setFont("Helvetica", 8); canvas.drawRightString(w-12*mm, h-8.5*mm, "RECHERCHE AGRICOLE & INNOVATION")
            canvas.setStrokeColor(colors.HexColor("#DDB64C")); canvas.setLineWidth(2); canvas.line(12*mm, 15*mm, w-12*mm, 15*mm)
            canvas.setFillColor(colors.HexColor("#16483F")); canvas.setFont("Helvetica-Bold", 8)
            canvas.drawString(12*mm, 9*mm, "YAM GROUP · YAM NUMÉRIQUE")
            canvas.setFont("Helvetica", 7); canvas.drawRightString(w-12*mm, 9*mm, f"Document scientifique · Page {document.page}")
            canvas.restoreState()
        doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
        return out.getvalue()
    except Exception as exc:
        st.error(f"Génération PDF impossible : {exc}. Vérifiez la dépendance reportlab.")
        return b""


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
        forms = DB.table("cra_forms").select("*").eq("id", form_id).limit(1).execute().data or []
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
    questions = form.get("questions") or []
    if not isinstance(questions, list) or not questions:
        st.error("Ce questionnaire existe, mais aucune question exploitable n'est enregistrée. Modifiez-le ou recréez-le.")
        st.stop()

    st.markdown(f"### {form.get('title') or 'Questionnaire ISRA / CRA'}")
    if form.get("description"):
        st.write(form["description"])
    st.caption("Les champs marqués * sont obligatoires.")
    st.markdown(f"**Contact :** [{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL})")

    answers_by_id: dict[str, Any] = {}
    answers_by_label: dict[str, Any] = {}
    question_labels: dict[str, str] = {}
    with st.form(f"public_form_{form_id}", clear_on_submit=False):
        respondent = st.text_input("Nom / structure du répondant *", key=f"respondent_{form_id}")
        contact = st.text_input("Téléphone ou adresse e-mail (facultatif)", key=f"contact_{form_id}")
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
        if not respondent.strip():
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
                "respondent": respondent.strip(),
                "contact": contact.strip(),
                # answers conserve le format historique pour les exports existants.
                "answers": answers_by_label,
                # answers_by_id évite les collisions si deux questions ont le même libellé.
                "answers_by_id": answers_by_id,
                "question_labels": question_labels,
                "submitted_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "owner_email": form.get("owner_email", ""),
            }
            if db_insert("cra_responses", payload):
                st.success("Votre réponse a bien été enregistrée. Merci pour votre participation.")
                st.balloons()
                st.info("Vous pouvez fermer cette page. Votre réponse est transmise au questionnaire correspondant.")
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

# Bandeau du compte connecté et déconnexion
u1, u2, u3 = st.columns([3,2,1])
u1.caption(f"Connecté : {st.session_state.get('cra_user_name')} · {st.session_state.get('cra_user_email')}")
u2.caption(f"Profil : {st.session_state.get('cra_user_role', 'Utilisateur')}")
if u3.button("Déconnexion"):
    for key in ["cra_authenticated", "cra_user_email", "cra_user_name", "cra_user_role", "cra_user_permissions"]:
        st.session_state.pop(key, None)
    st.rerun()



# ---------------------------------------------------------------------
# NAVIGATION ET ÉTAT LOCAL
# ---------------------------------------------------------------------
PAGES = [
    "Tableau de bord", "Fiche technique", "Fiche de mesure",
    "Référentiel des cultures", "Essais expérimentaux XXL",
    "Diagnostic phytosanitaire XXL", "Créer un questionnaire",
    "Questionnaires et réponses", "Données et exports",
    "Dossiers de culture", "Collaboration", "Gestion des comptes",
]
# Les droits sont configurés individuellement par l'administrateur.
if st.session_state.get("cra_user_role") == "Administrateur des comptes":
    allowed_pages = PAGES[:]
else:
    saved_permissions = st.session_state.get("cra_user_permissions", [])
    allowed_pages = PAGES[:] if "*" in saved_permissions else [x for x in PAGES if x in saved_permissions]
    # Un compte ancien sans droits définis reçoit un espace limité de saisie.
    if not allowed_pages:
        allowed_pages = ["Tableau de bord", "Fiche technique", "Fiche de mesure"]
page = st.radio("ESPACE DE TRAVAIL — RUBRIQUES AUTORISÉES", allowed_pages,
                horizontal=True, label_visibility="collapsed")
if DB_MESSAGE:
    st.success(DB_MESSAGE)

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

# ---------------------------------------------------------------------
# FICHE TECHNIQUE
# ---------------------------------------------------------------------
elif page == "Fiche technique":
    heading("Recherche agronomique · ISRA / CRA", "FICHE TECHNIQUE D'ESSAI AGRONOMIQUE",
            "Identification, protocole expérimental, calendrier cultural, observations périodiques et validation scientifique.")
    st.markdown('<div class="card"><b>Classement et traçabilité :</b> créez d’abord un dossier dans « Dossiers de culture », puis rattachez chaque fiche technique à ce dossier. Vous pourrez retrouver et exporter toutes les versions à tout moment.</div>', unsafe_allow_html=True)
    tech_folders = db_rows("cra_culture_folders", 2000)
    tf_options = {"Sans dossier (enregistrement personnel)": ""}
    for folder in tech_folders:
        label = f"{folder.get('culture','Culture')} · {folder.get('folder_name','Dossier')} · {folder.get('folder_code','')}"
        tf_options[label] = folder.get("id", "")
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
                    st.session_state["technical_folder_preselect"]=next((k for k,v in {f"{x.get('culture','')} · {x.get('folder_name','')} · {x.get('folder_code','')}":x.get('id') for x in db_rows('cra_culture_folders',3000)}.items() if v==qid), "")
                    st.success("Dossier créé. Relancez la sélection pour le choisir."); st.rerun()
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
        g1,g2 = st.columns(2)
        with g1:
            obs_nrows = st.number_input("Nombre de lignes d'observation", min_value=1, max_value=300, value=20, key="tech_obs_nrows")
        with g2:
            obs_columns_text = st.text_input("Colonnes (séparées par des virgules)", "Date, Bloc, Modalité, Parcelle, Stade, Hauteur (cm), Note sanitaire, Croissance, Observateur")
        obs_cols = [x.strip() for x in obs_columns_text.split(",") if x.strip()] or ["Date", "Observation"]
        obs_frame = pd.DataFrame([{col: "" for col in obs_cols} for _ in range(int(obs_nrows))])
        obs_grid = st.data_editor(obs_frame, key="technical_observations_grid", num_rows="fixed", use_container_width=True, hide_index=True, height=min(600, 38*(int(obs_nrows)+1)))

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
        "observations": observations, "signature_numerique": signature, "lien_reference": lien_reference.strip(),
        "folder_id": dossier_id, "folder_name": dossier_nom,
    }
    tech_frame = pd.DataFrame([{"N°": i+1, **row} for i,row in enumerate(tech_payload["observations_periodiques"])])
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
    tech_excel = technical_excel_one_sheet(tech_payload, tech_frame)
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
        headers = list(observations_frame.columns)
        table_data = [[Paragraph("<b>"+escape(str(h))+"</b>", cell_style) for h in headers]]
        for vals in observations_frame.fillna("").astype(str).itertuples(index=False, name=None):
            table_data.append([Paragraph(escape(str(v)), cell_style) for v in vals])
        if len(table_data) == 1:
            table_data.append([Paragraph("Aucune observation saisie", cell_style)] + [""] * max(0,len(headers)-1))
        obs_table = Table(table_data, colWidths=[doc.width/max(1,len(headers))]*len(headers), repeatRows=1)
        obs_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#BFE9DE")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#8BB9AA")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),6)]))
        story += [obs_table, Spacer(1,5*mm), Paragraph("3. OBSERVATIONS QUALITATIVES", styles["Heading3"]),
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
    ex1.download_button("📊 Excel de la fiche technique", tech_excel, f"FICHE_TECHNIQUE_{slugify(tech_payload['code'])}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    ex2.download_button("📄 PDF officiel", tech_pdf, f"FICHE_TECHNIQUE_{slugify(tech_payload['code'])}.pdf", "application/pdf", use_container_width=True)
    ex3.download_button("📑 CSV observations", tech_csv, f"OBSERVATIONS_{slugify(tech_payload['code'])}.csv", "text/csv", use_container_width=True)
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
            headers.append(st.text_input(f"En-tête {i+1}", value=default_header, key=f"m_header_{i}"))
            type_map[headers[-1] or f"Colonne {i+1}"] = st.selectbox(f"Type {i+1}", type_options,
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

        st.download_button("⬇️ Excel (.xlsx) — fiche complète sur une seule feuille",
            measurement_excel_one_sheet(metadata, edited_grid),
            f"FICHE_MESURES_{slugify(essai or 'ISRA_CRA')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    csv_frame=edited_grid.copy()
    csv_header = "# FICHE DE MESURES — ISRA / Saint-Louis\n" + "\n".join(
        f"# {k}: {v}" for k, v in metadata.items() if k not in ("grid", "headers", "types")) + "\n\n"
    csv_data=(csv_header + csv_frame.to_csv(index=False)).encode("utf-8-sig")
    st.download_button("⬇️ Télécharger la grille CSV", csv_data,
        f"FICHE_MESURES_{slugify(essai or 'ISRA_CRA')}.csv", "text/csv", use_container_width=True)

    def measurement_pdf(meta, frame, blank=False):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
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
        cols=list(frame.columns)
        data=[[Paragraph(f"<b>{escape(str(c))}</b>",small) for c in cols]]
        if blank:
            for _ in range(int(meta.get("nrows",20))): data.append([""]*len(cols))
        else:
            for row in frame.fillna("").astype(str).itertuples(index=False,name=None): data.append([Paragraph(escape(str(v)),small) for v in row])
        widths=[doc.width/max(1,len(cols))]*len(cols)
        gt=Table(data,colWidths=widths,repeatRows=1,rowHeights=8*mm if blank else None)
        gt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.45,colors.HexColor("#6B9B8D")),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#BFE9DE")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#16483F")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3)]))
        story += [gt,Spacer(1,4*mm),Paragraph("OBSERVATIONS",styles["Heading3"]),Paragraph(escape("" if blank else str(meta.get("observations",""))).replace("\n","<br/>") or "<br/><br/><br/>",small)]
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
        final_payload["fiche_code"]=f"FM-{uuid.uuid4().hex[:10].upper()}"
        final_payload["folder_id"]=measure_folder_id
        final_payload["folder_name"]=measure_folder_name
        if db_insert("cra_measurement_sheets",final_payload):
            st.success("Fiche de mesures enregistrée dans votre espace personnel ISRA / CRA Saint-Louis.")
    if blank_pdf:
        blank_meta=dict(metadata); blank_meta["observations"]=""
        st.download_button("📥 Télécharger le modèle PDF vierge",measurement_pdf(blank_meta,edited_grid.iloc[0:0],True),
            "ISRA_CRA_FICHE_MESURES_VIERGE.pdf","application/pdf")
    if filled_pdf:
        st.download_button("📥 Télécharger la fiche PDF remplie",measurement_pdf(metadata,edited_grid,False),
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
        st.download_button("📊 Exporter toutes mes fiches de mesures en Excel",excel_bytes({"Fiches":pd.DataFrame(rows)}),
            "MES_FICHES_MESURES_ISRA_CRA.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Aucune fiche de mesures finale enregistrée pour le moment.")

# ---------------------------------------------------------------------
# DOSSIERS DE CULTURE — ARCHIVAGE ET TRACABILITE
# ---------------------------------------------------------------------
elif page == "Dossiers de culture":
    heading("Archivage scientifique · ISRA / CRA", "DOSSIERS DE CULTURE",
            "Un dossier par culture, campagne ou essai : regroupez les fiches techniques et toutes les campagnes de mesures, puis retrouvez-les et téléchargez-les à tout moment.")
    with st.expander("＋ Ouvrir un nouveau dossier de culture", expanded=True):
        with st.form("create_culture_folder", clear_on_submit=True):
            a,b,c = st.columns(3)
            with a:
                folder_name = st.text_input("Nom du dossier", placeholder="Ex. Riz — Essai variétal 2026")
                folder_culture = choose_culture("Culture", "folder_create_culture")
            with b:
                folder_campaign = st.text_input("Campagne / année", str(date.today().year))
                folder_station = st.text_input("Station / site")
            with c:
                folder_responsible = st.text_input("Responsable du dossier")
                folder_description = st.text_area("Objet et description", height=75)
            create_folder = st.form_submit_button("📁 Créer et ouvrir le dossier", type="primary", use_container_width=True)
        if create_folder:
            if not folder_name.strip() or not folder_culture.strip():
                st.error("Le nom du dossier et la culture sont obligatoires.")
            else:
                folder_id = str(uuid.uuid4())
                folder_payload = {"id":folder_id,"folder_code":f"DC-{uuid.uuid4().hex[:8].upper()}",
                    "folder_name":folder_name.strip(),"culture":folder_culture,"campaign":folder_campaign,
                    "station":folder_station,"responsible":folder_responsible,"description":folder_description,
                    "created_at":datetime.now().isoformat(timespec="seconds")}
                if db_insert("cra_culture_folders", folder_payload):
                    st.session_state["selected_cra_folder"] = folder_id
                    st.success("Dossier créé. Vous pouvez maintenant y déposer vos fiches techniques et fiches de mesures.")
                    st.rerun()

    folders = db_rows("cra_culture_folders", 3000)
    if not folders:
        st.info("Aucun dossier de culture. Créez votre premier dossier ci-dessus.")
    else:
        folder_lookup = {f.get("id"): f for f in folders}
        folder_ids = list(folder_lookup)
        default_folder = st.session_state.get("selected_cra_folder")
        default_idx = folder_ids.index(default_folder) if default_folder in folder_ids else 0
        selected_folder_id = st.selectbox("📂 Ouvrir un dossier", folder_ids, index=default_idx,
            format_func=lambda fid: f"{folder_lookup[fid].get('culture','')} — {folder_lookup[fid].get('folder_name','')} ({folder_lookup[fid].get('folder_code','')})")
        st.session_state["selected_cra_folder"] = selected_folder_id
        folder = folder_lookup[selected_folder_id]
        st.markdown(f"<div class='card'><h3>📁 {folder.get('folder_name','Dossier')}</h3><b>Culture :</b> {folder.get('culture','')} &nbsp; · &nbsp; <b>Campagne :</b> {folder.get('campaign','')}<br><b>Station :</b> {folder.get('station','')} &nbsp; · &nbsp; <b>Responsable :</b> {folder.get('responsible','')}<br>{folder.get('description','')}<hr><b>Code dossier :</b> {folder.get('folder_code','')}</div>", unsafe_allow_html=True)
        all_tech = db_rows("cra_technical_sheets", 5000)
        all_measures = db_rows("cra_measurement_sheets", 5000)
        folder_tech = [r for r in all_tech if r.get("folder_id") == selected_folder_id]
        folder_measures = [r for r in all_measures if r.get("folder_id") == selected_folder_id]
        m1,m2,m3 = st.columns(3)
        m1.metric("Fiches techniques", len(folder_tech))
        m2.metric("Fiches de mesures", len(folder_measures))
        m3.metric("Total des documents", len(folder_tech)+len(folder_measures))
        if folder_tech:
            st.markdown("#### Fiches techniques déposées")
            st.dataframe(pd.DataFrame([{"Code":r.get("code"),"Année":r.get("annee"),"Station":r.get("station"),"Responsables":r.get("responsables"),"Date":r.get("date_collecte")} for r in folder_tech]), use_container_width=True, hide_index=True)
        if folder_measures:
            st.markdown("#### Fiches de mesures déposées")
            st.dataframe(pd.DataFrame([{"Code":r.get("fiche_code"),"Essai":r.get("essai"),"Année":r.get("annee"),"Date de mesure":r.get("date_mesure"),"Paramètres":r.get("parametres")} for r in folder_measures]), use_container_width=True, hide_index=True)
        if not folder_tech and not folder_measures:
            st.info("Ce dossier est ouvert mais ne contient pas encore de fiche. Dans les modules Fiche technique et Fiche de mesure, sélectionnez ce dossier avant l'enregistrement.")

        # Permet de classer dans un dossier les anciennes fiches déjà enregistrées.
        unfiled_tech = [r for r in all_tech if not r.get("folder_id")]
        unfiled_measures = [r for r in all_measures if not r.get("folder_id")]
        if unfiled_tech or unfiled_measures:
            with st.expander("↪ Classer des fiches déjà enregistrées dans ce dossier"):
                tech_choices = {f"Fiche technique · {r.get('culture','')} · {r.get('code','')} · {r.get('date_collecte','')}": ("cra_technical_sheets", r.get("id")) for r in unfiled_tech}
                measure_choices = {f"Fiche de mesures · {r.get('culture','')} · {r.get('essai','')} · {r.get('fiche_code','')}": ("cra_measurement_sheets", r.get("id")) for r in unfiled_measures}
                all_choices = {**tech_choices, **measure_choices}
                selected_to_file = st.multiselect("Sélectionner les fiches à déposer", list(all_choices), key=f"file_existing_{selected_folder_id}")
                if st.button("📂 Déposer les fiches sélectionnées", key=f"attach_existing_{selected_folder_id}", type="primary"):
                    moved = 0
                    for label in selected_to_file:
                        table_name, record_id = all_choices[label]
                        if record_id and db_update(table_name, record_id, {"folder_id": selected_folder_id, "folder_name": f"{folder.get('culture','')} · {folder.get('folder_name','')}"}):
                            moved += 1
                    st.success(f"{moved} fiche(s) classée(s) dans le dossier.")
                    st.rerun()

        # Classeur consolidé : toutes les fiches du dossier, leurs métadonnées et observations.
        tech_meta_rows=[]; tech_obs_rows=[]; measure_meta_rows=[]; measure_grid_rows=[]
        for r in folder_tech:
            tech_meta_rows.append({k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in r.items() if k not in ("observations_periodiques",)})
            for idx, obs in enumerate(r.get("observations_periodiques") or [], start=1):
                tech_obs_rows.append({"Code fiche":r.get("code"),"Culture":r.get("culture"),"N° observation":idx,**obs})
        for r in folder_measures:
            measure_meta_rows.append({k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in r.items() if k not in ("grid",)})
            grid = r.get("grid") or []
            if isinstance(grid,str):
                try: grid=json.loads(grid)
                except Exception: grid=[]
            for idx, obs in enumerate(grid, start=1):
                if isinstance(obs,dict): measure_grid_rows.append({"Code fiche":r.get("fiche_code"),"Culture":r.get("culture"),"Essai":r.get("essai"),"N° ligne":idx,**obs})
        folder_excel = excel_bytes({
            "Dossier":pd.DataFrame([{"Code dossier":folder.get("folder_code"),"Dossier":folder.get("folder_name"),"Culture":folder.get("culture"),"Campagne":folder.get("campaign"),"Station":folder.get("station"),"Responsable":folder.get("responsible"),"Description":folder.get("description")}]),
            "Fiches_techniques":pd.DataFrame(tech_meta_rows),
            "Observations_tech":pd.DataFrame(tech_obs_rows),
            "Fiches_mesures":pd.DataFrame(measure_meta_rows),
            "Grilles_mesures":pd.DataFrame(measure_grid_rows),
        })
        st.markdown("#### Téléchargements du dossier")
        d1,d2,d3 = st.columns(3)
        d1.download_button("📊 TOUT télécharger en Excel", folder_excel,
            f"DOSSIER_{slugify(folder.get('folder_name','culture'))}_ISRA.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        combined_rows = ([{"Type":"Fiche technique", "Code":r.get("code"), "Culture":r.get("culture"), "Date":r.get("date_collecte"), "Résumé":r.get("objectif","")} for r in folder_tech] +
                         [{"Type":"Fiche de mesures", "Code":r.get("fiche_code"), "Culture":r.get("culture"), "Date":r.get("date_mesure"), "Résumé":r.get("parametres","")} for r in folder_measures])
        d2.download_button("📄 Rapport PDF du dossier", pdf_bytes("DOSSIER DE CULTURE — " + str(folder.get("folder_name","")), pd.DataFrame(combined_rows or [{"Information":"Aucune fiche déposée"}])),
            f"RAPPORT_{slugify(folder.get('folder_name','culture'))}.pdf", "application/pdf", use_container_width=True)
        # Archive CSV : métadonnées et matrices au format exploitable par R/Python.
        csv_zip_io = BytesIO()
        with zipfile.ZipFile(csv_zip_io, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("fiches_techniques.csv", pd.DataFrame(tech_meta_rows).to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("observations_techniques.csv", pd.DataFrame(tech_obs_rows).to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("fiches_mesures.csv", pd.DataFrame(measure_meta_rows).to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("grilles_mesures.csv", pd.DataFrame(measure_grid_rows).to_csv(index=False).encode("utf-8-sig"))
        d3.download_button("📦 CSV complets (ZIP)", csv_zip_io.getvalue(),
            f"CSV_{slugify(folder.get('folder_name','culture'))}.zip", "application/zip", use_container_width=True)

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
                            old_obs=target.get("observations_periodiques") or []
                            if isinstance(old_obs,str):
                                try: old_obs=json.loads(old_obs)
                                except Exception: old_obs=[]
                            obs_editor=st.data_editor(pd.DataFrame(old_obs),key=f"cg_{share.get('id')}",num_rows="dynamic",use_container_width=True,hide_index=True)
                            e_signature=st.text_input("Signature / visa",target.get("signature_numerique", ""),key=f"cs_{share.get('id')}")
                            save_shared=st.form_submit_button("💾 Enregistrer et poursuivre le travail",type="primary",use_container_width=True)
                        if save_shared:
                            changes={"objectif":e_objectif,"hypothese":e_hypothese,"apports_interventions":e_apports,"observations":e_observations,"observations_periodiques":obs_editor.fillna("").to_dict(orient="records"),"signature_numerique":e_signature,"last_collaborative_edit_by":st.session_state.get("cra_user_email"),"last_collaborative_edit_at":datetime.now().isoformat(timespec="seconds")}
                            if db_update(target_table,target_id,changes): st.success("Fiche technique mise à jour pour tous les collaborateurs."); st.rerun()
                    elif target_table == "cra_measurement_sheets":
                        with st.form(f"collab_measure_form_{share.get('id')}"):
                            e_params=st.text_input("Paramètres mesurés",target.get("parametres", ""),key=f"mp_{share.get('id')}")
                            e_other=st.text_area("Autre(s)",target.get("autres", ""),key=f"mo_{share.get('id')}")
                            e_obs=st.text_area("Observations",target.get("observations", ""),key=f"mv_{share.get('id')}")
                            old_grid=target.get("grid") or []
                            if isinstance(old_grid,str):
                                try: old_grid=json.loads(old_grid)
                                except Exception: old_grid=[]
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
        st.download_button("Exporter le référentiel des cultures en Excel", excel_bytes({"Cultures": crop_df}),
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
                st.success("Protocole expérimental enregistré.")
                st.json(trial_payload)
    st.markdown("---")
    st.markdown("#### C. Registre des essais et suivi des observations")
    trials = db_rows("cra_trials", 2000)
    if trials:
        trials_df = pd.DataFrame(trials)
        st.download_button("Exporter tous mes essais en Excel", excel_bytes({"Essais": trials_df}),
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
            st.download_button("📊 Télécharger Excel (.xlsx)", excel_bytes({"Observations": obs_df}),
                f"Observations_{slugify(str(chosen_trial.get('code')))}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.download_button("📄 Télécharger PDF", pdf_bytes("Observations de l'essai", obs_df),
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
            st.json(diag)
    st.markdown("---")
    st.markdown("#### Registre sanitaire et alertes")
    diagnostics = db_rows("cra_phytosanitary_diagnostics", 5000)
    if diagnostics:
        diag_df = pd.DataFrame(diagnostics)
        if "alert_level" in diag_df:
            urgent_df = diag_df[diag_df["alert_level"].isin(["Urgent", "Intervention à planifier"])]
            st.metric("Diagnostics nécessitant une attention", len(urgent_df))
        st.dataframe(diag_df, use_container_width=True, hide_index=True)
        st.download_button("📊 Télécharger le registre Excel (.xlsx)", excel_bytes({"Diagnostics": diag_df}),
            "CRA_registre_phytosanitaire.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("📄 Télécharger le registre PDF", pdf_bytes("Registre phytosanitaire", diag_df),
            "CRA_registre_phytosanitaire.pdf", "application/pdf")
    else:
        st.info("Aucun diagnostic phytosanitaire enregistré.")

# ---------------------------------------------------------------------
# CRÉATION DE QUESTIONNAIRE DYNAMIQUE
# ---------------------------------------------------------------------
elif page == "Créer un questionnaire":
    heading("Concepteur de formulaires", "Créer et partager un questionnaire",
            "Définissez vous-même les questions, leur type, les choix possibles et les champs obligatoires.")
    st.caption(f"Contact officiel des questionnaires : {CONTACT_EMAIL}")
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
                       "questions": qlist, "active": active}
            if db_insert("cra_forms", payload):
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
            st.code(link)
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
                st.download_button(
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
        st.code(f"?form={fid}", language="text")

# ---------------------------------------------------------------------
# LISTE FORMULAIRES ET RÉPONSES
# ---------------------------------------------------------------------
elif page == "Questionnaires et réponses":
    heading("Administration des enquêtes", "Questionnaires et réponses reçues",
            "Consultez les formulaires créés, activez ou désactivez les liens et exportez les réponses.")
    forms = db_rows("cra_forms")
    responses = db_rows("cra_responses")
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
                st.json(form.get("questions") or [])
                if public_base and fid:
                    public_link = f"{public_base}/?form={fid}"
                    st.code(public_link)
                    st.link_button("Ouvrir le questionnaire public", public_link, use_container_width=True)
                    try:
                        import qrcode
                        qr_obj = qrcode.QRCode(box_size=8, border=4)
                        qr_obj.add_data(public_link)
                        qr_obj.make(fit=True)
                        qr_img = qr_obj.make_image(fill_color="black", back_color="white")
                        qr_io = BytesIO(); qr_img.save(qr_io, format="PNG")
                        qr_data = qr_io.getvalue()
                        st.image(qr_data, width=210, caption="QR code du lien public")
                        st.download_button("Télécharger le QR code", qr_data,
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
                            st.rerun()
                    else:
                        if st.button("Réactiver le lien", key=f"activate_{fid}"):
                            db_update("cra_forms", fid, {"active": True})
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
        st.download_button("Télécharger les réponses (.xlsx)",
            excel_bytes({"Réponses": df}), "CRA_reponses_questionnaires.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Télécharger les réponses (.csv)", as_csv(display),
            "CRA_reponses_questionnaires.csv", "text/csv")
        st.download_button("Télécharger les réponses (.pdf)", pdf_bytes("Réponses aux questionnaires", df),
            "CRA_reponses_questionnaires.pdf", "application/pdf")
    else:
        st.info("Aucune réponse ne correspond à ce filtre.")

# ---------------------------------------------------------------------
# DONNÉES ET EXPORTS
# ---------------------------------------------------------------------
elif page == "Données et exports":
    heading("Archivage scientifique", "Données et exports",
            "Consultez et téléchargez les fiches techniques, les mesures et les réponses aux enquêtes.")
    tech = db_rows("cra_technical_sheets")
    measures = db_rows("cra_measurement_sheets")
    responses = db_rows("cra_responses")
    cultures = db_rows("cra_cultures")
    trials = db_rows("cra_trials")
    trial_obs = db_rows("cra_trial_observations")
    diagnostics = db_rows("cra_phytosanitary_diagnostics")
    st.markdown("### 📦 Export intégral de votre espace personnel")
    all_sheets = {
        "Fiches techniques": pd.DataFrame(tech), "Fiches de mesure": pd.DataFrame(measures),
        "Questionnaires": pd.DataFrame(db_rows("cra_forms")), "Réponses": pd.DataFrame(responses),
        "Cultures": pd.DataFrame(cultures), "Essais": pd.DataFrame(trials),
        "Observations essais": pd.DataFrame(trial_obs), "Diagnostics": pd.DataFrame(diagnostics),
    }
    st.download_button("📊 TÉLÉCHARGER TOUTES MES DONNÉES EN EXCEL (.xlsx)",
        excel_bytes(all_sheets), "ISRA_CRA_MON_ESPACE_COMPLET.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
    st.download_button("📄 Télécharger le rapport global en PDF", pdf_bytes("Synthèse de mon espace personnel", pd.DataFrame([
        {"Module": name, "Nombre d'enregistrements": len(frame)} for name, frame in all_sheets.items()
    ])), "ISRA_CRA_synthese_personnelle.pdf", "application/pdf", use_container_width=True)
    tabs = st.tabs(["Fiches techniques", "Fiches de mesure", "Réponses aux questionnaires"])
    with tabs[0]:
        st.dataframe(pd.DataFrame(tech), use_container_width=True, hide_index=True)
        if tech:
            st.download_button("Exporter les fiches techniques (.xlsx)",
                excel_bytes({"Fiches techniques": pd.DataFrame(tech)}),
                "CRA_fiches_techniques.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.download_button("Télécharger aussi en PDF", pdf_bytes("Fiches techniques", pd.DataFrame(tech)),
                "CRA_fiches_techniques.pdf", "application/pdf")
    with tabs[1]:
        st.dataframe(pd.DataFrame(measures), use_container_width=True, hide_index=True)
        if measures:
            st.download_button("Exporter les fiches de mesure (.xlsx)",
                excel_bytes({"Fiches de mesure": pd.DataFrame(measures)}),
                "CRA_fiches_mesure.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.download_button("Télécharger aussi en PDF", pdf_bytes("Fiches de mesure", pd.DataFrame(measures)),
                "CRA_fiches_mesure.pdf", "application/pdf")
    with tabs[2]:
        response_rows = []
        for r in responses:
            row = {"Questionnaire": r.get("form_title"), "Répondant": r.get("respondent"),
                   "Contact": r.get("contact"), "Date": r.get("submitted_at")}
            answer_values = r.get("answers") or {}
            if not answer_values and r.get("answers_by_id"):
                labels = r.get("question_labels") or {}
                answer_values = {labels.get(k, k): v for k, v in r.get("answers_by_id", {}).items()}
            row.update(answer_values)
            response_rows.append(row)
        st.dataframe(pd.DataFrame(response_rows), use_container_width=True, hide_index=True)
        if response_rows:
            st.download_button("Exporter les réponses (.xlsx)",
                excel_bytes({"Réponses": pd.DataFrame(response_rows)}),
                "CRA_reponses.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.download_button("Télécharger aussi en PDF", pdf_bytes("Réponses aux questionnaires", pd.DataFrame(response_rows)),
                "CRA_reponses.pdf", "application/pdf")

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
                "Chercheur": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Référentiel des cultures", "Essais expérimentaux XXL", "Diagnostic phytosanitaire XXL", "Créer un questionnaire", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
                "Stagiaire": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Diagnostic phytosanitaire XXL", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
                "Technicien": ["Tableau de bord", "Fiche technique", "Fiche de mesure", "Référentiel des cultures", "Diagnostic phytosanitaire XXL", "Questionnaires et réponses", "Données et exports", "Dossiers de culture", "Collaboration"],
            }
            new_permissions = st.multiselect("Onglets autorisés pour cette personne", PAGES[:-2], default=role_defaults[new_role], help="Seuls les onglets sélectionnés apparaîtront dans sa barre de navigation. Les comptes et paramètres restent réservés à l'administration.")
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
                        revised_permissions = st.multiselect("Onglets visibles dans son espace", PAGES[:-2], default=[x for x in current_permissions if x in PAGES[:-2]])
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
