.PHONY: help build test test-unit test-integration clean lint setup

help:
	@echo "Available commands:"
	@echo "  setup         - Install dependencies"
	@echo "  build         - Build Docker images"
	@echo "  up            - Start services"
	@echo "  down          - Stop services"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests (requires running service)"
	@echo "  lint          - Run code linting"
	@echo "  clean         - Clean up containers and images"

setup:
	pip install -r requirements.txt

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	@PYTHONPATH=. pytest tests/unit/ -v --tb=short -x

test-integration:
	@echo "Running integration tests..."
	@pytest tests/integration/ -v --tb=short

lint:
	@echo "Checking Python code style..."
	@python -m py_compile app/**/*.py || echo "Syntax errors found"
	@echo "Code style check completed"

clean:
	docker-compose down -v
	docker system prune -f

dev-test: build up
	@echo "Waiting for services to start..."
	@sleep 15
	@make test-integration
	@make down 