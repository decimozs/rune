.ONESHELL:
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

API_URL ?= http://localhost:8000
KEY    ?=
COMPOSE ?= docker compose
SERVICE ?= ocr

.PHONY: help install dev run test up up-ui down build rebuild restart logs ps app-logs \
        pull shell health test-routes test-formats test-auth benchmark stress convert clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36mtarget\033[0m\n"} \
	     /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)

install: ## Install Python deps via uv
	uv sync

dev: ## Start Gotenberg + dev server with hot reload
	docker rm -f exist-ocr-gotenberg 2>/dev/null || true
	docker run --rm -d -p 3000:3000 --name exist-ocr-gotenberg gotenberg/gotenberg:8
	@echo "Waiting for Gotenberg..."; \
	for i in $$(seq 1 10); do \
		curl -sf http://localhost:3000/health > /dev/null 2>&1 && echo "Gotenberg ready" && break; \
		sleep 1; \
	done
	uv run fastapi dev app/main.py --port 8000 || true
	docker stop exist-ocr-gotenberg 2>/dev/null || true

dev-stop: ## Stop Gotenberg container started by make dev
	docker stop exist-ocr-gotenberg 2>/dev/null || true

run: ## Start production server
	uv run fastapi run app/main.py --port 8000

up: ## Start all Docker services (headless)
	$(COMPOSE) up -d

up-ui: ## Start all Docker services with demo UI
	$(COMPOSE) -f docker-compose.yml -f docker-compose.ui.yml up -d

down: ## Stop all Docker services
	$(COMPOSE) down

build: ## Build or rebuild Docker image
	$(COMPOSE) build

rebuild: ## Full clean rebuild (down → build --no-cache → up)
	$(COMPOSE) down -v
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Follow logs from all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

status: ps ## Alias for ps

app-logs: ## Follow logs from API service only
	$(COMPOSE) logs -f $(SERVICE)

pull: ## Pull required images (gotenberg)
	$(COMPOSE) pull gotenberg

shell: ## Open bash in running API container
	$(COMPOSE) exec $(SERVICE) bash

health: ## Check liveness + readiness
	@echo "=== Liveness ==="
	@curl -sf $(API_URL)/health && echo " ok" || echo " FAIL"
	@echo "=== Readiness ==="
	@curl -sf $(API_URL)/health/ready && echo " ok" || echo " FAIL"

test: ## Run unit tests (pytest)
	uv run pytest tests/ -v

test-routes: ## Validate all API routes
	scripts/test_routes.sh $(API_URL)

test-formats: ## Test all supported file formats
	scripts/test_formats.sh $(API_URL)

test-auth: ## Test API key auth flow (KEY=sk_live_... for valid key test)
	scripts/test_auth.sh $(API_URL) $(KEY)

benchmark: ## Run OCR benchmark
	scripts/benchmark.sh $(API_URL)

stress: ## Run stress test
	scripts/stress.sh $(API_URL)

convert: ## Convert all datasets to PDF via Gotenberg
	scripts/convert.sh all $(API_URL)

clean: ## Remove all test outputs
	scripts/cleanup.sh --all
