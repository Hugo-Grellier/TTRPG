# How each note type is written

`schema.yaml` defines the frontmatter; this file defines the body. Every
skill that writes notes follows it, whether the content comes from an
adventure (`campaign-compile`) or is created (`campaign-create`,
`campaign-edit`), so imported and original campaigns read the same way.

A note is the complete reference on its subject: everything the sources say
about it, structured, never summarized away. Condensing happens elsewhere:
session prep sheets (`session-prep`) pick from these notes what one session
needs.

Write in the campaign language, translating the source. Proper names take
their official translation when there is one (`glossary.tsv`, the edition in
the campaign language: *The Stag Lord* → *Seigneur Cerf*), the source's name
going to `aliases`; otherwise keep them as the source spells them. Common
nouns around a name are translated (*Otari Market* → *Marché d'Otari*,
*Ruins of the Thirsty Alpaca* → *Ruines du Thirsty Alpaca*); a business's
own name stays (*The Rowdy Rockfish*). Use the heading wording of that language below (add a
column for a new language), identically in every note, in this order. Leave
out a section the sources say nothing about; in an original note, write the
gap as a `> [!question]` instead. Facts that fit a frontmatter field (level,
ancestry, location, factions...) go there, not only in prose. Fields hold the
current state: before play, the state when the adventure begins (where the
NPC is in chapter 1, the factions they belong to then); moves and later
allegiances go in In the campaign. `location` is a place note: for a room or
keyed area, the place that contains it.

Each fact lives in the note of its subject; other notes say in one line what
it means for them and link it. A scene's read-aloud text, mechanics, DCs,
tactics, speeches and outcomes are in the scene note: the NPC note says what
they do there and links the scene; the place note links its scenes. A
faction's members keep their own story in their notes.

Every paragraph or list item ends with the sources it comes from,
`([[ap-page]])` or `([p. N](src:id#pN))`, N being the PDF page (what a PDF
viewer opens, not the printed folio), unpadded (`#p32`); the Sources section lists every page
that says something about the subject.

Provenance is read per paragraph, in any note, imported or original: a
cited paragraph is canon (the book or Archives of Nethys page says it); an
uncited paragraph in an `origin: custom` or `modified` note is this
campaign's own creation; a change to canon goes in `> [!adaptation]`, which
cites what it changes; a fact not checked in an official source (community
wiki, memory, a summary) goes in `> [!verify]` with where it comes from,
never as plain text. Cite the GM's library (`ttrpg library search`, then
`ttrpg source add <id>`) rather than Archives of Nethys when the book is
there; AoN pages are cited by URL.

Name items, spells, actions, conditions and creatures as the game's edition
in the campaign language names them, keeping the Foundry link:
`@UUID[Compendium.pf2e.equipment-srd.Item.…]{Broche de défense}`. Where
that name is unknown, keep the source's (no question needed); never drop the
thing or invent a name. The names
players see in Foundry are in `glossary.tsv` (`ttrpg glossary`: kind, Foundry
id, English, translation, and the remaster name when the English one is
pre-remaster), from pathfinder-fr and Archives of Nethys: look them up there,
by the Foundry id of the linked document first.

Callouts: `> [!secret]` never reaches players, `> [!question]` is a GM
decision still open, `> [!idea]` is a suggestion not yet adopted,
`> [!adaptation]` and `> [!verify]` as above, `> [!todo]` work left on a
draft (`ttrpg drafts` writes it; remove it when the note is written).
`ttrpg questions` lists every open question, verify and idea of the
campaign: ask a `[!question]` only for a decision the GM must make, not for
every detail the books leave out.

| Type | Sections (en) | Sections (fr) |
| --- | --- | --- |
| npc | In brief · Appearance · Personality · Background · Motivations · In the campaign · What they know · Relations · Rewards · Statistics · Sources | En bref · Apparence · Personnalité · Passé · Motivations · Dans la campagne · Ce que sait le PNJ · Relations · Récompenses · Statistiques · Sources |
| faction | In brief · History · Goals · Organization and means · Members · Territory · In the campaign · If the PCs do nothing · Relations · Sources | En bref · Histoire · Objectifs · Organisation et moyens · Membres · Territoire · Dans la campagne · Si les PJ n'agissent pas · Relations · Sources |
| location, settlement | In brief · Show the players · Description · History · Inhabitants · Government · What is here · Rumours · Improvements · In the campaign · Sources | En bref · À montrer aux joueurs · Description · Histoire · Habitants · Gouvernement · Ce qui s'y trouve · Rumeurs · Améliorations · Dans la campagne · Sources |
| region, hex | In brief · Show the players · Description · Travel · Encounters · What is here · Rumours · Published adventures · In the campaign · Sources | En bref · À montrer aux joueurs · Description · Voyages · Rencontres · Ce qui s'y trouve · Rumeurs · Aventures publiées · Dans la campagne · Sources |
| quest | In brief · Hook · Goal · How it unfolds · Reward · Done when · Failure · Sources | En bref · Accroche · Objectif · Déroulement · Récompense · Terminée quand · Échec · Sources |
| item | In brief · Description · Powers · History · Where it is · Sources | En bref · Description · Pouvoirs · Histoire · Où le trouver · Sources |
| scene | In brief · Read aloud · Situation · Stakes · Opposition · How it unfolds · Outcomes · Treasure · Sources | En bref · À lire · Situation · Enjeux · Opposition · Déroulement · Issues · Trésor · Sources |
| handout | Show the players · Sources | À montrer aux joueurs · Sources |
| clock | Segments (one line each: what happens when it fills) | Segments |
| event | What happens · Consequences | Ce qui se passe · Conséquences |
| map | Show the players · Areas · Tokens · Ambience · Sources | À montrer aux joueurs · Zones · Tokens · Ambiance · Sources |
| session | What happened · Consequences · Open threads | Ce qui s'est passé · Conséquences · Fils ouverts |
| pc | In brief · Concept · Background · Ties · Ambitions · Secrets · Arc hooks · In the campaign | En bref · Concept · Passé · Liens · Ambitions · Secrets · Accroches d'arc · Dans la campagne |
| company | In brief · Renown · Wealth · Influence · Authority · In the campaign | En bref · Renommée · Richesse · Influence · Autorité · Dans la campagne |
| mystery | In brief · Truth · Clues · Revelations · In the campaign · Sources | En bref · Vérité · Indices · Révélations · Dans la campagne · Sources |
| chapter (arc) | In brief · Premise · Stakes · Entry points · Forces · Possible outcomes · In the campaign · Sources | En bref · Prémisse · Enjeux · Points d'entrée · Forces en jeu · Issues possibles · Dans la campagne · Sources |

What goes in each:

- **In brief**: two or three sentences: who or what it is and why it matters
  in the campaign. The only summary in the note.
- **Appearance / Personality** (npc): looks, dress, voice, mannerisms,
  habits, typical phrases the source gives; how they treat the PCs.
- **Background / History**: the past, in order, as the sources tell it.
- **Motivations / Goals**: what they want, openly and secretly, and why.
- **In the campaign**: every appearance or role, in campaign order (by
  chapter in an adventure; by arc, front or session in a sandbox), with its conditions ("if the PCs...", "once the kingdom
  reaches level 5..."), how they change, and how it ends; each scene in one
  or two lines with its link.
- **Members** (faction): one line per member by link, with rank and role; the
  membership itself is the NPC's `factions` field. Rank and file without a
  note: numbers, roles and statistics links.
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
- **Handout**: `visibility: players`; the image and its text translated,
  nothing the players must not see. A players note links only players
  notes, so its sources are its own AP handout page; when to show it goes in
  the scene, item or NPC note that links it.
- **Segments** (clock): `segments` in frontmatter matches the number of lines.
- **Improvements** (location, settlement): for a place the PCs own or run
  (a home base, an inn): one line per improvement, done or possible, what it
  changes at the table, and where it comes from (money, a favour, a find, an
  artisan met on the road), linking that note. No ledger: costs and Earn
  Income stay in session notes.
- **Government** (location, settlement): who rules, how, and what the books
  leave out (a place without a ruler of its own says so, cited).
- **Rumours** (location, settlement, region, hex): a table of what the PCs
  can hear, true or false, each linking the note it leads to.
- **Travel** (region, hex): distances and travel times to the neighbouring
  places, measured on the official map (say which) or cited.
- **Published adventures** (region, hex): adventures and scenarios set
  there, with levels and pages, for the GM to reuse.
- **pc**: written with the player after session zero, never invented before.
  `player` is the player's name as in `campaign.yaml` `players`; `foundry`
  is the player's own actor (`Actor.<id>`), which the sync never touches. **Ties**:
  one line per NPC, faction, place or other PC with its stakes (family,
  mentor, debt, enemy). **Secrets**: what the player told the GM alone, in
  `> [!secret]`. **Arc hooks**: situations the campaign can bring back, each
  linking the note that would carry it; not every arc leads to the main
  threat.
- **Reputation** (faction `reputation`, -50 to 50): the party's standing with
  that group, GM Core's reputation subsystem (printed p. 200; Revered 30, Admired 15, Liked
  5, Ignored -4 to 4, Disliked -5, Hated -15, Hunted -30). Renown is
  reputation with a public (a district's people, a city, a nation) written as
  a faction. Wealth, informal influence and legal authority are different
  things: say them in the faction or settlement note, not in this number.
- **company**: the party as a group, one note (`pcs/`), its `base` the place
  they call home. Five things kept apart: **Renown** (`renown`: how far they
  are known, unknown → neighbourhood → local → regional → international →
  legendary; for what, and where it stops), reputation with each group (the
  factions' `reputation`), **Wealth** (what they own beyond the coins of
  their Foundry sheets: properties, businesses, income, debts, linking the
  place notes), **Influence** (who listens to them or owes them, informally,
  by link) and **Authority** (offices, titles, charters and legal powers,
  who granted them and what they allow). Famous is not powerful; liked by
  one faction is not liked by all.
- **mystery**: a truth the PCs uncover over time. **Truth** in `> [!secret]`.
  **Clues**: one line each: what it is, where or from whom (linked), what it
  points to, and once found, the session that found it (`[[session-id]]`);
  three clues at least for each conclusion the PCs must reach. **Revelations**:
  what changes when they know. `state` becomes `solved` or `abandoned`.
- **chapter (arc)**: in an original campaign, a possible arc, not a script:
  **Premise** and **Stakes**, **Entry points** (hooks, PCs' arc hooks,
  factions' clocks that lead in), **Forces** (factions, NPCs, clocks,
  mysteries by link), **Possible outcomes** and what each changes. An
  imported chapter keeps the adventure's text.
- **Map** notes describe a Foundry scene; the scene itself (walls, lights,
  sounds, token positions) is edited in Foundry. `stage`: `raw` (image only),
  `walled`, `lit`, `ready` (set by the GM once played or checked); `kind`:
  `battle` (tactical, square grid) or `overview` (region or world map, which
  never counts as a place's battle map). **Areas**
  link the scene notes of each zone; **Tokens** list which NPC or creature goes
  where; **Ambience** gives lighting, darkness, sounds and playlist. Places
  link their maps with `[[map-id]]` in the body or the map's `locations`.
- **Foundry fields** (synced by `ttrpg foundry apply`): npc and item `stats`
  is the compendium uuid a world copy is made from (npc `adjust`: `elite` or
  `weak`); npc `owners` lists the players (Foundry user names) who control
  it; a place's `discovered: "yes"` gives players a page with its title only, and
  its `map` and `cells` (World Explorer offsets `"i_j"`) reveal it on that map.
- **Party**: `party` in `campaign.yaml` is the number of player characters
  and session `level` the party level at that session; encounters are built
  for both (GM Core encounter budget adjusted per character): `ttrpg
  creatures` gives the budgets, each creature's XP and its compendium link.
- **Events** are dated in-game (`date`). Before `start` in `campaign.yaml`:
  the setting's past, cited canon (or the campaign's own invented history,
  uncited), never played. From `start` on: `played: "no"` is planned (dates
  from the adventure or the GM), `played: "yes"` happened at the table, set
  only after a session.
- **Start date**: choose `start` from the sources and write why in a note:
  the year the latest books describe the starting place, after the outcomes
  later books give to earlier adventure paths. Canon published for years
  after `start` is the future: `> [!secret]` or `[!idea]`, not fact.
