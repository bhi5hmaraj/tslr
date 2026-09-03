# Georeferencing and QGIS

The drawing is exact but placeless: `Plot` builds its corners in a local frame
with A at the origin. This is how it gets onto the earth.

## The fit

`Georef` fits that local frame onto observed corner coordinates with **rotation
and translation only, scale locked to the tape**. A survey tape is worth
centimetres and satellite imagery a couple of metres, so the imagery supplies
where and which-way and nothing else. The residuals are then an honest error bar
on the pins rather than something a fudged scale absorbed.

For TS 11/14/18, four corners read off Google Maps satellite view fit the
tape-exact shape to **0.84 m rms**, and the west and east compound walls are
clearly visible with the fitted boundary lying on them.

## What the imagery decided

`best_diagonal` runs that fit across the whole closure family and reports which
diagonal the observations actually support. Here they say **AC ≈ 79.0 m**
(band 77.8–80.2), not the 76.6 the sketch's angles implied — a difference worth
about a cent per lot. The answer is the same whether scale is locked or free, so
it is not an artefact of the pins reading systematically short.

**That is inference, not measurement.** `site.json` keeps
`diagonal_m.measured: null` until a tape says otherwise, and every sheet and the
viewer's first explain step say so.

## The imagery also settled a question

11/15, on the east boundary, is a **water channel, not a road**. That is visible
in the satellite view and confirms the entrance has to be the 3.00 m stretch at
the north-west corner.

## QGIS

`--gis` writes `generated/gis/`: a GeoPackage and a ready-to-open project in
EPSG:32644 (UTM 44N, so QGIS measures in metres) with Esri World Imagery
underneath.

    open -a QGIS generated/gis/tslr_11-14-18.qgz

Top to bottom: `plot_boundary`, `corners`, `pins_observed` (labelled with each
pin's residual, since they sit almost on the fitted corners and the gap is the
only interesting thing about them), then a **LEVEL** group and a **STEPPED**
group — the two layouts are alternatives, so each is filtered on `variant` and
stepped starts switched off. Then the basemaps.

The project is built by QGIS's own Python:
`/Applications/QGIS.app/Contents/MacOS/python -m tslr.qgis_build`. It ends with
`os._exit` because `QgsApplication.exitQgis()` segfaults headless *after*
everything is on disk, so the caller checks for the output file rather than the
return code.

## Map overlay

`generated/gmaps_overlay.js` pastes into the browser console on Google Maps
satellite view. It reads the map centre and zoom out of the URL and redraws four
times a second, so it tracks panning instead of drifting off.
