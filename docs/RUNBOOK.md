# Runbook ops — Secretary by Meoxa

Ce document est destiné à toi (ops solo). Il rassemble les gestes
d'exploitation courants pour éviter de les ré-inventer dans le stress.

Toutes les commandes supposent que tu es sur le VPS dans
`/opt/meoxa_secretary` sauf mention contraire.

---

## Commandes de base

```bash
# Raccourci alias (à mettre dans ton .bashrc)
alias dcp='docker compose -f docker-compose.prod.yml --env-file .env.prod'

# État de la stack
dcp ps

# Logs en direct
dcp logs -f backend
dcp logs -f worker
dcp logs -f nginx --tail=50

# Shell dans un service
dcp exec backend bash
dcp exec postgres psql -U meoxa -d meoxa_secretary
```

## Déployer une nouvelle version

```bash
git pull
dcp build backend frontend
dcp up -d backend worker scheduler frontend
dcp exec -T backend alembic upgrade head
curl -fsS https://secretary.meoxa.app/api/v1/status
```

## Relancer le backend après un freeze

```bash
dcp restart backend worker scheduler
# Ou si vraiment coincé :
dcp stop backend worker scheduler
dcp up -d backend worker scheduler
```

## Appliquer une migration manuellement

```bash
dcp exec -T backend alembic current    # vérifier l'état
dcp exec -T backend alembic upgrade head
dcp exec -T backend alembic downgrade -1   # rollback d'un cran (rare)
```

## Voir le coût LLM en cours

```bash
dcp exec postgres psql -U meoxa -d meoxa_secretary -c "
SELECT tenant_id,
       model,
       count(*) AS calls,
       sum(cost_micro_usd) / 1000000.0 AS cost_usd
FROM llm_usage_events
WHERE created_at >= date_trunc('month', now())
GROUP BY tenant_id, model
ORDER BY cost_usd DESC;
"
```

## Promouvoir un user en super-admin

```bash
dcp exec backend python -m meoxa_secretary.scripts.promote_superadmin contact@meoxa.app
```

## Créer un tenant/owner à la main (provisioning concierge)

```bash
dcp exec -T \
  -e ADMIN_EMAIL=client@exemple.fr \
  -e ADMIN_PASSWORD='MotDePasse123!' \
  -e ADMIN_ORG_NAME='Cabinet Exemple' \
  backend python -m meoxa_secretary.scripts.bootstrap_admin
```

## Backup manuel + vérification

```bash
/opt/meoxa_secretary/infra/scripts/backup.sh
ls -la /var/backups/meoxa
```

## Restaurer un backup (attention : destructif)

```bash
# 1. Arrêter les workers pour éviter les writes pendant la restore
dcp stop backend worker scheduler

# 2. Drop + recréer la DB
dcp exec postgres psql -U meoxa -d postgres -c "
DROP DATABASE meoxa_secretary;
CREATE DATABASE meoxa_secretary;
"

# 3. Restore
gunzip < /var/backups/meoxa/meoxa-YYYYMMDD-HHMMSS.sql.gz | \
  dcp exec -T postgres psql -U meoxa -d meoxa_secretary

# 4. Vérifier puis relancer
dcp exec -T backend alembic current
dcp up -d backend worker scheduler
```

## Rotation d'une clé secrète

### JWT_SECRET
1. Éditer `.env.prod` → nouvelle valeur (`openssl rand -hex 32`)
2. `dcp restart backend worker scheduler`
3. **Tous les users sont déconnectés** (les tokens signés avec l'ancien secret sont invalides)

### SETTINGS_ENCRYPTION_KEY
⚠️ **Ne jamais rotater sans script de migration** — tous les secrets chiffrés
en base (tokens OAuth MS, API keys, secrets TOTP) deviennent illisibles. Si
absolument nécessaire : écrire un script qui lit avec l'ancienne clé, chiffre
avec la nouvelle, puis met à jour `.env.prod` et redémarre.

### Clé Anthropic
Va dans `/app/admin/platform`, édite `anthropic.api_key`. Le cache (TTL 60s)
se met à jour automatiquement sans redémarrage.

## Le backend est en 502 via nginx

1. Vérifier que le backend répond en interne :
   ```bash
   dcp exec backend curl -fsS http://localhost:8000/health
   ```
2. Si OK → cache DNS nginx, redémarrer :
   ```bash
   dcp restart nginx
   ```
3. Sinon → logs backend :
   ```bash
   dcp logs --tail=100 backend
   ```

## Un client signale « je ne reçois plus de brouillons »

1. Vérifier l'intégration Microsoft :
   ```bash
   dcp exec postgres psql -U meoxa -d meoxa_secretary -c "
   SELECT ms_upn, expires_at, last_error, last_error_at
   FROM microsoft_integrations
   WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'nom-du-client');
   "
   ```
2. Si `last_error` rempli → le client doit se reconnecter à Microsoft.
3. Vérifier les souscriptions Graph :
   ```bash
   dcp exec postgres psql -U meoxa -d meoxa_secretary -c "
   SELECT resource_type, expires_at FROM graph_subscriptions
   WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'nom-du-client');
   "
   ```
4. Les subscriptions sont renouvelées toutes les 6 h par Celery beat. Si
   expires_at passé : forcer manuellement :
   ```bash
   dcp exec backend celery -A meoxa_secretary.workers.celery_app call \
     meoxa_secretary.workers.tasks.graph_notifications.renew_subscriptions
   ```

## Anthropic coûte trop cher ce mois

1. Voir quel tenant consomme :
   ```bash
   dcp exec postgres psql -U meoxa -d meoxa_secretary -c "
   SELECT t.slug, sum(u.cost_micro_usd)/1000000.0 AS usd
   FROM llm_usage_events u JOIN tenants t ON t.id = u.tenant_id
   WHERE u.created_at >= date_trunc('month', now())
   GROUP BY t.slug ORDER BY usd DESC LIMIT 10;
   "
   ```
2. Envisager de passer le tenant en modèle `default` si en `advanced` :
   via `/app/admin/settings` ou directement en DB.

## Suspendre un tenant (non-paiement, abus)

```bash
dcp exec postgres psql -U meoxa -d meoxa_secretary -c "
UPDATE tenants SET is_active = false WHERE slug = 'nom-du-client';
"
```

Les routes métier renverront 402 (abonnement requis) puisque `require_active_subscription`
bypass n'est actif que pour super-admin.

## Staging

```bash
# Bascule sur branche staging, lance stack isolée sur ports 8100/8101
git fetch origin
git checkout staging
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d
curl -fsS http://localhost:8100/health
```

Les volumes sont préfixés `staging_` donc pas de risque d'écraser la prod.

## Vérifier que GlitchTip reçoit bien

```bash
# Force une erreur côté backend
dcp exec backend python -c "
import sentry_sdk
from meoxa_secretary.core.observability import init_sentry
init_sentry()
try: raise RuntimeError('test-glitchtip-ingest')
except Exception as e: sentry_sdk.capture_exception(e)
"
```

L'erreur doit apparaître dans https://errors.meoxa.app sous 1 minute.

## Contacts d'urgence

- **Email support** : contact@meoxa.app
- **DPO** : dpo@meoxa.app
- **Sécurité (disclosure)** : security@meoxa.app
- **Hébergement** : [nom du provider, numéro de ticket]
- **Stripe** : https://dashboard.stripe.com (compte configuré avec 2FA)
- **Azure AD app** : https://portal.azure.com (tenant Meoxa)
