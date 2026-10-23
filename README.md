# Campaign Workbench (working name)

A local campaign workbench for game masters. [Vision](VISION.md) · [Roadmap](docs/ROADMAP.md) · [Resume state](docs/STATE.md).

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

Open **Mira's ford — offline loop**. Its fictional source leads to an initial proposal and a revision. The prep sheet uses the revised proposal and an established fact. A simulated boat branch produces an observation; the GM's decision establishes its consequence. The corrected crossing fact flags the dependent prep sheet. Search for “bell” to see the promise, correction, and linked consequence with their decisions and source locators. Reload to check persistence.

To repeat the journey yourself, create a campaign and use the page's jump links: add a source, propose and revise, record an observation and establish a fact, prepare a situation, simulate an action, consolidate the resulting observation with a decision, and search. A proposal, prep sheet, or simulated event never becomes canon on its own.

The interface uses English by default and a French catalog when a campaign's language is `fr`; the repository itself is written in English. Preparation and simulation are manually authored. Corrections flag dependent prep sheets for GM review; they do not rewrite them. This prototype does not read PDFs, connect to Foundry or Discord, publish to players, or manage user accounts. It listens only on `127.0.0.1` and must not be exposed to the network as it stands. The fixture is invented and can be removed with `make reset`.

## Working with an agent

In a new Claude Code or Codex session, enter **“Continue the roadmap.”** For product feedback, describe the experience and the outcome you want. The process is in [WORKFLOW.md](docs/WORKFLOW.md); ordinary ticket or plan approvals are not required.
