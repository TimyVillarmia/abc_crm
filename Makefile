SHELL := /bin/sh

-include .env

COMPOSE ?= docker compose
MODULE ?= abc_crm
DEV_DB ?= abc_crm_dev
TEST_DB ?= abc_crm_test
TEST_TAG ?= /$(MODULE)
DB_USER ?= admin
DB_NAME ?= postgres
VENV ?= .venv
PYTHON ?= python3
PYLINTHOME ?= .cache/pylint

.DEFAULT_GOAL := help

.PHONY: help env setup hooks up down restart status logs install upgrade shell lint pylint check format test reset

help: ## Show available local-development commands.
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make <target> [VARIABLE=value]\n\nTargets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\nVariables: MODULE=%s DEV_DB=%s TEST_DB=%s TEST_TAG=%s\n" "$(MODULE)" "$(DEV_DB)" "$(TEST_DB)" "$(TEST_TAG)"

env: ## Create .env from .env.example without overwriting local settings.
	@if [ -e .env ]; then \
		echo ".env already exists; leaving it unchanged."; \
	else \
		cp .env.example .env; \
		echo "Created .env from .env.example."; \
	fi

setup: ## Create the tooling virtual environment and install developer tools.
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install --requirement requirements-dev.txt

hooks: setup ## Install the repository pre-commit hook.
	$(VENV)/bin/pre-commit install --install-hooks
	@test -x .git/hooks/pre-commit

up: ## Start the local Odoo and PostgreSQL stack.
	$(COMPOSE) up -d

down: ## Stop the local stack while preserving its data.
	$(COMPOSE) down

restart: ## Restart the local stack.
	$(COMPOSE) restart

status: ## Show local stack service status.
	$(COMPOSE) ps

logs: ## Follow Odoo web-service logs.
	$(COMPOSE) logs -f web

install: ## Install the addon into DEV_DB (default: abc_crm_dev).
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm web odoo -d $(DEV_DB) --init $(MODULE) --stop-after-init

upgrade: ## Upgrade the addon in DEV_DB after addon changes.
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm web odoo -d $(DEV_DB) --update $(MODULE) --stop-after-init

shell: ## Open an Odoo shell connected to DEV_DB.
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm web odoo shell -d $(DEV_DB)

lint: ## Run the configured pre-commit checks across the repository.
	$(VENV)/bin/pre-commit run --all-files

pylint: ## Run the manual pylint-odoo check.
	@mkdir -p $(PYLINTHOME)
	PYLINTHOME=$(PYLINTHOME) $(VENV)/bin/pylint . --load-plugins=pylint_odoo --disable=all --enable=odoolint

check: lint pylint ## Run all local quality checks.

format: ## Apply Ruff lint fixes and formatting.
	$(VENV)/bin/ruff check . --fix
	$(VENV)/bin/ruff format .

test: ## Recreate TEST_DB and run Odoo tests selected by TEST_TAG.
	$(COMPOSE) up -d --wait db
	$(COMPOSE) exec -T db dropdb -U $(DB_USER) --maintenance-db=$(DB_NAME) --if-exists $(TEST_DB)
	$(COMPOSE) run --rm web odoo -d $(TEST_DB) --init $(MODULE) --test-enable --test-tags=$(TEST_TAG) --stop-after-init --log-level=test

reset: ## Remove all local Compose data (requires CONFIRM=1).
	@if [ "$(CONFIRM)" != "1" ]; then \
		echo "Refusing to remove local data. Run: make reset CONFIRM=1"; \
		exit 1; \
	fi
	$(COMPOSE) down -v
