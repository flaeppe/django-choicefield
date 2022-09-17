SHELL := /bin/bash
MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR ?= $(patsubst %/,%,$(dir $(MAKEFILE)))

.PHONY: test-migrations
test-migrations: export PYTHONPATH=$(PROJECT_DIR)
test-migrations: export DJANGO_SETTINGS_MODULE=tests.settings
test-migrations:
	django-admin makemigrations


.PHONY: runserver
runserver: export PYTHONPATH=$(PROJECT_DIR)
runserver: export DJANGO_SETTINGS_MODULE=tests.settings
runserver: export DJANGO_DATABASE_NAME=$(PROJECT_DIR)/tests/db.sqlite3
runserver:
	django-admin migrate
	django-admin runserver


.PHONY: createsuperuser
createsuperuser: export PYTHONPATH=$(PROJECT_DIR)
createsuperuser: export DJANGO_SETTINGS_MODULE=tests.settings
createsuperuser: export DJANGO_DATABASE_NAME=$(PROJECT_DIR)/tests/db.sqlite3
createsuperuser:
	django-admin migrate
	django-admin createsuperuser
