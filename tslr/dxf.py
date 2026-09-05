"""Write the carve as a DXF, which every CAD program opens.

FreeCAD 1.1.3 segfaults on this machine's macOS in Qt's Cocoa accessibility
bridge. It does so with an empty document and nobody touching it, so its window
cannot be relied on. The geometry does not depend on that window. A DXF opens
in LibreCAD, QCAD, AutoCAD, and most online viewers.

Written in metres, which is what a land drawing is dimensioned in here. The
header declares the unit, so a reader does not have to guess.
"""
from __future__ import annotations

from pathlib import Path

M2FT = 1 / 0.3048

# layer name -> DXF colour index
LAYERS = {"BOUNDARY": 7, "LOTS": 4, "ROAD": 8, "HEAD": 9,
          "BUILDABLE": 6, "TEXT": 2}


def _pair(code, value):
    return f"{code}\n{value}\n"


def _polyline(ring, layer):
    """A closed LWPOLYLINE. Closed by flag 70, not by repeating the first point."""
    out = _pair(0, "LWPOLYLINE") + _pair(8, layer) + _pair(100, "AcDbEntity")
    out += _pair(100, "AcDbPolyline") + _pair(90, len(ring)) + _pair(70, 1)
    for x, y in ring:
        out += _pair(10, f"{x:.4f}") + _pair(20, f"{y:.4f}")
    return out


def _text(at, height, s, layer="TEXT"):
    return (_pair(0, "TEXT") + _pair(8, layer) + _pair(10, f"{at[0]:.4f}")
            + _pair(20, f"{at[1]:.4f}") + _pair(40, f"{height:.4f}")
            + _pair(1, s))


def write(spec: dict, out: Path) -> Path:
    """`spec` is the same one the FreeCAD build takes: rings in feet."""
    m = lambda p: (p[0] / M2FT, p[1] / M2FT)
    body = _pair(0, "SECTION") + _pair(2, "HEADER")
    body += _pair(9, "$INSUNITS") + _pair(70, 6)          # 6 = metres
    body += _pair(0, "ENDSEC")

    body += _pair(0, "SECTION") + _pair(2, "TABLES")
    body += _pair(0, "TABLE") + _pair(2, "LAYER") + _pair(70, len(LAYERS))
    for name, colour in LAYERS.items():
        body += (_pair(0, "LAYER") + _pair(2, name) + _pair(70, 0)
                 + _pair(62, colour) + _pair(6, "CONTINUOUS"))
    body += _pair(0, "ENDTAB") + _pair(0, "ENDSEC")

    body += _pair(0, "SECTION") + _pair(2, "ENTITIES")
    body += _polyline([m(p) for p in spec["corners_ft"]], "BOUNDARY")
    for layer, items in (("LOTS", spec["lots"]), ("ROAD", spec["common"]),
                         ("BUILDABLE", spec["buildable"])):
        for it in items:
            ring = [m(p) for p in it["ring"]]
            lay = "HEAD" if "head" in it["label"].lower() else layer
            body += _polyline(ring, lay)
            at = (sum(p[0] for p in ring) / len(ring),
                  sum(p[1] for p in ring) / len(ring))
            body += _text(at, 0.9, it["label"])
    body += _pair(0, "ENDSEC") + _pair(0, "EOF")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    return out
