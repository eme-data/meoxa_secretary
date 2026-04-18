# meoxa_secretary

Application SaaS multi-tenant qui implémente le **Pack Secrétariat** de MDO Services (1490 € HT) :
automatisation des emails, comptes-rendus de réunions par bot Teams, et gestion d'agenda,
le tout intégré à Microsoft 365.

## Stack

| Couche      | Techno                                              |
| ----------- | --------------------------------------------------- |
| Backend     | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic      |
| Workers     | Celery · Redis                                      |
| Base        | PostgreSQL 16 (Row-Level Security par `tenant_id`)  |
| Frontend    | Next.js 15 · Tailwind · shadcn/ui                   |
| Auth        | JWT self-hosted (access + refresh)                  |
| Intégration | Microsoft Graph (Outlook, Calendar, Teams)          |
| LLM         | API Claude (Anthropic)                              |
| Transcription | Bot Teams + `faster-whisper`                      |
| Déploiement | Docker Compose · Nginx · Let's Encrypt · Ubuntu 24.04 |

## Structure

```
meoxa_secretary/
├── backend/          # API FastAPI + workers Celery
├── frontend/         # Application Next.js
├── infra/
│   ├── nginx/        # Reverse proxy
│   └── scripts/      # Déploiement, backups
├── docker-compose.yml         # Dev local
├── docker-compose.prod.yml    # VPS
└── Makefile
```

## Démarrage rapide (dev)

```bash
cp .env.example .env
# Éditer .env pour renseigner les clés d'infrastructure (non-modifiables via l'UI) :
#   JWT_SECRET                  -> openssl rand -hex 32
#   SETTINGS_ENCRYPTION_KEY     -> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#   POSTGRES_PASSWORD           -> libre
# Les clés applicatives (Anthropic, Microsoft 365, Bot Teams, S3…) se configurent
# ensuite depuis /app/admin/platform (super-admin).

make up              # démarre postgres + redis + backend + worker + frontend
make migrate         # applique les migrations Alembic
make seed            # crée un tenant + un super-admin de démo (demo@meoxa.local)

# Promouvoir un autre user en super-admin :
make superadmin email=mathieu@mdoservices.fr
```

- API : http://localhost:8000/docs
- Frontend : http://localhost:3000

## Commandes utiles

```bash
make up              # docker compose up -d
make down            # docker compose down
make logs            # docker compose logs -f
make shell-backend   # shell dans le conteneur backend
make migrate         # alembic upgrade head
make migration m=... # alembic revision --autogenerate -m "..."
make test            # pytest côté backend
make lint            # ruff + mypy
```

## Déploiement (VPS Ubuntu 24.04)

### Première installation — script automatisé

Sur un VPS Ubuntu 24.04 fraîchement provisionné :

```bash
# 1. Faire pointer le DNS : secretary.meoxa.app → IP du VPS
# 2. SSH sur le VPS puis :
git clone https://github.com/meoxa/meoxa_secretary.git /tmp/meoxa
cd /tmp/meoxa
sudo bash infra/scripts/install.sh
```

Le script gère :
- Timezone, swap 2 Go si RAM < 4 Go, auto-updates de sécurité
- Firewall UFW (22, 80, 443)
- Installation Docker CE + plugin compose
- Copie des sources dans `/opt/meoxa_secretary`
- Génération de `.env.prod` avec secrets aléatoires (`JWT_SECRET`, `SETTINGS_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`)
- Build des images, migrations Alembic (incluant l'extension `vector`)
- Obtention du certificat Let's Encrypt + Nginx HTTPS
- Création du premier super-admin plateforme (prompt interactif ou `ADMIN_EMAIL`/`ADMIN_PASSWORD` en env)
- Cron de backup quotidien 03:00 UTC

Variables d'env acceptées pour automatiser : `APP_DOMAIN`, `LETSENCRYPT_EMAIL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_ORG_NAME`, `INSTALL_DIR`, `SKIP_SWAP`, `SKIP_UFW`, `SKIP_CERTBOT`, `RCLONE_REMOTE`.

### Mises à jour (day-2)

Depuis `/opt/meoxa_secretary` sur le VPS :

```bash
./infra/scripts/deploy.sh        # git pull + build + migrate
```

## Sécurité & multi-tenance

- Chaque requête authentifiée porte un JWT contenant `tenant_id`.
- Toutes les tables métier ont une colonne `tenant_id` et une policy PostgreSQL RLS.
- La session DB applique `SET app.tenant_id` via une dépendance FastAPI.
- Aucune requête cross-tenant n'est possible côté applicatif.

## Configuration : 3 niveaux

| Niveau | Où | Édité par |
| --- | --- | --- |
| **Bootstrap** (infra) | `.env` — `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `SETTINGS_ENCRYPTION_KEY` | ops / SSH |
| **Platform settings** | Table `platform_settings` + `/app/admin/platform` | super-admin (toi) |
| **Tenant settings** | Table `tenant_settings` + `/app/admin/settings` | OWNER/ADMIN du tenant |

Les secrets (API keys, client secrets) sont chiffrés au repos via Fernet (clé : `SETTINGS_ENCRYPTION_KEY`) et jamais renvoyés en clair par l'API — seulement masqués (`sk-••••abcd`).

## CI / CD — GitHub Actions

4 workflows dans [`.github/workflows/`](.github/workflows/) :

| Workflow | Trigger | Rôle |
| --- | --- | --- |
| `backend.yml` | push/PR touchant `backend/**` | Ruff + format check + pytest (postgres+redis services) + alembic + build image |
| `frontend.yml` | push/PR touchant `frontend/**` | ESLint + tsc + `next build` + build image |
| `deploy.yml` | push sur `main` | SSH vers le VPS → `./infra/scripts/deploy.sh` → smoke test `/api/v1/status` |
| `security.yml` | cron lundi 06:00 UTC | `pip-audit` + `npm audit` → issue auto si CVE |

Plus [`.github/dependabot.yml`](.github/dependabot.yml) : PRs auto hebdo (pip, npm, docker, github-actions), groupées par minor/patch pour limiter le bruit.

### Secrets GitHub requis

Dans le repo → **Settings → Secrets and variables → Actions**, ajouter :

| Secret | Valeur | Utilisé par |
| --- | --- | --- |
| `VPS_HOST` | IP ou DNS du VPS (ex: `secretary.meoxa.app`) | `deploy.yml` |
| `VPS_USER` | utilisateur SSH (ex: `root` ou `meoxa`) | `deploy.yml` |
| `VPS_SSH_KEY` | clé privée SSH (format OpenSSH, contenu complet du fichier) | `deploy.yml` |
| `VPS_PORT` | (optionnel) port SSH si ≠ 22 | `deploy.yml` |

Côté VPS, la clé publique correspondante doit être dans `~/.ssh/authorized_keys` de l'utilisateur cible.

### Branche protégée (recommandé)

Pour exiger la CI verte avant merge sur `main` :
- **Settings → Branches → Add branch protection rule** → `main`
- Cocher **Require status checks to pass** et sélectionner les jobs `backend / lint`, `backend / test`, `frontend / lint-and-build`.

### Budget minutes (compte gratuit, repo privé)

2 000 min/mois. Avec concurrency cancel + path filters + cache, un push typique consomme 3-5 min. Suffit pour ~400 pushes/mois. Si besoin d'illimité : self-hosted runner sur le VPS (voir section "Self-hosted runner" dans la doc GitHub).

## Licence

Propriétaire — MDO Services © 2026.
