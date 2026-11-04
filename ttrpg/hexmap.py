"""Place named locations on a region's hex map.

The official map (with its scale) is the reference; PathfinderWiki's community map
(github.com/pf-wikis/mapping, CC BY-NC-SA) knows where hundreds of named places are, but its
distances are not canon. An affine fit on a few towns found on both maps carries every wiki place onto
the official map image; the hex is then Foundry's grid offset `"i_j"` for hex columns (odd columns
shifted down), as `canvas.grid.getOffset` gives it.
"""

import json
import math
import urllib.request
from pathlib import Path

WIKI = "https://raw.githubusercontent.com/pf-wikis/mapping/main/sources/{}.geojson"


def wiki_places(cache):
    """(name, kind, lon, lat, link) of every city and location of the wiki map, cached locally."""
    places = []
    for layer in ("cities", "locations"):
        path = cache / f"{layer}.geojson"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(WIKI.format(layer), timeout=120) as response:
                path.write_bytes(response.read())
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            props, (lon, lat) = feature["properties"], feature["geometry"]["coordinates"][:2]
            kind = "city" if layer == "cities" else props.get("type") or "location"
            places.append((props.get("labels", ""), kind, lon, lat, props.get("link", "")))
    return places


def solve3(m, v):
    """Solve a 3x3 linear system (Cramer)."""
    det = lambda a: (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                     + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    if abs(d) < 1e-12:
        raise ValueError("control points are aligned: give three that form a triangle")
    return [det([[v[r] if c == k else m[r][c] for c in range(3)] for r in range(3)]) / d for k in range(3)]


def fit(pairs):
    """Least-squares affine map (lon, lat) -> (x, y) from [((lon, lat), (x, y))...], three pairs at least."""
    if len(pairs) < 3:
        raise ValueError("give at least three control points")
    rows = [(lon, lat, 1.0) for (lon, lat), _ in pairs]
    normal = [[sum(r[a] * r[b] for r in rows) for b in range(3)] for a in range(3)]
    coef = [solve3(normal, [sum(r[a] * xy[axis] for r, (_, xy) in zip(rows, pairs)) for a in range(3)]) for axis in (0, 1)]
    return lambda lon, lat: tuple(c[0] * lon + c[1] * lat + c[2] for c in coef)


def hex_offset(x, y, size):
    """Foundry offset (row, column) of the hex containing scene point (x, y): hex columns, odd columns
    shifted down, `size` the hex height (grid.size). Hex (i, j) is centred on
    (j * 0.75w + w/2, i * size + (size/2 if j is odd)), w = size * 2/sqrt(3)."""
    w = size * 2 / math.sqrt(3)
    best = None
    j0 = round((x - w / 2) / (0.75 * w))
    for j in range(j0 - 2, j0 + 3):
        cx, shift = j * 0.75 * w + w / 2, size / 2 if j % 2 else 0
        i0 = round((y - shift) / size)
        for i in range(i0 - 2, i0 + 3):
            d = math.hypot(x - cx, y - (i * size + shift))
            if best is None or d < best[0]:
                best = (d, i, j)
    return best[1], best[2]


def place(places, controls, size, origin, image):
    """Wiki places that fall on the image: (name, kind, x, y, "i_j", link), plus the fit's error per control (px)."""
    known = {name: (lon, lat) for name, _, lon, lat, _ in places}
    missing = [name for name in controls if name not in known]
    if missing:
        raise KeyError(", ".join(missing))
    pairs = [(known[name], xy) for name, xy in controls.items()]
    to_image = fit(pairs)
    errors = {name: math.hypot(*(a - b for a, b in zip(to_image(*known[name]), xy))) for name, xy in controls.items()}
    out = []
    for name, kind, lon, lat, link in places:
        x, y = to_image(lon, lat)
        if 0 <= x < image[0] and 0 <= y < image[1]:
            i, j = hex_offset(x + origin[0], y + origin[1], size)
            out.append((name, kind, round(x), round(y), f"{i}_{j}", link))
    return out, errors
