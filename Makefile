.ONESHELL:
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

API_URL ?= http://localhost:8000
COMPOSE ?= docker compose
SERVICE ?= ocr

.PHONY: help install dev run up down build rebuild restart logs ps app-logs \
        pull shell health test-routes test-formats benchmark stress convert clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36mtarget\033[0m\n"} \
	     /^[a-zA-Z_-]+:.*?##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)

install: ## Install Python deps via uv
	uv sync

dev: ## Start dev server with hot reload
	uv run fastapi dev app/main.py --port 8000

run: ## Start production server
	uv run fastapi run app/main.py --port 8000

up: ## Start all Docker services
	$(COMPOSE) up -d

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

test-routes: ## Validate all API routes
	scripts/test_routes.sh $(API_URL)

test-formats: ## Test all supported file formats
	scripts/test_formats.sh $(API_URL)

benchmark: ## Run OCR benchmark
	scripts/benchmark.sh $(API_URL)

stress: ## Run stress test
	scripts/stress.sh $(API_URL)

convert: ## Convert all datasets to PDF via Gotenberg
	scripts/convert.sh all $(API_URL)

clean: ## Remove all test outputs
	scripts/cleanup.sh --all
