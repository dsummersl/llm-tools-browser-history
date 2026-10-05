.PHONY: setup test lint type adr new coverage vulture fix radon treepeat ci

setup:
	uv venv
	uv sync --python .venv/bin/python

test:
	uv run pytest

lint:
	uv run ruff check .

vulture:
	uv run vulture --min-confidence 55 browser_history

fix:
	uv run ruff check . --fix
	uv run ruff format .

type:
	uv run mypy

radon:
	uv run .github/scripts/check_radon.sh

treepeat:
	uv run treepeat detect -i '**/docs/adr/*.md' .

ci: test lint type radon treepeat vulture
