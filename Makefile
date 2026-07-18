.PHONY: install init validate test lint types coverage check dry-run smoke

install:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -e .

init:
	. .venv/bin/activate && oab init

validate:
	. .venv/bin/activate && oab validate

test:
	. .venv/bin/activate && python -m unittest discover -s tests -v

lint:
	. .venv/bin/activate && ruff check .

types:
	. .venv/bin/activate && mypy

coverage:
	. .venv/bin/activate && coverage erase && PYTHONPATH=tests coverage run -m unittest discover -s tests -v && coverage report

check: lint types coverage validate

dry-run:
	. .venv/bin/activate && oab functional --mode dry-run

smoke:
	. .venv/bin/activate && oab functional --mode smoke --allow-battery
