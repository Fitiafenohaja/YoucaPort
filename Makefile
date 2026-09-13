.PHONY: install lock test lint format build binary

install: ## Installe les dépendances avec Poetry
	poetry install

lock: ## Régénère poetry.lock
	poetry lock

test: ## Lance les tests avec Pytest
	poetry run pytest

lint: ## Vérifie le style avec Ruff
	poetry run ruff check .

format: ## Formate le code avec Ruff
	poetry run ruff format .

build: ## Construit les paquets dist/*.whl + tar.gz
	poetry build

binary: ## Construit un exécutable autonome (PyInstaller)
	bash scripts/build_binary.sh