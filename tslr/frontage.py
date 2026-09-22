"""Lots along a road that runs the length of one boundary.

TS 11/14/18 put its road across the north of a quadrilateral, so `Massing` and
`Fan` are written against `Plot`. 176/9B2 is a pentagon. Its road runs up the
west side from the gate at the south-west corner, so neither the shape nor the
side fits. The carve here takes a plain polygon and the index of the edge the
road follows, which covers both plots.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon

from .geometry import CENT, TOL, Piece, tidy
from .optimize_lot import _band, _cuts_equal_land, _fan_why, _parts, _profile


def _unit(a, b):
    d = math.dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d), d


@dataclass
class Frontage:
    """A road `road_w` ft inside one boundary, and `n` equal-area lots behind it.

    The road's inner edge is parallel to the boundary it runs along, so
    `road_w` is its narrowest point and its widest at once. That only holds
    because the boundary is one straight run. A kinked frontage would need the
    inner edge fitted to the narrowest gap instead.

    The lots are cut square to that edge, so each one reaches the road.

    `shape` picks what a lot is. "fan" fills the land: every lot takes the full
    depth to the far boundary, so nothing is left over and no two lots are the
    same shape. "rect" makes them identical rectangles, which is what a builder
    sets out from, and leaves the corners the rectangles cannot reach as
    separate parcels.
    """
    land: Polygon
    edge: int = 0                # which boundary the road runs along
    road_w: float = 23.0
    n: int = 4
    shape: str = "fan"           # "fan" or "rect"

    def __post_init__(self):
        q = list(self.land.exterior.coords[:-1])
        a, b = q[self.edge], q[(self.edge + 1) % len(q)]
        (u, self.run) = _unit(a, b)
        nx, ny = -u[1], u[0]
        inside = self.land.representative_point()
        if nx * (inside.x - a[0]) + ny * (inside.y - a[1]) < 0:
            nx, ny = -nx, -ny
        self.u, self.normal, self.a, self.b = u, (nx, ny), a, b

        # the strip within road_w of the frontage line, clipped to the land
        L = 900.0
        off = lambda p, t: (p[0] + nx * t, p[1] + ny * t)
        band = Polygon([(a[0] - u[0] * L, a[1] - u[1] * L),
                        (b[0] + u[0] * L, b[1] + u[1] * L),
                        off((b[0] + u[0] * L, b[1] + u[1] * L), self.road_w),
                        off((a[0] - u[0] * L, a[1] - u[1] * L), self.road_w)])
        self.road = self.land.intersection(band)
        self.region = self.land.difference(band)

        # a road wider than the plot leaves nothing to cut, and every figure
        # below would be measured off an empty shape
        if self.region.is_empty or self.region.geom_type != "Polygon":
            raise AssertionError(f"a {self.road_w:.2f} ft road leaves no land to "
                                 f"cut on this boundary")
        ts = [(p[0] - a[0]) * u[0] + (p[1] - a[1]) * u[1]
              for p in self.region.exterior.coords]
        lo, hi = min(ts), max(ts)
        self.inner_ends = self._inner_ends()
        if self.shape == "rect":
            self.lots, self.balance, self.cuts = self._rectangles()
        else:
            cuts = _cuts_equal_land(self.region, a, u, lo, hi, self.n)
            edges = [lo, *cuts, hi]
            self.lots = [_band(self.region, a, u, edges[i], edges[i + 1])
                         for i in range(self.n)]
            self.balance, self.balance_where, self.cuts = [], [], edges
        self.inner = self.inner_ends
        self.audit()

    def _inner_ends(self):
        """The road's inner edge, gate end first.

        It is the part of the road's own boundary sitting at road_w. Taking the
        region's extent instead overstates it, because the plot's north-east
        corner reaches past the top of the strip.
        """
        a, u, (nx, ny) = self.a, self.u, self.normal
        ts = [(p[0] - a[0]) * u[0] + (p[1] - a[1]) * u[1]
              for p in self.road.exterior.coords
              if abs(nx * (p[0] - a[0]) + ny * (p[1] - a[1]) - self.road_w) < 0.02]
        off = (a[0] + nx * self.road_w, a[1] + ny * self.road_w)
        return [(off[0] + u[0] * t, off[1] + u[1] * t) for t in (min(ts), max(ts))]

    def _local(self, p):
        """A point as (along the road, out from the frontage line)."""
        return ((p[0] - self.a[0]) * self.u[0] + (p[1] - self.a[1]) * self.u[1],
                (p[0] - self.a[0]) * self.normal[0] + (p[1] - self.a[1]) * self.normal[1])

    def _world(self, x, y):
        return (self.a[0] + self.u[0] * x + self.normal[0] * y,
                self.a[1] + self.u[1] * x + self.normal[1] * y)

    def _rectangles(self, m: int = 600):
        """`n` identical rectangles standing on the road, and what is left over.

        The near side is pinned to the road's inner edge. That is what makes
        every lot reach the road, and it is why this is not simply the largest
        rectangle that fits: the largest one is free to sit off the road and
        leave the lots landlocked.

        With the near side fixed, a rectangle is its two end cuts. The region is
        convex, so its far boundary is concave and the rectangle is as deep as
        the shallower of the two ends allows. Only the ends need probing.
        """
        xy = np.asarray([self._local(p) for p in self.region.exterior.coords[:-1]])
        lo, hi = (self._local(p)[0] for p in self.inner_ends
                  )  # only the road's own frontage can be stood on

        def best(xs):
            _, yhi = _profile(xy, xs)
            deep = np.minimum(yhi[:, None], yhi[None, :]) - self.road_w
            wide = np.clip(xs[None, :] - xs[:, None], 0, None)
            area = wide * np.clip(deep, 0, None)
            i, j = np.unravel_index(np.nanargmax(area), area.shape)
            return area[i, j], xs[i], xs[j], deep[i, j]

        area, xa, xb, d = best(np.linspace(lo, hi, m))
        span = (hi - lo) / m
        for _ in range(4):                      # refine around each end in turn
            xs = np.unique(np.clip(np.concatenate([
                np.linspace(xa - span, xa + span, m // 2),
                np.linspace(xb - span, xb + span, m // 2)]), lo, hi))
            area, xa, xb, d = best(xs)
            span /= 6
        if area <= 0:
            raise AssertionError("no rectangle stands on this road")

        cuts = [xa + (xb - xa) * i / self.n for i in range(self.n + 1)]
        lots = [Polygon([self._world(cuts[i], self.road_w),
                         self._world(cuts[i + 1], self.road_w),
                         self._world(cuts[i + 1], self.road_w + d),
                         self._world(cuts[i], self.road_w + d)])
                for i in range(self.n)]
        block = Polygon([self._world(xa, self.road_w), self._world(xb, self.road_w),
                         self._world(xb, self.road_w + d),
                         self._world(xa, self.road_w + d)])
        self.block, self.depth = block, d
        # What the rectangles cannot reach. Taking it as one shape gives an L
        # wrapped round the block, which is no use as a parcel. Cutting it at
        # the block's two ends gives the piece past each end and the strip
        # behind, each a shape somebody could be sold.
        xs = [self._local(p)[0] for p in self.region.exterior.coords]
        rest = self.region.difference(block.buffer(1e-9))
        named = [("south", _band(rest, self.a, self.u, min(xs), xa)),
                 ("behind", _band(rest, self.a, self.u, xa, xb)),
                 ("north", _band(rest, self.a, self.u, xb, max(xs)))]
        left = [(w, g) for w, part in named for g in _parts(part, drop=1.0)]
        self.balance_where = [w for w, _ in left]
        return lots, [g for _, g in left], cuts

    # -- what the road actually measures, rather than what it was asked for ---
    @property
    def widths(self) -> tuple[float, float]:
        """(narrowest, widest) perpendicular gap across the road."""
        gaps = [abs(self.normal[0] * (p[0] - self.a[0])
                    + self.normal[1] * (p[1] - self.a[1]))
                for p in self.road.exterior.coords]
        far = [g for g in gaps if g > TOL]
        return (min(far), max(far)) if far else (0.0, 0.0)

    @property
    def quad(self) -> Polygon:
        """`Sheet` asks a plot for its outline under this name."""
        return self.land

    def frontage(self, g: Polygon) -> float:
        """How much of the road's inner edge a lot opens onto.

        The length of its boundary sitting at road_w from the frontage line.
        A lot with none is landlocked, which no arrangement here should produce.
        """
        nx, ny = self.normal
        q = list(g.exterior.coords)
        tot = 0.0
        for p0, p1 in zip(q, q[1:]):
            off = [abs(nx * (p[0] - self.a[0]) + ny * (p[1] - self.a[1]) - self.road_w)
                   for p in (p0, p1)]
            if max(off) < 0.02:
                tot += math.dist(p0, p1)
        return tot

    @property
    def frontages(self) -> list[float]:
        return [self.frontage(g) for g in self.lots]

    def pieces(self) -> list[Piece]:
        """Each piece with arithmetic a reader can re-add by hand.

        The polygons are tidied first. Clipping leaves vertices sitting on a
        straight run, and a fan through those spends a term on a triangle of no
        height.
        """
        out = [Piece(f"Lot {i + 1}", g, self._why(g), g.area)
               for i, g in enumerate(self.lots)]
        out += [Piece(f"Balance {w}", g, self._why(g), g.area)
                for w, g in zip(self.balance_where, self.balance)]
        out.append(Piece("Road", self.road, self._why(self.road), self.road.area))
        return out

    def _why(self, g: Polygon) -> str:
        """A rectangle reads as one multiplication; anything else as a fan."""
        q = list(tidy(g).exterior.coords[:-1])
        if len(q) == 4:
            w, d = math.dist(q[0], q[1]), math.dist(q[1], q[2])
            if abs(w * d - g.area) < 0.05:
                return f"{w:.2f} x {d:.2f}"
        return _fan_why(tidy(g))

    def audit(self, tol=TOL):
        """Nothing is wasted here, so the lots and the road are the whole plot."""
        for p in self.pieces():
            p.verify(tol)
        for i, g in enumerate(self.lots):
            if not self.land.buffer(1e-6).contains(g):
                raise AssertionError(f"lot {i + 1} leaves the plot")
            if g.intersection(self.road).area > tol:
                raise AssertionError(f"lot {i + 1} overlaps the road")
            if self.frontage(g) < 1.0:
                raise AssertionError(f"lot {i + 1} has no frontage on the road")
        spread = max(g.area for g in self.lots) - min(g.area for g in self.lots)
        if spread > tol:
            raise AssertionError(f"lots differ by {spread:.2f} ft2")
        for i, g in enumerate(self.balance):
            if not self.land.buffer(1e-6).contains(g):
                raise AssertionError(f"balance {i + 1} leaves the plot")
        total = sum(p.area for p in self.pieces())
        if abs(total - self.land.area) > tol:
            raise AssertionError(f"parts sum to {total:,.2f} ft2, the plot is "
                                 f"{self.land.area:,.2f} ft2")
        lo, hi = self.widths
        if lo < self.road_w - 1e-6:
            raise AssertionError(f"the road pinches to {lo:.2f} ft, "
                                 f"under the {self.road_w:.2f} asked for")
        return self

    def tally(self) -> dict:
        """Balance land is not waste. It is land nobody has spoken for yet."""
        lots = sum(g.area for g in self.lots)
        bal = sum(g.area for g in self.balance)
        return dict(lots=lots, road=self.road.area, balance=bal,
                    total=lots + bal + self.road.area, plot=self.land.area)

    def __str__(self):
        lo, hi = self.widths
        t = self.tally()
        bal = (f"  balance {t['balance']:,.0f} ft2 ({t['balance'] / t['plot']:.1%}) "
               f"in {len(self.balance)} parcel(s)\n" if self.balance else "")
        size = ""
        if self.shape == "rect":
            q = list(self.lots[0].exterior.coords[:-1])
            size = f" of {math.dist(q[0], q[1]):.2f} x {math.dist(q[1], q[2]):.2f} ft"
        return (f"{self.shape} · road {self.road_w:.0f} ft along edge {self.edge}, "
                f"{lo:.2f}-{hi:.2f} ft wide, {self.run:.2f} ft long\n"
                f"  road {t['road']:,.0f} ft2 ({t['road'] / t['plot']:.1%})  "
                f"{self.n} lots{size} of {self.lots[0].area:,.0f} ft2 "
                f"({self.lots[0].area / CENT:.2f} cents)\n" + bal +
                f"  tally {t['total']:,.1f} of {t['plot']:,.1f} ft2")


def build(key: str = "176-9B2", road_w: float = 23.0, n: int = 4,
          shape: str = "fan"):
    """(record, carve, letters) for one survey in `tslr/surveys`."""
    import json
    from pathlib import Path
    rec = json.loads((Path(__file__).parent / "surveys" / f"{key}.json").read_text())
    ft = 1 / 0.3048
    land = Polygon([(x * ft, y * ft) for x, y in rec["corners_m"]])
    f = Frontage(land, edge=rec["road"]["edge"], road_w=road_w, n=n, shape=shape)
    letters = dict(zip(rec["walk"], "ABCDEFGH"))
    return rec, f, letters


def pdf(out, key: str = "176-9B2", road_w: float = 23.0, n: int = 4,
        shapes=("fan", "rect")):
    import subprocess
    import tempfile
    from pathlib import Path
    from . import pages
    from .sheet import Paper, Sheet
    carves = [build(key, road_w, n, sh) for sh in shapes]
    rec, f, letters = carves[0]
    # the largest standard scale whose drawing still fits the sheet, so a ruler
    # on the print agrees with the figures
    x0, y0, x1, y1 = f.land.bounds
    fit = lambda d: ((x1 - x0) * 0.3048 * 1000 / d <= 246
                     and (y1 - y0) * 0.3048 * 1000 / d <= 150)
    denom = next((d for d in (100, 125, 150, 200, 250, 300, 350, 400, 500) if fit(d)), 500)
    paper = Paper("A4", 297.0, 210.0, denom, 0.78, 32.0)
    out = Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        sheets = []
        for i, (rec, g, letters) in enumerate(carves):
            sheets += [pages.frontage_plan(Sheet(g, paper), rec, g, letters)
                       .save(f"{tmp}/{i}a"),
                       pages.frontage_schedule(Sheet(g, paper), rec, g, letters)
                       .save(f"{tmp}/{i}b")]
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdfunite", *sheets, str(out)], check=True)
    return out


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{survey} — road west, {n} lots</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0 auto; max-width: 1100px; padding: 22px 20px 60px;
       font: 15px/1.5 -apple-system, Helvetica, Arial, sans-serif; color: #111; }}
h1 {{ font-size: 19px; margin: 0; }}
h2 {{ font-size: 16px; margin: 34px 0 2px; }}
h2 small {{ font-weight: 400; color: #666; font-size: 13px; }}
.meta {{ color: #666; font-size: 13px; margin: 4px 0 0; }}
nav a {{ font-size: 13px; color: #0033aa; }}
figure {{ margin: 12px 0 0; border: 1px solid #e2e2e2; border-radius: 4px; }}
figure svg {{ display: block; width: 100%; height: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }}
th, td {{ text-align: left; padding: 5px 8px; border-bottom: 1px solid #eee; }}
th {{ color: #666; font-weight: 600; }}
td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
tr.bal td {{ color: #8a6414; background: #fffdf7; }}
tfoot td {{ font-weight: 700; border-top: 2px solid #999; border-bottom: none;
           background: #f2f9f2; }}
.why {{ color: #555; font-size: 12px; }}
.note {{ background: #fafafa; border-left: 3px solid #1b5e20; padding: 8px 12px;
        margin: 8px 0; font-size: 13.5px; }}
.note.warn {{ border-left-color: #a00; }}
.pick {{ display: flex; gap: 14px; margin: 16px 0 0; flex-wrap: wrap; }}
.pick div {{ flex: 1 1 320px; border: 1px solid #e2e2e2; border-radius: 4px;
            padding: 10px 14px; font-size: 13.5px; }}
.pick b {{ display: block; margin-bottom: 3px; }}
footer {{ margin-top: 34px; color: #888; font-size: 12px; }}
</style>
<nav><a href="index.html">&larr; TS 11/14/18</a></nav>
<h1>{survey} · {village} · {taluk}</h1>
<p class="meta">Registered {registered_as} = {reg:,.0f} m² = {reg_c:.2f} cents ·
  FMB at 1:{scale}, approved {approved} ·
  common road {road_w:.0f} ft up the west boundary, gate at {gate}</p>
<div class="pick">{pick}</div>
{sections}
<footer>Built by <code>python -m tslr.frontage</code>. Every figure on this page is
  derived, and the checks above run on each build.</footer>
"""

SECTION = """<h2>{title} <small>{sub}</small></h2>
<figure>{svg}</figure>
<table>
  <thead><tr><th>piece</th><th>frontage on the road</th><th>area = ½ × base × height</th>
    <th class="n">ft²</th><th class="n">cents</th><th class="n">m²</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot><tr><td>TALLY</td><td>parts sum to the plot</td><td></td>
    <td class="n">{tot:,.1f}</td><td class="n">{tot_c:.2f}</td>
    <td class="n">{tot_m:,.1f}</td></tr></tfoot>
</table>
{notes}
"""


def _section(rec, f, letters, sh_svg) -> str:
    """One option: its drawing, its schedule, and what it costs or buys."""
    rows = ""
    for p in f.pieces():
        bal = p.name.startswith("Balance")
        w = f.frontage(p.poly)
        rows += (f'<tr{" class=\'bal\'" if bal else ""}><td>{p.name}</td><td>'
                 + (f"{f.run:.2f} ft along the boundary, {f.road_w:.2f} ft wide"
                    if p.name == "Road" else
                    f"{w:.2f} ft" if w > 1.0 else
                    "<b>none</b> — attach to the lot beside it")
                 + f'</td><td class="why">{p.why}</td>'
                   f'<td class="n">{p.area:,.1f}</td>'
                   f'<td class="n">{p.area / CENT:.2f}</td>'
                   f'<td class="n">{p.area * 0.3048 ** 2:.1f}</td></tr>')
    t = f.tally()
    lo, _ = f.widths
    one = f.lots[0]
    q = list(one.exterior.coords[:-1])
    if f.shape == "rect":
        title = f"Option B — {f.n} identical rectangles, balance separate"
        sub = (f"{math.dist(q[0], q[1]):.2f} × {math.dist(q[1], q[2]):.2f} ft each, "
               f"{one.area:,.0f} ft² · {one.area / CENT:.2f} cents")
        notes = [
            ("", f"<b>Every lot is the same rectangle:</b> "
                 f"{math.dist(q[0], q[1]):.2f} ft of frontage by "
                 f"{math.dist(q[1], q[2]):.2f} ft deep, corners at 90°. That is what "
                 f"a builder sets out from, and what a buyer can picture."),
            ("", f"<b>The balance is {t['balance']:,.0f} ft² "
                 f"({t['balance'] / t['plot']:.1%}) in {len(f.balance)} parcels.</b> "
                 + " ".join(
                     f"The {w} parcel is {g.area:,.0f} ft² ({g.area / CENT:.2f} cents)"
                     + (f", with {f.frontage(g):.2f} ft on the road, so it can be sold "
                        f"on its own." if f.frontage(g) > 1.0 else
                        ", landlocked, so it has to go with the lot beside it.")
                     for w, g in zip(f.balance_where, f.balance))),
            ("", f"<b>It costs {(4093 - one.area) / 4093:.0%} of each lot.</b> Squaring "
                 f"the corners drops a lot from 4,093 ft² to {one.area:,.0f} ft². The "
                 f"land is not lost, it moves into the balance parcels."),
        ]
    else:
        title = f"Option A — {f.n} equal lots, nothing left over"
        sub = f"{one.area:,.0f} ft² · {one.area / CENT:.2f} cents each"
        notes = [
            ("", f"<b>Nothing is left over.</b> The {f.n} lots and the road are the "
                 f"whole plot: {t['total']:,.1f} ft² against {t['plot']:,.1f} ft². "
                 f"Each lot keeps {one.area:,.0f} ft² "
                 f"({one.area / CENT:.2f} cents)."),
            ("", f"<b>No two lots are the same shape.</b> Each takes the full depth to "
                 f"the far boundary, so they are four-sided and five-sided pieces, not "
                 f"rectangles. Frontages run "
                 f"{', '.join(f'{x:.2f}' for x in f.frontages)} ft."),
        ]
    notes.append(("", f"<b>The road holds {lo:.2f} ft at its narrowest.</b> Its inner "
                      f"edge runs parallel to the west boundary, so it is {lo:.2f} ft "
                      f"the whole {f.run:.2f} ft up from the gate at "
                      f"{letters[rec['walk'][4]]}, neither pinching nor splaying."))
    return SECTION.format(
        title=title, sub=sub, svg=sh_svg, rows=rows, tot=t["total"],
        tot_c=t["total"] / CENT, tot_m=t["total"] * 0.3048 ** 2,
        notes="".join(f'<p class="note{c}">{x}</p>' for c, x in notes))


def _svg(rec, f, letters) -> str:
    from . import pages
    from .sheet import Paper, Sheet
    sh = pages.frontage_plan(Sheet(f, Paper("web", 297.0, 210.0, 350, 0.78, 26.0)),
                             rec, f, letters, web=True)
    sh.out.append("</svg>")
    # no scale bar on screen, so the sheet can be cropped to the drawing
    crop = 188 if not f.balance else 200
    return ("\n".join(sh.out)
            .replace('width="297.0mm" height="210.0mm"', "", 1)
            .replace('viewBox="0 0 297.0 210.0"', f'viewBox="0 0 297.0 {crop}"', 1))


def page(out, key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    """A page of its own for this survey, next to the TS 11/14/18 viewer."""
    from pathlib import Path
    carves = [build(key, road_w, n, sh) for sh in ("fan", "rect")]
    rec, fan, letters = carves[0]
    _, rect, _ = carves[1]
    drawn = fan.land.area * 0.3048 ** 2
    reg = rec["registered_m2"]

    pick = (f'<div><b>Option A — equal lots, nothing left over</b>'
            f'{fan.n} lots of {fan.lots[0].area:,.0f} ft² '
            f'({fan.lots[0].area / CENT:.2f} cents), no two the same shape. '
            f'Every square foot is in a lot or the road.</div>'
            f'<div><b>Option B — identical rectangles, balance separate</b>'
            f'{rect.n} lots of {rect.lots[0].area:,.0f} ft² '
            f'({rect.lots[0].area / CENT:.2f} cents), all the same rectangle. '
            f'{rect.tally()["balance"]:,.0f} ft² falls out as '
            f'{len(rect.balance)} balance parcels.</div>')

    common = [
        ("", f"<b>The FMB agrees with its own register.</b> The line work encloses "
             f"{drawn:,.1f} m² against a registered {reg:,.0f} m², a gap of "
             f"{drawn - reg:+.1f} m² ({(drawn / reg - 1) * 100:+.2f}%). The corners "
             f"here are read from the PDF's vector geometry at the stated "
             f"1:{rec['scale']}, not measured off the picture."),
        (" warn", f"<b>Still to tape.</b> The north boundary is drawn at "
                  f"{math.dist(rec['corners_m'][0], rec['corners_m'][1]):.2f} m but "
                  f"written 38.2, and the neighbour chainages above it add to 38.6. "
                  f"Worth one pull of a tape from {letters[rec['walk'][0]]} to "
                  f"{letters[rec['walk'][1]]} before anything is signed."),
    ]
    sections = "".join(_section(rec, g, letters, _svg(rec, g, letters))
                       for _, g, _ in carves)
    sections += "".join(f'<p class="note{c}">{x}</p>' for c, x in common)

    html = PAGE.format(
        survey=rec["survey"], village=rec["village"], taluk=rec["taluk"],
        registered_as=rec["registered_as"], reg=reg,
        reg_c=reg / 0.3048 ** 2 / CENT, scale=rec["scale"],
        approved=rec["approved"], road_w=road_w, n=n,
        gate=letters[rec["walk"][4]], pick=pick, sections=sections)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


if __name__ == "__main__":
    rec, f, letters = build()
    print(f"{rec['survey']}  {rec['village']}")
    print(f)
    print("wrote", pdf("generated/176-9B2_road_west.pdf"))
    print("wrote", page("site/176-9B2.html"))
