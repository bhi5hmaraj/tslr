# TS 11/14/18 — subdivision layouts

## Why

The FMB extract for this plot records four boundary lengths and a registered
extent of 1875 m². Those numbers do not agree: the four sides cannot enclose
1875 m² in any arrangement — their absolute maximum is 1838.5 m². Four sides
do not even fix a shape, so an area quoted from them alone rests on an
assumption nobody stated.

That matters because the land is being priced. Every figure here therefore
carries where it came from, and nothing is drawn that has not been checked.

## What

A small library that closes the boundary, carves it into a road and saleable
land, and produces:

- **A3/A4 drawing sheets** at a verifiable print scale, every side dimensioned
- **`site/index.html`** — an interactive viewer, in English and Tamil, that
  re-solves as you change the road width and walks the construction step by step
- **A QGIS project and GeoPackage**, georeferenced to the real parcel

## How

    sides (+ a diagonal)  →  closure  →  carve  →  sheets · viewer · GIS

The carve: drop a perpendicular from the north-west corner to the south
boundary, run one up from the south-east corner to the north boundary, put the
road along the north edge and the largest possible rectangle below it. What is
left is three triangles.

Every piece states the arithmetic that produced its area, and a carve refuses to
build unless the parts sum to the whole, nothing overlaps, and the road never
pinches below its stated width.

## Running it

```
python -m tslr                 # the drawing sheets, to generated/
python -m tslr --html          # + site/index.html, the interactive viewer
python -m tslr --gis           # + GeoPackage, QGIS project, map overlay
python test_tslr.py            # the self-checks
```

Needs `shapely`, `pyproj`, `pytest`, and `rsvg-convert` + `pdfunite`
(`brew install librsvg poppler`). QGIS is optional, and used only by `--gis`.

Sides, pins and provenance live in **`tslr/site.json`** — edit that rather than
passing flags.

## Layout

| path | |
|---|---|
| `tslr/` | the library: geometry, sheets, GIS, viewer sources |
| `tslr/site.json` | the survey record — sides, corner pins, provenance |
| `site/index.html` | the published viewer (generated, committed) |
| `generated/` | PDFs, GeoPackage, QGIS project, map overlay |
| `test_tslr.py` | the self-checks |

## More

- [docs/method.md](docs/method.md) — closing the boundary, the diagonal, the
  carve, and how self-consistency is enforced
- [docs/viewer.md](docs/viewer.md) — the interactive page, explain mode, and
  deploying it
- [docs/gis.md](docs/gis.md) — georeferencing against satellite imagery, and the
  QGIS project
