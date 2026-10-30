# How each note type is written

`schema.yaml` defines the frontmatter; this file defines the body. Every
skill that writes notes follows it, whether the content comes from an
adventure (`campaign-compile`) or is created (`campaign-create`,
`campaign-edit`), so imported and original campaigns read the same way.

A note is the complete reference on its subject: everything the sources say
about it, structured, never summarized away. Condensing happens elsewhere:
session prep sheets (`session-prep`) pick from these notes what one session
needs.

Write in the campaign language, translating the source; keep proper names as
the source spells them. Use the heading wording of that language below (add a
column for a new language), identically in every note, in this order. Leave
out a section the sources say nothing about; in an original note, write the
gap as a `> [!question]` instead. Facts that fit a frontmatter field (level,
ancestry, location, factions, chapters...) go there, not only in prose.

Every paragraph ends with the sources it comes from, `([[ap-page]])` or
`([p. N](src:id#pN))`; the Sources section lists them all. An original note
has none.

Callouts: `> [!secret]` never reaches players, `> [!question]` is a GM
decision still open, `> [!idea]` is a suggestion not yet adopted.

| Type | Sections (en) | Sections (fr) |
| --- | --- | --- |
| npc | In brief · Appearance · Personality · Background · Motivations · In the campaign · What they know · Relations · Rewards · Statistics · Sources | En bref · Apparence · Personnalité · Passé · Motivations · Dans la campagne · Ce qu'il sait · Relations · Récompenses · Statistiques · Sources |
| faction | In brief · History · Goals · Organization and means · Territory · In the campaign · If the PCs do nothing · Relations · Sources | En bref · Histoire · Objectifs · Organisation et moyens · Territoire · Dans la campagne · Si les PJ n'agissent pas · Relations · Sources |
| location, settlement | In brief · Show the players · Description · History · Inhabitants · What is here · In the campaign · Sources | En bref · À montrer aux joueurs · Description · Histoire · Habitants · Ce qui s'y trouve · Dans la campagne · Sources |
| region, hex | In brief · Show the players · Description · Encounters · What is here · In the campaign · Sources | En bref · À montrer aux joueurs · Description · Rencontres · Ce qui s'y trouve · Dans la campagne · Sources |
| quest | In brief · Hook · Goal · How it unfolds · Reward · Done when · Failure · Sources | En bref · Accroche · Objectif · Déroulement · Récompense · Terminée quand · Échec · Sources |
| item | In brief · Description · Powers · History · Where it is · Sources | En bref · Description · Pouvoirs · Histoire · Où le trouver · Sources |
| scene | In brief · Read aloud · Situation · Stakes · Opposition · How it unfolds · Outcomes · Treasure · Sources | En bref · À lire · Situation · Enjeux · Opposition · Déroulement · Issues · Trésor · Sources |
| clock | Segments (one line each: what happens when it fills) | Segments |
| event | What happens · Consequences | Ce qui se passe · Conséquences |
| map | Show the players · Areas · Tokens · Ambience · Sources | À montrer aux joueurs · Zones · Tokens · Ambiance · Sources |
| session | What happened · Consequences · Open threads | Ce qui s'est passé · Conséquences · Fils ouverts |

What goes in each:

- **In brief**: two or three sentences: who or what it is and why it matters
  in the campaign. The only summary in the note.
- **Appearance / Personality** (npc): looks, dress, voice, mannerisms,
  habits, typical phrases the source gives; how they treat the PCs.
- **Background / History**: the past, in order, as the sources tell it.
- **Motivations / Goals**: what they want, openly and secretly, and why.
- **In the campaign**: every appearance or role, chapter by chapter in
  campaign order, with its conditions ("if the PCs...", "once the kingdom
  reaches level 5..."), how they change, and how it ends.
- **What they know** (npc): what they can reveal, at what price or condition.
- **Relations**: one line per link to another note, with its stakes. The
  structured relation itself is a frontmatter field on one side only.
- **Rewards**: what helping or defeating them earns: treasure, favours,
  archetypes, allies, kingdom effects.
- **Statistics**: a Foundry `@UUID[...]` link (actor or compendium) per
  version the campaign uses, and any adjustment; never a copied stat block.
- **If the PCs do nothing** (faction): link the faction's clock; the front is
  what the world does on its own.
- **Show the players / Read aloud**: what can be read aloud or seen, the
  source's boxed text translated in full; secrets elsewhere.
- **What is here / Inhabitants**: NPCs, scenes, treasure, services, hooks, by
  link with one line each.
- **Situation / Stakes / Opposition / How it unfolds / Outcomes** (scene):
  table-facing first; tactics, morale, hazards and DCs as the source gives
  them; a scene is runnable when the GM needs no other document during it.
- **Segments** (clock): `segments` in frontmatter matches the number of lines.
- **Map** notes describe a Foundry scene; the scene itself (walls, lights,
  sounds, token positions) is edited in Foundry. `stage`: `raw` (image only),
  `walled`, `lit`, `ready` (set by the GM once played or checked); `kind`:
  `battle` (tactical, square grid) or `overview` (region or world map, which
  never counts as a place's battle map). **Areas**
  link the scene notes of each zone; **Tokens** list which NPC or creature goes
  where; **Ambience** gives lighting, darkness, sounds and playlist. Places
  link their maps with `[[map-id]]` in the body or the map's `locations`.
- **Events** are dated in-game (`date`); `played: "yes"` only after a session.
  Planned events take dates from `start` in `campaign.yaml`.
