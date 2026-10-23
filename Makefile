PYTHON ?= python3
DB ?= data/campaign.db
PORT ?= 8765

.PHONY: doctor start test check fixture reset demo resume
doctor:
	$(PYTHON) --version
	$(PYTHON) -m campaign check --db $(DB)

start:
	$(PYTHON) -m campaign serve --db $(DB) --port $(PORT)

test:
	$(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) -m compileall -q campaign tests

fixture:
	$(PYTHON) -m campaign fixture --db $(DB)

reset:
	$(PYTHON) -m campaign reset --db $(DB)

demo: fixture start

resume: doctor
	@cat docs/STATE.md
