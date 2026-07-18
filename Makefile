.PHONY: install init validate test dry-run smoke

install:
	python3 -m venv .venv
	. .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -e .

init:
	. .venv/bin/activate && oab init

validate:
	. .venv/bin/activate && oab validate

test:
	. .venv/bin/activate && python -m unittest discover -s tests -v

dry-run:
	. .venv/bin/activate && oab functional --mode dry-run

smoke:
	. .venv/bin/activate && oab functional --mode smoke --allow-battery
