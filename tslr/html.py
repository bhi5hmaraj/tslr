"""Assemble the local interactive viewer.

The page is one self-contained file: `viewer.js` and `viewer.css` are inlined,
so it opens from a `file://` URL with no server and no build step. Editing the
viewer means editing those two files, not a string in here.

Python stays the source of truth. The page receives the four plot corners and a
set of test vectors, and asserts against them on load, so the two can never
quietly disagree.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .geometry import CENT, FT2, Massing, Plot

HERE = Path(__file__).parent
TEMPLATE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{survey} — massing</title>
<style>{css}</style>
<div id="left">
  <header>
    <h1>{survey} · {ward}</h1>
    <div class="meta"><span id="l-closure"></span> <span id="area"></span> ·
      <span id="l-slant"></span> <span id="slant"></span>°</div>
  </header>
  <svg id="plan"></svg>
  <div id="tip" hidden></div>
  <div id="zoom"><button id="zout">−</button><button id="zfit"></button
    ><button id="zin">+</button></div>
</div>
<div id="right">
  <button id="lang"></button>
  <label id="l-bnd"></label>
  <div class="grid">
    <span id="l-north"></span><input id="north" type="number" step="0.01">
    <span id="l-east"></span><input id="east" type="number" step="0.01">
    <span id="l-south"></span><input id="south" type="number" step="0.01">
    <span id="l-west"></span><input id="west" type="number" step="0.01">
    <span id="l-diagonal"></span><input id="diagonal" type="number" step="0.01">
  </div>
  <label for="road" id="l-road"></label>
  <div class="row"><input id="road" type="range" min="6" max="{road_max:.1f}"
      step="0.5" value="20"><span id="roadv"></span></div>
  <label for="lots" id="l-lots"></label>
  <div class="row"><input id="lots" type="range" min="1" max="8" step="1" value="1">
    <span id="lotsv"></span></div>
  <label class="row"><input id="metric" type="checkbox"> <span id="l-metric"></span></label>
  <button id="explain">Explain this construction</button>
  <div id="stepper">
    <div class="row"><button id="prev">‹</button>
      <input id="steps" type="range" min="0" max="8" step="1" value="0">
      <button id="next">›</button><span id="stepno"></span></div>
  </div>
  <div id="sched"></div>
  <div id="check"></div>
  <footer id="l-foot" data-reg="{registered:.0f}"></footer>
</div>
<script>{js}</script>
"""


def _diag_range(plot: Plot):
    """The window a diagonal must fall in for both triangles to close."""
    return (max(abs(plot.south - plot.east), abs(plot.north - plot.west)),
            min(plot.south + plot.east, plot.north + plot.west))


def road_limit(plot: Plot) -> float:
    """The widest road this plot can hold: the rectangle vanishes once the road
    eats the whole depth at the plot's shallow east end."""
    m = Massing(plot, 1.0)                      # any width that certainly builds
    return m.h_east * math.cos(math.radians(m.slant))


def vectors(plot: Plot, step=2.0, lo=10.0):
    """road width -> the five piece areas, for the page to check itself against.

    The range is derived from the plot rather than assumed, so every width here
    is one that builds and nothing is quietly dropped.
    """
    hi = road_limit(plot)
    widths = [lo + i * step for i in range(int((hi - lo) // step) + 1)]
    return {str(w): [round(p.area, 3) for p in Massing(plot, w).pieces] for w in widths}


def build(plot: Plot, out: Path, site: dict | None = None):
    site = site or {}
    # The page derives its own geometry, so it gets the sides rather than the
    # corners: no Python is needed to open, edit or host the result.
    data = {"sides": {"north": plot.north, "east": plot.east, "south": plot.south,
                      "west": plot.west,
                      "diagonal": plot.diagonal or round(plot.diagonals_m["AC"], 4)},
            "vectors": vectors(plot),
            # whether the diagonal was taped on site or inferred; the page says so,
            # because it is the one input the FMB does not record
            "diagTaped": bool((site.get("diagonal_m") or {}).get("measured")),
            "band": (site.get("diagonal_m") or {}).get("predicted_band"),
            "range": [round(x, 2) for x in _diag_range(plot)]}
    html = TEMPLATE.format(
        survey=site.get("survey", "plot"), ward=site.get("ward", ""),
        registered=plot.registered, road_max=road_limit(plot) - 1,
        css=(HERE / "viewer.css").read_text(),
        js=(HERE / "viewer.js").read_text().replace("__SITE__", json.dumps(data)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out
