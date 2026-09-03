# Method

## Closing the boundary

Four fixed side lengths do not fix a quadrilateral — they hinge. They close into
a one-parameter family whose areas run from nearly nothing up to the cyclic
member's, which is Brahmagupta's maximum. So any area quoted from four sides
alone rests on an assumed shape.

**One diagonal makes it rigid.** The quad splits into two triangles, each solved
from three known sides, and the area becomes a fact rather than a choice. Pass
`--diagonal`, or set `diagonal_m.measured` in `site.json`, and every sheet
prints the derivation instead of a caveat.

Label the reading **AC** (south-west to north-east) or **BD** when you take it.
Feeding one in as the other closes perfectly and quietly gives a different plot
— the one site error no audit downstream can catch, so there is a test for it.

Without a diagonal, `Plot` falls back on the member of the family whose corner
angles match the FMB drawing, and says so. It will not silently pick the
max-area member: that one splays both side boundaries outward, which the sketch
does not, and which throws the foot of the perpendicular from D outside the
south boundary — breaking the carve entirely.

## Why the areas never match the register

For TS 11/14/18 the sides 72.60 / 25.00 / 63.20 / 30.00 m close to **1812.4 m²**
at the sketch's angles; their absolute maximum is **1838.5 m²**; the register
says **1875 m²**. So either a boundary is mis-recorded or every side is about
1.7% long.

`geometry.side_for_area` reports which single figure is the cheapest
explanation — for this plot, east 25.00 → 26.05 m, or west 30.00 → 31.08 m.
`Plot.fitted()` takes the other route and stretches all four sides by 1.7% so
the closure lands on 1875 exactly; the shape and every angle are unchanged.

Both are offered. Neither is applied silently.

## The carve

From **D** (north-west) drop a perpendicular to the south boundary; from **B**
(south-east) run one up to the north boundary. The road runs the full north
edge, its inner edge meeting the west boundary at **F** and the east at **E**.
The rectangle stands square to the south boundary and rises until it meets that
inner edge. Three triangles remain.

The road width is measured **perpendicular to the north boundary**, which is not
the same as the depth it costs: the north boundary is tilted 6.56° to the south,
so a 20 ft road eats 20 ÷ cos 6.56° = 20.13 ft of depth. That distinction is
easy to lose by hand and is called out on the sheets.

`Carve` also splits the rectangle into equal lots, either identical rectangles
or equal-area ones whose rear line steps down west to east — the stepped version
is worth about 7% more saleable land at the cost of a ragged rear line.

## Self-consistency

`Plot` checks its closure carries the lengths it was handed. `Carve` audits
itself on construction: every piece's stated arithmetic must reproduce its drawn
area, no two pieces may overlap, the parts must sum to the whole, no lot may
escape the boundary, and the road may never pinch below the width asked for.
Any of those fails and it raises rather than printing a plausible sheet.

Each piece therefore carries its own derivation, and the schedule prints it: a
lot is `w × d`, a road bay is `(h₁ + h₂)/2 × w`, a corner offcut is
`½ × base × height`.

## Showing the working

Only six numbers come from outside: four sides, the diagonal, and the road
width, which is a design choice. Everything else is derived, and the viewer's
explain mode shows the arithmetic for each — corner angles from the cosine rule
on the two triangles the diagonal makes, the slant from `180° − A − D`, the
perpendicular offsets from `road ÷ sin` of the corner they cut, the depths from
`hW − PB · tan slant`, and lengths like `AG = GF ÷ tan A`.

The four corner angles must sum to 360°. That check is independent of everything
else, so a mistyped side shows up before any area is computed.
