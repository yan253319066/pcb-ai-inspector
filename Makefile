.PHONY: help install dev test lint format clean run

# Python executable
PYTHON := python
PIP := pip
CONDA := conda

help: ## Show this help message
	@echo "PCB AI Inspector - Development Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"

test: ## Run tests
	pytest src/pcb_ai_inspector/tests -v

test-cov: ## Run tests with coverage
	pytest src/pcb_ai_inspector/tests -v --cov=pcb_ai_inspector --cov-report=html

lint: ## Run linting checks
	flake8 src/pcb_ai_inspector
	mypy src/pcb_ai_inspector

format: ## Format code
	black src/pcb_ai_inspector
	isort src/pcb_ai_inspector

typecheck: ## Run type checking
	mypy src/pcb_ai_inspector

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage

run: ## Run the application
	$(PYTHON) -m pcb_ai_inspector

# Development environment setup
env: ## Create conda environment
	$(CONDA) create -n pcb-ai python=3.11.9 -y
	$(CONDA) activate pcb-ai
	$(PIP) install -e ".[dev]"

activate: ## Activate conda environment
	$(CONDA) activate pcb-ai
