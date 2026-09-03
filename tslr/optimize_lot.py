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


def buildable(plot: Plot, road_w: float) -> tuple[Polygon, LineString]:
    """(land left after the road, the road's inner edge).

    The plot and the road strip are both convex. The strip is cut by one
    straight line, so what is left is a convex quadrilateral A-B-E-F. Every
    routine below relies on that convexity.
    """
    m = Massing(plot, road_w)
    A, B, _, _ = plot.corners
    return Polygon([A, B, m.E, m.F]), LineString([m.F, m.E])


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
