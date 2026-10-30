PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: test check recorder-test
test:
	$(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) -m compileall -q ttrpg tests

# Discord recorder (Node): run `npm ci --prefix recorder` once.
recorder-test:
	cd recorder && npm test
