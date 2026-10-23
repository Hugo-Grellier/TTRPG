# Campaign Workbench (working name)

A campaign assistant for game masters, currently at the local foundation stage. [Vision](VISION.md) · [Roadmap](docs/ROADMAP.md) · [Resume state](docs/STATE.md).

## Requirements and commands

Python 3.12+ and `make`. No Python package, cloud account, or paid API is required.

```sh
make doctor        # Python version and SQLite check
make fixture       # fictional campaign, safe to rerun
make start         # http://127.0.0.1:8899
make check         # tests and compilation
make reset         # delete the local test database (stop the server first)
make resume        # environment health and resume state
```

`make demo` loads the fixture and starts the server. `DB=/tmp/demo.db PORT=8900 make demo` uses an isolated database and port. Stop with Ctrl+C.

## Current demonstration

Open the fictional campaign. Search for “promised”: the fact links to a decision, an observation, and a locator in a fictional source. Then create another campaign, add a source with a locator, record an observation (note or simulated play), state the GM's decision and a canonical fact, and search for that fact. Reload the page: SQLite retains the data. An observation alone remains noncanonical.

The interface uses English by default and a French catalog when a campaign's language is `fr`; the repository itself is written in English. This prototype does not read PDFs, prepare sessions, connect to Foundry or Discord, or manage user accounts. It listens only on `127.0.0.1` and must not be exposed to the network as it stands. Only GM visibility exists. The fixture is invented and can be removed with `make reset`.

## Working with an agent

In a new Claude Code or Codex session, enter **“Continue the roadmap.”** For product feedback, describe the experience and the outcome you want. The process is in [WORKFLOW.md](docs/WORKFLOW.md); ordinary ticket or plan approvals are not required.
