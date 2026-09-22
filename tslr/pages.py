"""The two page templates.

`plan` is measurements only -- boundaries, lot sizes, road widths, the two
construction cuts and the offcut heights. `schedule` is the arithmetic that adds
those measurements back up to the plot, so the plan stays readable and the
numbers stay checkable.
"""
from __future__ import annotations

import math

from . import geometry as G
from .sheet import Sheet


def _title(sh, left, right, sub_l="", sub_r=""):
    sh.txt(14, 12, left, 4.4, "start", weight="bold")
    sh.txt(sh.p.w - 14, 12, right, 3.2, "end", fill="#666")
    if sub_l:
        sh.txt(14, 18.5, sub_l, 3.6, "start", fill="#333")
    if sub_r:
        sh.txt(sh.p.w - 14, 18.5, sub_r, 3.0, "end", fill="#666")


def plan(sh: Sheet, option: str, place="TS 11/14/18 · Ward-16 Thallakulam · Madurai North"):
    c = sh.c
    A, B, C, D = c.plot.corners
    sh.open()
    _title(sh, place, f"scale 1:{sh.p.denom} — print at 100% on {sh.p.name}",
           f"OPTION {option}", "north up · all figures in feet")

    for _, t in c.offcuts:
        sh.path(t, "#f6dcdc", "#c98c8c", 0.18)
    sh.path(c.road, "#e9e9e9", "#999", 0.2)
    for lot in c.lots:
        sh.path(lot, "#fff", "#000", 0.45)
    sh.path(c.plot.quad, "none", "#000", 0.9)
    for a, b in ((D, c.P), (B, c.Q)):                     # the two construction cuts
        sh.line(a, b, "#a00", 0.7)

    w20 = c.width_line(20)
    parts = list(w20.geoms) if w20.geom_type.startswith("Multi") else [w20]
    parts = [s for s in parts if not s.is_empty and s.length >= 1]
    for seg in parts:
        sh.line(seg.coords[0], seg.coords[-1], "#0033aa", 0.5, dash="2.4 1.6")
    if parts:
        seg = max(parts, key=lambda t: t.length)
        (ax, ay), (bx, by) = sh.px(seg.coords[0]), sh.px(seg.coords[-1])
        sh.txt((ax + bx) / 2, (ay + by) / 2 + 3.2, "20 ft ⟂", 2.8, fill="#0033aa",
               weight="bold", rot=math.degrees(math.atan2(by - ay, bx - ax)))

    for nm, pt in (("P", c.P), ("Q", c.Q)):
        cx, cy = sh.px(pt)
        sh.out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.1" fill="#a00"/>')
        sh.txt(cx + 4, cy + 1.2, nm, 3.6, fill="#a00", weight="bold")
    for nm, pt in zip("ABCD", c.plot.corners):
        cx, cy = sh.px(pt)
        sh.txt(cx + (-4.5 if nm in "AD" else 4.5), cy + (4 if nm in "AB" else -2),
               nm, 3.6, weight="bold")

    for k, lot in enumerate(c.lots):
        cx, cy = sh.px(lot.centroid.coords[0])
        sh.txt(cx, cy - 1.6, f"LOT {k + 1}", 5.4, weight="bold")
        sh.txt(cx, cy + 4.4, f"{c.cuts[k + 1] - c.cuts[k]:.2f} × {c.depths[k]:.2f}", 4.0)
    # the road split at the lot joints -- one bay per lot, so the schedule's
    # (h1 + h2)/2 x w arithmetic can be found on the drawing
    for x in c.cuts:
        sh.line(c.at(x, 0), c.at(x, c.height(x)), "#9e9e9e", 0.25, dash="1.6 1.2")
    for k, bay in enumerate(c.road_bays):
        bx, by = sh.px(bay.poly.representative_point().coords[0])
        sh.txt(bx, by + 1.0, f"bay {k + 1}", 2.9, fill="#666")
    for x, d in zip(c.cuts, list(c.depths) + [c.depths[-1]]):
        sh.dim(c.at(x, c.height(x)), c.at(x, d), 0, f"{c.height(x) - d:.2f}", 2.6, "#666")
    rx, ry = sh.px(c.road.representative_point().coords[0])
    sh.txt(rx, ry + 7.5, f"ROAD  {c.road_west:.2f} → {c.road_east:.2f} ft wide", 3.2,
           weight="bold", fill="#444")

    for nm, t in c.offcuts:
        pt = t.representative_point()
        gx, gy = sh.px((pt.x, pt.y))
        if nm == "W1":                                    # a 2.6 ft slice: tag it on a leader
            sh.line((gx, gy), (gx - 13, gy - 11), "#8b2f2f", 0.22, raw=True)
            gx, gy = gx - 15, gy - 12
        sh.txt(gx, gy + 1.0, nm, 3.6, weight="bold", fill="#8b2f2f")
        big = max(G.fan(t), key=lambda z: z[4])
        if big[4] >= 150:
            sh.height_mark(big[0], big[1], big[3])

    dx, dy = sh.px(D)
    sh.out.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="1.7" fill="none" stroke="#a00" '
                  f'stroke-width=".5"/>')
    sh.line((dx - 1.7, dy), (20, dy - 9), "#a00", 0.25, raw=True)
    sh.txt(14, dy - 11, "ENTRANCE 9.84", 3.2, "start", fill="#a00", weight="bold")
    nx, ny = sh.p.w - 24.0, sh.oy + sh.plan_h * 0.96
    sh.line((nx, ny), (nx, ny - 13), "#111", 0.5, raw=True)
    sh.out.append(f'<path d="M {nx - 2},{ny - 9} L {nx},{ny - 14} L {nx + 2},{ny - 9} Z" '
                  f'fill="#111"/>')
    sh.txt(nx, ny + 4.5, "N", 4.0, weight="bold")

    m = c.plot
    for a, b, off, name, length in ((D, C, -12, "north", m.north), (B, A, -19, "south", m.south),
                                    (C, B, -13, "east", m.east), (A, D, -11, "west", m.west)):
        sh.dim(a, b, off, f"{name}  {length * G.M2FT:.2f}", 3.2)
    sh.dim(B, c.P, -11, f"P–B  {c.base:.2f}", 2.9, "#a00")
    sh.dim(c.Q, B, 6.5, f"B–Q  {c.h_east:.2f}", 2.8, "#a00")
    for k, lot in enumerate(c.lots):
        e = G.verts(lot)
        sh.dim(e[2], e[3], 4.5, f"{c.cuts[k + 1] - c.cuts[k]:.2f}", 2.8, "#006644")
        sh.dim(e[3], e[0], 4.5, f"{c.depths[k]:.2f}", 2.8, "#006644")
    sh.scalebar(14, sh.oy + sh.plan_h + 30 * sh.p.ts)
    return sh


def schedule(sh: Sheet, option: str, base_plot: G.Plot | None = None):
    """base_plot: the unstretched plot, when this carve sits on a fitted one."""
    c, m = sh.c, sh.c.plot
    t = c.tally()
    sh.open()
    _title(sh, f"TS 11/14/18 — OPTION {option} — SCHEDULE",
           f"lots {t['lots'] / t['plot'] * 100:.1f}% · road {t['road'] / t['plot'] * 100:.1f}%"
           f" · wastage {t['waste'] / t['plot'] * 100:.1f}%")
    sh.txt(14, 18.5, "perpendicular down from D → P · perpendicular up from B → Q · "
           + ("rear line steps down west→east" if c.stepped else "three identical rectangles")
           + f" · road {c.road_w:.2f} ft ⟂ at its narrowest, opening to {c.road_west:.2f} ft",
           3.0, "start", fill="#333")
    a = m.corner_angles
    sh.txt(14, 24, f"sides {m.north:.2f} / {m.east:.2f} / {m.south:.2f} / {m.west:.2f} m · "
           f"closure = {m.area_m2:.1f} m² = {m.area_ft2:,.0f} ft² = {m.area_ft2 / G.CENT:.2f} "
           f"cents · W1 = west corner triangle A-P-D, W2 = east corner triangle B-Q-C",
           3.0, "start", fill="#666")
    sh.txt(14, 29.5, f"closure: {m.derivation}", 3.0, "start", fill="#666")
    sh.txt(14, 34.5, f"corner angles A {a[0]:.2f}° B {a[1]:.2f}° C {a[2]:.2f}° D {a[3]:.2f}° · "
           f"A+C = {a[0] + a[2]:.2f}° so the quadrilateral is "
           f"{'CYCLIC' if m.is_cyclic else 'NOT cyclic'} — Brahmagupta's "
           f"{m.max_area_m2:.1f} m² is out of reach for this shape · "
           f"diagonals AC {m.diagonals_m['AC']:.2f} m, BD {m.diagonals_m['BD']:.2f} m",
           3.0, "start", fill="#666")

    trio = lambda a: [f"{a:,.0f}", f"{a / G.CENT:.2f}", f"{a / G.FT2:.1f}"]
    rows = []
    for k, pc in enumerate(c.lot_pieces):
        w, d = c.cuts[k + 1] - c.cuts[k], c.depths[k]
        rows.append(([pc.name, f"{w:.2f} × {d:.2f} × {w:.2f} × {d:.2f}", pc.why]
                     + trio(pc.area), True))
    for k, b in enumerate(c.road_bays):
        rows.append(([f"{b.name} (over Lot {k + 1})", " × ".join(f"{ln:.2f}" for _, _, ln in G.sides(G.tidy(b.poly))),
                      b.why] + trio(b.area), False))
    rows.append((["LOTS + ROAD", "", ""] + trio(t["lots"] + t["road"]), True))
    rows.append(([" "] * 6, False))
    for pc in c.offcut_pieces:
        rows.append(([pc.name, " × ".join(f"{ln:.2f}" for _, _, ln in G.sides(pc.poly)),
                      pc.why] + trio(pc.area), False))
    rows.append((["WASTAGE", "", ""] + trio(t["waste"]), True))
    y = sh.table(14, sh.p.w - 28, 44, "SCHEDULE — every side length in feet, every area "
                 "from its own arithmetic", rows, ["TOTAL", "", ""] + trio(t["total"]),
                 fs=1.25) + 6
    sh.txt(14, y, f"TALLY   {t['lots'] + t['road']:,.0f} (lots + road)  +  {t['waste']:,.0f} "
           f"(wastage)  =  {t['total']:,.0f} ft²  =  {t['total'] / G.CENT:.2f} cents  =  "
           f"{t['total'] / G.FT2:.1f} m²  =  the whole plot", 3.8, "start", weight="bold")
    y += 6

    if base_plot is not None:
        k = m.north / base_plot.north
        sh.txt(14, y + 2, f"SIDES STRETCHED {(k - 1) * 100:.2f}% from the FMB's "
               f"{base_plot.north:.2f} / {base_plot.east:.2f} / {base_plot.south:.2f} / "
               f"{base_plot.west:.2f} m so the closure equals the REGISTERED "
               f"{m.registered:.0f} m² exactly.", 3.2, "start", fill="#a00")
        sh.txt(14, y + 7, f"Shape and every angle unchanged: each length ×{k:.5f}, each area "
               f"×{k ** 2:.4f}. Verify on the ground before relying on it.", 3.2, "start",
               fill="#a00")
    else:
        pro = m.register_factor
        sh.txt(14, y + 2, f"REGISTERED EXTENT is {m.registered:.0f} m² "
               f"({m.registered * G.FT2:,.0f} ft² / {m.registered * G.FT2 / G.CENT:.2f} cents) "
               f"— {m.registered - m.area_m2:.1f} m² more than these four sides can close "
               f"(absolute maximum {m.max_area_m2:.1f} m²).", 3.2, "start", fill="#a00")
        sh.txt(14, y + 7, f"To price on the register multiply every area above by {pro:.4f}: "
               f"lot = {c.lot_area * pro:,.0f} ft² = {c.lot_area * pro / G.CENT:.2f} cents. "
               f"The fitted-sides option does this by stretching the boundary instead.",
               3.2, "start", fill="#a00")
    return sh


def massing(sh: Sheet, m, title="MASSING — road, rectangle, triangles"):
    """One page: the plot, the slanted road, the big rectangle, the three
    triangles, and the arithmetic that adds them back to the whole."""
    A, B, C, D = m.plot.corners
    sh.c = m
    sh.open()
    _title(sh, "TS 11/14/18 · Ward-16 Thallakulam · Madurai North",
           f"scale 1:{sh.p.denom} — print at 100% on {sh.p.name}", title,
           "north up · all figures in feet")

    fills = {"Road": ("#e9e9e9", "#9e9e9e"), "Rectangle": ("#d8f3f8", "#00b8d4"),
             "T1 under the road": ("#fdf0d5", "#c98a1e")}
    for pc in m.pieces:
        f, st = fills.get(pc.name, ("#f6dcdc", "#8b2f2f"))
        sh.path(pc.poly, f, st, 0.5)
    sh.path(m.plot.quad, "none", "#000", 1.0)
    for a, b in ((m.at(m.x_west, 0), m.F), (B, m.at(m.base, m.depth))):
        sh.line(a, b, "#a00", 0.7)          # the two 90 deg lines off the south boundary

    for pc in m.pieces:
        cx, cy = sh.px(pc.poly.representative_point().coords[0])
        big = pc.name in ("Road", "Rectangle")
        tag = pc.name.split(" ")[0]
        # A sliver is narrower than its own caption: park it clear of the drawing
        # and run a leader back to the shape.
        _, ymin, _, ymax = pc.poly.bounds
        narrow = (pc.poly.bounds[2] - pc.poly.bounds[0]) * sh.sc < 26
        if narrow:
            tx, ty = 20.0, cy + 22
            sh.line((cx, cy), (tx + 12, ty - 4), "#8b2f2f", 0.22, raw=True)
            cx, cy = tx + 12, ty
        sh.txt(cx, cy - (2.0 if big else 0.6), tag, 5.2 if big else 3.8,
               weight="bold", fill="#111" if big else "#8b2f2f")
        sh.txt(cx, cy + (4.0 if big else 4.2), pc.why, 3.6 if big else 3.0)
        sh.txt(cx, cy + (9.0 if big else 8.4),
               f"{pc.area:,.0f} ft² · {pc.area / G.CENT:.2f} cents", 3.2, fill="#444")

    for nm, pt in (("F", m.F), ("E", m.E)):
        cx, cy = sh.px(pt)
        sh.out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.1" fill="#a00"/>')
        sh.txt(cx + 4, cy + 1.2, nm, 3.6, fill="#a00", weight="bold")
    for nm, pt in zip("ABCD", m.plot.corners):
        cx, cy = sh.px(pt)
        sh.txt(cx + (-4.5 if nm in "AD" else 4.5), cy + (4 if nm in "AB" else -2),
               nm, 3.8, weight="bold")

    side = lambda n, x: f"{n}  {x * G.M2FT:.2f}"
    p = m.plot
    sh.dim(D, C, -12, side("north", p.north), 3.2)
    sh.dim(B, A, -19, side("south", p.south), 3.2)
    sh.dim(C, B, -13, side("east", p.east), 3.2)
    sh.dim(A, D, -11, side("west", p.west), 3.2)
    r = G.verts(m.rect)
    sh.dim(r[2], r[3], 4.5, f"rectangle {m.width:.2f}", 2.9, "#006644")
    sh.dim(r[3], r[0], 4.5, f"{m.depth:.2f} deep", 2.9, "#006644")
    sh.dim(m.at(m.x_west, m.depth), m.F, 5.5,
           f"T1 {m.inner(m.x_west) - m.depth:.2f}", 2.8, "#c98a1e")
    sh.dim(m.at(m.base * 0.24, m.inner(m.base * 0.24)),
           m.at(m.base * 0.24, m.height(m.base * 0.24)), 0,
           f"road {m.road_w:.2f} ⟂", 2.8, "#666")
    sh.dim(m.at(m.x_west, 0), A, -11, f"{math.dist(A, m.at(m.x_west, 0)):.2f}", 2.8, "#8b2f2f")

    trio = lambda a: [f"{a:,.0f}", f"{a / G.CENT:.2f}", f"{a / G.FT2:.1f}"]
    rows = [([pc.name, " × ".join(f"{ln:.2f}" for _, _, ln in G.sides(G.tidy(pc.poly))),
              pc.why] + trio(pc.area), pc.name == "Rectangle") for pc in m.pieces]
    y = sh.table(14, sh.p.w - 28, sh.oy + sh.plan_h + 30 * sh.p.ts,
                 f"SCHEDULE — {m.road_w:.0f} ft road, north boundary slants {m.slant:.2f}°",
                 rows, ["TOTAL", "", ""] + trio(m.plot.area_ft2), fs=1.15) + 5
    sh.txt(14, y, f"TALLY   road {m.road.area:,.0f}  +  rectangle {m.rect.area:,.0f}  +  "
           f"triangles {m.t1.area + m.west.area + m.east.area:,.0f}  =  "
           f"{m.plot.area_ft2:,.0f} ft²  =  {m.plot.area_ft2 / G.CENT:.2f} cents  =  "
           f"{m.plot.area_m2:.1f} m²  =  the whole plot", 3.6, "start", weight="bold")
    sh.scalebar(14, y + 11)
    return sh


# ------------------------------------------------ an FMB checked by offsets
def _ft(q):
    return (q[0] / 0.3048, q[1] / 0.3048)


def _right_angle(sh, corner, size=2.2):
    """a small square in the corner that opens up and to the right."""
    x, y = sh.px(corner)
    sh.out.append(f'<path d="M {x + size:.2f},{y:.2f} L {x + size:.2f},{y - size:.2f} '
                  f'L {x:.2f},{y - size:.2f}" fill="none" stroke="#8b2f2f" stroke-width="0.22"/>')


def x_plan(sh: Sheet, rec: dict, xc: dict, shape: str):
    """The plot, B's parallel to CD meeting AD at X, and the feet of X, A and B.
    Measurements only; the arithmetic is on the next sheet."""
    pt = {k: _ft(v) for k, v in xc["points"].items()}
    L = lambda a, b: xc["length"](a, b) / 0.3048
    lab = lambda a, b: f"{a}{b} {L(a, b):.2f}"
    sh.open()
    _title(sh, f"{rec['survey']} · {rec['village']} · {rec['taluk']}",
           f"scale 1:{sh.p.denom} — print at 100% on {sh.p.name}",
           shape, "north up · every length in feet")

    corners = [pt[k] for k in "ABCD"]
    for i in range(4):
        sh.line(corners[i], corners[(i + 1) % 4], "#000", 0.6)
    sh.line(pt["X"], pt["B"], "#333", 0.35)
    for top, foot in (("X", "P"), ("A", "Q"), ("B", "R")):
        sh.line(pt[top], pt[foot], "#8b2f2f", 0.3, dash="1.4 1.0")
    for k in "PQRY":
        _right_angle(sh, pt[k])

    # the four recorded sides, outside the plot
    sh.dim(pt["D"], pt["C"], 17, lab("C", "D") + "  (recorded 45.6 m)")
    sh.dim(pt["D"], pt["A"], -17, lab("D", "A") + "  (recorded 39.6 m)")
    sh.dim(pt["A"], pt["B"], -8, lab("A", "B"))
    sh.dim(pt["B"], pt["C"], -8, lab("B", "C"))
    # CD and DA split by the construction
    for a, b in (("D", "P"), ("P", "Q"), ("Q", "R"), ("R", "C")):
        sh.dim(pt[a], pt[b], 8, lab(a, b))
    sh.dim(pt["D"], pt["X"], -8, lab("D", "X"))
    sh.dim(pt["X"], pt["A"], -8, lab("X", "A"))
    # the parallel, and the three heights
    sh.dim(pt["X"], pt["Y"], -5, lab("X", "Y"))
    sh.dim(pt["Y"], pt["B"], -5, lab("Y", "B"))
    sh.dim(pt["Y"], pt["A"], 5, lab("Y", "A"))
    sh.dim(pt["P"], pt["X"], 5, lab("P", "X"))
    sh.dim(pt["Q"], pt["Y"], 5, lab("Q", "Y"))
    sh.dim(pt["R"], pt["B"], -5, lab("R", "B"))
    bx, by = sh.px(((pt["X"][0] + pt["B"][0]) / 2, pt["X"][1]))
    sh.out.append(f'<rect x="{bx - 13:.2f}" y="{by + 1.2:.2f}" width="26" height="4.2" '
                  f'fill="white"/>')
    sh.txt(bx, by + 4.4, f"BX {L('X', 'B'):.2f}", 3.3, weight="bold")

    # feet sit just above CD, clear of its dimensions; Y below the parallel,
    # clear of XY's tick
    for k, (dx, dy) in dict(A=(0, -5.2), B=(3.4, 0), C=(3.4, 1.2), D=(-3.4, 1.2),
                            X=(-3.2, -1.2), Y=(-2.8, 4.4), P=(-2.6, -2.4), Q=(-2.6, -2.4),
                            R=(-2.6, -2.4)).items():
        x, y = sh.px(pt[k])
        big = k in "ABCD"
        sh.txt(x + dx, y + dy + 1.2, k, 5.0 if big else 3.6,
               weight="bold", fill="#000" if big else "#8b2f2f")

    for name, kind, a, _, _ in xc["pieces"]:
        poly = [pt[c] for c in name]
        cx = sum(q[0] for q in poly) / len(poly)
        cy = sum(q[1] for q in poly) / len(poly)
        x, y = sh.px((cx, cy))
        colour = "#1b5e20" if kind == "rectangle" else "#6a1b9a"
        small = name == "XYA"                        # narrow: smaller type, lifted clear of XY
        fs, lift = (2.5, 2.0) if small else (3.0, 0.0)
        sh.txt(x, y - 0.6 - lift, name, fs, weight="bold", fill=colour)
        sh.txt(x, y + 2.9 - lift, f"{a / 0.3048 ** 2:,.0f} ft²", fs * 0.92, fill=colour)
    sh.scalebar(14, sh.p.h - 13)
    return sh


def x_schedule(sh: Sheet, rec: dict, xc: dict, shape: str, p: G.Plot, others: list):
    sh.open()
    _title(sh, f"{rec['survey']} · areas by offsets", "every length in feet",
           shape, "north up")
    L = lambda a, b: xc["length"](a, b) / 0.3048
    F2, CENT = 1 / 0.3048 ** 2, 435.6
    rows = []
    for name, kind, a, (b1, b2), (h1, h2) in xc["pieces"]:
        base, high = L(b1, b2), L(h1, h2)
        why = (f"½ × {base:.2f} × {high:.2f}" if kind == "triangle"
               else f"{base:.2f} × {high:.2f}")
        rows.append(([f"{kind} {name}", f"{b1}{b2} {base:.2f}, {h1}{h2} {high:.2f}",
                      why, f"{a * F2:,.1f}", f"{a * F2 / CENT:.2f}", f"{a:.1f}"], False))
    tot = xc["area_m2"]
    # a page of its own, so the type can be read at arm's length
    y = sh.table(14, sh.p.w - 28, 34, "Two rectangles and four right triangles", rows,
                 foot=["TOTAL", "", "adds back to the plot", f"{tot * F2:,.1f}",
                       f"{tot * F2 / CENT:.2f}", f"{tot:.1f}"], fs=1.45)

    names = {v: k for k, v in __import__("tslr.survey", fromlist=["letters"]).letters(rec).items()}
    ang = dict(zip(rec["walk"], p.corner_angles))
    lines = [
        "Letters: A at the top, then B, C, D clockwise. On the FMB these are "
        + ", ".join(f"{k} = corner {v}" for k, v in
                    __import__("tslr.survey", fromlist=["letters"]).letters(rec).items()
                    if k != v) + ".",
        "Corner angles: " + ", ".join(f"{names[k]} {ang[k]:.2f}°" for k in rec["walk"][::-1]) + ".",
        f"Registered {rec['registered_as']} = {rec['registered_m2']:.0f} m² = "
        f"{rec['registered_m2'] * F2:,.1f} ft² = {rec['registered_m2'] * F2 / CENT:.2f} cents.",
    ]
    y += 8
    for t in lines:
        sh.txt(14, y, t, 4.2, "start")
        y += 7.4
    y += 4
    sh.txt(14, y, "The same four sides, closed other ways", 5.0, "start", weight="bold")
    y += 8
    for label, area, note in others:
        sh.txt(18, y, f"{label}", 4.2, "start", weight="bold")
        sh.txt(85, y, f"{area * F2:,.0f} ft²  =  {area * F2 / CENT:.2f} cents", 4.2, "start")
        sh.txt(165, y, note, 3.8, "start", fill="#555")
        y += 7.2
    return sh


# ------------------------------------------- a road down one side, equal lots
def _option(f) -> str:
    kind = ("IDENTICAL RECTANGLES, BALANCE SEPARATE" if f.shape == "rect"
            else "EQUAL LOTS, NOTHING LEFT OVER")
    road = (f"COMMON ROAD {f.gate_end:.0f} FT AT THE GATE NARROWING TO "
            f"{f.road_w:.0f} FT" if f.gate_w is not None
            else f"COMMON ROAD {f.road_w:.0f} FT WEST")
    par = " · LOTS PARALLEL TO AB" if f.square_to is not None else ""
    return f"{road} · {f.n} {kind}{par}"


def _poly_ft(g):
    return [(x, y) for x, y in g.exterior.coords[:-1]]


def frontage_plan(sh: Sheet, rec: dict, f, letters: dict, web=False):
    """The plot, the common road down one boundary, and the lots behind it.

    Measurements only. The arithmetic that adds them back to the plot is on the
    sheet after this one.
    """
    FT = 1 / 0.3048
    corner = {k: (x * FT, y * FT) for k, (x, y) in zip(rec["walk"], rec["corners_m"])}
    sh.open()
    _title(sh, f"{rec['survey']} · {rec['village']} · {rec['taluk']}",
           "north up · every length in feet" if web else
           f"scale 1:{sh.p.denom} — print at 100% on {sh.p.name}",
           _option(f), "" if web else "north up · every length in feet")

    sh.path(f.road, fill="#f1f1f1", stroke="none")
    for g in f.balance:
        sh.path(g, fill="#fdf3e3", stroke="#c98a1e", width=0.3, dash="1.6 1.1")
    for g in f.lots:
        sh.path(g, stroke="#1b5e20", width=0.35)
    sh.path(f.land, stroke="#000", width=0.7)

    # the four recorded sides, outside the plot, plus the road's inner edge
    walk = rec["walk"]
    for i, k in enumerate(walk):
        a, b = corner[k], corner[walk[(i + 1) % len(walk)]]
        lab = f"{letters[k]}{letters[walk[(i + 1) % len(walk)]]} " \
              f"{math.dist(a, b):.2f}"
        sh.dim(a, b, -11, lab)

    # what each lot fronts onto, read along that inner edge
    # lots set out parallel to another boundary do not divide the road's edge
    # between them, so there is nothing to dimension along it
    (ux, uy) = f.iu
    run = 0.0
    for i, g in enumerate(f.lots):
        w = f.frontage(g)
        if w < 1.0:
            continue
        p0 = (f.inner[0][0] + ux * run, f.inner[0][1] + uy * run)
        p1 = (f.inner[0][0] + ux * (run + w), f.inner[0][1] + uy * (run + w))
        sh.dim(p0, p1, 4, f"{w:.2f}", colour="#1b5e20")
        run += w
    if f.shape == "rect":
        q = list(f.lots[0].exterior.coords[:-1])
        sh.dim(q[0], q[1], -4, f"{math.dist(q[0], q[1]):.2f}", colour="#1b5e20")
        sh.dim(q[1], q[2], -4, f"{math.dist(q[1], q[2]):.2f}", colour="#1b5e20")
    sh.dim(corner[rec["road"]["along"].split("-")[0]], f.inner[0], -4,
           f"{f.gate_end:.2f}", colour="#a00")
    if f.gate_w is not None:
        sh.dim(corner[rec["walk"][0]], f.inner[1], 4, f"{f.far_end:.2f}", colour="#a00")

    for i, g in enumerate(f.lots):
        c = g.representative_point()
        x, y = sh.px((c.x, c.y))
        sh.txt(x, y - 1.0, f"LOT {i + 1}", 4.0, weight="bold", fill="#1b5e20")
        sh.txt(x, y + 4.0, f"{g.area:,.0f} ft²", 3.2, fill="#1b5e20")
        sh.txt(x, y + 8.0, f"{g.area / G.CENT:.2f} cents", 3.0, fill="#1b5e20")
    # A balance parcel is thin, so its figures will not sit on it without
    # covering a boundary or a dimension. It carries a numbered tag instead,
    # and the numbers are spelled out under the drawing.
    for i, (w, g) in enumerate(zip(f.balance_where, f.balance), 1):
        c = g.representative_point()
        x, y = sh.px((c.x, c.y))
        sh.out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" fill="#fff" '
                      f'stroke="#c98a1e" stroke-width="0.4"/>')
        sh.txt(x, y + 1.3, str(i), 3.3, weight="bold", fill="#c98a1e")
    ly = sh.p.h - 34
    if f.balance:
        sh.txt(14, ly, "BALANCE, not spoken for", 3.0, "start", weight="bold",
               fill="#c98a1e")
        for i, (w, g) in enumerate(zip(f.balance_where, f.balance), 1):
            free = f.frontage(g) > 1.0
            ly += 4.4
            sh.txt(15, ly, f"{i}", 2.9, "start", weight="bold", fill="#c98a1e")
            sh.txt(19, ly, f"{w} — {g.area:,.0f} ft² · {g.area / G.CENT:.2f} cents · "
                   + (f"{f.frontage(g):.2f} ft on the road" if free
                      else "no frontage, attach to the lot beside it"),
                   2.9, "start", fill="#555" if free else "#a00")
    c = f.road.representative_point()
    x, y = sh.px((c.x, c.y))
    sh.txt(x, y, f"COMMON ROAD {f.road_w:.0f} ft", 3.4, weight="bold",
           fill="#555", rot=-78)

    # the gate, at the corner the record names
    g0 = corner[rec["road"]["gate"].split(",")[0]]
    gx, gy = sh.px(g0)
    sh.txt(gx - 4, gy + 9, "GATE", 3.4, "end", weight="bold", fill="#a00")
    sh.line((gx - 3, gy + 7.5), (gx + 2, gy + 2.5), "#a00", 0.6, raw=True)

    for k, p in corner.items():
        x, y = sh.px(p)
        sh.out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.1" fill="#000"/>')
        sh.txt(x + 4.5, y - 2.5, f"{letters[k]}", 4.6, weight="bold")
        sh.txt(x + 4.5, y + 1.8, f"({k})", 2.8, fill="#777")
    # a screen has no scale, and the 100 mm check bar means nothing on one
    if not web:
        sh.scalebar(14, sh.p.h - 13)
    return sh


def frontage_schedule(sh: Sheet, rec: dict, f, letters: dict):
    """The arithmetic, and the check that it adds back to the registered plot."""
    F2, CENT = 1 / 0.3048 ** 2, G.CENT
    sh.open()
    _title(sh, f"{rec['survey']} · areas", "every length in feet",
           _option(f), "north up")
    rows = []
    for i, (p, w) in enumerate(zip(f.pieces(), f.frontages + [None])):
        rows.append(([p.name,
                      f"{w:.2f} ft on the road" if w is not None else
                      f"{f.run:.2f} ft along the boundary, {f.road_w:.2f} ft wide",
                      p.why, f"{p.area:,.1f}", f"{p.area / CENT:.2f}",
                      f"{p.area * 0.3048 ** 2:.1f}"], False))
    t = f.tally()
    y = sh.table(14, sh.p.w - 28, 34, "Lots and road, by fans of triangles", rows,
                 foot=["TALLY", "parts sum to the plot", "", f"{t['total']:,.1f}",
                       f"{t['total'] / CENT:.2f}", f"{t['total'] * 0.3048 ** 2:.1f}"],
                 fs=1.35, cw=[0.08, 0.17, 0.42, 0.12, 0.10, 0.11])
    lo, hi = f.widths
    reg = rec["registered_m2"]
    drawn = f.land.area * 0.3048 ** 2
    lines = [
        "Corners keep the FMB's own numbers, with a letter beside each: "
        + ", ".join(f"{v} = {k}" for k, v in letters.items()) + ".",
        f"The road runs {f.run:.2f} ft up the west boundary from the "
        f"gate at {letters[rec['road']['gate'].split(',')[0]]}. It is "
        f"{lo:.2f} ft at its narrowest and {hi:.2f} ft at its widest, because its "
        f"inner edge is parallel to the boundary.",
        f"Every lot reaches it: {', '.join(f'{w:.2f}' for w in f.frontages)} ft of "
        f"frontage, summing to the {math.dist(*f.inner):.2f} ft inner edge.",
        f"Registered {rec['registered_as']} = {reg:,.0f} m². The FMB's own line "
        f"work encloses {drawn:,.1f} m², which is {drawn - reg:+.1f} m² "
        f"({(drawn / reg - 1) * 100:+.2f}%) against it.",
        (f"Road takes {t['road'] / t['plot']:.1%} of the plot. The {f.n} lots, the "
         f"{len(f.balance)} balance parcels and the road are the whole of it."
         if f.balance else
         f"Road takes {t['road'] / t['plot']:.1%} of the plot. Nothing is wasted: "
         f"the {f.n} lots and the road are the whole of it."),
    ]
    y += 8
    for s in lines:
        for line in _wrap(s, 112):
            sh.txt(14, y, line, 3.6, "start")
            y += 5.0
        y += 2.6
    return sh


def _wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + ([line] if line else [])
