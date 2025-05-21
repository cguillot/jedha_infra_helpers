.PHONY: sync
sync:
	@uv sync --all-packages

.PHONY: locked
locked:
	@uv lock --locked

.PHONY: lint
lint: sync
	@uv run ruff check --fix
	@uv run ruff format

.PHONY: test
test:
#	 @uv run pytest tests
	+$(MAKE) -C libs/hfdm test

.PHONY: publish
publish:
	+$(MAKE) -C libs/hfdm build
#	@uv publish
