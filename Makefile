# Makefile for testing the module.

SHELL = /bin/bash
PYTHON ?= python
VENV ?= venv-${PYTHON}

IN_VENV = source "${VENV}/bin/activate" &&

OUTPUT_FORMAT = --show-diff

.PHONY: setup artifacts inttests tests coverage

setup: ${VENV}/marker

artifacts:
	mkdir -p artifacts

${VENV}/marker:
	-rm -rf "${VENV}"
	virtualenv -p "${PYTHON}" "${VENV}"
	source "${VENV}/bin/activate" && pip install -r requirements-test.txt
	touch "${VENV}/marker"

tests: setup artifacts
	${IN_VENV} ${PYTHON} rozipinfo_test.py -v

inttests: artifacts
	./test.pl --show-command ${OUTPUT_FORMAT} --junitxml artifacts/inttest-${PYTHON}.xml "${PYTHON}" .

coverage: setup
	-rm -rf .coverage
	${IN_VENV} TEST_WITH_COVERAGE=1 ${PYTHON} rozipinfo_test.py -v

package: tests inttests
	./package.sh
