# The interactive viewer

`site/index.html` — one self-contained file. Open it from disk or from the
deployed URL; there is no server, no build step and no dependency.

## What it does

Change the road width, the lot count or any boundary figure and everything
re-solves immediately: the drawing, every side length, each piece's area in
ft² / cents / m², and the tally back to the plot. Hovering a piece highlights it
in both the drawing and the schedule.

The plot boundary is survey data, not a design variable, so only the
construction is adjustable — but the sides and diagonal are editable inputs,
because the page closes the quadrilateral itself and those are the figures most
likely to change when the tape comes out.

## Explain mode

The same model, one move at a time, with a slider and arrow keys. Nine steps:
close the boundary, find the slant, set the road back, square the rectangle,
raise it, then a step per triangle, then add it back up. Each names what it adds
and shows the arithmetic that produced its numbers; nothing is drawn before the
step that derives it, and corner angles are marked with arcs on the steps that
reason about them.

The numbers are the current ones, so playing with the road width and then
pressing Explain walks *that* configuration rather than a canned example.

## Two languages

Every string the reader sees lives in `I18N`, English and Tamil side by side —
labels, table headings, piece names, failure messages and all nine explain
steps. Tamil is the working language on site; English is what the FMB extract is
written in. The choice sits in `localStorage`.

Numbers, vertex letters and the geometry are language-neutral, so a Tamil reader
and an English reader are looking at the same drawing and can point at the
same G.

## Verification

Python emits the five piece areas for every buildable road width and the page
asserts against them on load, showing a pass or fail line. If the JavaScript
ever drifts from the Python, the page says so out loud instead of quietly
printing different numbers from the PDFs. Edit a side away from the recorded
figures and it says the check no longer applies rather than pretending.

`meetR` refuses circles that cannot meet, and the closure audits that its
corners carry the side lengths they were given — clamping instead would return a
plausible, wrong quadrilateral.

## No framework

The page is HTML, inline CSS and about 700 lines of plain JavaScript. The five
pieces are a quad, a rectangle and three triangles, each with a closed-form
area, so there are no polygon booleans and nothing for a geometry library to do.
[Turf.js](https://turfjs.org/) and [JSTS](https://www.npmjs.com/package/turf-jsts)
are the right reach if that ever changes — JSTS shares its lineage with Shapely,
so the semantics would match the Python.
[PlaneGCS](https://github.com/Salusoft89/planegcs), FreeCAD's own constraint
solver as WebAssembly, is the escape hatch if free-form dragging becomes the
requirement.

## Editing it

`tslr/viewer.js` (three modules: `Geom`, `Render`, `UI`) and `tslr/viewer.css`
are real files; `tslr/html.py` inlines them at build time. Edit those and re-run
`python -m tslr --html`.

## Deploying

`site/index.html` is published as-is. `netlify.toml` sets `publish = "site"`
with no build command, and every push to `main` redeploys.

The page is built **locally**, not on the host, because the build bakes in the
self-check vectors the page asserts against — a build that quietly failed on the
host would publish a page that disagrees with the drawings.
`test_the_published_page_matches_the_source` fails if the committed file drifts
from the source.
