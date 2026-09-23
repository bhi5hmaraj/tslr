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
from .optimize_lot import (_band, _cuts_equal_land, _fan_why, _parts,
                           _profile, inscribed)


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
    road_w: float = 23.0         # at the far end, and the narrowest it may get
    n: int = 4
    shape: str = "fan"           # "fan" or "rect"
    gate_w: float | None = None  # at the gate end; None keeps it constant
    square_to: int | None = None  # edge the rectangles run parallel to

    def __post_init__(self):
        q = list(self.land.exterior.coords[:-1])
        a, b = q[self.edge], q[(self.edge + 1) % len(q)]
        (u, self.run) = _unit(a, b)
        nx, ny = -u[1], u[0]
        inside = self.land.representative_point()
        if nx * (inside.x - a[0]) + ny * (inside.y - a[1]) < 0:
            nx, ny = -nx, -ny
        self.u, self.normal, self.a, self.b = u, (nx, ny), a, b

        # The strip between the frontage line and a straight inner edge. With
        # gate_w set the two ends differ, so the road tapers: the inner edge is
        # still one straight line, it just is not parallel to the boundary.
        w0 = self.road_w if self.gate_w is None else self.gate_w
        w1 = self.road_w
        for _ in range(8):
            self._strip(w0, w1)
            if self.gate_w is None or self.region.is_empty:
                break
            # The inner edge leaves the plot past the far corner, where the
            # north boundary cuts it, and the perpendicular width there falls
            # short of what was asked for. Open the road until it does not.
            lo, _ = self.widths
            if lo >= self.road_w - 1e-9:
                break
            short = self.road_w - lo
            w1 += short
            # Lots set out parallel to another boundary only lie flush while the
            # inner edge stays square to it, so that edge may be moved but not
            # turned. Opening one end alone turns it, and the search runs away.
            if self.square_to is not None:
                w0 += short
        self.gate_end, self.far_end = w0, w1

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
            self.lots, self.balance, self.cuts = (
                self._angled_rectangles() if self.square_to is not None
                else self._rectangles())
        else:
            cuts = _cuts_equal_land(self.region, a, u, lo, hi, self.n)
            edges = [lo, *cuts, hi]
            self.lots = [_band(self.region, a, u, edges[i], edges[i + 1])
                         for i in range(self.n)]
            self.balance, self.balance_where, self.cuts = [], [], edges
        self.inner = self.inner_ends
        self.audit()

    def _strip(self, w0: float, w1: float):
        """Lay the road with these two widths, and keep what it leaves."""
        a, b, u, (nx, ny), L = self.a, self.b, self.u, self.normal, 900.0
        q0 = (a[0] + nx * w0, a[1] + ny * w0)          # inner edge at the gate
        q1 = (b[0] + nx * w1, b[1] + ny * w1)          # and at the far end
        (iu, _) = _unit(q0, q1)
        # everything on the boundary's side of the inner edge, as a rectangle
        # standing on that line. Joining the two edges into a quad instead makes
        # a bowtie once they are extended far enough to cross, and a tapered
        # road's edges always cross somewhere.
        side = (-iu[1], iu[0])
        if side[0] * (a[0] - q0[0]) + side[1] * (a[1] - q0[1]) < 0:
            side = (-side[0], -side[1])
        band = Polygon([(q0[0] - iu[0] * L, q0[1] - iu[1] * L),
                        (q1[0] + iu[0] * L, q1[1] + iu[1] * L),
                        (q1[0] + iu[0] * L + side[0] * L, q1[1] + iu[1] * L + side[1] * L),
                        (q0[0] - iu[0] * L + side[0] * L, q0[1] - iu[1] * L + side[1] * L)])
        self.q0, self.q1, self.iu = q0, q1, iu
        self.road = self.land.intersection(band)
        self.region = self.land.difference(band)

    def _on_inner(self, p) -> bool:
        """Is this point on the road's inner edge?

        Measured against that edge's own line. A tapered road's inner edge is
        not a constant offset from the boundary, so offset cannot answer it.
        """
        return abs(-self.iu[1] * (p[0] - self.q0[0])
                   + self.iu[0] * (p[1] - self.q0[1])) < 0.02

    def _inner_ends(self):
        """The road's inner edge, gate end first.

        It is the part of the road's own boundary lying on that edge. Taking
        the region's extent instead overstates it, because the plot's
        north-east corner reaches past the top of the strip.
        """
        ts = [(p[0] - self.q0[0]) * self.iu[0] + (p[1] - self.q0[1]) * self.iu[1]
              for p in self.road.exterior.coords if self._on_inner(p)]
        if not ts:
            raise AssertionError("the road has no inner edge inside the plot")
        return [(self.q0[0] + self.iu[0] * t, self.q0[1] + self.iu[1] * t)
                for t in (min(ts), max(ts))]

    def recorded(self, a, b, tol=0.05) -> bool:
        """Is this segment one of the boundaries the FMB writes a figure against?

        A sheet mixes two kinds of number. The four boundary lengths are the
        survey's own, and everything else follows from choosing a road width
        and a lot count. Only the first kind can be checked against the record.
        """
        q = list(self.land.exterior.coords[:-1])
        for i in range(len(q)):
            c, d = q[i], q[(i + 1) % len(q)]
            if ((math.dist(a, c) < tol and math.dist(b, d) < tol)
                    or (math.dist(a, d) < tol and math.dist(b, c) < tol)):
                return True
        return False

    def to_road(self, p) -> float:
        """How far a point stands back from the road's inner edge, square to it."""
        return abs(-self.iu[1] * (p[0] - self.q0[0])
                   + self.iu[0] * (p[1] - self.q0[1]))

    @property
    def setback(self):
        """Where the block stands off the road, as (near end, far end) in feet.

        Zero at both ends means the lots sit flush. Lots set out parallel to
        another boundary lean away from a road that is not square to it, and
        the wedge this leaves is what makes them landlocked.
        """
        if self.shape != "rect" or self.square_to is None:
            return (0.0, 0.0)
        q = list(self.block.exterior.coords[:-1])
        return (self.to_road(q[0]), self.to_road(q[3]))

    def _local(self, p):
        """A point as (along the road, out from the frontage line)."""
        return ((p[0] - self.a[0]) * self.u[0] + (p[1] - self.a[1]) * self.u[1],
                (p[0] - self.a[0]) * self.normal[0] + (p[1] - self.a[1]) * self.normal[1])

    def _world(self, x, y):
        return (self.a[0] + self.u[0] * x + self.normal[0] * y,
                self.a[1] + self.u[1] * x + self.normal[1] * y)

    def _angled_rectangles(self):
        """`n` rectangles set out parallel to another boundary.

        Pinning the near side to the road is no longer possible: a rectangle
        can only lie flush against a line it is parallel to. So this takes the
        largest rectangle at the asked-for bearing and slices it, and whatever
        sits between it and the road falls out as balance. How much that is
        depends on the angle between the two, which the road's taper controls.
        """
        q = list(self.land.exterior.coords[:-1])
        e0, e1 = q[self.square_to], q[(self.square_to + 1) % len(q)]
        theta = math.degrees(math.atan2(e1[1] - e0[1], e1[0] - e0[0]))
        area, box = inscribed(self.region, theta)
        if area <= 0:
            raise AssertionError(f"no rectangle at {theta:.2f} deg fits the land")
        self.block, self.lot_angle = Polygon(box), theta

        # box comes back as (xa,y0), (xb,y0), (xb,y1), (xa,y1) in that frame, so
        # slicing between the first and last edge stacks the lots along the road
        w = [((box[3][0] - box[0][0]) * i / self.n,
              (box[3][1] - box[0][1]) * i / self.n) for i in range(self.n + 1)]
        lots = [Polygon([(box[0][0] + w[i][0], box[0][1] + w[i][1]),
                         (box[1][0] + w[i][0], box[1][1] + w[i][1]),
                         (box[1][0] + w[i + 1][0], box[1][1] + w[i + 1][1]),
                         (box[0][0] + w[i + 1][0], box[0][1] + w[i + 1][1])])
                for i in range(self.n)]
        self.depth = math.dist(box[0], box[1])
        rest = self.region.difference(self.block.buffer(1e-9))
        # named by which side of the block they fall on, in the block's own frame
        (bu, _) = _unit(box[0], box[1])
        xs = [(p[0] - box[0][0]) * bu[0] + (p[1] - box[0][1]) * bu[1]
              for p in self.region.exterior.coords]
        named = [("road side", _band(rest, box[0], bu, min(xs), 0.0)),
                 ("far side", _band(rest, box[0], bu, self.depth, max(xs)))]
        mid = _band(rest, box[0], bu, 0.0, self.depth)
        (nu, _) = _unit(box[0], box[3])
        ys = [(p[0] - box[0][0]) * nu[0] + (p[1] - box[0][1]) * nu[1]
              for p in self.region.exterior.coords]
        named += [("south", _band(mid, box[0], nu, min(ys), 0.0)),
                  ("north", _band(mid, box[0], nu, math.dist(box[0], box[3]), max(ys)))]
        left = [(w, g) for w, part in named for g in _parts(part, drop=0.02)]
        self.balance_where = [w for w, _ in left]
        return lots, [g for _, g in left], [0.0]

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
        left = [(w, g) for w, part in named for g in _parts(part, drop=0.02)]
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
        q = list(g.exterior.coords)
        return sum(math.dist(p0, p1) for p0, p1 in zip(q, q[1:])
                   if self._on_inner(p0) and self._on_inner(p1))

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

    def sides_of(self, g) -> str:
        """A piece's edges, with a star on any that is a recorded boundary."""
        q = list(tidy(g).exterior.coords[:-1])
        out = []
        for i in range(len(q)):
            a, b = q[i], q[(i + 1) % len(q)]
            if math.dist(a, b) < 0.5:
                continue
            out.append(f"{math.dist(a, b):.2f}" + ("*" if self.recorded(a, b) else ""))
        return " / ".join(out)

    def rows(self) -> list[tuple]:
        """Every piece as the schedule prints it: name, access, working, areas.

        The sheet and the page both print this table. While each built its own
        the two drifted, and the sheet's zip ran out at the fourth lot, so it
        dropped the balance parcels and the road and still printed a tally.
        """
        out = []
        for p in self.pieces():
            if p.name == "Road":
                how = (f"{self.run:.2f} ft long, "
                       + (f"{self.gate_end:.2f} to {self.far_end:.2f} ft"
                          if self.gate_w is not None else f"{self.road_w:.2f} ft wide"))
            else:
                w = self.frontage(p.poly)
                how = (f"{w:.2f} ft on the road" if w > 1.0
                       else "none — landlocked")
            out.append((p.name, how, p.why, p.area, p.area / CENT,
                        p.area * 0.3048 ** 2, self.sides_of(p.poly)))
        return out

    def audit(self, tol=0.05):
        """Every piece counted, and the pieces are the whole plot.

        Tighter than the package tolerance on purpose. A carve that quietly
        drops a sliver still looks right at a loose one, and the tally is the
        only thing on these sheets that cannot be checked by eye.
        """
        for p in self.pieces():
            p.verify(tol)
        for i, g in enumerate(self.lots):
            if not self.land.buffer(1e-6).contains(g):
                raise AssertionError(f"lot {i + 1} leaves the plot")
            if g.intersection(self.road).area > tol:
                raise AssertionError(f"lot {i + 1} overlaps the road")
            if self.square_to is None and self.frontage(g) < 1.0:
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


def flush_gate(land: Polygon, edge: int, square_to: int, far_w: float) -> float:
    """The gate width that squares the road's inner edge to another boundary.

    A rectangle lies flush only against a line it is parallel to. So lots set
    out parallel to `square_to` reach the road along their whole side only when
    the inner edge is square to that boundary, and that fixes the gate width
    once the far end is chosen. Anything else leaves a strip between the two.
    """
    q = list(land.exterior.coords[:-1])
    a, b = q[edge], q[(edge + 1) % len(q)]
    e0, e1 = q[square_to], q[(square_to + 1) % len(q)]
    d = (b[0] - a[0], b[1] - a[1])
    (u, _) = _unit(a, b)
    n = (-u[1], u[0])
    # against a point inside the plot. Testing against a corner of the road's
    # own edge gives a dot product of zero, so the normal never gets turned.
    inside = land.representative_point()
    if n[0] * (inside.x - a[0]) + n[1] * (inside.y - a[1]) < 0:
        n = (-n[0], -n[1])
    t = (e1[0] - e0[0], e1[1] - e0[1])
    den = n[0] * t[0] + n[1] * t[1]
    if abs(den) < 1e-9:
        raise AssertionError("that boundary is parallel to the road")
    return far_w + (d[0] * t[0] + d[1] * t[1]) / den


def options(key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    """Every way of carving this plot that is worth putting on paper."""
    rec, _, _ = build(key, road_w, n)
    land = Polygon([(x / 0.3048, y / 0.3048) for x, y in rec["corners_m"]])
    gate = round(flush_gate(land, rec["road"]["edge"], 0, road_w), 2)
    return [dict(tag="C", shape="rect", gate_w=31.0, square_to=0, chosen=True),
            dict(tag="D", shape="rect", gate_w=gate, square_to=0),
            dict(tag="A", shape="fan"),
            dict(tag="B", shape="rect")]


def build(key: str = "176-9B2", road_w: float = 23.0, n: int = 4,
          shape: str = "fan", gate_w: float | None = None,
          square_to: int | None = None, tag: str = "", chosen: bool = False):
    """(record, carve, letters) for one survey in `tslr/surveys`."""
    import json
    from pathlib import Path
    rec = json.loads((Path(__file__).parent / "surveys" / f"{key}.json").read_text())
    ft = 1 / 0.3048
    land = Polygon([(x * ft, y * ft) for x, y in rec["corners_m"]])
    f = Frontage(land, edge=rec["road"]["edge"], road_w=road_w, n=n, shape=shape,
                 gate_w=gate_w, square_to=square_to)
    f.tag, f.chosen = tag, chosen
    letters = dict(zip(rec["walk"], "ABCDEFGH"))
    return rec, f, letters


def pdf(out, key: str = "176-9B2", road_w: float = 23.0, n: int = 4):
    import subprocess
    import tempfile
    from pathlib import Path
    from . import pages
    from .sheet import Paper, Sheet
    carves = [build(key, road_w, n, **o) for o in options(key, road_w, n)]
    rec, f, letters = carves[0]
    # the largest standard scale whose drawing still fits the sheet, so a ruler
    # on the print agrees with the figures
    x0, y0, x1, y1 = f.land.bounds
    # This plot is taller than it is wide, so on a landscape sheet the height
    # binds and a column of the width goes spare. The legend lives in that
    # column, which is why the width budget below is the narrower one.
    fit = lambda d: ((x1 - x0) * 0.3048 * 1000 / d <= 168
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
.rec {{ color: #1b5e20; font-weight: 700; }}
.key {{ color: #666; font-size: 12.5px; margin: 10px 0 0; }}
/* hover a piece on the drawing or its row: both light up, and a tip follows */
svg .hit {{ fill: transparent; cursor: pointer; }}
svg .lit {{ stroke: #c62828 !important; stroke-width: 1.4 !important; }}
svg path.lit {{ fill: #ffe9e9 !important; }}
tr.lit td {{ background: #ffe9e9 !important; }}
#tip {{ position: fixed; z-index: 9; pointer-events: none; display: none;
       background: #111; color: #fff; padding: 6px 9px; border-radius: 4px;
       font-size: 12px; line-height: 1.45; max-width: 260px; }}
#tip b {{ display: block; }}
.note {{ background: #fafafa; border-left: 3px solid #1b5e20; padding: 8px 12px;
        margin: 8px 0; font-size: 13.5px; }}
.note.warn {{ border-left-color: #a00; }}
.pick {{ display: flex; gap: 14px; margin: 16px 0 0; flex-wrap: wrap; }}
.pick div {{ flex: 1 1 320px; border: 1px solid #e2e2e2; border-radius: 4px;
            padding: 10px 14px; font-size: 13.5px; }}
.pick b {{ display: block; margin-bottom: 3px; }}
.pick div.on {{ border-color: #1b5e20; border-width: 2px; background: #f4faf4; }}
.pick div.on b::after {{ content: " — CHOSEN"; color: #1b5e20; }}
h2.on {{ border-left: 4px solid #1b5e20; padding-left: 9px; }}
h2.off {{ color: #888; }}
h2.off + figure, h2.off + figure + table, h2.off ~ .note {{ opacity: .72; }}
footer {{ margin-top: 34px; color: #888; font-size: 12px; }}
</style>
<nav><a href="index.html">&larr; TS 11/14/18</a></nav>
<h1>{survey} · {village} · {taluk}</h1>
<p class="meta">Registered {registered_as} = {reg:,.0f} m² = {reg_c:.2f} cents ·
  FMB at 1:{scale}, approved {approved} ·
  common road {road_w:.0f} ft up the west boundary, gate at {gate}</p>
<div class="pick">{pick}</div>
<p class="key"><span class="rec">*</span> marks a figure the FMB records. Every
  other number on this page is derived from those, the road width and the lot
  count, so it moves if either of those changes.</p>
{sections}
<div id="tip"></div>
<script>
// The drawing and the schedule are the same pieces twice, so hovering either
// lights both. Pieces are matched by a data-piece stamped on the shape and on
// the row; nothing else on the page is interactive.
const tip = document.getElementById("tip");
function lite(key, on, ev) {{
  for (const el of document.querySelectorAll(`[data-piece="${{key}}"]`))
    el.closest("tr") ? el.closest("tr").classList.toggle("lit", on)
                     : el.classList.toggle("lit", on);
  if (!on) {{ tip.style.display = "none"; return; }}
  const row = document.querySelector(`tr[data-piece="${{key}}"]`);
  if (!row) return;
  const c = row.cells;
  tip.innerHTML = `<b>${{c[0].textContent}}</b>${{c[3].textContent}} ft&sup2; ·
    ${{c[4].textContent}} cents · ${{c[5].textContent}} m&sup2;<br>${{c[2].textContent}}
    <br>sides ${{row.dataset.sides}}<br>${{c[1].textContent}}`;
  tip.style.display = "block";
  move(ev);
}}
function move(ev) {{
  if (!ev || tip.style.display === "none") return;
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(ev.clientX + pad, innerWidth - w - 8) + "px";
  tip.style.top = Math.max(8, Math.min(ev.clientY + pad, innerHeight - h - 8)) + "px";
}}
for (const el of document.querySelectorAll("[data-piece]")) {{
  const key = el.dataset.piece;
  el.addEventListener("mouseenter", e => lite(key, true, e));
  el.addEventListener("mousemove", move);
  el.addEventListener("mouseleave", () => lite(key, false));
}}
</script>
<footer>Built by <code>python -m tslr.frontage</code>. Every figure on this page is
  derived, and the checks above run on each build.</footer>
"""

SECTION = """<h2 class="{cls}">{title} <small>{sub}</small></h2>
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
    for name, how, why, ft2, c, m2, sides in f.rows():
        bal = name.startswith("Balance")
        key = f"{f.tag}-{name}".replace(" ", "_")
        rows += (f'<tr data-piece="{key}" data-sides="{sides}"'
                 f'{" class=\'bal\'" if bal else ""}>'
                 f'<td>{name}</td>'
                 f'<td>{how.replace("none —", "<b>none</b> —")}</td>'
                 f'<td class="why">{why}</td><td class="n">{ft2:,.1f}</td>'
                 f'<td class="n">{c:.2f}</td><td class="n">{m2:.1f}</td></tr>')
    t = f.tally()
    lo, _ = f.widths
    one = f.lots[0]
    q = list(one.exterior.coords[:-1])
    tag = getattr(f, "tag", "")
    if f.square_to is not None:
        flush = f.frontage(f.lots[0]) > 1.0
        title = (f"Option {tag} — {f.n} rectangles parallel to AB, "
                 + ("flush on the road" if flush else "as asked, 31 ft at the gate"))
        sub = (f"{math.dist(q[0], q[1]):.2f} × {math.dist(q[1], q[2]):.2f} ft each, "
               f"{one.area:,.0f} ft² · {one.area / CENT:.2f} cents · road "
               f"{f.gate_end:.2f} ft at the gate to {f.far_end:.2f} ft")
        notes = [
            ("", f"<b>The lots run parallel to AB,</b> the north boundary, not "
                 f"square to the road. Each is {math.dist(q[0], q[1]):.2f} by "
                 f"{math.dist(q[1], q[2]):.2f} ft, {one.area:,.0f} ft² "
                 f"({one.area / CENT:.2f} cents)."),
            (("" if flush else " warn"),
             (f"<b>Every lot reaches the road along its whole side,</b> "
              f"{f.frontage(one):.2f} ft of it. That works because the road's inner "
              f"edge is square to AB, which is what a {f.gate_end:.2f} ft gate buys: "
              f"a rectangle lies flush only against a line it is parallel to."
              if flush else
              f"<b>No lot reaches the road.</b> A "
              f"{f.balance[f.balance_where.index('road side')].area:,.0f} ft² strip "
              f"runs between the block and the road, because at {f.gate_end:.2f} ft "
              f"the inner edge is not square to AB and a rectangle cannot lie flush "
              f"against it. The strip has to join the road or the lots before this "
              f"can be sold.")),
            ("", f"<b>The balance is {t['balance']:,.0f} ft² "
                 f"({t['balance'] / t['plot']:.1%}) in {len(f.balance)} parcels:</b> "
                 + ", ".join(f"{w} {g.area:,.0f} ft²"
                             for w, g in zip(f.balance_where, f.balance)) + "."),
        ]
    elif f.shape == "rect":
        title = f"Option {tag} — {f.n} identical rectangles, balance separate"
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
        title = f"Option {tag} — {f.n} equal lots, nothing left over"
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
    _, hi = f.widths
    notes.append(("", f"<b>The road holds {lo:.2f} ft at its narrowest.</b> "
                      + (f"It is set out {f.gate_end:.2f} ft at the gate and "
                         f"{f.far_end:.2f} ft at the top, so it opens to {hi:.2f} ft "
                         f"where a car has to turn in."
                         if f.gate_w is not None else
                         f"Its inner edge runs parallel to the west boundary, so it is "
                         f"{lo:.2f} ft the whole {f.run:.2f} ft up from the gate at "
                         f"{letters[rec['walk'][4]]}, neither pinching nor splaying.")))
    return SECTION.format(
        cls="on" if getattr(f, "chosen", False) else "off",
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
    carves = [build(key, road_w, n, **o) for o in options(key, road_w, n)]
    rec, fan, letters = carves[0]
    _, rect, _ = carves[1]
    drawn = fan.land.area * 0.3048 ** 2
    reg = rec["registered_m2"]

    pick = ""
    for _, g, _ in carves:
        one = g.lots[0]
        q = list(one.exterior.coords[:-1])
        size = (f"{math.dist(q[0], q[1]):.2f} × {math.dist(q[1], q[2]):.2f} ft, "
                if g.shape == "rect" else "")
        road = (f"road {g.gate_end:.0f}→{g.far_end:.0f} ft"
                if g.gate_w is not None else f"road {g.road_w:.0f} ft")
        pick += (f'<div class="{"on" if g.chosen else ""}"><b>Option {g.tag}</b>'
                 f'{g.n} lots, {size}{one.area:,.0f} ft² '
                 f'({one.area / CENT:.2f} cents) · {road} · '
                 + (f'frontage {g.frontage(one):.2f} ft each'
                    if g.frontage(one) > 1.0 else
                    f'<span style="color:#a00">no frontage, '
                    f'{max(g.setback):.2f} ft off the road</span>')
                 + (f' · balance {g.tally()["balance"]:,.0f} ft²'
                    if g.balance else " · nothing left over") + '</div>')

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
