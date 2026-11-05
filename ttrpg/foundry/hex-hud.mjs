// Hex hover panel for region maps, shipped in every exported campaign module (ttrpg export-foundry).
// Hovering a hex shows its number, region, terrain, travel and exploration, and the campaign places on it.
// Region, terrain and travel come from the map's hex table (hexes/<scene id>.json, public); places come from
// the journal pages the live sync writes (flags.ttrpg.scene and .cells), filtered by what the user may see:
// players only get the title-only "discovered" pages. With World Explorer on, players see nothing of a hex
// that is not revealed.
const BASE = new URL("..", import.meta.url).pathname.replace(/^\//, "");
let config = { labels: {}, scenes: [] };
// Loaded once, awaited by every canvas: the first scene can be drawn before "ready".
let loading = null;
let table = null, panel = null, last = null, timer = null;

const esc = (s) => foundry.utils.escapeHTML(String(s ?? ""));

async function load(path) {
  const response = await fetch(`${BASE}${path}`);
  return response.ok ? response.json() : null;
}

function places(scene, cell) {
  const out = new Map();
  for (const entry of game.journal) {
    for (const page of entry.pages) {
      const flags = page.flags?.ttrpg;
      if (flags?.scene !== scene.uuid || !flags.cells?.includes(cell) || !page.testUserPermission(game.user, "OBSERVER")) continue;
      const id = flags.id ?? flags.discovered;
      const known = out.get(id) ?? { name: page.name };
      if (flags.discovered) known.discovered = true;
      if (flags.kind === "hex") known.hex = flags;
      if (flags.id) known.gm = true;
      out.set(id, known);
    }
  }
  return [...out.values()];
}

function revealed(scene, cell) {
  const explorer = scene.flags?.["world-explorer"];
  if (!explorer?.enabled || game.user.isGM) return true;
  return Boolean(explorer.gridData?.[cell]?.reveal);
}

function render(scene, cell, x, y) {
  if (!panel) return;
  const L = config.labels;
  const row = table?.cells?.[cell] ?? {};
  const found = revealed(scene, cell) ? places(scene, cell) : null;
  const hex = found?.find((p) => p.hex)?.hex ?? {};
  const [i, j] = cell.split("_");
  const line = (key, value) => (value ? `<p><span class="key">${esc(L[key] ?? key)}</span> ${esc(value)}</p>` : "");
  let html = `<p class="title">${esc(L.hex ?? "Hex")} ${esc(i)}.${esc(j)}</p>`;
  if (!found) {
    html += `<p class="unknown">${esc(L.unknown ?? "Unexplored")}</p>`;
  } else {
    html += line("region", hex.region || row.region) + line("terrain", hex.terrain || row.terrain)
      + line("travel", hex.travel || row.travel) + line("explored", hex.explored);
    const named = found.filter((p) => !p.hex || found.length === 1);
    if (named.length) {
      html += `<ul>${named.map((p) => {
        const eye = game.user.isGM ? `<i class="fa-solid ${p.discovered ? "fa-eye" : "fa-eye-slash"}"></i> ` : "";
        return `<li>${eye}${esc(p.name)}</li>`;
      }).join("")}</ul>`;
    }
  }
  panel.innerHTML = html;
  panel.style.left = `${x + 16}px`;
  panel.style.top = `${y + 16}px`;
  panel.hidden = false;
}

function hide() {
  clearTimeout(timer);
  last = null;
  if (panel) panel.hidden = true;
}

function move(event) {
  const scene = canvas.scene;
  if (!table && !game.journal.some((e) => e.pages.some((p) => p.flags?.ttrpg?.scene === scene?.uuid))) return;
  const point = canvas.canvasCoordinatesFromClient({ x: event.clientX, y: event.clientY });
  const rect = canvas.dimensions.sceneRect;
  if (!rect.contains(point.x, point.y)) return hide();
  const { i, j } = canvas.grid.getOffset(point);
  const cell = `${i}_${j}`;
  if (cell === last) {
    if (panel && !panel.hidden) { panel.style.left = `${event.clientX + 16}px`; panel.style.top = `${event.clientY + 16}px`; }
    return;
  }
  hide();
  last = cell;
  timer = setTimeout(() => render(scene, cell, event.clientX, event.clientY), 300);
}

Hooks.once("setup", () => {
  loading = load("hud.json").then((value) => { config = value ?? config; });
});

Hooks.once("ready", () => {
  panel = document.createElement("section");
  panel.id = "ttrpg-hex-hud";
  panel.hidden = true;
  document.body.append(panel);
});

Hooks.on("canvasReady", async () => {
  hide();
  await loading;
  const scene = canvas.scene;
  table = scene && config.scenes.includes(scene.id) ? await load(`hexes/${scene.id}.json`) : null;
  const view = canvas.app.view;
  view.removeEventListener("pointermove", move);
  view.removeEventListener("pointerleave", hide);
  if (canvas.grid.isHexagonal) {
    view.addEventListener("pointermove", move);
    view.addEventListener("pointerleave", hide);
  }
});
