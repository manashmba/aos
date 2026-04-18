.PHONY: help up down logs ps backend-test backend-dev frontend-dev bot-dev migrate build

help:
	@echo "AOS dev targets"
	@echo "  make up           - start full stack (postgres, redis, backend, frontend, bot, grafana)"
	@echo "  make down         - stop stack"
	@echo "  make logs         - tail logs from the backend"
	@echo "  make ps           - list services"
	@echo "  make migrate      - run alembic migrations inside the backend container"
	@echo "  make backend-test - run backend pytest"
	@echo "  make backend-dev  - run backend locally (uvicorn)"
	@echo "  make frontend-dev - run frontend locally (vite)"
	@echo "  make bot-dev      - run whatsapp bot locally"
	@echo "  make build        - docker compose build"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f aos-backend

ps:
	docker compose ps

build:
	docker compose build

migrate:
	docker compose exec aos-backend alembic upgrade head

backend-test:
	cd aos-backend && pytest -q

backend-dev:
	cd aos-backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd aos-frontend && npm run dev

bot-dev:
	cd whatsapp-bot && npm run dev
