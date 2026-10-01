.PHONY: up down lint test test-backend test-bot test-frontend migrate api-types importlinter i18n-check i18n-bot i18n-bot-init

# compose.yaml lives in the repo root, so `docker compose …` works from any subfolder
LOCALES := uz ru en ja

up:            ## postgres(pgvector), redis, backend, worker (Taskiq), frontend, bot
	docker compose up -d

down:
	docker compose down

importlinter:  ## regenerate module-boundary contracts from existing modules
	python3 scripts/sync_importlinter.py

lint: i18n-check
	python3 scripts/sync_importlinter.py --check
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run lint-imports
	cd bot && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd frontend && pnpm lint && pnpm typecheck

test: test-backend test-bot test-frontend

test-backend:
	cd backend && uv run pytest -q

test-bot:
	cd bot && uv run pytest -q

test-frontend:
	cd frontend && pnpm test --run

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
