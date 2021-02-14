.PHONY: install
install:
	poetry install

.PHONY: docs
docs:
	poetry run python docs/build/main.py

.PHONY: lint
lint:
	poetry run flake8 packman packman_cli packman_gui

.PHONY: tests
tests:
	docker-compose -f docker/docker-compose.test.yml build
	docker-compose -f docker/docker-compose.test.yml run packman-test pytest

.PHONY: run
run:
	poetry run python -m packman_cli.cli
