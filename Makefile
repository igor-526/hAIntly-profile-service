.PHONY: format lint test

format:
	uv run ruff check . --fix
	uv run ruff format .

lint:
	uv run mypy src tests
	uv run flake8 src tests

test:
	uv run pytest
