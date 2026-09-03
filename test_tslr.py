"""One runnable check: python test_tslr.py

Everything downstream rests on the closure carrying the lengths it was given and
on the carved pieces reconciling with the whole. `Plot` and `Carve` audit
themselves on construction, so most of this is checking that those audits
actually bite — a guard that never fires is not a guard.
"""
import math
import tempfile
from pathlib import Path

import pytest

from tslr import CENT, Carve, Plot
from tslr.geometry import M2FT, Piece, brahmagupta, diagonal_for_area, fan, heron, sides

FMB = Plot(72.60, 25.00, 63.20, 30.00)


def test_closure_carries_the_recorded_sides():
    c = FMB.corners
    got = [math.dist(c[i], c[(i + 1) % 4]) / M2FT for i in range(4)]
    assert [round(x, 2) for x in got] == [63.20, 25.00, 72.60, 30.00], got
    assert FMB.area_m2 <= FMB.max_area_m2 <= FMB.registered
    # the sketch-matched shape must put P inside the south boundary, or the carve
    # has nothing to stand on
    assert 0 < Carve(FMB).P[0] < math.dist(c[0], c[1])


def test_a_diagonal_pins_the_shape_and_agrees_with_heron():
    for ends in ("AC", "BD"):
        d = FMB.diagonals_m[ends]
        exact = Plot(72.60, 25.00, 63.20, 30.00, diagonal=d, diagonal_ends=ends)
        assert abs(exact.area_m2 - FMB.area_m2) < 0.2, ends
        for a, b in zip(exact.corners, FMB.corners):
            assert math.dist(a, b) < 0.05, ends
        if ends == "AC":                       # the two-triangle split, by hand
            assert abs(heron(63.20, 25.00, d) + heron(d, 72.60, 30.00)
                       - exact.area_m2) < 0.2


def test_the_max_area_member_is_the_cyclic_one():
    assert not FMB.is_cyclic                   # this plot is not
    a = FMB.corner_angles
    assert abs(a[0] + a[2] - 180) > 15         # and not by a hair
    # whichever diagonal you measure, the biggest area it can imply is Brahmagupta's
    for ends in ("AC", "BD"):
        _, peak, _ = diagonal_for_area(FMB, ends)
        assert abs(peak - FMB.max_area_m2) < 0.2, ends


def test_every_piece_reproduces_its_own_arithmetic():
    for stepped in (False, True):
        c = Carve(FMB, stepped=stepped)        # Carve.audit() runs on construction
        for p in c.pieces:
            assert abs(p.check - p.area) < 0.5, f"{p.name}: {p.why}"
        t = c.tally()
        assert abs(t["total"] - t["plot"]) < 0.5
        assert max(l.area for l in c.lots) - min(l.area for l in c.lots) < 0.5
        assert abs(sum(b.area for b in c.road_bays) - c.road.area) < 0.5


def test_the_audit_actually_bites():
    c = Carve(FMB)
    with pytest.raises(AssertionError):
        Piece("bogus", c.lots[0], "1 × 1", 1.0).verify()
    with pytest.raises(AssertionError):        # a road narrower than asked for
        Carve(FMB, road_w=200.0)
    with pytest.raises(ValueError):            # a diagonal no triangle can hold
        Plot(72.60, 25.00, 63.20, 30.00, diagonal=20.0)


def test_which_diagonal_was_measured_matters():
    """Feeding an AC tape reading in as BD closes fine and gives the wrong plot --
    the one mistake on site that no audit downstream can catch."""
    d = FMB.diagonals_m["AC"]
    as_ac = Plot(72.60, 25.00, 63.20, 30.00, diagonal=d, diagonal_ends="AC")
    as_bd = Plot(72.60, 25.00, 63.20, 30.00, diagonal=d, diagonal_ends="BD")
    assert abs(as_ac.area_m2 - as_bd.area_m2) > 5, "label the tape reading AC or BD"


def test_offcuts_are_triangles_measurable_by_half_base_height():
    for _, tri in Carve(FMB).offcuts:
        assert len(sides(tri)) == 3
        assert abs(sum(a for *_, a in fan(tri)) - tri.area) < 0.5


def test_fitted_sides_close_on_the_register():
    f, k = FMB.fitted(), FMB.stretch
    assert abs(f.area_m2 - FMB.registered) < 0.5
    for a, b in zip(FMB.sides_m, f.sides_m):   # one factor, every side
        assert abs(b / a - k) < 1e-9
    assert abs(f.area_ft2 / FMB.area_ft2 - k ** 2) < 1e-6
    assert abs(brahmagupta(*f.sides_m) / brahmagupta(*FMB.sides_m) - k ** 2) < 1e-6


def test_the_published_page_matches_the_source():
    """site/index.html is what Netlify serves and what the drawings must agree
    with, so a stale one is a page that quietly contradicts the PDFs."""
    published = Path("site/index.html")
    if not published.exists():
        pytest.skip("site/index.html not built yet — run: python -m tslr --html")
    from tslr.gis import load_site, plot_from_site
    from tslr.html import build as build_html
    plot, _ = plot_from_site(load_site("tslr/site.json"))
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build_html(plot, Path(tmp) / "index.html",
                           load_site("tslr/site.json")).read_text()
    assert fresh == published.read_text(), \
        "site/index.html is stale — run: python -m tslr --html"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
