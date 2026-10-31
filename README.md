# Migration ISRA – CRA Saint-Louis vers Supabase PostgreSQL

## Contenu livré
- `app.py` : application Streamlit migrée du stockage SQLite vers Supabase PostgreSQL.
- `schema.sql` : tables, index, RLS, permissions minimales, journal d'audit et triggers PostgreSQL.
- `import_sqlite.py` : import ponctuel de l'ancienne base locale `cra_isra_local.db`.
- `requirements.txt` : dépendances Python.
- `.env.example` et `.streamlit/secrets.toml.example` : modèles sans secret réel.
- `GUIDE_MIGRATION.docx` : procédure courte de déploiement.

## Configuration
Le projet Supabase référencé dans les paramètres transmis est `mlmbvjzkesnwportvmax`, région `eu-west-3`. L'application utilise l'API Supabase depuis le serveur Streamlit, pas la connexion PostgreSQL directe. La clé `anon` fournie n'est pas une clé serveur et ne permet pas cette architecture. Il faut créer/récupérer la clé `service_role` (secret) dans les paramètres API du projet et la placer uniquement dans les secrets du serveur Streamlit.

Ne placez jamais la clé `service_role`, le mot de passe PostgreSQL ou un fichier `.env` dans Git, le navigateur, le code source ou le ZIP public.

## Installation rapide
1. Dans Supabase > SQL Editor, exécuter `schema.sql`.
2. Dans les secrets de l'hébergement Streamlit, configurer `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CRA_ADMIN_EMAIL` et `CRA_ADMIN_PASSWORD`.
3. Installer `pip install -r requirements.txt`.
4. Lancer `streamlit run app.py`.
5. Au premier login avec le couple admin configuré, l'application crée le compte administrateur et son hash PBKDF2.

## Migration des anciennes données
Si vous possédez l'ancien fichier SQLite `cra_isra_local.db`, sauvegardez-le puis lancez :

```bash
python import_sqlite.py /chemin/vers/cra_isra_local.db
```

L'import est à exécuter une seule fois. Vérifiez les volumes et quelques fiches dans Supabase avant de supprimer l'ancienne base.

## Sécurité et limites à connaître
- Le backend Streamlit détient la clé `service_role` : elle contourne RLS. Elle doit rester exclusivement côté serveur. Les contrôles d'accès aux enregistrements sont appliqués dans le backend Streamlit ; ne réutilisez pas cette clé dans une application front-end.
- `schema.sql` active RLS et révoque les droits directs `anon`/`authenticated`. Le rôle `service_role` a les droits requis.
- Les changements sur comptes et enregistrements sont consignés dans `cra_audit_log`; des triggers SQL assurent aussi une trace au niveau base. Le journal est append-only (UPDATE/DELETE refusés).
- Les mots de passe applicatifs sont stockés sous forme de hash PBKDF2-SHA256 avec sel, jamais en clair.
- L'authentification applicative est personnalisée et distincte de Supabase Auth. Pour une exposition publique à grande échelle, la prochaine étape recommandée est de basculer les utilisateurs vers Supabase Auth et de faire porter les politiques RLS par `auth.uid()`.
- Le partage collaboratif est conservé par les règles de l'application. Faites des tests avec deux comptes distincts avant mise en production.
- Activez MFA pour les comptes administrateurs Supabase, sauvegardes/PITR selon le plan, et surveillance des journaux.

## Identifiants transmis dans la conversation
Le mot de passe PostgreSQL communiqué a été exposé dans le chat. Considérez-le comme compromis : changez-le immédiatement dans Supabase Database Settings, puis mettez à jour le gestionnaire de secrets. Il n'est volontairement pas recopié dans ce ZIP. La clé `anon` est publique par conception mais ne doit pas être confondue avec `service_role`.
