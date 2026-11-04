---
name: lore-research
description: Gather what the published setting says about a subject (a city district, a deity, an organization, a region, a creature, a historical event) from the GM's whole PDF library and Archives of Nethys, and write it as a cited campaign note, canon kept apart from adaptations, open conflicts and unchecked facts. Use when the GM asks what canon says about something, or before inventing anything set in the published world.
---

# Research the published setting

The campaign may be original, but its world is published: use what the books
say before inventing, and say where it comes from. A note written here is the
complete reference on its subject as the books describe it; the campaign's
own changes come after, marked as such.

## 1. Find every source

Name the subject, its aliases and short forms (English names: the books are
in English unless the library holds a translation).

- **The GM's library** (every official PDF they own, extracted to text):

  ```sh
  tools/bin/ttrpg library search "Westerhold" --pages                 # books, page counts, pages
  tools/bin/ttrpg library search "Westerhold" --book absalom --context 4   # each match with 4 lines around
  ```

  The pattern is a regular expression, case-insensitive: `'\bWest\b'` for a
  whole word, `'Deepkeg|Drun'` for several names.

  Read each listed page in full (`tools/bin/ttrpg library page <id> <N> --text`),
  and the pages around it when a section starts or continues there: an
  entry often ends on the next page. `tools/bin/ttrpg library page <id> <N>`
  renders the page as an image (it prints the PNG path; open it): read it
  for maps, tables, sidebars and two-column pages, whose extracted text
  interleaves the columns.
  The page number is the PDF page (the file `pNNN.txt`), not the folio
  printed on the page, which is often one or two lower: cite the PDF page. `library list <words>` finds a
  book's id.
- **Archives of Nethys** (official text online): `tools/bin/ttrpg aon <name>
  [--category deity|creature|rules|...]` gives each entry's book and printed
  page, its URL, and whether it is the legacy or the remaster version. AoN
  holds rules, creatures, deities, items and some organizations, rarely a
  district or a village: do not ask it about places. The page it gives is
  the printed folio: find the passage in the library (`library search
  '<a phrase>' --book <id>`) to cite the PDF page; cite AoN by URL only
  when the book is not in the library.
- **Community wiki** (pathfinderwiki.com): only to discover which books talk
  about the subject. A fact found nowhere else goes in `> [!verify]` with the
  wiki page it comes from.

If `library` says the library is missing (a cloud agent), the pages already
cited are in `sources/<id>/pNNN.txt`; for anything else work from AoN and say
in your report that the books were not read.

## 2. Weigh them

- Remaster rules over legacy rules. For lore, the most recent publication
  describes the world as it is now; older ones give its history. Adventure
  paths and Society scenarios move the timeline: say which year (AR) a
  source describes when it matters (a ruler replaced, a district burned).
  A dated historical event the campaign needs is an `event` note dated
  before `start` (`note-types.md`, Events); what books publish for years
  after `start` is the future, not a fact of the note.
- Two sources that disagree: give both, cited, in a `> [!question]`, and
  state neither as fact elsewhere in the note.
- An adventure's spoilers (its villain, its ending) are facts like others,
  in `> [!secret]` when players could meet them.

## 3. Write the note

- Once you know which books you cite, declare them:
  `tools/bin/ttrpg source add <id> <id>=<alias>...` (it writes
  `campaign.yaml`; ids are the library's; a book already declared keeps its
  alias, which it prints). When several agents research in parallel, report
  the books to declare instead, and the one who finishes declares them.
- One note per subject, found first by title and `aliases`, in the folder of
  its kind (`campaign-edit` step 3: `places/`, `factions/`, `npcs/`...); the type that fits (`settlement`, `location`, `faction`, `npc`,
  `region`, `item`, `event`...; a deity or an organization without a place
  is a `faction`, a historical era a `note`). Sections and frontmatter per
  `tools/ttrpg/note-types.md` and `tools/ttrpg/schema.yaml`, written in the
  campaign language; proper names as the source spells them unless the
  library holds the campaign language's edition.
- Every paragraph ends with its citations, `([p. N](src:<id>#pN))`, N the
  PDF page; the Sources section lists each page once with what it is about.
  `origin: ap` for a note that reports published material, open
  `[!question]`s included; `modified` once it carries the campaign's own
  changes (`[!adaptation]`, invented paragraphs).
- Each fact lives in the note of its subject: a settlement note says in one
  line what each resident, faction or place inside means there (with its
  citation); their own story goes in their notes. Link a subject that has a
  note (`[[id]]`); name one that has none in plain text and list it in your
  report. `aliases` are other names the books use, not index labels.
- Leave out a section the books say nothing about; a gap the GM must fill
  is one `> [!question]` where it belongs, only when the campaign needs the
  answer (a detail the books leave out is not a question: say it in your
  report).
- The campaign's changes to canon, if the GM asked for them: `> [!adaptation]`
  citing what they change. Ideas of yours: `> [!idea]`. Nothing invented as
  plain text.
- Subjects met on the way that deserve their own note: list them in your
  report with their pages; do not write them unless asked.

## 4. Check and report

Go back through the pages read: each fact about the subject is in the note
or in the note of the subject it belongs to, and every page that says
something about it is cited. Run `tools/bin/ttrpg source excerpts` (commits the cited pages' text for
agents without the library) and `tools/bin/ttrpg check`, then report: books
and pages read, what the books do not say (the gaps the GM will fill), the
conflicts, and `tools/bin/ttrpg questions` for the notes you touched. When
several agents research in parallel, report instead of finishing for all.
