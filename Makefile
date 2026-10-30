PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: test check
test:
	$(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) -m compileall -q ttrpg tests
