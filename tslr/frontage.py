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

from shapely.geometry import Polygon

from .geometry import CENT, TOL, Piece, tidy
from .optimize_lot import _band, _cuts_equal_land, _fan_why


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
    """
    land: Polygon
    edge: int = 0                # which boundary the road runs along
    road_w: float = 23.0
    n: int = 4

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
        cuts = _cuts_equal_land(self.region, a, u, lo, hi, self.n)
        edges = [lo, *cuts, hi]
        self.lots = [_band(self.region, a, u, edges[i], edges[i + 1])
                     for i in range(self.n)]
        self.cuts = edges
        # The inner edge is the part of the road's own boundary sitting at
        # road_w, gate end first. Taking the region's extent instead overstates
        # it: the region reaches further up than the road does, because the
        # plot's north-east corner lies past the top of the strip.
        ts = [(p[0] - a[0]) * u[0] + (p[1] - a[1]) * u[1]
              for p in self.road.exterior.coords
              if abs(nx * (p[0] - a[0]) + ny * (p[1] - a[1]) - self.road_w) < 0.02]
        off = (a[0] + nx * self.road_w, a[1] + ny * self.road_w)
        self.inner = [(off[0] + u[0] * t, off[1] + u[1] * t)
                      for t in (min(ts), max(ts))]
        self.audit()

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
        out = [Piece(f"Lot {i + 1}", g, _fan_why(tidy(g)), g.area)
               for i, g in enumerate(self.lots)]
        out.append(Piece("Road", self.road, _fan_why(tidy(self.road)), self.road.area))
        return out

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
        lots = sum(g.area for g in self.lots)
        return dict(lots=lots, road=self.road.area, waste=0.0,
                    total=lots + self.road.area, plot=self.land.area)

    def __str__(self):
        lo, hi = self.widths
        t = self.tally()
        return (f"road {self.road_w:.0f} ft along edge {self.edge}, "
                f"{lo:.2f}-{hi:.2f} ft wide, {self.run:.2f} ft long\n"
                f"  road {t['road']:,.0f} ft2 ({t['road'] / t['plot']:.1%})  "
                f"{self.n} lots of {self.lots[0].area:,.0f} ft2 "
                f"({self.lots[0].area / CENT:.2f} cents)\n"
                f"  tally {t['total']:,.1f} of {t['plot']:,.1f} ft2")


def build(key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    """(record, carve, letters) for one survey in `tslr/surveys`."""
    import json
    from pathlib import Path
    rec = json.loads((Path(__file__).parent / "surveys" / f"{key}.json").read_text())
    ft = 1 / 0.3048
    land = Polygon([(x * ft, y * ft) for x, y in rec["corners_m"]])
    f = Frontage(land, edge=rec["road"]["edge"], road_w=road_w, n=n)
    letters = dict(zip(rec["walk"], "ABCDEFGH"))
    return rec, f, letters


def pdf(out, key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    import subprocess
    import tempfile
    from pathlib import Path
    from . import pages
    from .sheet import Paper, Sheet
    rec, f, letters = build(key, road_w, n)
    # the largest standard scale whose drawing still fits the sheet, so a ruler
    # on the print agrees with the figures
    x0, y0, x1, y1 = f.land.bounds
    fit = lambda d: ((x1 - x0) * 0.3048 * 1000 / d <= 246
                     and (y1 - y0) * 0.3048 * 1000 / d <= 150)
    denom = next((d for d in (100, 125, 150, 200, 250, 300, 350, 400, 500) if fit(d)), 500)
    paper = Paper("A4", 297.0, 210.0, denom, 0.78, 32.0)
    out = Path(out)
    with tempfile.TemporaryDirectory() as tmp:
        sheets = [pages.frontage_plan(Sheet(f, paper), rec, f, letters).save(f"{tmp}/a"),
                  pages.frontage_schedule(Sheet(f, paper), rec, f, letters).save(f"{tmp}/b")]
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdfunite", *sheets, str(out)], check=True)
    return out


PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{survey} — road west, {n} equal lots</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0 auto; max-width: 1100px; padding: 22px 20px 60px;
       font: 15px/1.5 -apple-system, Helvetica, Arial, sans-serif; color: #111; }}
h1 {{ font-size: 19px; margin: 0; }}
h2 {{ font-size: 15px; margin: 28px 0 8px; }}
.meta {{ color: #666; font-size: 13px; margin: 4px 0 0; }}
nav a {{ font-size: 13px; color: #0033aa; }}
figure {{ margin: 16px 0 0; border: 1px solid #e2e2e2; border-radius: 4px; }}
figure svg {{ display: block; width: 100%; height: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }}
th, td {{ text-align: left; padding: 5px 8px; border-bottom: 1px solid #eee; }}
th {{ color: #666; font-weight: 600; }}
td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
tfoot td {{ font-weight: 700; border-top: 2px solid #999; border-bottom: none;
           background: #f2f9f2; }}
.why {{ color: #555; font-size: 12px; }}
.note {{ background: #fafafa; border-left: 3px solid #1b5e20; padding: 8px 12px;
        margin: 8px 0; font-size: 13.5px; }}
.note.warn {{ border-left-color: #a00; }}
footer {{ margin-top: 30px; color: #888; font-size: 12px; }}
</style>
<nav><a href="index.html">&larr; TS 11/14/18</a></nav>
<h1>{survey} · {village} · {taluk}</h1>
<p class="meta">Registered {registered_as} = {reg:,.0f} m² = {reg_c:.2f} cents ·
  FMB at 1:{scale}, approved {approved} ·
  common road {road_w:.0f} ft up the west boundary, gate at {gate} ·
  {n} lots of equal area</p>
<figure>{svg}</figure>
<h2>Every piece, and the arithmetic behind it</h2>
<table>
  <thead><tr><th>piece</th><th>frontage on the road</th><th>area = ½ × base × height</th>
    <th class="n">ft²</th><th class="n">cents</th><th class="n">m²</th></tr></thead>
  <tbody>{rows}</tbody>
  <tfoot><tr><td>TALLY</td><td>parts sum to the plot</td><td></td>
    <td class="n">{tot:,.1f}</td><td class="n">{tot_c:.2f}</td>
    <td class="n">{tot_m:,.1f}</td></tr></tfoot>
</table>
{notes}
<footer>Built by <code>python -m tslr.frontage</code>. Every figure on this page is
  derived, and the checks above run on each build.</footer>
"""


def page(out, key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    """A page of its own for this survey, next to the TS 11/14/18 viewer."""
    from pathlib import Path
    from . import pages
    from .sheet import Paper, Sheet
    rec, f, letters = build(key, road_w, n)
    sh = pages.frontage_plan(Sheet(f, Paper("web", 297.0, 210.0, 350, 0.78, 26.0)),
                             rec, f, letters, web=True)
    sh.out.append("</svg>")
    # no scale bar on screen, so the sheet can be cropped to the drawing
    svg = ("\n".join(sh.out)
           .replace('width="297.0mm" height="210.0mm"', "", 1)
           .replace('viewBox="0 0 297.0 210.0"', 'viewBox="0 0 297.0 188"', 1))

    rows = ""
    for p, w in zip(f.pieces(), f.frontages + [None]):
        rows += (f'<tr><td>{p.name}</td><td>'
                 + (f"{w:.2f} ft" if w is not None else
                    f"{f.run:.2f} ft along the boundary, {f.road_w:.2f} ft wide")
                 + f'</td><td class="why">{p.why}</td>'
                 f'<td class="n">{p.area:,.1f}</td>'
                 f'<td class="n">{p.area / CENT:.2f}</td>'
                 f'<td class="n">{p.area * 0.3048 ** 2:.1f}</td></tr>')
    t = f.tally()
    lo, hi = f.widths
    drawn = f.land.area * 0.3048 ** 2
    reg = rec["registered_m2"]
    notes = "".join(f'<p class="note{c}">{s}</p>' for c, s in [
        ("", f"<b>The road holds {lo:.2f} ft at its narrowest.</b> Its inner edge "
             f"runs parallel to the west boundary, so it is {lo:.2f} ft the whole "
             f"{f.run:.2f} ft up from the gate at {letters[rec['walk'][4]]}, "
             f"neither pinching nor splaying."),
        ("", f"<b>Every lot reaches the road.</b> Frontages of "
             f"{', '.join(f'{w:.2f}' for w in f.frontages)} ft add to the "
             f"{math.dist(*f.inner):.2f} ft inner edge, so none of them is landlocked "
             f"and no strip in front has to be shared."),
        ("", f"<b>Nothing is wasted.</b> The {n} lots and the road are the whole "
             f"plot: {t['total']:,.1f} ft² against {t['plot']:,.1f} ft². Road takes "
             f"{t['road'] / t['plot']:.1%}, so each lot keeps "
             f"{f.lots[0].area:,.0f} ft² ({f.lots[0].area / CENT:.2f} cents)."),
        ("", f"<b>The FMB agrees with its own register.</b> The line work encloses "
             f"{drawn:,.1f} m² against a registered {reg:,.0f} m², a gap of "
             f"{drawn - reg:+.1f} m² ({(drawn / reg - 1) * 100:+.2f}%). The corners "
             f"here are read from the PDF's vector geometry at the stated "
             f"1:{rec['scale']}, not measured off the picture."),
        (" warn", f"<b>Still to tape.</b> The north boundary is drawn at "
                  f"{math.dist(*[(x / 0.3048, y / 0.3048) for x, y in rec['corners_m'][:2]]) * 0.3048:.2f} m "
                  f"but written 38.2, and the neighbour chainages above it add to 38.6. "
                  f"Worth one pull of a tape from {letters[rec['walk'][0]]} to "
                  f"{letters[rec['walk'][1]]} before anything is signed."),
    ])
    html = PAGE.format(
        survey=rec["survey"], village=rec["village"], taluk=rec["taluk"],
        registered_as=rec["registered_as"], reg=reg, reg_c=reg / 0.3048 ** 2 / CENT,
        scale=rec["scale"], approved=rec["approved"], road_w=road_w, n=n,
        gate=letters[rec["walk"][4]], svg=svg, rows=rows,
        tot=t["total"], tot_c=t["total"] / CENT, tot_m=t["total"] * 0.3048 ** 2,
        notes=notes)
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
