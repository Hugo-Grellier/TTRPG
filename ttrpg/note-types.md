# How each note type is written

`schema.yaml` defines the frontmatter; this file defines the body. Every
skill that writes notes follows it, whether the content comes from an
adventure (`campaign-distill`) or is created (`campaign-create`,
`campaign-edit`), so imported and original campaigns read the same way.

Write in the campaign language. Use the heading wording of that language
below (add a column for a new language), identically in every note. One
screen per note: link to a longer note or an AP page for detail. Sources go
last as `[[ap-page]]` or `[p. N](src:id#pN)` links; an original note has none.

Callouts: `> [!secret]` never reaches players, `> [!question]` is a GM
decision still open, `> [!idea]` is a suggestion not yet adopted.

| Type | Sections (en) | Sections (fr) |
| --- | --- | --- |
| npc | At the table · What they know · Relations · Statistics · Sources | À la table · Ce qu'il sait · Relations · Statistiques · Sources |
| faction | Goal · Means · If the PCs do nothing · Sources | But · Moyens · Si les PJ n'agissent pas · Sources |
| location, settlement | Show the players · What is here · Sources | À montrer aux joueurs · Ce qui s'y trouve · Sources |
| region, hex | Show the players · Encounters · What is here · Sources | À montrer aux joueurs · Rencontres · Ce qui s'y trouve · Sources |
| quest | Goal · Reward · Done when · Sources | Objectif · Récompense · Terminée quand · Sources |
| clock | Segments (one line each: what happens when it fills) | Segments |
| event | What happens · Consequences | Ce qui se passe · Conséquences |
| scene | Situation · Stakes · Opposition · Outcomes · Sources | Situation · Enjeux · Opposition · Issues · Sources |
| session | What happened · Consequences · Open threads | Ce qui s'est passé · Conséquences · Fils ouverts |

What goes in each:

- **At the table** (npc): role in two lines, appearance and voice in two
  lines, what they want, how they react to the PCs.
- **What they know** (npc): what they can reveal, at what price or condition.
- **Relations**: one line per link to another note, with its stakes. The
  structured relation itself is a frontmatter field on one side only.
- **Statistics**: a Foundry `@UUID[...]` link (actor or compendium) and any
  adjustment; never a copied stat block.
- **If the PCs do nothing** (faction): link the faction's clock; the front is
  what the world does on its own.
- **Show the players**: what can be read aloud or seen; secrets elsewhere.
- **What is here**: NPCs, scenes, treasure, hooks, by link.
- **Situation / Stakes / Opposition / Outcomes** (scene): table-facing first;
  a scene is runnable when the GM needs no other document during it.
- **Segments** (clock): `segments` in frontmatter matches the number of lines.
- **Events** are dated in-game (`date`); `played: "yes"` only after a session.
  Planned events take dates from `start` in `campaign.yaml`.
