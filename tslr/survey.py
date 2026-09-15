"""Check an FMB whose four sides are all it records.

Four lengths do not fix a quadrilateral, so a written area cannot be checked
against the sides alone. Something has to supply the one missing figure. An
FMB offers three candidates, and they need not agree.

  drawing:  the sketch has a stated scale, so its angles are evidence.
  register: the written area picks out the diagonals that produce it.
  cyclic:   Brahmagupta's maximum, the most those sides can hold at all.

Corners keep the sketch's own labels. A record lists them anticlockwise,
starting at the west end of the base. That lines them up with `Plot`'s A to D.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .geometry import FT2, Plot, brahmagupta, heron

HERE = Path(__file__).parent / "surveys"
CENT_M2 = 435.6 / FT2


def load(key: str) -> dict:
    return json.loads((HERE / f"{key}.json").read_text())


def plot(rec: dict, diagonal: float | None = None) -> Plot:
    """The record as a `Plot`. Without a diagonal it closes to the drawn angles."""
    s, e, n, w = rec["sides_m"]
    return Plot(n, e, s, w, registered=rec["registered_m2"],
                diagonal=drawn_diagonal(rec) if diagonal is None else diagonal,
                diagonal_ends="AC")


def _misfit(rec, p):
    """Root mean square gap between a closure's corners and the drawn ones."""
    return math.sqrt(sum((a - rec["drawn_angles"][k]) ** 2
                         for k, a in zip(rec["walk"], p.corner_angles)) / 4)


def drawn_diagonal(rec: dict) -> float:
    """The diagonal whose closure best matches the drawn angles.

    The sides fix everything but one figure, so fitting the drawing is a search
    along a single line. Fitting the diagonal, rather than walking corner
    angles, always closes exactly: every candidate is two triangles glued
    along it.
    """
    lo, hi = _diagonal_range(rec)
    lo, hi = lo + 1e-6, hi - 1e-6
    fit = lambda d: _misfit(rec, plot(rec, d))
    best = min((lo + (hi - lo) * i / 600 for i in range(1, 600)), key=fit)
    step = (hi - lo) / 600
    for _ in range(40):                          # golden section around the best
        a, b = max(lo, best - step), min(hi, best + step)
        c, d = b - (b - a) * 0.618, a + (b - a) * 0.618
        best = (a + d) / 2 if fit(c) < fit(d) else (c + b) / 2
        step *= 0.618
    return best


def _diagonal_range(rec):
    s, e, n, w = rec["sides_m"]
    return max(abs(s - e), abs(n - w)), min(s + e, n + w)


def _area_at(rec, d):
    """Area with the first-to-third-corner diagonal at d."""
    s, e, n, w = rec["sides_m"]
    return heron(s, e, d) + heron(d, n, w)


def register_diagonals(rec: dict) -> list[float]:
    """The diagonals that make the sides enclose exactly the registered area.

    Area rises to the cyclic peak and falls again, so a reachable register is
    met twice, once either side of it. An unreachable one is met never.
    """
    lo, hi = _diagonal_range(rec)
    lo, hi = lo + 1e-9, hi - 1e-9
    target = rec["registered_m2"]
    f = lambda d: _area_at(rec, d) - target
    grid = [lo + (hi - lo) * i / 40000 for i in range(40001)]
    out = []
    for a, b in zip(grid, grid[1:]):
        if f(a) * f(b) <= 0 and f(a) != f(b):
            for _ in range(80):
                m = (a + b) / 2
                a, b = (m, b) if f(a) * f(m) > 0 else (a, m)
            out.append((a + b) / 2)
    return out


def cyclic_diagonal(rec: dict) -> float:
    """B + D = 180 makes cos D = -cos B, and the two law-of-cosines forms of
    the diagonal can then be set equal. Nothing is searched."""
    s, e, n, w = rec["sides_m"]
    cos_b = (s * s + e * e - n * n - w * w) / (2 * (s * e + n * w))
    return math.sqrt(s * s + e * e - 2 * s * e * cos_b)


def closures(rec: dict) -> list[dict]:
    """Every candidate shape, with what each makes of the area and the corners."""
    rows = [("drawing", drawn_diagonal(rec))]
    rows += [(f"register{i + 1}", d) for i, d in enumerate(register_diagonals(rec))]
    rows.append(("cyclic", cyclic_diagonal(rec)))
    out = []
    for key, d in rows:
        p = plot(rec, d)
        out.append({"key": key, "diagonal": d, "other": p.diagonals_m["BD"],
                    "area_m2": p.area_m2, "plot": p,
                    "angles": dict(zip(rec["walk"], p.corner_angles)),
                    "misfit": _misfit(rec, p)})
    return out


def offsets(rec: dict, p: Plot) -> dict:
    """The pencil method. Drop a perpendicular from the apex to the base. Run a
    line through the other top corner, parallel to the base. The plot then reads
    as two right triangles and a trapezoid, each 1/2 x base x height.

    `Plot` lays the base along the x axis, so the perpendicular is vertical and
    the parallel is horizontal, and every offset is a coordinate.
    """
    walk = rec["walk"]
    pts = {k: (x / (FT2 ** 0.5), y / (FT2 ** 0.5)) for k, (x, y) in zip(walk, p.corners)}
    base0, base1 = pts[walk[0]], pts[walk[1]]
    apex, through = pts[rec["offsets"]["apex"]], pts[rec["offsets"]["through"]]
    foot_x, h_apex, h_through = apex[0], apex[1], through[1]
    run = through[0] - foot_x                     # foot of the perpendicular to the corner
    if not (base0[0] < foot_x < base1[0]):
        raise AssertionError("the perpendicular from the apex misses the base")
    if not (0 < h_through < h_apex and run > 0):
        raise AssertionError("this construction needs the other corner lower and to the side")
    pieces = [
        ("left triangle", 0.5 * foot_x * h_apex,
         f"1/2 x {foot_x:.2f} x {h_apex:.2f}"),
        ("top triangle", 0.5 * run * (h_apex - h_through),
         f"1/2 x {run:.2f} x {h_apex - h_through:.2f}"),
        ("trapezoid", 0.5 * ((base1[0] - foot_x) + run) * h_through,
         f"1/2 x ({base1[0] - foot_x:.2f} + {run:.2f}) x {h_through:.2f}"),
    ]
    return {"foot_from_base0": foot_x, "foot_to_base1": base1[0] - foot_x,
            "height_apex": h_apex, "height_through": h_through, "run": run,
            "pieces": pieces, "total": sum(a for _, a, _ in pieces)}


def report(key: str) -> str:
    rec = load(key)
    s, e, n, w = rec["sides_m"]
    walk = rec["walk"]
    side = lambda i: f"{walk[i]}-{walk[(i + 1) % 4]}"
    lines = [f"{rec['survey']}, {rec['village']}, {rec['taluk']}",
             "  sides " + ", ".join(f"{side(i)} {v}" for i, v in enumerate(rec["sides_m"])) + " m",
             f"  registered {rec['registered_m2']:.1f} m2 ({rec['registered_as']}) = "
             f"{rec['registered_m2'] / CENT_M2:.2f} cents",
             f"  most these sides can hold (Brahmagupta) "
             f"{brahmagupta(n, e, s, w):.1f} m2 = {brahmagupta(n, e, s, w) / CENT_M2:.2f} cents"]
    for c in closures(rec):
        lines.append(f"  {c['key']:<10} {walk[0]}-{walk[2]} {c['diagonal']:6.2f}  "
                     f"{c['area_m2']:6.1f} m2 {c['area_m2'] / CENT_M2:5.2f} c  "
                     + " ".join(f"{k} {c['angles'][k]:6.2f}" for k in walk)
                     + f"   off the drawing by {c['misfit']:.2f} deg rms")
    return "\n".join(lines)


def letters(rec: dict) -> dict:
    """The record's corners under the letters used on the sheets: A at the top,
    then B, C, D clockwise. The record walks anticlockwise from the base's west
    end, so D, C, B, A in that order."""
    return dict(zip("DCBA", rec["walk"]))


def x_construction(rec: dict, p: Plot) -> dict:
    """B's line parallel to CD meets AD at X. Drop X and A square onto CD.

    `Plot` lays CD along the x axis with D at the origin, so a parallel to CD
    is a horizontal and a perpendicular to it a vertical. The plot then reads
    as two rectangles and four right triangles, each needing only one
    multiplication. B is dropped as well, so the right-hand end is a rectangle
    and a triangle rather than a trapezoid.
    """
    to_m = lambda q: (q[0] * 0.3048, q[1] * 0.3048)
    D, C, B, A = (to_m(q) for q in p.corners)
    hb = B[1]
    if not (0 < hb < A[1]):
        raise AssertionError("B must sit below A for its parallel to reach AD")
    X = (A[0] * hb / A[1], hb)                       # D is the origin, so AD scales
    P, Q, R, Y = (X[0], 0.0), (A[0], 0.0), (B[0], 0.0), (A[0], hb)
    if not (0 < P[0] < Q[0] < R[0] < C[0]):
        raise AssertionError("the feet of X, A and B must fall in order along CD")
    pt = dict(A=A, B=B, C=C, D=D, X=X, Y=Y, P=P, Q=Q, R=R)
    L = lambda a, b: math.dist(pt[a], pt[b])
    pieces = [
        ("DPX", "triangle", 0.5 * L("D", "P") * L("P", "X"), ("D", "P"), ("P", "X")),
        ("PQYX", "rectangle", L("P", "Q") * L("P", "X"), ("P", "Q"), ("P", "X")),
        ("QRBY", "rectangle", L("Q", "R") * L("R", "B"), ("Q", "R"), ("R", "B")),
        ("RCB", "triangle", 0.5 * L("R", "C") * L("R", "B"), ("R", "C"), ("R", "B")),
        ("XYA", "triangle", 0.5 * L("X", "Y") * L("Y", "A"), ("X", "Y"), ("Y", "A")),
        ("YBA", "triangle", 0.5 * L("Y", "B") * L("Y", "A"), ("Y", "B"), ("Y", "A")),
    ]
    total = sum(a for _, _, a, _, _ in pieces)
    if abs(total - p.area_m2) > 1e-6:
        raise AssertionError(f"pieces sum to {total:.3f} m2, the plot is {p.area_m2:.3f}")
    return {"points": pt, "pieces": pieces, "length": L, "area_m2": total}


def pdf(key: str, out: Path) -> Path:
    """Plan and tally for the drawing's shape, then for the register's nearest."""
    import subprocess
    import tempfile
    from . import pages
    from .sheet import Paper, Sheet
    rec = load(key)
    paper = Paper("A4", 297.0, 210.0, 250, 0.78, 38.0)
    cs = closures(rec)
    by = {c["key"]: c for c in cs}
    reg = min((c for c in cs if c["key"].startswith("register")), key=lambda c: c["misfit"])
    peak = max(cs, key=lambda c: c["area_m2"])
    notes = {
        "drawing": (f"SHAPE: THE DRAWING — sides closed to the 1:{rec['scale']} sketch's "
                    f"angles, {by['drawing']['misfit']:.2f}° from it"),
        reg["key"]: (f"SHAPE: THE REGISTER — the 850 m² closure nearest the sketch, "
                     f"{reg['misfit']:.1f}° from it"),
    }
    summary = [("drawing", by["drawing"]["area_m2"],
                f"fits the sketch to {by['drawing']['misfit']:.2f}°"),
               ("register", reg["area_m2"], f"nearest 850 m² shape, {reg['misfit']:.1f}° off the sketch"),
               ("cyclic maximum", peak["area_m2"], "the most these four sides can hold")]
    sheets = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate((by["drawing"], reg)):
            xc = x_construction(rec, c["plot"])
            sheets.append(pages.x_plan(Sheet(c["plot"], paper), rec, xc, notes[c["key"]])
                          .save(f"{tmp}/{i}a"))
            sheets.append(pages.x_schedule(Sheet(c["plot"], paper), rec, xc, notes[c["key"]],
                                           c["plot"], summary).save(f"{tmp}/{i}b"))
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdfunite", *sheets, str(out)], check=True)
    return out


if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else "1542-1"
    print(report(key))
    print("wrote", pdf(key, Path("generated") / f"{key}_offsets.pdf"))
