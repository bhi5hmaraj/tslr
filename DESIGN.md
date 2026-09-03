# Interactive massing tool — design

A single local HTML page for trying road widths and layouts on TS 11/14/18
without a round trip through Claude. Companion to `python -m tslr`, which stays
the source of the printable sheets.

## What it has to do

1. Show the plot, road, rectangle and triangles, to scale, with real dimensions.
2. Let the road width be changed and everything re-solve **immediately**.
3. Show every piece's area in ft² / cents / m², and the tally back to the plot.
4. Agree with the PDF to the last digit. Two tools disagreeing is worse than one.
5. Open from a file or a link. No install, no server, works on a phone.

## What it deliberately will not do

- **Not** free-form dragging of corners. The plot boundary is survey data, not a
  design variable; only the *construction* is adjustable.
- **Not** a replacement for the sheets. Printing, dimensioning and the schedule
  stay in Python, which does them better.
- **Not** georeferenced. The map question is settled; this is the abstract view.

## Library survey

| candidate | what it is | verdict |
|---|---|---|
| [Turf.js](https://turfjs.org/) | geospatial toolkit, GeoJSON-native, wraps JSTS | **not used** — see below |
| [JSTS](https://www.npmjs.com/package/turf-jsts) | JS port of JTS, the same lineage as GEOS/Shapely | **not used**, but the fallback |
| [PlaneGCS](https://github.com/Salusoft89/planegcs) | FreeCAD's 2D constraint solver, WASM, TS types | **not used** — see below |
| plain SVG + pointer events | — | **used** |
| — | the closure and construction | **written here**, ~90 lines |

**Turf/JSTS.** The right reach if this needed polygon booleans, and JSTS shares
its lineage with Shapely so the semantics would match the Python exactly. But
this construction has no booleans in it: the five pieces are a quad, a rectangle
and three triangles, each with a closed-form area. The audit is arithmetic, not
topology. Turf's `area` is also geodesic and expects lon/lat, while every number
on the sheets is planar feet — so it would have to be sidestepped anyway. Reach
for JSTS the day lot splitting produces shapes that need `difference`.

**PlaneGCS.** Genuinely interesting: FreeCAD's own solver in the browser, which
would give true constraint-drag. Overkill here — the construction solves in
closed form, and a numeric solver would introduce convergence behaviour where
there is currently none. This is the escape hatch if free-form dragging ever
becomes the requirement.

**Net: zero dependencies.** The page is one self-contained file.

## Source of truth

```
tslr/site.json ──► sides + diagonal ──► baked into the page as five numbers
                                    └──► the page closes the quad itself
```

The page carries the closure too — four sides and a diagonal, solved as two
triangles glued along the diagonal — so the sides are editable inputs and the
built file is a static asset with no Python behind it. `site.json` supplies the
starting figures; the test vectors keep the two implementations honest, and the
self-check says so out loud when the sides are edited away from the record.

## The construction, in closed form

Given corners A B C D (feet, A at origin, AB along +x):

```
P  = foot of the perpendicular from D onto AB
Q  = perpendicular up from B to the line DC
slant   = atan2(|PD| - |BQ|, |PB|)
drop    = road_w / cos(slant)          vertical gap giving road_w perpendicular
inner(x)= height(x) - drop             the road's inner edge
F, E    = inner edge ∩ AD,  inner edge ∩ BC
depth   = inner(at B)                  rectangle meets the road at its east end
```

Five pieces, each with its own arithmetic:

| piece | area |
|---|---|
| Road | (\|DC\| + \|FE\|)/2 × road_w |
| Rectangle | width × depth |
| T1 gore | ½ × width × (inner(F) − depth) |
| T2 west corner | ½ × A→F_foot × inner(F) |
| T3 east corner | shoelace of B, E, rectangle's NE corner |

About forty lines. Everything else is drawing.

## UI

```
  road width  [====|--------]  20.0 ft     ← slider 10–30, 0.5 steps, plus a number box
  lots        (•)0  ( )2  ( )3             ← 0 = massing, otherwise split the rectangle
  units       (•)ft  ( )m
```

The drawing fills the page and scales to the window. Hovering a piece highlights
it and its schedule row. The tally line is always visible and turns red if the
parts stop summing to the plot — a permanently displayed audit, not a hidden one.

## Explain mode

A second view of the same model: the construction one move at a time, with a
slider and arrow keys. Each step names what it adds and where its numbers come
from, and nothing is drawn before the step that derives it — close the boundary,
find the slant, set the road back, square the rectangle, raise it, name what is
left, add it back up. The numbers are the current ones, so playing with the road
width and then pressing Explain walks that configuration, not a canned example.

## Two languages

Every string the reader sees lives in `I18N`, English and Tamil side by side —
labels, table headings, piece names, failure messages and all seven explain
steps. Tamil is the working language on site; English is what the FMB extract is
written in, so both are needed. The choice sits in `localStorage`, wrapped in a
try/catch because a private window throws on access.

Numbers, vertex letters and the geometry are language-neutral: only the words
change, so a Tamil reader and an English reader are looking at the same drawing.

## Showing the working

Only six numbers come from outside: four sides, the diagonal, and the road width,
which is a design choice. **The diagonal is not derivable from the sides** — four
sides hinge, so it is a fifth independent measurement, and the FMB does not
record one. Step 1 says so, gives the window it must fall in for both triangles
to close, and states where the current value came from: satellite imagery, not a
tape. Until it is taped that is the weakest link in everything below it. Everything else on the drawing is derived, and
each explain step now carries the arithmetic that produced its numbers —
`AG = GF ÷ tan A = 77.76 ÷ 7.617 = 10.21`, and so on down to the areas. The
formulas are symbols and numbers, so they read the same in both languages; only
the heading above them is translated.

Corner angles are marked with arcs on the steps that reason about them, and
step 1 shows where they come from: the diagonal splits the plot into two
triangles, each angle falls out of the cosine rule on three known sides, and the
four must sum to 360° — a closure check the reader can run.

The chain is short enough to check by hand: corner angles from the cosine rule,
slant from `180° − A − D`, the perpendicular offsets from `road ÷ sin` of the
corner they cut, and the depths from `hW − PB · tan slant`.

## Verification

Python emits test vectors — road width → the five areas — for widths 10 to 30 in
2 ft steps. The page asserts against them on load and shows a small pass/fail
mark. If the JS and the Python ever drift, the page says so out loud rather than
quietly printing different numbers from the PDF.

## Build and update

`python -m tslr --html` writes `generated/massing.html`: the template with the
corners, the test vectors and the site metadata substituted in. Regenerating
after a `site.json` change is the same one command that rebuilds the PDFs.

## Open questions

- Lot splitting is in, as a count from 1 to 8. The rectangle is a true
  rectangle, so equal lots are equal widths — no solving needed. Unequal-area
  layouts stay in the Python, where the audit lives.
- Local file only. The page is static and self-contained, so hosting it is a
  copy, not a build.
