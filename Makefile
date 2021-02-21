# Installs the project
.PHONY: install
install:
	poetry install

# Builds Docker
.PHONY: docker
docker:
	docker-compose -f docker/docker-compose.test.yml up --build

# Generates JSON schema and any other auto-generated docs
.PHONY: docs
docs:
	poetry run python docs/build/main.py
	mkdocs gh-deploy

# Checks code for code style issues etc.
.PHONY: lint
lint:
	poetry run flake8 packman packman_cli packman_gui

# Builds Docker and lints
.PHONY: lint-docker
lint-docker:
	make docker
	docker-compose -f docker/docker-compose.test.yml run packman-test make lint

# Runs all tests
.PHONY: tests
tests:
	make docker
	docker-compose -f docker/docker-compose.test.yml run packman-test pytest --testdox

# Alias for make tests
.PHONY: test
test:
	make tests

# Starts an interactive session
.PHONY: cli
cli:
	poetry run python -m packman_cli.cli

# Starts a GUI session
.PHONY: gui
gui:
	poetry run python -m packman_gui.gui
