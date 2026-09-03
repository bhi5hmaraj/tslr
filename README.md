# TS 11/14/18 — subdivision layouts

The interactive viewer is `site/index.html`, deployed to Netlify straight from
this repo. It is one self-contained file with no dependencies and no build step
on the host — see **Deploying** below.

Carves a TSLR/FMB plot into three equal-area rectangular lots served by one
common road, and prints the result at a measurable scale with every side length
and area shown so the arithmetic can be re-added by hand.

```
python -m tslr                                        # A4, all three options
python -m tslr --paper A3 --out ~/Downloads/plan.pdf
python -m tslr --sides 72.60 25 63.20 30 --road 20
python -m tslr --diagonal 76.58 --ends AC             # exact closure, no assumption
python test_tslr.py                                   # self-check
```

Needs `shapely`, `pytest`, and `rsvg-convert` + `pdfunite`
(`brew install librsvg poppler`).

## Measure the diagonal

Four sides do not fix a quadrilateral. They close into a one-parameter family
whose areas run up to the cyclic member's — Brahmagupta's maximum — so any area
you quote from sides alone rests on an assumed shape. **One diagonal makes it
rigid**: the quad splits into two triangles, Heron each, and the area is a fact.

Pass `--diagonal` and the schedule prints the derivation instead of a caveat.
Without it, `Plot` says so on every sheet and reports what the tape *would* have
to read to justify the registered area.

Label the reading **AC** (south-west to north-east) or **BD** when you take it —
feeding one in as the other closes perfectly and quietly gives a different plot.

## Self-consistency

`Plot` checks its closure carries the lengths it was handed. `Carve` audits
itself on construction: every piece's stated arithmetic must reproduce its drawn
area, no two pieces may overlap, the parts must sum to the whole, no lot may
escape the boundary, and the road may never pinch below the width asked for.
Any of those fails and it raises rather than printing a plausible sheet.

Each piece therefore carries its own derivation, and the schedule prints it:
a lot is `w × d`, a road bay is `(h₁ + h₂)/2 × w`, a corner offcut is
`½ × base × height`.

## The construction

From D (north-west) drop a perpendicular to the south boundary, foot **P**. From
B (south-east) run a perpendicular up to the north boundary, foot **Q**. Three
rectangles sit on the base P–B; everything above them is road, a slanted wedge
15 ft wide *measured perpendicular to the north boundary* at its narrowest end.
What is left is two corner triangles, A-P-D and B-Q-C.

`--stepped` layouts let each lot run as deep as its own east corner allows, so
the rear line steps down west to east: same equal areas, ~7% more saleable land,
at the cost of a ragged rear line.

## Why the areas never quite match the register

Four fixed side lengths close into a one-parameter family of quadrilaterals. The
largest member (Brahmagupta's cyclic one) is often still smaller than the
registered extent, and it is the wrong shape anyway — it splays both side
boundaries outward, which throws the foot of the perpendicular from D outside
the plot. `Plot` therefore picks the member whose corner angles match the
drawing, and reports the shortfall rather than hiding it.

For TS 11/14/18: sides 72.60 / 25.00 / 63.20 / 30.00 m close to 1812.4 m²,
their absolute maximum is 1838.5 m², and the register says 1875 m². Either a
boundary is mis-recorded (`geometry.side_for_area` says which is the cheapest
explanation) or every side is ~1.7% long. Option C stretches all four by that
1.7% so the closure lands on 1875 exactly.

## Layout

| file | |
|---|---|
| `tslr/geometry.py` | `Plot` (closure, register fit), `Carve` (the construction), piece measurement |
| `tslr/sheet.py` | `Paper`, `Sheet` — coordinate mapping and SVG primitives |
| `tslr/pages.py` | the two page templates: `plan` and `schedule` |
| `tslr/__main__.py` | CLI |

## Deploying

`site/index.html` is published as-is; `netlify.toml` sets `publish = "site"`
with no build command. The page is built locally by `python -m tslr --html`,
which bakes in the self-check vectors it asserts against on load — building on
the host would risk publishing a page that disagrees with the PDFs, and
`test_the_published_page_matches_the_source` fails if the committed file drifts
from the source.

There is no framework. The page is HTML, CSS and about 700 lines of plain
JavaScript, so a bundler would add a lockfile and a dependency tree to serve one
static file.

## Layout

| path | |
|---|---|
| `tslr/` | the library: geometry, sheets, GIS, viewer sources |
| `tslr/site.json` | the durable survey record — sides, pins, provenance |
| `site/index.html` | the published viewer (generated, committed) |
| `generated/` | PDFs, GeoPackage, QGIS project, map overlay (generated) |
| `test_tslr.py` | the self-checks |
