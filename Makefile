# Makefile for testing the module.

SHELL = /bin/bash
PYTHON ?= python
VENV ?= venv

IN_VENV = source "${VENV}/bin/activate" &&

.PHONY: setup artifacts inttests tests coverage

setup: ${VENV}/marker

artifacts:
	mkdir -p artifacts

${VENV}/marker:
	-rm -rf "${VENV}"
	virtualenv -p "${PYTHON}" "${VENV}"
	source "${VENV}/bin/activate" && pip install -r requirements-test.txt
	touch "${VENV}/marker"

tests: setup
	${IN_VENV} ${PYTHON} rozipinfo_test.py -v --with-coverage --cover-html

inttests: artifacts
	./test.pl --show-command --show-output --junitxml artifacts/inttest.xml ./showzip.py tests.txt

coverage: setup
	-rm -rf .coverage
	${IN_VENV} ${PYTHON} rozipinfo_test.py -v --with-coverage --cover-html
