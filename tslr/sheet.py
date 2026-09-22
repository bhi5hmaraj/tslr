"""Turning a Carve into printable sheets.

A `Sheet` is a paper size plus a drawing scale, and knows how to map plot feet
to millimetres on that paper. Every length below is in mm; `ts` shrinks type,
dimension offsets and table rows together so the same page code works on A3
and A4 without anything colliding.

Two page templates: `plan` carries measurements and nothing else, `schedule`
carries the arithmetic that adds those measurements back up to the plot.
"""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass

from . import geometry as G

FONT = "Helvetica,Arial,sans-serif"


@dataclass(frozen=True)
class Paper:
    name: str
    w: float            # mm
    h: float
    denom: int          # drawing scale 1:denom
    ts: float           # type / spacing scale
    oy: float           # top of the plan area, mm


A3 = Paper("A3", 420.0, 297.0, 250, 1.00, 56.0)
A4 = Paper("A4", 297.0, 210.0, 300, 0.78, 55.0)


class Sheet:
    """Coordinate mapping and SVG primitives for one page."""

    def __init__(self, carve, paper: Paper = A4):
        self.c, self.p = carve, paper
        self.sc = 0.3048 * 1000 / paper.denom          # mm per foot
        # a bare Plot or polygon draws as well as a Carve: only the boundary
        # sets the frame
        plot = getattr(carve, "plot", carve)
        self.minx, self.miny, self.maxx, self.maxy = getattr(plot, "quad", plot).bounds
        self.plan_w = (self.maxx - self.minx) * self.sc
        self.plan_h = (self.maxy - self.miny) * self.sc
        self.ox = (paper.w - self.plan_w) / 2
        self.oy = paper.oy
        self.out = []

    # -- mapping ----------------------------------------------------------
    def px(self, pt):
        """plot feet -> paper mm, north up."""
        return (self.ox + (pt[0] - self.minx) * self.sc,
                self.oy + (self.maxy - pt[1]) * self.sc)

    # -- primitives -------------------------------------------------------
    def open(self):
        self.out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.p.w}mm" '
                    f'height="{self.p.h}mm" viewBox="0 0 {self.p.w} {self.p.h}">',
                    '<rect width="100%" height="100%" fill="white"/>']
        return self

    def txt(self, x, y, s, size=2.8, anchor="middle", fill="#111", weight="normal", rot=None):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;")
        g = (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size * self.p.ts}" '
             f'text-anchor="{anchor}" fill="{fill}" font-family="{FONT}" '
             f'font-weight="{weight}">{s}</text>')
        self.out.append(g if rot is None else
                        f'<g transform="rotate({rot:.2f} {x:.2f} {y:.2f})">{g}</g>')

    def path(self, poly, fill="none", stroke="#000", width=0.45, dash=None):
        d = "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in
                              (self.px(c) for c in G.verts(poly))) + " Z"
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
                        f'stroke-width="{width}"{extra}/>')

    def line(self, a, b, stroke="#000", width=0.5, dash=None, raw=False):
        (x1, y1), (x2, y2) = (a, b) if raw else (self.px(a), self.px(b))
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                        f'stroke="{stroke}" stroke-width="{width}"{extra}/>')

    def dim(self, p, q, off, label, size=2.7, colour="#0033aa"):
        """dimension line parallel to p-q, pushed `off` mm to its left-hand side."""
        off, size = off * self.p.ts, size * self.p.ts
        (x1, y1), (x2, y2) = self.px(p), self.px(q)
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        nx, ny = -dy / L, dx / L
        ax, ay, bx, by = x1 + nx * off, y1 + ny * off, x2 + nx * off, y2 + ny * off
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        ang += 180 if ang > 90 or ang < -90 else 0
        self.line((ax, ay), (bx, by), colour, 0.18, raw=True)
        for (ex, ey), (sx, sy) in (((ax, ay), (x1, y1)), ((bx, by), (x2, y2))):
            ux, uy = ex - sx, ey - sy
            m = math.hypot(ux, uy) or 1
            self.line((ex - ux / m * 1.6, ey - uy / m * 1.6), (ex, ey), colour, 0.15, raw=True)
            self.line((ex - nx * 1.1, ey - ny * 1.1), (ex + nx * 1.1, ey + ny * 1.1),
                      colour, 0.25, raw=True)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        self.out.append(
            f'<g transform="rotate({ang:.2f} {mx:.2f} {my:.2f})">'
            f'<rect x="{mx - len(label) * size * 0.30:.2f}" y="{my - size * 0.95:.2f}" '
            f'width="{len(label) * size * 0.60:.2f}" height="{size * 1.25:.2f}" fill="white"/>'
            f'<text x="{mx:.2f}" y="{my + size * 0.32:.2f}" font-size="{size}" '
            f'text-anchor="middle" fill="{colour}" font-family="{FONT}">{label}</text></g>')

    def height_mark(self, tri, base, h):
        """dashed perpendicular from a triangle's base to its apex, labelled."""
        ft = G.foot(G.apex(tri, base), base[0], base[1])
        (x1, y1), (x2, y2) = self.px(ft), self.px(G.apex(tri, base))
        self.line((x1, y1), (x2, y2), "#8b2f2f", 0.22, dash="1.2 0.9", raw=True)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self.out.append(f'<rect x="{mx - 5:.2f}" y="{my - 1.6:.2f}" width="10" height="3.2" '
                        f'fill="white" opacity=".85"/>')
        self.txt(mx, my + 0.9, f"h {h:.2f}", 2.5, fill="#8b2f2f")

    def table(self, x0, w, y0, head, rows, foot=None, fs=1.0, cw=None):
        # a page whose arithmetic is long needs the width spent differently
        cw = cw or [0.11, 0.30, 0.24, 0.12, 0.11, 0.12]
        cols = [x0 + w * sum(cw[:i]) for i in range(6)]
        ts = self.p.ts
        self.txt(x0, y0, head, 3.8 * fs, "start", weight="bold")
        for cx, h in zip(cols, ["piece", "sides (ft)", "area = base × height",
                                "area ft²", "cents", "m²"]):
            self.txt(cx, y0 + 6.5 * ts, h, 2.7 * fs, "start", fill="#666", weight="bold")
        self.line((x0, y0 + 8.4 * ts), (x0 + w, y0 + 8.4 * ts), "#999", 0.2, raw=True)
        y = y0 + 13.4 * ts
        for cells, bold in rows:
            for cx, v in zip(cols, cells):
                self.txt(cx, y, v, 2.75 * fs, "start", weight="bold" if bold else "normal")
            y += 4.6 * ts * fs
        if foot:
            self.line((x0, y - 3.4 * ts), (x0 + w, y - 3.4 * ts), "#999", 0.2, raw=True)
            for cx, v in zip(cols, foot):
                self.txt(cx, y + 1.4 * ts, v, 2.9 * fs, "start", weight="bold")
            y += 6 * ts
        return y

    def scalebar(self, x, y):
        """graphic scale plus a 100 mm bar that proves the print wasn't resized."""
        d = self.p.denom
        mm_per_m = 1000.0 / d
        self.txt(x, y - 2.5, f"SCALE 1:{d}  —  1 mm on paper = {d / 1000:.2f} m = "
                 f"{d / 1000 * G.M2FT:.2f} ft on the ground", 2.9, "start", weight="bold")
        for k in range(5):
            self.out.append(f'<rect x="{x + k * 5 * mm_per_m:.3f}" y="{y:.2f}" '
                            f'width="{5 * mm_per_m:.3f}" height="2.2" '
                            f'fill="{"#111" if k % 2 else "#fff"}" stroke="#111" '
                            f'stroke-width=".2"/>')
        for k in range(6):
            self.txt(x + k * 5 * mm_per_m, y + 5.2, k * 5, 2.5)
        self.txt(x + 25 * mm_per_m + 4, y + 5.2, "m", 2.5, "start")
        x2 = x + 25 * mm_per_m + 34
        self.line((x2, y + 1.1), (x2 + 100, y + 1.1), "#a00", 0.5, raw=True)
        for e in (x2, x2 + 100):
            self.line((e, y - 1.4), (e, y + 3.6), "#a00", 0.5, raw=True)
        self.txt(x2, y + 5.4, "this bar is exactly 100 mm — check it with a ruler; if it "
                 "differs the print was resized", 2.6, "start", fill="#a00")

    def save(self, path_stem):
        self.out.append("</svg>")
        svg = f"{path_stem}.svg"
        with open(svg, "w") as fh:
            fh.write("\n".join(self.out))
        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", f"{path_stem}.pdf", svg], check=True)
        return f"{path_stem}.pdf"
