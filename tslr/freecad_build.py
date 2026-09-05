"""Build the plot and its carve as a FreeCAD document.

Runs under FreeCAD's own Python, which has no shapely, so it is handed a JSON
spec rather than importing the rest of the package:

    TSLR_SPEC=spec.json TSLR_OUT=out.FCStd freecadcmd tslr/freecad_build.py

The paths come through the environment because freecadcmd reads anything else
on its command line as a file to open, and tries to import it.

The boundary is a real Sketch. Its four sides and the A-C diagonal are
dimensional constraints, so the shape is not a picture of the figures. It is
driven by them, and editing a constraint moves the plot. Everything else is a
face, labelled with what it is worth.

Coordinates arrive in feet and are built in millimetres at full size, so
FreeCAD's own measuring tools give ground truth.
"""
import json
import os
import sys

import FreeCAD as App
import Part
import Sketcher

MM = 304.8                                   # millimetres in a foot


def vec(p):
    return App.Vector(p[0] * MM, p[1] * MM, 0)


def boundary(doc, spec):
    """The four sides and the diagonal, as constraints rather than as drawing."""
    sk = doc.addObject("Sketcher::SketchObject", "Boundary")
    sk.Label = "Boundary - the four recorded sides"
    q = [vec(p) for p in spec["corners_ft"]]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(q[i], q[(i + 1) % 4]), False)
    for i in range(4):                       # 1 is a line's start, 2 its end
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0.0))
    sk.addConstraint(Sketcher.Constraint("DistanceY", 0, 1, 0.0))
    for i, key in enumerate(("south", "east", "north", "west")):
        n = sk.addConstraint(Sketcher.Constraint("Distance", i, spec["sides_m"][key] * 1000))
        sk.renameConstraint(n, key)
    # the diagonal is construction geometry: it fixes the shape without being a side
    d = sk.addGeometry(Part.LineSegment(q[0], q[2]), True)
    sk.addConstraint(Sketcher.Constraint("Coincident", d, 1, 0, 1))
    sk.addConstraint(Sketcher.Constraint("Coincident", d, 2, 2, 1))
    n = sk.addConstraint(Sketcher.Constraint("Distance", d, spec["diagonal_m"] * 1000))
    sk.renameConstraint(n, "diagonal_AC")
    return sk


def face(doc, item, wire_only=False):
    """One carved piece, as a face you can click and measure."""
    pts = [vec(p) for p in item["ring"]]
    w = Part.makePolygon(pts + [pts[0]])
    obj = doc.addObject("Part::Feature", item["key"])
    obj.Shape = w if wire_only else Part.Face(w)
    obj.Label = item["label"]
    if App.GuiUp and item.get("colour"):
        r, g, b = (c / 255 for c in item["colour"])
        obj.ViewObject.ShapeColor = (r, g, b)
        obj.ViewObject.LineColor = (r * 0.6, g * 0.6, b * 0.6)
        obj.ViewObject.LineWidth = 2
        if wire_only:
            obj.ViewObject.DrawStyle = "Dashed"
        else:
            obj.ViewObject.Transparency = 35
    return obj


def build(spec, out):
    doc = App.newDocument(spec["name"].replace("/", "-"))
    boundary(doc, spec)
    for group, items, wire in (("Lots", spec["lots"], False),
                               ("Common", spec["common"], False),
                               ("Buildable", spec["buildable"], True)):
        if not items:
            continue
        g = doc.addObject("App::DocumentObjectGroup", group.replace(" ", "_"))
        g.Label = group
        g.Group = [face(doc, it, wire) for it in items]
    doc.recompute()
    doc.saveAs(out)
    if App.GuiUp:
        # the plot lies in the XY plane, so look straight down at it
        import FreeCADGui as Gui
        Gui.activeDocument().activeView().viewTop()
        Gui.SendMsgToActiveView("ViewFit")
    print(f"boundary: {len(doc.Boundary.Constraints)} constraints, "
          f"{doc.Boundary.FullyConstrained and 'fully constrained' or 'UNDER-CONSTRAINED'}")
    for name in ("Lots", "Common", "Buildable"):
        g = doc.getObject(name.replace(" ", "_"))
        if g:
            print(f"{name}: " + ", ".join(o.Label for o in g.Group))
    print("wrote " + out)
    return doc


# freecadcmd execs this file without setting __name__ to "__main__", so the
# environment is what says to run.
if os.environ.get("TSLR_SPEC"):
    with open(os.environ["TSLR_SPEC"]) as fh:
        build(json.load(fh), os.environ["TSLR_OUT"])
    if not App.GuiUp:
        sys.exit(0)
