# GlitchTip — error monitoring self-hosted

Alternative Sentry-compatible, sans abonnement. Consomme ~800 Mo RAM à l'idle
sur le VPS (à prévoir si < 4 Go).

## Installation (première fois)

```bash
cd /opt/meoxa_secretary/infra/glitchtip

cp .env.example .env
# Générer la secret key :
#   openssl rand -hex 50  → SECRET_KEY
# Choisir un GLITCHTIP_DB_PASSWORD
# Ajuster GLITCHTIP_DOMAIN

docker compose up -d

# Crée le super-admin GlitchTip (interactif)
docker compose exec web ./manage.py createsuperuser
```

GlitchTip écoute sur `127.0.0.1:8001` (loopback uniquement). Pour l'exposer
publiquement en HTTPS, voir la section suivante.

## Exposition via Nginx sur errors.meoxa.app

1. **DNS** : créer un A record `errors.meoxa.app` → IP du VPS
2. **Certificat Let's Encrypt** :
   ```bash
   cd /opt/meoxa_secretary
   docker compose -f docker-compose.prod.yml run --rm certbot certonly \
     --webroot -w /var/www/certbot -d errors.meoxa.app \
     --email mathieu@mdoservices.fr --agree-tos --non-interactive
   ```
3. **Conf Nginx** : déposer le fichier `nginx-glitchtip.conf` (fourni ici) dans
   `/opt/meoxa_secretary/infra/nginx/conf.d/glitchtip.conf`, puis :
   ```bash
   docker compose -f docker-compose.prod.yml restart nginx
   ```

## Configuration des projets

1. Login sur https://errors.meoxa.app
2. **Créer une Organization** (ex : MDO Services)
3. **Créer 2 Projects** :
   - `meoxa-backend` (platform: Python)
   - `meoxa-frontend` (platform: JavaScript/Next.js)
4. Récupérer les DSN (Settings → Client Keys) et les coller dans `.env.prod`
   de meoxa :
   ```
   SENTRY_DSN=https://...@errors.meoxa.app/1         # backend
   NEXT_PUBLIC_SENTRY_DSN=https://...@errors.meoxa.app/2  # frontend
   ```
5. Redémarrer meoxa : `docker compose -f docker-compose.prod.yml up -d backend worker frontend`

## Maintenance

- **Backups** : `gt_postgres_data` contient les événements. À inclure dans
  la stratégie de backup (le script `backup.sh` de meoxa ne les inclut pas).
- **Rétention** : par défaut GlitchTip conserve 90 jours (configurable par
  projet dans Settings → Data Retention).
- **Mises à jour** :
  ```bash
  cd /opt/meoxa_secretary/infra/glitchtip
  docker compose pull
  docker compose up -d --force-recreate
  docker compose run --rm migrate    # applique les nouvelles migrations
  ```

## Arrêter complètement

```bash
docker compose down           # stoppe sans perdre les données
docker compose down -v        # ⚠️ supprime aussi les volumes
```
