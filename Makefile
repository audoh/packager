# Installs the project
.PHONY: install
install:
	poetry install

# Generates JSON schema and any other auto-generated docs
.PHONY: docs
docs:
	poetry run python docs/build/main.py

# Checks code for code style issues etc.
.PHONY: lint
lint:
	poetry run flake8 packman packman_cli packman_gui

# Runs all tests
.PHONY: tests
tests:
	docker-compose -f docker/docker-compose.test.yml build
	docker-compose -f docker/docker-compose.test.yml run packman-test pytest

# Starts an interactive session
.PHONY: cli
cli:
	poetry run python -m packman_cli.cli

# Starts a GUI session
.PHONY: gui
gui:
	poetry run python -m packman_gui.gui
