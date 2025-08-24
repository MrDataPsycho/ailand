.PHONY: docs docs-build docs-deploy

docs:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build

docs-deploy:
	uv run mkdocs gh-deploy