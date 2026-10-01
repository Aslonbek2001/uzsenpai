.PHONY: up down lint lint-backend lint-bot lint-frontend test test-backend test-bot test-frontend migrate api-types importlinter i18n-check i18n-bot i18n-bot-init

# compose.yaml lives in the repo root, so `docker compose …` works from any subfolder
LOCALES := uz ru en ja

# Every app is independent: its own lockfile, image and targets. `make lint-bot` never touches the backend.
# An app that isn't scaffolded yet is skipped, not failed.
define if_app
	@if [ -f $(1) ]; then $(2); else echo "$(dir $(1)): not scaffolded yet — skipped"; fi
endef

up:            ## postgres(pgvector), redis, backend, worker + scheduler (Taskiq), frontend, bot
	docker compose up -d --build

down:
	docker compose down

importlinter:  ## regenerate module-boundary contracts from existing modules
	python3 scripts/sync_importlinter.py

lint: i18n-check lint-backend lint-bot lint-frontend

lint-backend:
	python3 scripts/sync_importlinter.py --check
	$(call if_app,backend/pyproject.toml,cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run lint-imports)

lint-bot:
	$(call if_app,bot/pyproject.toml,cd bot && uv run ruff check . && uv run ruff format --check . && uv run mypy app)

lint-frontend:
	$(call if_app,frontend/package.json,cd frontend && pnpm lint && pnpm typecheck)

test: test-backend test-bot test-frontend

test-backend:  ## needs postgres + redis: docker compose up -d postgres redis
	$(call if_app,backend/pyproject.toml,cd backend && uv run pytest -q)

test-bot:
	$(call if_app,bot/pyproject.toml,cd bot && uv run pytest -q)

test-frontend:
	$(call if_app,frontend/package.json,cd frontend && pnpm test --run)

migrate:
	cd backend && uv run alembic upgrade head

# Requires the backend running on :8000
api-types:
	cd frontend && pnpm exec openapi-typescript http://localhost:8000/openapi.json -o src/shared/api/generated/schema.d.ts

# Every UI/bot string present in uz, ru, en, ja (bot .po files are parsed with Babel from the bot env)
i18n-check:
	@if [ -d bot/locales ]; then cd bot && uv run python ../scripts/i18n_check.py; else python3 scripts/i18n_check.py; fi

# First time only: create the four bot catalogs
i18n-bot-init:
	cd bot && uv run pybabel extract -k __ -o locales/messages.pot app && \
	for l in $(LOCALES); do uv run pybabel init -i locales/messages.pot -d locales -D messages -l $$l; done

# After changing bot texts: re-extract, update the four .po files, compile
i18n-bot:
	cd bot && uv run pybabel extract -k __ -o locales/messages.pot app && \
	uv run pybabel update -d locales -D messages -i locales/messages.pot && \
	uv run pybabel compile -d locales -D messages
