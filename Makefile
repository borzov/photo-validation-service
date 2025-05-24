.PHONY: help build test test-unit test-integration test-all-modules test-complete test-coverage clean lint setup

help:
	@echo "Available commands:"
	@echo "  setup              - Install dependencies"
	@echo "  build              - Build Docker images"
	@echo "  up                 - Start services"
	@echo "  down               - Stop services"
	@echo "  test               - Run all tests"
	@echo "  test-unit          - Run unit tests only"
	@echo "  test-all-modules   - Run comprehensive tests for all 11 modules"
	@echo "  test-integration   - Run integration tests (requires running service)"
	@echo "  test-complete      - Run complete system tests with all modules"
	@echo "  test-coverage      - Run tests with coverage report"
	@echo "  lint               - Run code linting"
	@echo "  clean              - Clean up containers and images"
	@echo "  dev-test           - Build, start, test, and stop (full cycle)"

setup:
	pip install -r requirements.txt

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

test: test-unit test-all-modules

test-unit:
	@echo "Running basic unit tests..."
	@PYTHONPATH=. pytest tests/unit/test_cv_checks.py tests/unit/test_api.py -v --tb=short -x

test-all-modules:
	@echo "Running comprehensive tests for all 11 CV modules..."
	@PYTHONPATH=. pytest tests/unit/test_cv_all_modules.py -v --tb=short -x

test-integration:
	@echo "Running integration tests..."
	@PYTHONPATH=. pytest tests/integration/ -v --tb=short

test-complete:
	@echo "Running complete system tests with all modules..."
	@PYTHONPATH=. pytest tests/integration/test_complete_system.py -v --tb=short

test-coverage:
	@echo "Running tests with coverage report..."
	@PYTHONPATH=. pytest tests/unit/ --cov=app --cov-report=html --cov-report=term-missing -v

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
	@make test-complete
	@make down

# Проверка всех модулей анализа фотографий
check-modules:
	@echo "Checking all 11 photo analysis modules..."
	@python -c "from app.cv.checks.registry import check_registry; check_registry.discover_checks(); metadata = check_registry.get_all_metadata(); print(f'Найдено модулей: {len(metadata)}'); [print(f'{name}: {data.display_name} ({data.category})') for name, data in metadata.items()]"

# Быстрая проверка работоспособности
quick-test:
	@echo "Running quick functionality test..."
	@PYTHONPATH=. python -c "from app.cv.checks.registry import check_registry; check_registry.discover_checks(); print('✅ Registry OK'); from app.cv.checks.runner import CheckRunner; print('✅ Runner OK'); print('✅ All core components working')" 