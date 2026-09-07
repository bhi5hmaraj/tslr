"""The plot and the way it is carved up.

A TSLR/FMB sketch records four side lengths and a registered extent that rarely
agree, because four fixed sides do not fix a quadrilateral -- they close into a
one-parameter family, whose areas run from nearly nothing up to the cyclic
member's (Brahmagupta's maximum). So:

  * measure a DIAGONAL as well and the shape is rigid. Two triangles, two Herons,
    one area, no assumption. Use this whenever you have the measurement.
  * without one, `Plot` falls back on the member whose corner angles match the
    drawing, and says so. It will not silently pick the max-area member: that one
    splays both side boundaries outward, which the sketch does not, and which
    throws the foot of the perpendicular from D outside the south boundary --
    breaking the carve below.

`Carve` is that construction: perpendicular down from D to the south boundary
(foot P), perpendicular up from B to the north boundary (foot Q). Three equal
rectangles sit on the base P-B; everything above them is road -- a slanted wedge,
15 ft measured PERPENDICULAR to the north boundary at its narrowest end. What is
left is two corner triangles, A-P-D and B-Q-C.

Every carved piece carries the arithmetic that produced its area, and every
`Carve` audits itself on construction: the parts must sum to the whole and each
piece's stated formula must reproduce its drawn area, or it raises.

All internal geometry is in FEET; sides are given in metres because that is how
the FMB records them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

M2FT = 1 / 0.3048
FT2 = M2FT ** 2                      # sq ft per sq metre
CENT = 435.6                         # sq ft in one cent (1/100 acre)
TOL = 0.5                            # ft2 -- audit tolerance, 0.003% of this plot

# Corner angles A, B, C, D scaled off the FMB drawing of TS 11/14/18.
SKETCH_ANGLES = (85.66, 110.06, 74.36, 89.92)


# ---------------------------------------------------------------- small maths
def unit(p, q):
    d = (q[0] - p[0], q[1] - p[1])
    L = math.hypot(*d)
    return (d[0] / L, d[1] / L), L


def foot(p, a, b):
    """perpendicular foot of p on the line a-b."""
    (ux, uy), _ = unit(a, b)
    t = (p[0] - a[0]) * ux + (p[1] - a[1]) * uy
    return (a[0] + ux * t, a[1] + uy * t)


def cross_to(p, a, b, c, d):
    """from p, perpendicular to a-b, out to the line c-d."""
    (ux, uy), _ = unit(a, b)
    nx, ny = -uy, ux
    (vx, vy), _ = unit(c, d)
    t = ((c[0] - p[0]) * vy - (c[1] - p[1]) * vx) / (nx * vy - ny * vx)
    return (p[0] + nx * t, p[1] + ny * t)


def shoelace(pts):
    n = len(pts)
    return abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                   for i in range(n))) / 2


def angles(pts):
    out = []
    for i in range(len(pts)):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, cos)))))
    return out


def heron(a, b, c):
    s = (a + b + c) / 2
    t = s * (s - a) * (s - b) * (s - c)
    if t <= 0:
        raise ValueError(f"sides {a:.2f}, {b:.2f}, {c:.2f} cannot form a triangle")
    return math.sqrt(t)


def brahmagupta(a, b, c, d):
    """largest area four sides of these lengths can ever enclose -- attained only
    by the cyclic quadrilateral, where opposite angles sum to 180 degrees."""
    s = (a + b + c + d) / 2
    t = (s - a) * (s - b) * (s - c) * (s - d)
    return math.sqrt(t) if t > 0 else float("nan")


def meet(p, r1, q, r2, left=True):
    """the two circles' intersection; `left` picks the side of p->q to land on."""
    (ux, uy), d = unit(p, q)
    if d > r1 + r2 or d < abs(r1 - r2):
        raise ValueError(f"no closure: circles r={r1:.2f}, r={r2:.2f} at {d:.2f} apart")
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    s = 1 if left else -1
    return (p[0] + ux * a - s * uy * h, p[1] + uy * a + s * ux * h)


# ---------------------------------------------------------------- a named part
@dataclass(frozen=True)
class Piece:
    """A carved area plus the arithmetic that produced it, so a reader can
    re-add the schedule by hand and land on the same number."""
    name: str
    poly: Polygon
    why: str                 # e.g. "68.25 x 63.45" or "1/2 x 98.43 x 2.59"
    check: float             # what that arithmetic evaluates to, ft2

    @property
    def area(self) -> float:
        return self.poly.area

    def verify(self, tol=TOL):
        if abs(self.check - self.area) > tol:
            raise AssertionError(f"{self.name}: {self.why} = {self.check:,.1f} ft2 but the "
                                 f"drawn shape is {self.area:,.1f} ft2")
        return self


# ------------------------------------------------------------------- the plot
@dataclass(frozen=True)
class Plot:
    """Four boundary lengths in metres, anticlockwise from the south.

    Pass `diagonal` (also metres) to fix the shape exactly; `diagonal_ends`
    says which corners it joins, "AC" (south-west to north-east) or "BD".
    """
    north: float
    east: float
    south: float
    west: float
    registered: float = 1875.0          # m2 as entered in the register
    diagonal: float | None = None
    diagonal_ends: str = "AC"
    target_angles: tuple = SKETCH_ANGLES
    corners: tuple = field(init=False, repr=False)   # A, B, C, D in FEET

    def __post_init__(self):
        pts = self._close_exact() if self.diagonal else self._close_by_angles()
        object.__setattr__(self, "corners", tuple((x * M2FT, y * M2FT) for x, y in pts))
        self._audit_sides()

    # -- closure ----------------------------------------------------------
    def _close_exact(self):
        """Sides plus one diagonal make the quadrilateral rigid: two triangles
        glued along the diagonal, each solved by circle intersection."""
        A, B = (0.0, 0.0), (self.south, 0.0)
        if self.diagonal_ends.upper() == "AC":
            C = meet(A, self.diagonal, B, self.east, left=True)
            D = meet(A, self.west, C, self.north, left=True)
        elif self.diagonal_ends.upper() == "BD":
            D = meet(B, self.diagonal, A, self.west, left=False)
            C = meet(B, self.east, D, self.north, left=False)
        else:
            raise ValueError("diagonal_ends must be 'AC' or 'BD'")
        return [A, B, C, D]

    def _quad(self, alpha, beta):
        return [(0.0, 0.0), (self.south, 0.0),
                (self.south - self.east * math.cos(beta), self.east * math.sin(beta)),
                (self.west * math.cos(alpha), self.west * math.sin(alpha))]

    def _close_by_angles(self, steps=18000):
        """Walk the angle at A; for each, bisect the angle at B until the north
        side comes out right; keep the shape closest to the sketch's angles."""
        best = None
        for i in range(1, steps):
            a = math.radians(i * 180 / steps)
            f = lambda b: math.dist(self._quad(a, b)[2], self._quad(a, b)[3]) - self.north
            lo, hi = 1e-6, math.pi - 1e-6
            if f(lo) * f(hi) > 0:
                continue
            for _ in range(80):
                m = (lo + hi) / 2
                lo, hi = (lo, m) if f(lo) * f(m) <= 0 else (m, hi)
            p = self._quad(a, (lo + hi) / 2)
            if p[2][1] <= 0 or p[3][1] <= 0:
                continue
            err = sum((x - y) ** 2 for x, y in zip(angles(p), self.target_angles))
            if best is None or err < best[0]:
                best = (err, p)
        if best is None:
            raise ValueError("these four sides cannot close into a quadrilateral")
        return best[1]

    def _audit_sides(self):
        """The closure must carry the lengths it was given, whichever route
        produced it -- everything downstream is measured off these corners."""
        c = self.corners
        got = [math.dist(c[i], c[(i + 1) % 4]) / M2FT for i in range(4)]
        want = [self.south, self.east, self.north, self.west]
        for name, a, b in zip(("south", "east", "north", "west"), got, want):
            if abs(a - b) > 0.01:
                raise AssertionError(f"closure {name} came out {a:.3f} m, not {b:.3f} m")
        if self.diagonal:
            d = math.dist(c[0], c[2]) if self.diagonal_ends.upper() == "AC" \
                else math.dist(c[1], c[3])
            if abs(d / M2FT - self.diagonal) > 0.01:
                raise AssertionError(f"closure diagonal came out {d / M2FT:.3f} m")

    # -- derived ----------------------------------------------------------
    @property
    def quad(self) -> Polygon:
        return Polygon(self.corners)

    @property
    def area_ft2(self) -> float:
        return shoelace(self.corners)

    @property
    def area_m2(self) -> float:
        return self.area_ft2 / FT2

    @property
    def max_area_m2(self) -> float:
        return brahmagupta(self.north, self.east, self.south, self.west)

    @property
    def sides_m(self) -> tuple:
        return (self.north, self.east, self.south, self.west)

    @property
    def corner_angles(self) -> list:
        return angles(self.corners)

    @property
    def is_cyclic(self) -> bool:
        """True when opposite angles sum to 180 -- the one shape of the family
        that reaches Brahmagupta's maximum area."""
        a = self.corner_angles
        return abs(a[0] + a[2] - 180) < 0.5

    @property
    def diagonals_m(self) -> dict:
        c = self.corners
        return {"AC": math.dist(c[0], c[2]) / M2FT, "BD": math.dist(c[1], c[3]) / M2FT}

    @property
    def derivation(self) -> str:
        """How this area was arrived at, in a form that can be re-added by hand."""
        if self.diagonal:
            e = self.diagonal_ends.upper()
            if e == "AC":
                t1, t2 = (self.south, self.east, self.diagonal), \
                         (self.diagonal, self.north, self.west)
            else:
                t1, t2 = (self.south, self.diagonal, self.west), \
                         (self.east, self.north, self.diagonal)
            return (f"Heron({t1[0]:.2f}, {t1[1]:.2f}, {t1[2]:.2f}) + "
                    f"Heron({t2[0]:.2f}, {t2[1]:.2f}, {t2[2]:.2f}) = "
                    f"{heron(*t1):.1f} + {heron(*t2):.1f} = {self.area_m2:.1f} m²")
        a = self.corner_angles
        return (f"four sides only — shape assumed from the sketch's corner angles "
                f"(A+C = {a[0] + a[2]:.1f}°, cyclic would be 180°); measure a diagonal "
                f"to fix it exactly")

    @property
    def register_factor(self) -> float:
        """multiply an area by this to pro-rate it up to the registered extent."""
        return self.registered / self.area_m2

    @property
    def stretch(self) -> float:
        """side factor that would make the closure area equal the register."""
        return math.sqrt(self.register_factor)

    def fitted(self) -> "Plot":
        """Same shape, every side (and diagonal) stretched by one factor until
        the closure area equals the registered extent."""
        k = self.stretch
        return replace(self, north=self.north * k, east=self.east * k,
                       south=self.south * k, west=self.west * k,
                       diagonal=None if self.diagonal is None else self.diagonal * k)


# ------------------------------------------------------------------ the carve
@dataclass
class Carve:
    """Three equal-area rectangles on the base P-B, road above them.

    stepped=False gives three identical rectangles; stepped=True lets each lot
    run as deep as its own east corner allows, so the rear line steps down west
    to east and the lots gain area at the road's expense.
    """
    plot: Plot
    road_w: float = 15.0
    stepped: bool = False

    def __post_init__(self):
        A, B, C, D = self.plot.corners
        self.P = foot(D, A, B)
        self.Q = cross_to(B, A, B, D, C)
        self.h_west, self.h_east = math.dist(self.P, D), math.dist(B, self.Q)
        (ux, uy), self.base = unit(self.P, B)
        nx, ny = -uy, ux
        if nx * (D[0] - self.P[0]) + ny * (D[1] - self.P[1]) < 0:
            nx, ny = -nx, -ny
        self.slant = math.degrees(math.atan2(self.h_west - self.h_east, self.base))
        self.at = lambda t, h: (self.P[0] + ux * t + nx * h, self.P[1] + uy * t + ny * h)
        self.height = lambda x: self.h_west - (self.h_west - self.h_east) * x / self.base
        self.band = Polygon([self.P, B, self.Q, D])
        self.cuts, self.depths = self._split(self._clear(self.road_w))
        self.lots = [Polygon([self.at(self.cuts[k], 0), self.at(self.cuts[k + 1], 0),
                              self.at(self.cuts[k + 1], self.depths[k]),
                              self.at(self.cuts[k], self.depths[k])]) for k in range(3)]
        self.road = self.band.difference(unary_union(self.lots))
        self.west = Polygon([A, self.P, D])
        self.east = Polygon([B, self.Q, C])
        self.audit()

    def _clear(self, w):
        """vertical gap that leaves w ft measured perpendicular to the north edge."""
        return w / math.cos(math.radians(self.slant))

    def _split(self, need):
        if not self.stepped:
            return ([self.base * k / 3 for k in range(4)],
                    [self.height(self.base) - need] * 3)

        def span(x0, target):
            """narrowest lot starting at x0 that still reaches `target` area."""
            a, b = x0, self.base
            if (b - x0) * (self.height(b) - need) < target:
                return None
            for _ in range(200):
                m = (a + b) / 2
                a, b = (a, m) if (m - x0) * (self.height(m) - need) >= target else (m, b)
            return b

        lo, hi = 0.0, 20000.0
        for _ in range(200):                     # bisect on the common lot area
            x, ok = 0.0, True
            for _ in range(3):
                q = span(x, (lo + hi) / 2)
                if q is None:
                    ok = False
                    break
                x = q
            lo, hi = ((lo + hi) / 2, hi) if ok and x <= self.base else (lo, (lo + hi) / 2)
        cuts, x = [0.0], 0.0
        for _ in range(3):
            x = span(x, lo)
            cuts.append(x)
        return cuts, [self.height(cuts[k + 1]) - need for k in range(3)]

    # -- the pieces, each with its arithmetic ------------------------------
    @property
    def lot_pieces(self):
        out = []
        for k, poly in enumerate(self.lots):
            w, d = self.cuts[k + 1] - self.cuts[k], self.depths[k]
            out.append(Piece(f"Lot {k + 1}", poly, f"{w:.2f} × {d:.2f}", w * d))
        return out

    @property
    def road_bays(self):
        """The road split at the lot joints: one trapezoid per bay, each
        (west upright + east upright) / 2 x width."""
        out = []
        for k in range(3):
            x0, x1, d = self.cuts[k], self.cuts[k + 1], self.depths[k]
            h0, h1 = self.height(x0) - d, self.height(x1) - d
            poly = Polygon([self.at(x0, d), self.at(x1, d),
                            self.at(x1, d + h1), self.at(x0, d + h0)])
            out.append(Piece(f"road bay {k + 1}", poly,
                             f"({h0:.2f} + {h1:.2f})/2 × {x1 - x0:.2f}", (h0 + h1) / 2 * (x1 - x0)))
        return out

    @property
    def road_piece(self):
        bays = self.road_bays
        return Piece("Road", self.road, " + ".join(b.why for b in bays),
                     sum(b.check for b in bays))

    @property
    def offcut_pieces(self):
        out = []
        for name, poly, corners in (("W1", self.west, "A-P-D"), ("W2", self.east, "B-Q-C")):
            tri = max(fan(poly), key=lambda z: z[4])
            out.append(Piece(f"{name} ({corners})", poly,
                             f"½ × {tri[2]:.2f} × {tri[3]:.2f}", tri[2] * tri[3] / 2))
        return out

    @property
    def pieces(self):
        return self.lot_pieces + [self.road_piece] + self.offcut_pieces

    # -- self-consistency --------------------------------------------------
    def audit(self, tol=TOL):
        """Every stage must reconcile: each piece's stated arithmetic reproduces
        its drawn area, the pieces do not overlap, and they sum to the plot."""
        pieces = self.lot_pieces + self.road_bays + self.offcut_pieces
        for p in pieces:
            p.verify(tol)
        for i, a in enumerate(pieces):
            for b in pieces[i + 1:]:
                if a.poly.intersection(b.poly).area > tol:
                    raise AssertionError(f"{a.name} overlaps {b.name}")
        total = sum(p.area for p in pieces)
        if abs(total - self.plot.area_ft2) > tol:
            raise AssertionError(f"parts sum to {total:,.1f} ft2, plot is "
                                 f"{self.plot.area_ft2:,.1f} ft2")
        for lot in self.lots:
            if not self.plot.quad.buffer(1e-6).contains(lot):
                raise AssertionError("a lot escapes the boundary")
        A, B, C, D = self.plot.corners
        nx, ny = D[1] - C[1], C[0] - D[0]
        n = math.hypot(nx, ny)
        for lot in self.lots:
            gap = min(abs((nx * (x - C[0]) + ny * (y - C[1])) / n)
                      for x, y in lot.exterior.coords)
            if gap < self.road_w - 1e-6:
                raise AssertionError(f"road pinches to {gap:.2f} ft, under {self.road_w:.2f}")
        return self

    # -- reporting --------------------------------------------------------
    def width_line(self, w):
        """a line w ft perpendicular inside the north boundary, clipped to the
        road: it runs from the west until the road narrows past w."""
        need = self._clear(w)
        far = LineString([self.at(-50, self.height(-50) - need),
                          self.at(self.base + 50, self.height(self.base + 50) - need)])
        return self.road.intersection(far)

    @property
    def road_west(self):
        return self.h_west - self.depths[0]

    @property
    def road_east(self):
        return self.h_east - self.depths[-1]

    @property
    def offcuts(self):
        return [("W1", self.west), ("W2", self.east)]

    @property
    def lot_area(self):
        return self.lots[0].area

    def tally(self):
        lots = sum(l.area for l in self.lots)
        waste = sum(t.area for _, t in self.offcuts)
        return dict(lots=lots, road=self.road.area, waste=waste,
                    total=lots + self.road.area + waste, plot=self.plot.area_ft2)


# --------------------------------------------------- measuring a drawn piece
def verts(poly):
    return list(poly.exterior.coords)[:-1]


def sides(poly, min_len=0.5):
    """(p, q, length) for every edge worth dimensioning; hairlines are skipped."""
    c = verts(poly) + verts(poly)[:1]
    return [(c[i], c[i + 1], math.dist(c[i], c[i + 1]))
            for i in range(len(c) - 1) if math.dist(c[i], c[i + 1]) >= min_len]


def tidy(poly, tol=0.05):
    """merge hairline vertices and drop ones sitting on a straight run, so a side
    list reads as the shape's real edges rather than its split points."""
    out = []
    for q in verts(poly):
        if not out or math.dist(out[-1], q) > tol:
            out.append(q)
    if len(out) > 3 and math.dist(out[0], out[-1]) <= tol:
        out.pop()
    keep = []
    for i, q in enumerate(out):
        a, b = out[i - 1], out[(i + 1) % len(out)]
        cross = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if abs(cross) / max(math.dist(a, b), 1e-9) > 0.01:
            keep.append(q)
    return Polygon(keep if len(keep) >= 3 else out)


def fan(poly, tol=0.05):
    """triangles from vertex 0, each as (pts, base_pq, base_len, height, area) --
    enough to re-add the area by hand as 1/2 x base x height."""
    p = verts(tidy(poly, tol))
    out = []
    for i in range(1, len(p) - 1):
        t = [p[0], p[i], p[i + 1]]
        area = abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) -
                   (t[2][0] - t[0][0]) * (t[1][1] - t[0][1])) / 2
        if area < 0.02:
            continue
        e = max(((t[k], t[(k + 1) % 3], math.dist(t[k], t[(k + 1) % 3])) for k in range(3)),
                key=lambda z: z[2])
        out.append((t, (e[0], e[1]), e[2], 2 * area / e[2], area))
    return out


def apex(tri, base):
    return next(q for q in tri if q not in base)


def side_for_area(plot: Plot, which: str, target: float | None = None):
    """What would one side have to be for the other three to enclose `target`?

    Answers the standing question on a sketch whose sides and registered extent
    disagree: which figure is worth re-measuring on the ground. Returns the
    candidate lengths in metres (there are two, either side of the peak), plus
    the best area those other three sides allow.
    """
    target = plot.registered if target is None else target
    order = dict(north=(plot.east, plot.south, plot.west),
                 east=(plot.south, plot.west, plot.north),
                 south=(plot.west, plot.north, plot.east),
                 west=(plot.north, plot.east, plot.south))[which]
    lo, hi = 0.01, sum(order) - 0.01
    vals = [(lo + (hi - lo) * i / 20000, None) for i in range(20001)]
    vals = [(x, brahmagupta(x, *order)) for x, _ in vals]
    vals = [(x, a) for x, a in vals if a == a]                 # drop the NaN tails
    if not vals:
        return [], 0.0
    peak = max(a for _, a in vals)
    roots = []
    for (x0, a0), (x1, a1) in zip(vals, vals[1:]):
        if (a0 - target) * (a1 - target) <= 0 and a0 != a1:
            f = lambda x: brahmagupta(x, *order) - target
            a, b = x0, x1
            for _ in range(80):
                m = (a + b) / 2
                a, b = (m, b) if (f(a) > 0) == (f(m) > 0) else (a, m)
            roots.append((a + b) / 2)
    return roots, peak


def diagonal_for_area(plot: Plot, ends="AC", target: float | None = None):
    """What diagonal would make these four sides enclose `target`? Tells you what
    the tape should read on site if the register is right."""
    target = plot.registered if target is None else target
    if ends.upper() == "AC":                  # splits into A-B-C and A-C-D
        pairs = ((plot.south, plot.east), (plot.north, plot.west))
        t1 = lambda d: (plot.south, plot.east, d)
        t2 = lambda d: (d, plot.north, plot.west)
    else:                                     # BD splits into A-B-D and B-C-D
        pairs = ((plot.south, plot.west), (plot.north, plot.east))
        t1 = lambda d: (plot.south, d, plot.west)
        t2 = lambda d: (plot.east, plot.north, d)
    area = lambda d: heron(*t1(d)) + heron(*t2(d))
    lo = max(abs(a - b) for a, b in pairs) + 1e-6      # both triangles must close
    hi = min(a + b for a, b in pairs) - 1e-6
    grid = [lo + (hi - lo) * i / 5000 for i in range(1, 5000)]
    vals = [(d, area(d)) for d in grid]
    peak_d, peak = max(vals, key=lambda z: z[1])
    roots = []
    for (d0, a0), (d1, a1) in zip(vals, vals[1:]):
        if (a0 - target) * (a1 - target) <= 0 and a0 != a1:
            a, b = d0, d1
            for _ in range(80):
                m = (a + b) / 2
                a, b = (m, b) if (area(a) > target) == (area(m) > target) else (a, m)
            roots.append((a + b) / 2)
    return roots, peak, peak_d


def road_frame(plot: Plot, road_w: float):
    """The road's own geometry, and only that.

    Where the inner edge cuts the two side boundaries depends on the plot and
    the width, not on how the land behind it is later carved. Keeping it
    separate means a construction that does not suit a given closure cannot
    take the road down with it.
    """
    A, B, C, D = plot.corners
    P = foot(D, A, B)                      # 90 deg down from the top-left
    Q = cross_to(B, A, B, D, C)            # straight up from the bottom-right
    h_west, h_east = math.dist(P, D), math.dist(B, Q)
    (ux, uy), base = unit(P, B)
    nx, ny = -uy, ux
    if nx * (D[0] - P[0]) + ny * (D[1] - P[1]) < 0:
        nx, ny = -nx, -ny
    slant = math.degrees(math.atan2(h_west - h_east, base))
    at = lambda t, h: (P[0] + ux * t + nx * h, P[1] + uy * t + ny * h)
    height = lambda x: h_west - (h_west - h_east) * x / base
    drop = road_w / math.cos(math.radians(slant))
    inner = lambda x: height(x) - drop
    far = LineString([at(-400, inner(-400)), at(400, inner(400))])
    F = far.intersection(LineString([A, D])).coords[0]
    E = far.intersection(LineString([B, C])).coords[0]
    return (P, Q, h_west, h_east, base, slant, at, height, inner, F, E,
            (ux, uy), (nx, ny))


@dataclass
class Massing:
    """Road, one big rectangle, and the triangles that fall out of them.

    The road is a constant strip measured perpendicular to the north boundary and
    runs the full length of it, D to C, so both ends of the plot are reachable.
    Its inner edge meets the west boundary at F and the east boundary at E. The
    rectangle stands square to the south boundary and rises until it meets that
    inner edge. Three triangles remain: the triangle between the rectangle's flat top
    and the road's slanted underside, and a corner at each end.
    """
    plot: Plot
    road_w: float = 20.0

    def __post_init__(self):
        A, B, C, D = self.plot.corners
        fr = road_frame(self.plot, self.road_w)
        (self.P, self.Q, self.h_west, self.h_east, self.base, self.slant,
         self.at, self.height, self.inner, self.F, self.E) = fr[:11]
        (ux, uy), (nx, ny) = fr[11], fr[12]
        self.x_west = (self.F[0] - self.P[0]) * ux + (self.F[1] - self.P[1]) * uy
        self.depth = self.inner(self.base)     # rectangle meets the road at the east
        at, w, e = self.at, self.x_west, self.base
        self.rect = Polygon([at(w, 0), at(e, 0), at(e, self.depth), at(w, self.depth)])
        self.t1 = Polygon([at(w, self.depth), at(e, self.depth), self.F])
        self.road = Polygon([self.F, self.E, C, D])
        self.west = Polygon([A, at(w, 0), self.F])
        self.east = Polygon([B, self.E, at(e, self.depth)])
        self.audit()

    @property
    def width(self):
        return self.base - self.x_west

    @property
    def pieces(self):
        A, B, C, D = self.plot.corners
        return [
            Piece("Road", self.road,
                  f"({math.dist(D, C):.2f} + {math.dist(self.F, self.E):.2f})/2 × "
                  f"{self.road_w:.2f} ⟂",
                  (math.dist(D, C) + math.dist(self.F, self.E)) / 2 * self.road_w),
            Piece("Rectangle", self.rect, f"{self.width:.2f} × {self.depth:.2f}",
                  self.width * self.depth),
            Piece("T1", self.t1,
                  f"½ × {self.width:.2f} × {self.inner(self.x_west) - self.depth:.2f}",
                  self.width * (self.inner(self.x_west) - self.depth) / 2),
            Piece("T2 west", self.west,
                  f"½ × {math.dist(A, self.at(self.x_west, 0)):.2f} × "
                  f"{self.inner(self.x_west):.2f}",
                  math.dist(A, self.at(self.x_west, 0)) * self.inner(self.x_west) / 2),
            Piece("T3 east", self.east,
                  f"½ × {self.depth:.2f} × {math.dist(B, self.at(self.base, 0)) + abs(self.E[0] - B[0]):.2f}",
                  self.east.area)]

    def audit(self, tol=TOL):
        for p in self.pieces:
            p.verify(tol)
        # T1, T2 and T3 are written down from this construction, which assumes
        # the foot of the perpendicular from D lands inside AB. An obtuse corner
        # at A puts it outside, and the pieces then describe land the plot does
        # not own while still summing correctly, because they sum among
        # themselves. Containment is the check that catches it.
        land = self.plot.quad.buffer(1e-6)
        for p in self.pieces:
            if not land.contains(p.poly):
                raise AssertionError(f"{p.name} falls outside the plot: this "
                                     f"construction needs a corner at A under 90 "
                                     f"degrees, and it is "
                                     f"{self.plot.corner_angles[0]:.2f}")
        total = sum(p.area for p in self.pieces)
        if abs(total - self.plot.area_ft2) > tol:
            raise AssertionError(f"parts sum to {total:,.1f} ft2, plot is "
                                 f"{self.plot.area_ft2:,.1f} ft2")
        return self

    def tally(self):
        return {p.name: p.area for p in self.pieces} | {"plot": self.plot.area_ft2}
