#!/usr/bin/env bash
# Backup PostgreSQL quotidien — à ajouter dans cron sur le VPS :
#   0 3 * * * /opt/meoxa_secretary/infra/scripts/backup.sh >> /var/log/meoxa-backup.log 2>&1
#
# Optionnel — copie off-site via rclone :
#   1. Installer rclone sur le VPS : `apt install rclone`
#   2. Configurer un remote : `rclone config` (ex: Backblaze B2, S3, Scaleway)
#   3. Ajouter dans .env.prod : RCLONE_REMOTE="meoxa-backup:bucket/path"
#
# Sans RCLONE_REMOTE, seuls les backups locaux sont conservés.

set -euo pipefail

cd "$(dirname "$0")/../.."
source .env.prod

BACKUP_DIR="${BACKUP_DIR:-/var/backups/meoxa}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="${BACKUP_DIR}/meoxa-${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "→ Dump Postgres"
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
    | gzip > "${ARCHIVE}"

echo "→ Rotation des backups locaux > ${RETENTION_DAYS} jours"
find "${BACKUP_DIR}" -name "meoxa-*.sql.gz" -mtime +${RETENTION_DAYS} -delete

if [[ -n "${RCLONE_REMOTE:-}" ]]; then
    echo "→ Push off-site vers ${RCLONE_REMOTE}"
    rclone copy "${ARCHIVE}" "${RCLONE_REMOTE}" --log-level INFO
    # Rotation off-site (même rétention)
    rclone delete "${RCLONE_REMOTE}" --min-age "${RETENTION_DAYS}d" --include "meoxa-*.sql.gz" \
        --log-level INFO || true
else
    echo "→ RCLONE_REMOTE non défini — pas de copie off-site"
fi

echo "✓ Backup: ${ARCHIVE}"
