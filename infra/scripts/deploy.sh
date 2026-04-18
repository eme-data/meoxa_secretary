#!/usr/bin/env bash
# Déploiement sur VPS Ubuntu 24.04 — à lancer depuis le répertoire du projet.
#
# Pré-requis :
#   - Docker + plugin compose installés (`apt install docker.io docker-compose-v2`)
#   - Fichier `.env.prod` présent à la racine
#   - DNS pointant vers le VPS
#
# Première installation :
#   1. Éditer infra/nginx/conf.d/meoxa.conf (remplacer APP_DOMAIN)
#   2. Lancer ce script une première fois (il obtiendra les certificats)

set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -f .env.prod ]]; then
    echo "Fichier .env.prod manquant — copier .env.example, l'éditer puis relancer."
    exit 1
fi

source .env.prod

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

echo "→ git pull"
git pull --ff-only

echo "→ Build des images"
$COMPOSE build

echo "→ Démarrage Postgres + Redis"
$COMPOSE up -d postgres redis

echo "→ Migrations Alembic"
$COMPOSE run --rm backend alembic upgrade head

echo "→ Démarrage de la stack"
$COMPOSE up -d

if [[ ! -d "infra/certbot/conf/live/${APP_DOMAIN}" ]]; then
    echo "→ Premier lancement : obtention du certificat Let's Encrypt pour ${APP_DOMAIN}"
    $COMPOSE run --rm certbot certonly --webroot -w /var/www/certbot \
        -d "${APP_DOMAIN}" --email "mathieu@mdoservices.fr" \
        --agree-tos --non-interactive
    $COMPOSE restart nginx
fi

echo "✓ Déploiement terminé — https://${APP_DOMAIN}"
