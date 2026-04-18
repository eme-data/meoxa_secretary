#!/usr/bin/env bash
# =============================================================================
# meoxa_secretary — installation automatisée sur Ubuntu 24.04
#
# Usage :
#   sudo bash infra/scripts/install.sh
#
# Variables optionnelles (exportables pour rendre l'install non-interactive) :
#   APP_DOMAIN           (défaut : secretary.meoxa.app)
#   LETSENCRYPT_EMAIL    (défaut : mathieu@mdoservices.fr)
#   ADMIN_EMAIL          (défaut : valeur saisie au prompt)
#   ADMIN_PASSWORD       (défaut : valeur saisie au prompt, masquée)
#   ADMIN_ORG_NAME       (défaut : MDO Services)
#   INSTALL_DIR          (défaut : /opt/meoxa_secretary)
#   REPO_URL             (défaut : détecté depuis le répertoire courant)
#   SKIP_SWAP            (défaut : 0, mettre 1 pour ne pas créer de swap)
#   SKIP_UFW             (défaut : 0, mettre 1 pour ne pas toucher au firewall)
#   SKIP_CERTBOT         (défaut : 0, mettre 1 pour skipper Let's Encrypt)
# =============================================================================

set -euo pipefail

# ------------------- Helpers -------------------

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;36m'
BOLD=$'\033[1m'
NC=$'\033[0m'

log()   { echo "${BLUE}[·]${NC} $*"; }
ok()    { echo "${GREEN}[✓]${NC} $*"; }
warn()  { echo "${YELLOW}[!]${NC} $*"; }
err()   { echo "${RED}[✗]${NC} $*" >&2; }
die()   { err "$*"; exit 1; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        die "Ce script doit être lancé en root (utilise 'sudo')."
    fi
}

prompt_default() {
    local label="$1" default="$2" varname="$3" secret="${4:-0}"
    local current="${!varname:-}"
    if [[ -n "$current" ]]; then return; fi
    if [[ "$secret" == "1" ]]; then
        read -rsp "$label [${default:-...}]: " val; echo
    else
        read -rp "$label [${default}]: " val
    fi
    printf -v "$varname" '%s' "${val:-$default}"
}

# ------------------- Phase 0 : pré-requis -------------------

phase_checks() {
    log "Vérifications système"
    require_root

    if ! grep -q "Ubuntu 24.04" /etc/os-release; then
        warn "Distribution non-Ubuntu 24.04 détectée — on continue mais non testé."
    fi

    ARCH=$(dpkg --print-architecture)
    log "Architecture : $ARCH"

    if [[ $(nproc) -lt 2 ]]; then
        warn "CPU < 2 cores — performances limitées à prévoir."
    fi

    TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    if [[ $TOTAL_MEM_KB -lt 3500000 ]]; then
        warn "RAM < 4 Go — le bot Teams (Whisper) risque de swapper."
    fi

    ok "OK — Ubuntu $(lsb_release -rs), $(nproc) cores, $((TOTAL_MEM_KB/1024)) Mo RAM"
}

# ------------------- Phase 1 : configuration interactive -------------------

phase_config() {
    log "Configuration"
    prompt_default "Domaine de l'app" "secretary.meoxa.app" APP_DOMAIN
    prompt_default "Email Let's Encrypt / admin" "mathieu@mdoservices.fr" LETSENCRYPT_EMAIL
    prompt_default "Nom de l'organisation (super-admin)" "MDO Services" ADMIN_ORG_NAME
    prompt_default "Email du premier super-admin" "$LETSENCRYPT_EMAIL" ADMIN_EMAIL
    if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
        while true; do
            read -rsp "Mot de passe super-admin (≥ 10 car.) : " ADMIN_PASSWORD; echo
            if [[ ${#ADMIN_PASSWORD} -ge 10 ]]; then break; fi
            warn "Trop court, réessaie."
        done
    fi
    prompt_default "Répertoire d'installation" "/opt/meoxa_secretary" INSTALL_DIR

    ok "APP_DOMAIN=$APP_DOMAIN"
    ok "INSTALL_DIR=$INSTALL_DIR"
}

# ------------------- Phase 2 : système (locale, timezone, swap, updates) -------------------

phase_system() {
    log "Configuration système de base"

    timedatectl set-timezone Europe/Paris || warn "timezone inchangée"

    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        ca-certificates curl gnupg lsb-release \
        git make openssl jq dnsutils \
        ufw unattended-upgrades

    # Mises à jour de sécurité auto
    cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

    # Swap (si pas déjà configuré et peu de RAM)
    if [[ "${SKIP_SWAP:-0}" != "1" ]]; then
        local swap_size_mb
        swap_size_mb=$(free -m | awk '/^Swap:/{print $2}')
        if [[ $swap_size_mb -lt 1024 ]]; then
            log "Création d'un swap de 2 Go"
            if [[ ! -f /swapfile ]]; then
                fallocate -l 2G /swapfile
                chmod 600 /swapfile
                mkswap /swapfile
                swapon /swapfile
                echo "/swapfile none swap sw 0 0" >> /etc/fstab
            fi
        fi
    fi

    ok "Système prêt"
}

# ------------------- Phase 3 : firewall UFW -------------------

phase_firewall() {
    if [[ "${SKIP_UFW:-0}" == "1" ]]; then
        warn "UFW ignoré (SKIP_UFW=1)"
        return
    fi
    log "Configuration du firewall UFW"
    ufw --force reset >/dev/null
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp    comment "SSH"
    ufw allow 80/tcp    comment "HTTP Let's Encrypt + redirect"
    ufw allow 443/tcp   comment "HTTPS"
    ufw --force enable >/dev/null
    ok "UFW actif : 22, 80, 443"
}

# ------------------- Phase 4 : Docker + rclone -------------------

phase_docker() {
    if command -v docker &>/dev/null && docker compose version &>/dev/null; then
        ok "Docker + compose déjà installés ($(docker --version | awk '{print $3}' | tr -d ','))"
        return
    fi
    log "Installation de Docker CE + plugin compose"

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    local codename
    codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
    cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$ARCH signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $codename stable
EOF

    DEBIAN_FRONTEND=noninteractive apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    systemctl enable --now docker
    ok "Docker installé"
}

phase_rclone_optional() {
    # Optionnel — si RCLONE_REMOTE est défini dans l'env, on installe rclone.
    if [[ -n "${RCLONE_REMOTE:-}" ]] && ! command -v rclone &>/dev/null; then
        log "Installation de rclone (pour backups off-site)"
        curl -fsSL https://rclone.org/install.sh | bash
        ok "rclone installé — lance 'rclone config' pour créer le remote '$RCLONE_REMOTE'"
    fi
}

# ------------------- Phase 5 : code source -------------------

phase_source() {
    log "Mise en place des sources"

    local script_dir repo_root
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    repo_root=$(cd "$script_dir/../.." && pwd)

    if [[ "$repo_root" != "$INSTALL_DIR" ]]; then
        if [[ ! -d "$INSTALL_DIR" ]]; then
            mkdir -p "$(dirname "$INSTALL_DIR")"
            log "Copie des sources dans $INSTALL_DIR"
            cp -a "$repo_root" "$INSTALL_DIR"
        else
            log "$INSTALL_DIR existe déjà — on y reste"
        fi
    fi

    cd "$INSTALL_DIR"
    ok "Sources dans $INSTALL_DIR"
}

# ------------------- Phase 6 : secrets + .env.prod -------------------

generate_fernet_key() {
    python3 - <<'PY'
import base64, os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
}

phase_env() {
    log "Génération de .env.prod"
    cd "$INSTALL_DIR"

    if [[ -f .env.prod ]]; then
        warn ".env.prod existe déjà — on le garde intact"
        return
    fi

    local jwt_secret postgres_password fernet_key
    jwt_secret=$(openssl rand -hex 32)
    postgres_password=$(openssl rand -hex 24)
    fernet_key=$(generate_fernet_key)

    cp .env.example .env.prod
    # Valeurs de production
    sed -i \
        -e "s|^ENVIRONMENT=.*|ENVIRONMENT=production|" \
        -e "s|^APP_DOMAIN=.*|APP_DOMAIN=$APP_DOMAIN|" \
        -e "s|^LOG_LEVEL=.*|LOG_LEVEL=INFO|" \
        -e "s|^BACKEND_URL=.*|BACKEND_URL=https://$APP_DOMAIN|" \
        -e "s|^FRONTEND_URL=.*|FRONTEND_URL=https://$APP_DOMAIN|" \
        -e "s|^NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://$APP_DOMAIN|" \
        -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://$APP_DOMAIN|" \
        -e "s|^JWT_SECRET=.*|JWT_SECRET=$jwt_secret|" \
        -e "s|^SETTINGS_ENCRYPTION_KEY=.*|SETTINGS_ENCRYPTION_KEY=$fernet_key|" \
        -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$postgres_password|" \
        -e "s|^POSTGRES_HOST=.*|POSTGRES_HOST=postgres|" \
        -e "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://meoxa:$postgres_password@postgres:5432/meoxa_secretary|" \
        -e "s|^MS_REDIRECT_URI=.*|MS_REDIRECT_URI=https://$APP_DOMAIN/api/v1/integrations/microsoft/callback|" \
        .env.prod

    chmod 600 .env.prod
    ok "Secrets générés et stockés dans .env.prod (chmod 600)"
}

# ------------------- Phase 7 : DNS check -------------------

phase_dns() {
    log "Vérification DNS"
    local server_ip dns_ip
    server_ip=$(curl -fsS4 https://api.ipify.org 2>/dev/null || echo "inconnu")
    dns_ip=$(dig +short "$APP_DOMAIN" A | tail -n1 || true)

    if [[ -z "$dns_ip" ]]; then
        warn "$APP_DOMAIN ne résout pas encore. Crée un enregistrement A → $server_ip avant Let's Encrypt."
        return 1
    fi
    if [[ "$dns_ip" != "$server_ip" ]]; then
        warn "$APP_DOMAIN résout vers $dns_ip, mais le serveur est $server_ip"
        return 1
    fi
    ok "DNS OK : $APP_DOMAIN → $server_ip"
    return 0
}

# ------------------- Phase 8 : nginx conf avec le bon domaine -------------------

phase_nginx_config() {
    log "Mise à jour de la conf Nginx"
    local nginx_conf="$INSTALL_DIR/infra/nginx/conf.d/meoxa.conf"
    if [[ ! -f "$nginx_conf" ]]; then
        die "Fichier $nginx_conf introuvable"
    fi
    # Si le domaine n'est pas celui par défaut, on remplace.
    if [[ "$APP_DOMAIN" != "secretary.meoxa.app" ]]; then
        sed -i "s|secretary\.meoxa\.app|$APP_DOMAIN|g" "$nginx_conf"
    fi
    ok "Nginx configuré pour $APP_DOMAIN"
}

# ------------------- Phase 9 : premier démarrage -------------------

# Wrapper paresseux : $INSTALL_DIR n'est connu qu'après phase_config().
compose() {
    docker compose \
        -f "$INSTALL_DIR/docker-compose.prod.yml" \
        --env-file "$INSTALL_DIR/.env.prod" \
        "$@"
}

phase_build_and_start() {
    log "Build des images Docker (peut prendre 5-10 min)"
    cd "$INSTALL_DIR"
    compose build

    log "Démarrage de Postgres + Redis"
    compose up -d postgres redis

    log "Attente de Postgres (healthcheck)"
    for _ in {1..60}; do
        if compose ps postgres --format json 2>/dev/null | grep -q '"Health":"healthy"'; then
            break
        fi
        sleep 2
    done

    log "Application des migrations Alembic"
    compose run --rm backend alembic upgrade head

    log "Démarrage de la stack complète (sans nginx)"
    compose up -d backend worker scheduler frontend
    ok "Services applicatifs lancés"
}

# ------------------- Phase 10 : Let's Encrypt + nginx -------------------

phase_certificate() {
    if [[ "${SKIP_CERTBOT:-0}" == "1" ]]; then
        warn "Certbot ignoré (SKIP_CERTBOT=1) — lance nginx en HTTP seul"
        return
    fi

    local cert_dir="$INSTALL_DIR/infra/certbot/conf/live/$APP_DOMAIN"
    if [[ -d "$cert_dir" ]]; then
        ok "Certificat déjà présent pour $APP_DOMAIN"
    else
        log "Obtention du certificat Let's Encrypt pour $APP_DOMAIN"
        # Le bloc 443 de Nginx référence le cert — on ne peut pas lancer nginx
        # avant d'avoir le cert. On utilise certbot en standalone pour le 1er challenge.
        compose run --rm -p 80:80 certbot certonly --standalone \
            -d "$APP_DOMAIN" \
            --email "$LETSENCRYPT_EMAIL" \
            --agree-tos --non-interactive --no-eff-email
    fi

    log "Démarrage de Nginx"
    compose up -d nginx certbot
    ok "Nginx + auto-renouvellement Let's Encrypt actifs"
}

# ------------------- Phase 11 : bootstrap super-admin -------------------

phase_bootstrap_admin() {
    log "Création du super-admin plateforme"
    cd "$INSTALL_DIR"
    compose exec -T \
        -e ADMIN_EMAIL="$ADMIN_EMAIL" \
        -e ADMIN_PASSWORD="$ADMIN_PASSWORD" \
        -e ADMIN_ORG_NAME="$ADMIN_ORG_NAME" \
        backend python -m meoxa_secretary.scripts.bootstrap_admin
}

# ------------------- Phase 12 : cron backup -------------------

phase_cron() {
    log "Installation du cron de backup (03:00 quotidien)"
    local backup_script="$INSTALL_DIR/infra/scripts/backup.sh"
    chmod +x "$backup_script"
    cat > /etc/cron.d/meoxa-backup <<EOF
# Backup quotidien meoxa_secretary — installé par install.sh
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 3 * * * root $backup_script >> /var/log/meoxa-backup.log 2>&1
EOF
    chmod 644 /etc/cron.d/meoxa-backup
    ok "Cron de backup installé"
}

# ------------------- Phase 13 : récap final -------------------

phase_summary() {
    local status_url="https://$APP_DOMAIN/api/v1/status"
    cat <<EOF

${BOLD}${GREEN}=== Installation terminée ===${NC}

  Application    : ${BOLD}https://$APP_DOMAIN${NC}
  API docs       : https://$APP_DOMAIN/docs (uniquement en dev, désactivé en prod)
  Health check   : $status_url

  Super-admin    : ${BOLD}$ADMIN_EMAIL${NC}
  Organisation   : $ADMIN_ORG_NAME

${BOLD}Prochaines étapes :${NC}
  1. Connecte-toi et active la 2FA sur /app/security
  2. Dans l'admin plateforme (/app/admin/platform), configure :
       • anthropic.api_key            (obligatoire pour LLM)
       • microsoft.client_id / secret (obligatoire pour OAuth MS)
       • stripe.api_key + price_id + webhook_secret  (facturation)
       • voyage.api_key               (optionnel — RAG)
  3. Sur portal.azure.com, ajoute la redirect URI :
       https://$APP_DOMAIN/api/v1/integrations/microsoft/callback
  4. Sur dashboard.stripe.com, crée un webhook endpoint vers :
       https://$APP_DOMAIN/api/v1/webhooks/stripe
     → copie le whsec_... dans stripe.webhook_secret

${BOLD}Commandes utiles (depuis $INSTALL_DIR) :${NC}
  make prod-up           # relancer la stack
  make prod-deploy       # git pull + build + migrate
  docker compose -f docker-compose.prod.yml logs -f backend
  docker compose -f docker-compose.prod.yml ps

EOF
}

# ------------------- Exécution -------------------

main() {
    phase_checks
    phase_config
    phase_system
    phase_firewall
    phase_docker
    phase_rclone_optional
    phase_source
    phase_env
    # DNS non-bloquant : on continue même s'il n'est pas OK (certbot le sera).
    phase_dns || warn "Configure ton DNS avant le certificat"
    phase_nginx_config
    phase_build_and_start
    phase_certificate
    phase_bootstrap_admin
    phase_cron
    phase_summary
}

main "$@"
