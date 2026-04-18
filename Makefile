.PHONY: help up down restart logs ps build rebuild \
        shell-backend shell-frontend shell-db \
        migrate migration downgrade seed \
        test lint format \
        prod-up prod-down prod-deploy

COMPOSE = docker compose
COMPOSE_PROD = docker compose -f docker-compose.prod.yml --env-file .env.prod

help: ## Affiche cette aide
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------- Dev ----------

up: ## Lance la stack complète en dev
	$(COMPOSE) up -d

down: ## Arrête la stack
	$(COMPOSE) down

restart: down up ## Redémarre la stack

logs: ## Suit les logs
	$(COMPOSE) logs -f --tail=200

ps: ## Liste les conteneurs
	$(COMPOSE) ps

build: ## Build les images
	$(COMPOSE) build

rebuild: ## Rebuild sans cache
	$(COMPOSE) build --no-cache

shell-backend: ## Shell dans le backend
	$(COMPOSE) exec backend bash

shell-frontend: ## Shell dans le frontend
	$(COMPOSE) exec frontend sh

shell-db: ## psql dans postgres
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-meoxa} -d $${POSTGRES_DB:-meoxa_secretary}

# ---------- Migrations ----------

migrate: ## Applique les migrations Alembic
	$(COMPOSE) exec backend alembic upgrade head

migration: ## Crée une migration: make migration m="ajout de la table X"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

downgrade: ## Rollback d'une migration
	$(COMPOSE) exec backend alembic downgrade -1

seed: ## Insère les données de démo
	$(COMPOSE) exec backend python -m meoxa_secretary.scripts.seed

superadmin: ## Promeut un user super-admin: make superadmin email=x@y.fr
	$(COMPOSE) exec backend python -m meoxa_secretary.scripts.promote_superadmin $(email)

# ---------- Qualité ----------

test: ## Lance pytest
	$(COMPOSE) exec backend pytest -q

lint: ## Ruff + mypy
	$(COMPOSE) exec backend ruff check meoxa_secretary
	$(COMPOSE) exec backend mypy meoxa_secretary

format: ## Ruff format
	$(COMPOSE) exec backend ruff format meoxa_secretary

# ---------- Production ----------

prod-up: ## Démarre la stack production
	$(COMPOSE_PROD) up -d

prod-down: ## Arrête la stack production
	$(COMPOSE_PROD) down

prod-deploy: ## Pull + rebuild + migrate (à lancer sur le VPS)
	git pull
	$(COMPOSE_PROD) build
	$(COMPOSE_PROD) up -d
	$(COMPOSE_PROD) exec backend alembic upgrade head
