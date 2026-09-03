"""Build the option set as one PDF, and optionally the QGIS project.

    python -m tslr                       # A4, all three options
    python -m tslr --paper A3 --out generated/plan.pdf
    python -m tslr --sides 72.60 25 63.20 30 --road 20
    python -m tslr --optimize            # best block of identical lots, per road width
    python -m tslr --gis                 # + GeoPackage, .qgz and the map overlay
    python -m tslr --html                # + site/index.html, the interactive viewer

Sides and corner pins default to tslr/site.json, which is the durable record of
what was measured and where it came from -- edit that rather than passing flags.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from . import CENT, Carve, Plot, Sheet, pages
from .geometry import Massing, diagonal_for_area, side_for_area
from .sheet import A3, A4

PAPERS = {"A3": A3, "A4": A4}
QGIS_PY = "/Applications/QGIS.app/Contents/MacOS/python"


def options(plot: Plot, road: float):
    """(label, carve, base_plot_or_None) for each layout worth printing."""
    fitted = plot.fitted()
    return [("A — LEVEL", Carve(plot, road), None),
            ("B — STEPPED", Carve(plot, road, stepped=True), None),
            (f"C — LEVEL, SIDES FITTED TO {plot.registered:.0f} m²",
             Carve(fitted, road), plot)]


def build(plot: Plot, out: Path, paper=A4, road=15.0):
    pdfs = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, carve, base) in enumerate(options(plot, road)):
            sheet = lambda: Sheet(carve, paper)
            pdfs.append(pages.plan(sheet(), label).save(f"{tmp}/{i}a"))
            pdfs.append(pages.schedule(sheet(), label, base).save(f"{tmp}/{i}b"))
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdfunite", *pdfs, str(out)], check=True)
    return out


def summary(plot: Plot, road: float):
    a = plot.corner_angles
    lines = [f"plot {plot.area_ft2:,.0f} ft² = {plot.area_ft2 / CENT:.2f} cents = "
             f"{plot.area_m2:.1f} m²   (registered {plot.registered:.0f}, "
             f"four-side maximum {plot.max_area_m2:.1f})",
             f"  closure: {plot.derivation}",
             f"  angles A{a[0]:.2f} B{a[1]:.2f} C{a[2]:.2f} D{a[3]:.2f} · A+C = "
             f"{a[0] + a[2]:.2f}° · " + ("cyclic" if plot.is_cyclic else "not cyclic")
             + f" · diagonals AC {plot.diagonals_m['AC']:.2f} m, "
               f"BD {plot.diagonals_m['BD']:.2f} m"]
    if plot.diagonal is None:
        for ends in ("AC", "BD"):
            roots, peak, at = diagonal_for_area(plot, ends)
            lines.append(f"  to reach {plot.registered:.0f} m² the {ends} tape would read "
                         + (" or ".join(f"{v:.2f} m" for v in roots) if roots else
                            f"nothing — the best any {ends} gives is {peak:.1f} m² at {at:.2f} m"))
    for label, carve, _ in options(plot, road):
        t = carve.tally()
        lines.append(f"  {label:<40} lot {carve.lot_area:6,.0f} ft² "
                     f"({carve.lot_area / CENT:5.2f} cents)  lots {t['lots'] / t['plot']:5.1%}"
                     f"  road {t['road'] / t['plot']:5.1%}  waste {t['waste'] / t['plot']:5.1%}")
    return "\n".join(lines)


def optimise(plot: Plot, road: float, lots: int):
    """Is our construction leaving land on the table? Search every orientation."""
    from .optimize_lot import best_block, buildable
    region, _ = buildable(plot, road)
    ours = Massing(plot, road).rect
    lines = [f"buildable after a {road:.0f} ft road: {region.area:,.0f} ft2 "
             f"-- no set of lots can beat this",
             f"  ours, squared to the south boundary  {ours.area:9,.0f} ft2 "
             f"{ours.area / plot.area_ft2:6.1%}"]
    b = best_block(plot, road, n=lots)
    lines.append(f"  best over every orientation          {b.rect.area:9,.0f} ft2 "
                 f"{b.rect.area / plot.area_ft2:6.1%}  turned {b.theta:+.2f} deg")
    lines.append(f"  {b}")
    lines.append(f"{'road ft':>9}{'block ft2':>12}{'% plot':>9}{'each ft2':>10}{'cents':>8}")
    for w in (5, 10, 15, 20, 25, 30):
        c = best_block(plot, float(w), n=lots, coarse=2.0)
        lines.append(f"{w:>9}{c.rect.area:>12,.0f}{c.rect.area / plot.area_ft2:>9.1%}"
                     f"{c.lot_area:>10,.0f}{c.lot_area / CENT:>8.2f}")
    return "\n".join(lines)


def gis(plot, site, out_dir: Path, road: float):
    """GeoPackage + QGIS project + a browser overlay, all georeferenced."""
    from .gis import Georef, overlay_js, write_geojson
    if not site or not site.get("pins_wgs84"):
        raise SystemExit("--gis needs corner pins in site.json")
    ref = Georef(plot, {k: tuple(v) for k, v in site["pins_wgs84"].items()}, site["epsg"])
    carves = {"level": Carve(plot, road), "stepped": Carve(plot, road, stepped=True)}
    d = out_dir / "gis"
    write_geojson(d, ref, carves, survey=site["survey"])
    js = out_dir / "gmaps_overlay.js"
    js.write_text(overlay_js(ref, carves))
    print(f"  georeference: {ref.rms:.2f} m rms, A->B bears {ref.bearing:.2f}°, "
          f"residuals " + " ".join(f"{k}{v:.2f}" for k, v in ref.residuals.items()))
    qgz = d / "tslr_11-14-18.qgz"
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONEXECUTABLE")}
    qgz.unlink(missing_ok=True)
    r = subprocess.run([QGIS_PY, "-m", "tslr.qgis_build", str(d), str(qgz)],
                       capture_output=True, text=True, env=env)
    for line in r.stdout.splitlines():
        print("  " + line)
    if not qgz.exists():
        print(r.stderr[-800:])
        raise SystemExit("QGIS project build failed")
    return [str(qgz), str(qgz.with_suffix(".gpkg")), str(js)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tslr", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sides", nargs=4, type=float, metavar=("N", "E", "S", "W"),
                    default=[72.60, 25.00, 63.20, 30.00], help="boundary lengths in metres")
    ap.add_argument("--registered", type=float, default=1875.0, help="registered extent, m²")
    ap.add_argument("--diagonal", type=float, help="diagonal in metres — fixes the shape "
                    "exactly; without it the shape is assumed from the sketch's angles")
    ap.add_argument("--ends", choices=("AC", "BD"), default="AC",
                    help="which corners the diagonal joins (default AC, SW to NE)")
    ap.add_argument("--road", type=float, default=15.0, help="road width in feet, at its "
                    "narrowest, measured perpendicular to the north boundary")
    ap.add_argument("--paper", choices=sorted(PAPERS), default="A4")
    ap.add_argument("--out", type=Path, default=Path("generated/layout_options.pdf"))
    ap.add_argument("--site", type=Path, default=Path(__file__).with_name("site.json"),
                    help="durable survey record; supplies sides and corner pins")
    ap.add_argument("--gis", action="store_true",
                    help="also write the GeoPackage, QGIS project and map overlay")
    ap.add_argument("--html", action="store_true",
                    help="also write the local interactive massing viewer")
    ap.add_argument("--optimize", action="store_true",
                    help="search every orientation for the best block of identical lots")
    ap.add_argument("--lots", type=int, default=3, help="lots in that block (default 3)")
    a = ap.parse_args(argv)

    site = None
    if a.site.exists() and a.sides == [72.60, 25.00, 63.20, 30.00]:
        from .gis import load_site, plot_from_site
        site = load_site(a.site)
        plot, how = plot_from_site(site)
        print(f"site: {site['survey']} — closure from {how}")
    else:
        plot = Plot(*a.sides, registered=a.registered,
                    diagonal=a.diagonal, diagonal_ends=a.ends)
    print(summary(plot, a.road))
    if a.optimize:
        print(optimise(plot, a.road, a.lots))
    print("wrote", build(plot, a.out, PAPERS[a.paper], a.road))
    if a.html:
        from .html import build as build_html
        print("wrote", build_html(plot, Path("site/index.html"), site))
    if a.gis:
        print("wrote", *gis(plot, site, a.out.parent, a.road), sep="\n  ")


if __name__ == "__main__":
    main()
