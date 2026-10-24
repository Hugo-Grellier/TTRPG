# Campaign Workbench (working name)

A local campaign workbench for game masters. [Vision](VISION.md) · [Roadmap](docs/ROADMAP.md) · [Resume state](docs/STATE.md).

## Requirements and commands

Python 3.12+, `make`, and the Markdown renderer. Install the dependency in a local virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`make` uses `.venv/bin/python` when it exists. No cloud account or paid API is required.

```sh
make doctor        # Python version and SQLite check
make fixture       # fictional campaign, safe to rerun
make start         # http://127.0.0.1:8899
make check         # tests and compilation
make reset         # delete the local test database (stop the server first)
make resume        # environment health and resume state
```

`make demo` loads the fixture and starts the server. By default, private campaign data lives in `${XDG_DATA_HOME:-~/.local/share}/ttrpg/campaign.db`, outside the source checkout. Set `TTRPG_DATA_DIR` or `DB` to choose another location; `DB=/tmp/demo.db PORT=8900 make demo` uses an isolated database and port. Stop with Ctrl+C.

## Current demonstration

Open **Mira's ford — offline loop** from the campaign list. The left navigation opens on **Campaign**; **Product** holds `VISION.md` and the other design documents separately. Campaign preparations are records in the private SQLite database shown on each document, normally `~/.local/share/ttrpg/campaign.db`. A preparation's **Download Markdown** link saves a copy that you can open in another editor. Edits to that copy do not sync back to the app.

The workspace puts Codex/Claude Code conversation beside Markdown-rendered material and review comments. Select any passage, even one word, to comment on exactly that text; campaign record line numbers can also select a full line. The inline form shows the chosen passage, and clicking a saved comment returns to it. The composer offers editable playbooks for exploration, revision, preparation, and contradiction review. Clicking **Send** passes the open campaign document and its comments, or the selected product-doc path and its comments, plus established facts to the selected installed CLI. Each CLI can edit repository files in a private per-campaign draft Git worktree under the user data directory. The workspace shows the draft diff for review; replies cannot establish canon. CLI sessions resume on later messages. The bottom bar shows CLI status; it is not an interactive terminal.

The fixture's fictional source leads to an initial proposal and a revision. Its prep sheet uses the revised proposal and an established fact. A simulated boat branch produces an observation; the GM's decision establishes its consequence. The corrected crossing fact flags the dependent prep sheet. The **Campaign records and forms** link opens the earlier data-entry view; search for “bell” there to see the promise, correction, and linked consequence with their decisions and source locators. Reload to check persistence.

To repeat the journey yourself, create a campaign and use the page's jump links: add a source, propose and revise, record an observation and establish a fact, prepare a situation, simulate an action, consolidate the resulting observation with a decision, and search. A proposal, prep sheet, or simulated event never becomes canon on its own.

The interface uses English by default and a French catalog when a campaign's language is `fr`; the repository itself is written in English. Preparation and simulation are manually authored. Corrections flag dependent prep sheets for GM review; they do not rewrite them. The conversation uses installed Codex/Claude Code subscriptions when the GM explicitly sends a message; availability and limits depend on those CLIs. This prototype has no draft acceptance action, PDF reading, Foundry or Discord connection, player publication, or user accounts. It listens only on `127.0.0.1` and must not be exposed to the network as it stands. The fixture is invented and can be removed with `make reset`.

## Working with an agent

In a new Claude Code or Codex session, enter **“Continue the roadmap.”** For product feedback, describe the experience and the outcome you want. The process is in [WORKFLOW.md](docs/WORKFLOW.md); ordinary ticket or plan approvals are not required.
