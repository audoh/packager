docker_cmd = docker-compose -f docker/docker-compose.test.yml run packman-test
pytest_cmd = pytest --testdox ${PYTEST_ARGS}


define run_docker_command
	$(docker_cmd) $(1)
endef

# To run commands without debug output:
# bash: make watch --quiet 2> /dev/null
# powershell: make watch --quiet 2> $null

# Default: installs the project and starts the watcher
.PHONY: quickstart
quickstart:
	make install watch

# Installs the project
.PHONY: install
install:
	poetry install

# Builds Docker
.PHONY: docker
docker:
	docker-compose -f docker/docker-compose.test.yml up --build 1>&2

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
	$(call run_docker_command,make lint)

# Runs all tests
.PHONY: tests
tests:
	make docker
	$(call run_docker_command,$(pytest_cmd))

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

# Runs lint and test
.PHONY: checks
checks:
	make lint tests

# Runs checks when anything changes
.PHONY: watch
watch:
	make docker
	poetry run python watcher.py . 'make docker && $(docker_cmd) $(pytest_cmd)'
