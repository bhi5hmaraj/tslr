"""Where do identical lots fit best, once a real road is reserved?

The v8 overlay laid three identical 63.6 x 75.0 ft lots on this plot. It got far
more sellable land than our massing does. That is worth answering properly
rather than assuming our own construction is tight.

Identical lots in a single row are one rectangle cut into equal columns. So the
best layout for n identical lots is just the largest rectangle that fits, which
is what `best_block` solves. It searches every orientation, not only the one
square to the south boundary that `Massing` assumes.

The road is reserved first. Its width is constant, measured perpendicular to
the north boundary, and it runs the full length of that boundary. So every
answer here is one you can drive to. `frontage` says how much of the block
touches the road. A block that wins on area but fronts nothing is not a layout.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Polygon

from .geometry import CENT, TOL, Massing, Piece, Plot


def buildable(plot: Plot, road_w: float, head: float = 0.0) -> tuple[Polygon, LineString]:
    """(land left after the road, the frontage lots can open onto).

    The plot and the road strip are both convex. The strip is cut by one
    straight line, so what is left is a convex quadrilateral A-B-E-F. Every
    routine below relies on that convexity.

    `head` reserves a turning head at the dead end: a right triangle whose one
    leg runs `head` feet back along the road from E, then square down to the
    east boundary. Cutting a corner off a convex shape leaves it convex.
    """
    m = Massing(plot, road_w)
    A, B, _, _ = plot.corners
    if head <= 0:
        return Polygon([A, B, m.E, m.F]), LineString([m.F, m.E])
    W, V = head_ends(plot, road_w, head)
    return Polygon([A, B, V, W, m.F]), LineString([m.F, W])


def head_ends(plot: Plot, road_w: float, head: float):
    """Where a turning head of that length starts on the road, and lands on BE."""
    m = Massing(plot, road_w)
    _, B, _, _ = plot.corners
    d = math.dist(m.E, m.F)
    u = ((m.F[0] - m.E[0]) / d, (m.F[1] - m.E[1]) / d)
    if head > (B[0] - m.E[0]) * u[0] + (B[1] - m.E[1]) * u[1]:
        raise AssertionError(f"a {head:.2f} ft head drops west of B and misses the "
                             f"east boundary")
    W = (m.E[0] + u[0] * head, m.E[1] + u[1] * head)
    n = (-u[1], u[0])
    # W + t*n meets the line B-E
    ex, ey = m.E[0] - B[0], m.E[1] - B[1]
    den = n[0] * ey - n[1] * ex
    t = ((B[0] - W[0]) * ey - (B[1] - W[1]) * ex) / den
    return W, (W[0] + n[0] * t, W[1] + n[1] * t)


def head_limit(plot: Plot, road_w: float) -> float:
    """The longest head whose perpendicular still lands on the east boundary."""
    m = Massing(plot, road_w)
    _, B, _, _ = plot.corners
    d = math.dist(m.E, m.F)
    return ((B[0] - m.E[0]) * (m.F[0] - m.E[0]) + (B[1] - m.E[1]) * (m.F[1] - m.E[1])) / d


def _profile(xy: np.ndarray, xs: np.ndarray):
    """Lower and upper boundary of a convex polygon at each x in `xs`."""
    p, q = xy, np.roll(xy, -1, axis=0)
    x0, x1 = p[:, 0, None], q[:, 0, None]
    on = (xs >= np.minimum(x0, x1) - 1e-9) & (xs <= np.maximum(x0, x1) + 1e-9)
    vert = np.abs(x1 - x0) < 1e-12
    dx = np.where(vert, np.inf, x1 - x0)
    y = p[:, 1, None] + (q[:, 1, None] - p[:, 1, None]) * (xs - x0) / dx
    y = np.where(on & np.isfinite(y), y, np.nan)
    # a vertical edge stands over a single x, so it offers both of its endpoints
    ylo = np.where(on & vert, np.minimum(p[:, 1, None], q[:, 1, None]), np.nan)
    yhi = np.where(on & vert, np.maximum(p[:, 1, None], q[:, 1, None]), np.nan)
    with np.errstate(all="ignore"):
        return (np.nanmin(np.concatenate([y, ylo]), axis=0),
                np.nanmax(np.concatenate([y, yhi]), axis=0))


def _best_on(xy: np.ndarray, xs: np.ndarray):
    """Best (area, xa, xb, ybot, ytop) over the sampled cuts `xs`."""
    ylo, yhi = _profile(xy, xs)
    top = np.minimum(yhi[:, None], yhi[None, :])
    bot = np.maximum(ylo[:, None], ylo[None, :])
    a = np.clip(xs[None, :] - xs[:, None], 0, None) * np.clip(top - bot, 0, None)
    i, j = np.unravel_index(np.nanargmax(a), a.shape)
    return a[i, j], xs[i], xs[j], bot[i, j], top[i, j]


def inscribed(region: Polygon, theta: float, m: int = 220, rounds: int = 4):
    """Largest rectangle with edges at `theta` degrees inside a convex region.

    In a convex region the lower boundary is convex and the upper is concave. A
    rectangle spanning [xa, xb] is therefore as tall as the tighter of its two
    ends allows, so only the two ends need probing. The search is then 2-D over
    (xa, xb): coarse across the whole width, then refined around the winner.
    """
    t = math.radians(theta)
    c, s = math.cos(-t), math.sin(-t)
    pts = np.asarray(region.exterior.coords[:-1])
    xy = np.column_stack([pts[:, 0] * c - pts[:, 1] * s, pts[:, 0] * s + pts[:, 1] * c])
    lo, hi = xy[:, 0].min(), xy[:, 0].max()
    area, xa, xb, y0, y1 = _best_on(xy, np.linspace(lo, hi, m))
    span = (hi - lo) / m
    for _ in range(rounds):
        xs = np.unique(np.concatenate([np.linspace(xa - span, xa + span, m // 2),
                                       np.linspace(xb - span, xb + span, m // 2)]))
        xs = xs[(xs >= lo) & (xs <= hi)]
        area, xa, xb, y0, y1 = _best_on(xy, xs)
        span /= 6
    c, s = math.cos(t), math.sin(t)
    return area, [(x * c - y * s, x * s + y * c)
                  for x, y in [(xa, y0), (xb, y0), (xb, y1), (xa, y1)]]


@dataclass
class Block:
    """One rectangle of land, split into `n` identical lots."""
    plot: Plot
    road_w: float
    corners: list
    theta: float
    n: int

    def __post_init__(self):
        a, b, c, d = self.corners
        self.rect = Polygon(self.corners)
        self.width, self.depth = math.dist(a, b), math.dist(b, c)
        self.lots = [Polygon([_lerp(a, b, i / self.n), _lerp(a, b, (i + 1) / self.n),
                              _lerp(d, c, (i + 1) / self.n), _lerp(d, c, i / self.n)])
                     for i in range(self.n)]
        region, inner = buildable(self.plot, self.road_w)
        self.road = self.plot.quad.difference(region)
        self.offcuts = _parts(region.difference(self.rect))
        self.frontage = self.rect.exterior.intersection(inner.buffer(0.05)).length
        self.audit()

    @property
    def lot_area(self) -> float:
        return self.rect.area / self.n

    @property
    def lot_size(self) -> tuple[float, float]:
        return self.width / self.n, self.depth

    def pieces(self) -> list[Piece]:
        w, d = self.lot_size
        out = [Piece(f"Lot {i + 1}", g, f"{w:.2f} x {d:.2f}", w * d)
               for i, g in enumerate(self.lots)]
        out.append(Piece("Road", self.road,
                         f"{self.road_w:.2f} ft perpendicular, full north boundary",
                         self.road.area))
        out += [Piece(f"Offcut {i + 1}", g, "leftover, by subtraction", g.area)
                for i, g in enumerate(self.offcuts)]
        return out

    def audit(self, tol=TOL):
        """The parts must add back to the whole, and stay inside it."""
        region, _ = buildable(self.plot, self.road_w)
        spill = self.rect.difference(region.buffer(1e-6)).area
        if spill > tol:
            raise AssertionError(f"the block leaves the buildable land by {spill:.2f} ft2")
        for p in self.pieces():
            p.verify(tol)
        total = sum(p.area for p in self.pieces())
        if abs(total - self.plot.area_ft2) > tol:
            raise AssertionError(f"parts sum to {total:,.2f} ft2 but the plot is "
                                 f"{self.plot.area_ft2:,.2f} ft2")
        return self

    def tally(self) -> dict:
        waste = sum(g.area for g in self.offcuts)
        return dict(lots=self.rect.area, road=self.road.area, waste=waste,
                    total=self.rect.area + self.road.area + waste,
                    plot=self.plot.area_ft2)

    def __str__(self):
        w, d = self.lot_size
        t = self.tally()
        return (f"{self.n} x {w:.2f} x {d:.2f} ft = {self.lot_area:,.0f} ft2 "
                f"({self.lot_area / CENT:.2f} cents) each, turned {self.theta:+.2f} deg, "
                f"{t['lots'] / t['plot']:.1%} of the plot, {self.frontage:.0f} ft on the road")


def _score(region, inner, theta, min_frontage):
    area, box = inscribed(region, theta)
    if min_frontage:
        front = Polygon(box).exterior.intersection(inner.buffer(0.05)).length
        if front < min_frontage:
            return -1.0, box
    return area, box


def best_block(plot: Plot, road_w: float = 20.0, n: int = 3,
               coarse: float = 1.0, min_frontage: float = 0.0) -> Block:
    """The largest block of `n` identical lots, over every orientation.

    `min_frontage` rejects orientations whose block barely touches the road. A
    block can always gain area by turning away from the road. Nobody can build
    on the result.
    """
    region, inner = buildable(plot, road_w)
    grid = [round(-90 + i * coarse, 6) for i in range(int(180 / coarse))]
    best = max((_score(region, inner, th, min_frontage)[0], th) for th in grid)
    for step in (coarse / 4, coarse / 20, coarse / 100):
        near = [best[1] + k * step for k in (-2, -1, 1, 2)]
        best = max(max((_score(region, inner, th, min_frontage)[0], th) for th in near), best)
    return Block(plot, road_w, _score(region, inner, best[1], min_frontage)[1], best[1], n)


def _lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def _parts(geom, drop=0.5):
    """Leftovers, largest first, ignoring slivers thrown up by float noise."""
    gs = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    return sorted((g for g in gs if g.area > drop), key=lambda g: -g.area)


def _band(region: Polygon, a, u, t0, t1) -> Polygon:
    """The slice of `region` between offsets t0 and t1 along the direction u."""
    L = 900
    p0 = (a[0] + u[0] * t0, a[1] + u[1] * t0)
    p1 = (a[0] + u[0] * t1, a[1] + u[1] * t1)
    return region.intersection(Polygon([
        (p0[0] - u[1] * L, p0[1] + u[0] * L), (p1[0] - u[1] * L, p1[1] + u[0] * L),
        (p1[0] + u[1] * L, p1[1] - u[0] * L), (p0[0] + u[1] * L, p0[1] - u[0] * L)]))


@dataclass
class Fan:
    """Lots that tile the land the road leaves, with nothing over.

    Dropping the rectangle costs the corner lot its square corners and buys back
    every square foot of offcut. The lots are four-sided, cut by straight lines
    across the land, so each one still fronts the road and backs onto the south
    boundary.

    What is made equal is a choice, and it changes what a buyer gets. Equal land
    hands the corner lot the same area as the rest, but its wedge will not take
    the same building. Equal buildable widens that lot until the largest
    rectangle inside it matches the others, which is what an architect is
    actually buying.
    """
    plot: Plot
    road_w: float
    n: int = 3
    square_to: str = "road"          # "road" or "south": what the cuts stand square to
    equalise: str = "land"           # "land" or "buildable"
    head: float = 0.0                # turning head reserved at the dead end, ft

    def __post_init__(self):
        region, inner = buildable(self.plot, self.road_w, self.head)
        F, E = inner.coords[0], inner.coords[-1]
        A, B = self.plot.corners[0], self.plot.corners[1]
        a, b = (F, E) if self.square_to == "road" else (A, B)
        self.head_poly = (Polygon([*head_ends(self.plot, self.road_w, self.head)][:1]
                                  + [Massing(self.plot, self.road_w).E]
                                  + [head_ends(self.plot, self.road_w, self.head)[1]])
                          if self.head > 0 else None)
        d = math.dist(a, b)
        u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
        ts = [(q[0] - a[0]) * u[0] + (q[1] - a[1]) * u[1]
              for q in region.exterior.coords]
        lo, hi = min(ts), max(ts)
        # buildings are set out parallel to the frontage, so the rectangle
        # that matters is the one square to the road
        self.angle = math.degrees(math.atan2(E[1] - F[1], E[0] - F[0]))
        self.region, self.inner = region, inner
        cuts = (_cuts_equal_buildable(self, region, a, u, lo, hi)
                if self.equalise == "buildable" else
                _cuts_equal_land(region, a, u, lo, hi, self.n))
        edges = [lo, *cuts, hi]
        self.lots = [_band(region, a, u, edges[i], edges[i + 1]) for i in range(self.n)]
        self.rects = [Polygon(inscribed(g, self.angle)[1]) for g in self.lots]
        self.road = self.plot.quad.difference(buildable(self.plot, self.road_w)[0])
        self.audit()

    @property
    def lot_area(self) -> float:
        return self.region.area / self.n

    @property
    def rect_area(self) -> float:
        """The buildable rectangle every lot is guaranteed."""
        return min(r.area for r in self.rects)

    def rect_size(self, i: int) -> tuple[float, float]:
        q = list(self.rects[i].exterior.coords[:-1])
        return math.dist(q[0], q[1]), math.dist(q[1], q[2])

    def pieces(self) -> list[Piece]:
        out = [Piece(f"Lot {i + 1}", g, _fan_why(g), g.area)
               for i, g in enumerate(self.lots)]
        out.append(Piece("Road", self.road,
                         f"{self.road_w:.2f} ft perpendicular, full north boundary",
                         self.road.area))
        if self.head_poly is not None:
            q = list(self.head_poly.exterior.coords[:-1])
            out.append(Piece("Turning head", self.head_poly,
                             f"1/2 x {self.head:.2f} x {math.dist(q[0], q[2]):.2f}",
                             self.head * math.dist(q[0], q[2]) / 2))
        return out

    def audit(self, tol=TOL):
        """No offcuts means the lots, the road and the head are the whole plot."""
        for p in self.pieces():
            p.verify(tol)
        got = ([g.area for g in self.lots] if self.equalise == "land"
               else [r.area for r in self.rects])
        spread = max(got) - min(got)
        if spread > (tol if self.equalise == "land" else 1.0):
            raise AssertionError(f"lots differ by {spread:.2f} ft2 on {self.equalise}, "
                                 f"so they are not equal")
        for r, g in zip(self.rects, self.lots):
            if r.difference(g.buffer(1e-6)).area > tol:
                raise AssertionError("a buildable rectangle leaves its own lot")
        total = sum(p.area for p in self.pieces())
        if abs(total - self.plot.area_ft2) > tol:
            raise AssertionError(f"parts sum to {total:,.2f} ft2 but the plot is "
                                 f"{self.plot.area_ft2:,.2f} ft2")
        return self

    def tally(self) -> dict:
        """The head is common ground, so it counts with the road, not the lots."""
        head = self.head_poly.area if self.head_poly is not None else 0.0
        return dict(lots=self.region.area, road=self.road.area + head, waste=0.0,
                    total=self.region.area + self.road.area + head,
                    plot=self.plot.area_ft2)

    def corners(self) -> list[list[float]]:
        """Interior angles of each lot. The corner lot pays for the zero waste."""
        return [_angles(g) for g in self.lots]

    def __str__(self):
        worst = min(min(a) for a in self.corners())
        land = " ".join(f"{g.area:,.0f}" for g in self.lots)
        return (f"{self.n} four-sided lots, equal {self.equalise}: land {land} ft2, "
                f"buildable {self.rect_area:,.0f} ft2 ({self.rect_area / CENT:.2f} cents) "
                f"each, no waste, sharpest corner {worst:.0f} deg")


def _cuts_equal_land(region, a, u, lo, hi, n):
    """Cut positions that give every lot the same area."""
    cuts = []
    for i in range(1, n):
        c, e = (cuts[-1] if cuts else lo), hi
        for _ in range(60):
            mid = (c + e) / 2
            under = _band(region, a, u, lo, mid).area
            c, e = (mid, e) if under < region.area * i / n else (c, mid)
        cuts.append((c + e) / 2)
    return cuts


def _reach(fan, region, a, u, lo, hi, target):
    """Cuts giving every lot a buildable rectangle of at least `target`, or None.

    Each lot is taken no wider than it needs to be. So if this walk runs out of
    land, the target is out of reach for any other set of cuts.
    """
    prev, out = lo, []
    for _ in range(fan.n - 1):
        if _rect_of(fan, region, a, u, prev, hi) < target:
            return None
        c, e = prev, hi
        for _ in range(45):
            mid = (c + e) / 2
            c, e = (mid, e) if _rect_of(fan, region, a, u, prev, mid) < target else (c, mid)
        out.append((c + e) / 2)
        prev = out[-1]
    return out if _rect_of(fan, region, a, u, prev, hi) >= target else None


def _rect_of(fan, region, a, u, t0, t1) -> float:
    g = _band(region, a, u, t0, t1)
    return inscribed(g, fan.angle)[0] if g.area > 1 else 0.0


def _cuts_equal_buildable(fan, region, a, u, lo, hi):
    """Cut positions that give every lot the same largest inscribed rectangle."""
    c, e = 0.0, region.area / fan.n
    for _ in range(40):
        mid = (c + e) / 2
        c, e = (mid, e) if _reach(fan, region, a, u, lo, hi, mid) else (c, mid)
    return _reach(fan, region, a, u, lo, hi, c)


def _fan_why(g: Polygon) -> str:
    """Triangles from the first corner, so the area can be re-added by hand."""
    q = list(g.exterior.coords[:-1])
    parts = []
    for i in range(1, len(q) - 1):
        base = math.dist(q[0], q[i])
        parts.append(f"1/2 x {base:.2f} x {2 * Polygon([q[0], q[i], q[i + 1]]).area / base:.2f}")
    return " + ".join(parts)


def _angles(g: Polygon) -> list[float]:
    q = list(g.exterior.coords[:-1])
    out = []
    for i, _ in enumerate(q):
        p, r = q[i - 1], q[(i + 1) % len(q)]
        v1 = ((p[0] - q[i][0]), (p[1] - q[i][1]))
        v2 = ((r[0] - q[i][0]), (r[1] - q[i][1]))
        cos = (v1[0] * v2[0] + v1[1] * v2[1]) / math.dist(p, q[i]) / math.dist(q[i], r)
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, cos)))))
    return out
