.PHONY: sync
sync:
	@uv sync --package hfdm

.PHONY: lint
lint:
	@uv run ruff check --fix
	@uv run ruff format

.PHONY: test
test:
	@uv run pytest tests

.PHONY: build
build: sync
	@uv build --package hfdm
