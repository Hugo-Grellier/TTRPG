PYTHON ?= python3
DATA_DIR ?= $(if $(TTRPG_DATA_DIR),$(TTRPG_DATA_DIR),$(if $(XDG_DATA_HOME),$(XDG_DATA_HOME),$(HOME)/.local/share)/ttrpg)
DB ?= $(DATA_DIR)/campaign.db
PORT ?= 8899

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
