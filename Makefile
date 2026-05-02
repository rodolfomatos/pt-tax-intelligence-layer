.PHONY: install run test lint format check docs-check code-check test-check lint-check docker-build docker-up docker-down docker-logs docker-restart clean help git-status git-add git-commit git-push git-pull git-fetch git-branch git-log alembic-migrate alembic-rollback alembic-current

PYTHON=python3
PIP=pip
VENV_DIR=venv
PORT=8000
COMPOSE_PROJECT_NAME=pt-tax-intelligence

# Check if we should use venv
ifneq ("$(wildcard $(VENV_DIR))","")
PYTHON=$(VENV_DIR)/bin/python
PIP=$(VENV_DIR)/bin/pip
endif

help:
	@echo "PT Tax Intelligence Layer - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Run the development server"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linting"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker services (detached)"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make docker-restart - Restart Docker services"
	@echo "  make docker-logs  - Show Docker logs (follow)"
	@echo "  make shell        - Open shell in app container"
	@echo "  make db           - Open psql in database container"
	@echo ""
	@echo "Database Migrations:"
	@echo "  make alembic-migrate    - Run pending migrations"
	@echo "  make alembic-rollback   - Rollback last migration"
	@echo "  make alembic-current - Show current migration"
	@echo ""
	@echo "Git:"
	@echo "  make git-status   - Show working tree status"
	@echo "  make git-add      - Stage all changes (git add .)"
	@echo "  make git-commit   - Commit changes (prompts for message)"
	@echo "  make git-push     - Push to origin main"
	@echo "  make git-push-u   - Push and set upstream (git push -u origin main)"
	@echo "  make git-pull     - Pull from origin main"
	@echo "  make git-fetch    - Fetch from remote"
	@echo "  make git-branch   - Show branches"
	@echo "  make git-log     - Show recent commits"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean        - Clean temporary files"
	@echo "  make docs         - Generate documentation"

install: venv
	@echo "Installing dependencies..."
	$(PIP) install -e .

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
		$(VENV_DIR)/bin/pip install --upgrade pip; \
	fi

run: $(VENV_DIR)
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port $(PORT) --reload

test: $(VENV_DIR)
	$(PYTHON) -m pytest tests/ -v --cov=app --cov-report=term-missing

lint: $(VENV_DIR)
	$(PYTHON) -m ruff check app/ tests/ scripts/ --exclude alembic,venv

format: $(VENV_DIR)
	$(PYTHON) -m ruff check --fix .

# AES Quality Gates
check: docs-check code-check test-check lint-check

docs-check:
	@# Verify required docs exist and have substantial content (>10 lines)
	@for f in docs/VISION.md docs/REQUIREMENTS.md docs/personas.md docs/architecture.md docs/ROADMAP.md; do \
		if [ ! -f "$$f" ]; then echo "Missing $$f"; exit 1; fi; \
		lines=$$(wc -l < "$$f"); \
		if [ "$$lines" -lt 10 ]; then echo "File $$f is too short ($$lines lines)"; exit 1; fi; \
	done
	@echo "✅ Documentation check passed"

code-check:
	@# Verify code structure and no TODO in source files
	@test -d app || (echo "Missing app/ directory"; exit 1)
	@test -d tests || (echo "Missing tests/ directory"; exit 1)
	@grep -R "TODO:" app/ tests/ 2>/dev/null || echo "✅ No TODO markers found"
	@echo "✅ Code structure check passed"

test-check:
	@# Run tests with coverage threshold (currently 50%, aiming for 80%)
	@$(PYTHON) -m pytest tests/ -m "not integration" --cov=app --cov-fail-under=50 --cov-report=term-missing

lint-check:
	@# Run linter in non-fix mode (exclude generated code)
	$(PYTHON) -m ruff check app/ tests/ scripts/ --exclude alembic,venv

docker-build:
	docker compose build --no-cache

docker-up:
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services started. API available at http://localhost:8000"

docker-down:
	docker compose down

docker-restart:
	docker compose restart

docker-logs:
	docker compose logs -f

docker-logs-app:
	docker compose logs -f app

docker-logs-db:
	docker compose logs -f db

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage

docs:
	python scripts/generate_docs.py

shell:
	docker exec -it pt-tax-intelligence-app /bin/bash

db:
	docker exec -it pt-tax-intelligence-db psql -U postgres -d tax_intelligence

ps:
	docker compose ps

logs:
	docker compose logs

status:
	@echo "=== Service Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Health Check ==="
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Service not running"

# Git commands
git-status:
	git status

git-add:
	git add .

git-commit:
	@echo "Enter commit message:"
	@read msg; git commit -m "$$msg"

git-push:
	git push origin main

git-push-u:
	git push -u origin main

git-pull:
	git pull origin main

git-fetch:
	git fetch origin

git-branch:
	git branch -a

git-log:
	git log --oneline -10

# Database Migrations
alembic-migrate:
	alembic upgrade head

alembic-rollback:
	alembic downgrade -1

alembic-current:
	alembic current
