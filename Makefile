.DEFAULT_GOAL := help
SHELL := /bin/bash

# ─── Colors ──────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

##@ Help
.PHONY: help
help: ## Hiển thị tất cả các lệnh
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(CYAN)Usage:$(RESET)\n  make $(YELLOW)<target>$(RESET)\n"} \
	/^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2 } \
	/^##@/ { printf "\n$(CYAN)%s$(RESET)\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Docker
.PHONY: up down restart logs ps build

up: ## Khởi động toàn bộ Docker stack
	@echo "$(GREEN)▶ Starting all services...$(RESET)"
	docker compose up -d

down: ## Dừng toàn bộ Docker stack
	@echo "$(YELLOW)■ Stopping all services...$(RESET)"
	docker compose down

restart: ## Khởi động lại Docker stack
	docker compose down && docker compose up -d

build: ## Build lại Docker images
	docker compose build --no-cache

logs: ## Xem logs realtime (tất cả services)
	docker compose logs -f

logs-backend: ## Xem logs backend
	docker compose logs -f backend

logs-frontend: ## Xem logs frontend
	docker compose logs -f frontend

logs-celery: ## Xem logs Celery worker
	docker compose logs -f celery_worker

ps: ## Xem trạng thái các containers
	docker compose ps

##@ Development – Backend
.PHONY: dev-backend migrate makemigrations db-current db-history seed lint-backend test-backend shell-db shell-backend

dev-backend: ## Chạy FastAPI dev server trong Docker (hot reload)
	@echo "$(GREEN)▶ Starting FastAPI dev server on :8000...$(RESET)"
	docker compose up backend

migrate: ## Chạy Alembic migrations (upgrade head)
	@echo "$(GREEN)▶ Running database migrations...$(RESET)"
	docker compose exec backend alembic upgrade head

makemigrations: ## Tạo Alembic migration mới
	@read -p "Migration message: " msg; \
	docker compose exec backend alembic revision --autogenerate -m "$$msg"

db-current: ## Xem migration hiện tại
	docker compose exec backend alembic current

db-history: ## Xem lịch sử migrations
	docker compose exec backend alembic history --verbose

seed: ## Seed dữ liệu mẫu vào database
	@echo "$(GREEN)▶ Seeding sample data...$(RESET)"
	docker compose exec backend python -m app.db.init_db

lint-backend: ## Kiểm tra & fix code style (Ruff)
	docker compose exec backend ruff check . --fix && docker compose exec backend ruff format .

test-backend: ## Chạy toàn bộ backend tests
	@echo "$(GREEN)▶ Running backend tests...$(RESET)"
	docker compose exec backend pytest tests/ -v

test-cov: ## Chạy tests với coverage report
	docker compose exec backend pytest tests/ --cov=app --cov-report=html -v

shell-db: ## Mở psql shell vào database container
	docker compose exec db psql -U admin -d warning_ai_db

shell-backend: ## Mở bash shell vào backend container
	docker compose exec backend bash

##@ Development – Frontend
.PHONY: dev-frontend install-frontend build-frontend lint-frontend

install-frontend: ## Cài đặt dependencies Node.js
	@echo "$(GREEN)▶ Installing frontend dependencies...$(RESET)"
	cd frontend && npm install

dev-frontend: ## Chạy Next.js dev server (hot reload)
	@echo "$(GREEN)▶ Starting Next.js dev server on :3000...$(RESET)"
	cd frontend && bash -c 'source ~/.nvm/nvm.sh && nvm use 20 && npm run dev'

build-frontend: ## Build frontend production bundle
	cd frontend && npm run build

lint-frontend: ## Kiểm tra code style frontend (ESLint)
	cd frontend && npm run lint

##@ Utilities
.PHONY: env clean reset-db

env: ## Copy .env.example → .env (nếu chưa có)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✔ .env created from .env.example$(RESET)"; \
		echo "$(YELLOW)⚠ Hãy chỉnh sửa .env với giá trị thực của bạn!$(RESET)"; \
	else \
		echo "$(YELLOW)⚠ .env đã tồn tại, bỏ qua.$(RESET)"; \
	fi

clean: ## Xóa các file tạm (cache, .pyc, .next)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/.next frontend/out
	rm -rf .ruff_cache .mypy_cache .pytest_cache

reset-db: ## ⚠ XÓA và tạo lại toàn bộ database (cẩn thận!)
	@echo "$(YELLOW)⚠ WARNING: Resetting database...$(RESET)"
	docker compose down -v
	docker compose up -d db
	sleep 3
	$(MAKE) migrate
	$(MAKE) seed
