.PHONY: install test lint typecheck check serve demo

install:
	uv sync --dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run pyright

check: lint typecheck test

serve:
	uv run take-home-router serve --host 127.0.0.1 --port 8000

demo:
	uv run take-home-router route --prompt "Explain why memoization improves this recursive algorithm" --explain
