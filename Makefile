.PHONY: docs
docs:
	python docs/build/main.py

.PHONY: tests
tests:
	docker-compose -f docker/docker-compose.test.yml build
	docker-compose -f docker/docker-compose.test.yml run packman-test pytest
