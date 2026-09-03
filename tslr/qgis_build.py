"""Build a QGIS project from the exported GeoJSON layers.

Runs under QGIS's own bundled Python, not the project venv:

    /Applications/QGIS.app/Contents/MacOS/python -m tslr.qgis_build <geojson_dir> <out.qgz>

A .qgz is a zipped document whose layer ids, styles and CRS blocks must agree;
QGIS writes it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from qgis.core import (QgsApplication, QgsCoordinateReferenceSystem, QgsFillSymbol,
                       QgsMarkerSymbol, QgsPalLayerSettings, QgsProject, QgsRasterLayer,
                       QgsTextFormat, QgsVectorFileWriter, QgsVectorLayer,
                       QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor

# name -> (fill, stroke, stroke width mm, label field)
STYLE = {
    "plot_boundary": ("0,0,0,0", "#e8590c", 0.9, None),
    "lots":          ("0,229,255,45", "#00b8d4", 0.5, "name"),
    "road":          ("255,255,255,60", "#9e9e9e", 0.4, None),
    "offcuts":       ("246,220,220,120", "#8b2f2f", 0.4, "name"),
}
BASEMAPS = {
    "Esri World Imagery": "https://server.arcgisonline.com/ArcGIS/rest/services/"
                          "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D",
    "OpenStreetMap": "https://tile.openstreetmap.org/%7Bz%7D/%7Bx%7D/%7By%7D.png",
}
ORDER = ["plot_boundary", "corners", "pins_observed", "lots", "offcuts", "road"]


def label(layer, field, expression=False, colour="#00363d", size=10):
    s = QgsPalLayerSettings()
    s.fieldName = field
    s.isExpression = expression
    s.enabled = True
    fmt = QgsTextFormat()
    fmt.setSize(size)
    fmt.setColor(QColor(colour))
    buf = fmt.buffer()
    buf.setEnabled(True)
    buf.setSize(1.0)
    buf.setColor(QColor("white"))
    fmt.setBuffer(buf)
    s.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
    layer.setLabelsEnabled(True)


VARIANT = ["lots", "offcuts", "road"]      # these carry both layouts in one table


def styled(gpkg, name, title, variant=None):
    uri = f"{gpkg}|layername={name}"
    lyr = QgsVectorLayer(uri, title, "ogr")
    if not lyr.isValid():
        return None
    if variant:
        lyr.setSubsetString(f"variant = '{variant}'")
    if name in STYLE:
        fill, stroke, w, lab = STYLE[name]
        lyr.renderer().setSymbol(QgsFillSymbol.createSimple(
            {"color": fill, "outline_color": stroke, "outline_width": str(w)}))
        if lab:
            label(lyr, lab)
    elif "pins" in name:
        # the observed pins sit almost on top of the fitted corners: label them
        # with what is actually worth reading, the residual
        lyr.renderer().setSymbol(QgsMarkerSymbol.createSimple(
            {"name": "circle", "size": "2.0", "outline_color": "white",
             "color": "255,45,85,255"}))
        label(lyr, "concat(name, '  ', format_number(residual_m, 2), ' m')",
              expression=True, colour="#8b0030", size=8)
    else:
        lyr.renderer().setSymbol(QgsMarkerSymbol.createSimple(
            {"name": "circle", "size": "2.6", "outline_color": "white",
             "color": "232,89,12,255"}))
        label(lyr, "name", colour="#8a3500", size=11)
    return lyr


def build(src_dir: Path, out: Path, gpkg: Path, epsg=32644):
    # Data source paths are stored relative to the project file, so these are
    # resolved absolute.
    src_dir, out, gpkg = (Path(x).resolve() for x in (src_dir, out, gpkg))
    qgs = QgsApplication([], False)
    qgs.initQgis()
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem(f"EPSG:{epsg}"))
    project.setTitle("TS 11/14/18 — Thallakulam subdivision")
    root = project.layerTreeRoot()

    gpkg.unlink(missing_ok=True)
    for name in ORDER:                                       # geojson -> geopackage
        src = src_dir / f"{name}.geojson"
        if not src.exists():
            continue
        v = QgsVectorLayer(str(src), name, "ogr")
        if not v.isValid():
            print(f"  !! {name} failed to load", file=sys.stderr)
            continue
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName, opts.layerName = "GPKG", name
        opts.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteFile
                                     if not gpkg.exists()
                                     else QgsVectorFileWriter.CreateOrOverwriteLayer)
        err = QgsVectorFileWriter.writeAsVectorFormatV3(
            v, str(gpkg), project.transformContext(), opts)
        if err[0] != QgsVectorFileWriter.NoError:
            print(f"  !! {name}: {err}", file=sys.stderr)

    # addMapLayer prepends to the tree, so legend order is set explicitly.
    tree = []
    for name in ("plot_boundary", "corners", "pins_observed"):
        lyr = styled(gpkg, name, name)
        if lyr:
            project.addMapLayer(lyr, False)
            tree.append(("layer", lyr))
            print(f"  + {name}: {len(list(lyr.getFeatures()))} features")
    # Each layout variant is its own group; one is shown at a time.
    for variant in ("level", "stepped"):
        members = []
        for name in VARIANT:
            lyr = styled(gpkg, name, f"{name} ({variant})", variant)
            if lyr:
                project.addMapLayer(lyr, False)
                members.append(lyr)
                print(f"  + {name} ({variant}): {len(list(lyr.getFeatures()))} features")
        tree.append(("group", variant.upper(), members, variant == "level"))
    for name, url in BASEMAPS.items():
        r = QgsRasterLayer(f"type=xyz&url={url}&zmax=21&zmin=0", name, "wms")
        if r.isValid():
            project.addMapLayer(r, False)
            tree.append(("layer", r, name == "Esri World Imagery"))
            print(f"  + basemap: {name}")

    for i, node in enumerate(tree):
        if node[0] == "layer":
            n = root.insertLayer(i, node[1])
            n.setItemVisibilityChecked(node[2] if len(node) > 2 else True)
        else:
            g = root.insertGroup(i, node[1])
            for lyr in node[2]:
                g.addLayer(lyr)
            g.setItemVisibilityChecked(node[3])

    out.unlink(missing_ok=True)
    ok = project.write(str(out))
    # exitQgis() segfaults headless after the project is on disk.
    print(f"  = {out}" if ok else "  !! project.write failed")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if ok else 1)


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "generated/gis")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else src / "tslr_11-14-18.qgz")
    build(src, out, out.with_suffix(".gpkg"))
