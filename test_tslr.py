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


def test_no_orientation_beats_our_block_by_much():
    """The v8 overlay fits far more identical lots than our massing does. Either
    it is wrong or we are under-optimising, and the difference is money. Search
    every orientation and see."""
    from tslr.geometry import Massing
    from tslr.optimize_lot import best_block, buildable
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    region, _ = buildable(site, 20.0)
    ours = Massing(site, 20.0).rect.area
    best = best_block(site, 20.0, n=3)
    assert ours < best.rect.area < region.area, (ours, best.rect.area, region.area)
    # turning the block to lie along the road is worth something, but little
    assert best.rect.area / ours < 1.05, best.rect.area / ours
    # and the winner is the one squared to the road, which is why it wins
    assert best.frontage > 0.9 * best.width, (best.frontage, best.width)


def test_v8s_yield_needs_a_road_you_cannot_drive():
    """v8 claims 3 x 63.6 x 75.0 = 14,310 ft2 of identical lots. Find the road
    width that allows it, over every orientation, and the claim answers itself."""
    from tslr.optimize_lot import best_block
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    lo, hi = 1.0, 20.0
    for _ in range(24):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if best_block(site, mid, n=3, coarse=4.0).rect.area < 14245 \
            else (mid, hi)
    assert 3.0 < (lo + hi) / 2 < 7.0, (lo + hi) / 2


def test_a_block_that_leaves_the_land_is_refused():
    """Block audits itself, so hand it a rectangle that overruns the road."""
    from tslr.optimize_lot import Block
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    A, B, C, D = site.corners
    with pytest.raises(AssertionError, match="leaves the buildable land"):
        Block(site, 20.0, [A, B, C, D], 0.0, 3)


def test_four_sided_lots_leave_nothing_over():
    """The v8 question, answered the other way: keep a real 20 ft road and drop
    the rectangle. Lots cut straight across the land tile it exactly, so the
    offcuts vanish -- and they beat v8's own figure while keeping the road."""
    from tslr.optimize_lot import Fan, best_block, buildable
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    region, _ = buildable(site, 20.0)
    f = Fan(site, 20.0, 3)                       # audits itself: equal, and no waste
    assert abs(f.tally()["lots"] - region.area) < 0.01
    assert f.tally()["waste"] == 0.0
    assert f.lot_area > best_block(site, 20.0, 3).lot_area
    assert f.tally()["lots"] > 14245, "should beat v8, which had no road left"
    # the corner lot is what pays: every other lot stays near square
    sharp = [min(c) for c in f.corners()]
    assert min(sharp) < 70 and sorted(sharp)[1] > 80, sharp
    assert all(len(g.exterior.coords) - 1 == 4 for g in f.lots)


def test_a_fan_that_is_not_equal_is_refused():
    from tslr.optimize_lot import Fan
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    f = Fan(site, 20.0, 3)
    f.lots = [f.lots[0], f.lots[1], f.lots[2].buffer(-1)]
    with pytest.raises(AssertionError, match="not equal"):
        f.audit()


def test_equal_buildable_beats_equal_land_for_the_family_that_loses():
    """Three families, so what matters is what the worst-off one gets. Equal land
    hands the corner family the same area but a wedge it cannot build on."""
    from tslr.optimize_lot import Fan
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    land = Fan(site, 20.0, 3, equalise="land")
    build = Fan(site, 20.0, 3, equalise="buildable")
    assert build.rect_area > land.rect_area, (build.rect_area, land.rect_area)
    # neither wastes anything, so the whole difference is in how it is shared
    for f in (land, build):
        assert f.tally()["waste"] == 0.0
        assert abs(f.tally()["lots"] - sum(g.area for g in f.lots)) < 0.01
    # equalising the buildable rectangle pays the corner lot in land
    areas = [g.area for g in build.lots]
    assert max(areas) == areas[-1] and max(areas) > min(areas) * 1.1, areas
    # and 4,268 ft2 is the most all three can be promised: asking for more fails
    from tslr.optimize_lot import _reach, buildable as land_left
    region, _ = land_left(site, 20.0)
    import math
    A, B, E, F = region.exterior.coords[:-1]
    d = math.dist(F, E)
    u = ((E[0] - F[0]) / d, (E[1] - F[1]) / d)
    ts = [(q[0] - F[0]) * u[0] + (q[1] - F[1]) * u[1] for q in region.exterior.coords]
    assert _reach(build, region, F, u, min(ts), max(ts), build.rect_area * 1.02) is None


def test_the_squared_rectangle_has_no_road_frontage_of_its_own():
    """The strip the road opens onto is crossed by everyone, so it cannot be
    private land. Squaring the block to the south boundary creates one."""
    import math
    from tslr.geometry import Massing
    from tslr.optimize_lot import Fan, buildable
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    m = Massing(site, 20.0)
    _, inner = buildable(site, 20.0)
    F, E = m.F, m.E
    d = math.dist(F, E)
    u = ((E[0] - F[0]) / d, (E[1] - F[1]) / d)

    def entrance(poly):
        q = list(poly.exterior.coords[:-1])
        tot = 0.0
        for i, a in enumerate(q):
            b = q[(i + 1) % len(q)]
            if max(abs(-u[1] * (z[0] - F[0]) + u[0] * (z[1] - F[1]))
                   for z in (a, b)) > 0.02:
                continue
            t = sorted((z[0] - F[0]) * u[0] + (z[1] - F[1]) * u[1] for z in (a, b))
            tot += max(0.0, min(t[1], d) - max(t[0], 0.0))
        return tot

    assert entrance(m.rect) == 0.0, "the rectangle would front the road directly"
    t1 = next(p for p in m.pieces if p.name.startswith("T1"))
    t3 = next(p for p in m.pieces if p.name.startswith("T3"))
    assert entrance(t1.poly) > 190, "T1 is the strip the road opens onto"
    assert 30.5 < entrance(t3.poly) < 31.5, entrance(t3.poly)   # the east triangle
    # so the common land is the road plus T1, half again what the road alone says
    common = m.road.area + t1.area
    assert common / site.area_ft2 > 0.36 > m.road.area / site.area_ft2

    # four-sided lots have no such strip: each one reaches the road itself
    f = Fan(site, 20.0, 3, equalise="buildable")
    ents = [entrance(g) for g in f.lots]
    assert min(ents) > 50, ents
    assert abs(sum(ents) - d) < 0.01, "the lots share the whole road edge"


def test_the_turning_head_comes_off_the_last_lot():
    """A dead-end road needs somewhere to turn a car. That triangle is common
    ground, so it must leave the lots and join the road, not vanish."""
    from tslr.optimize_lot import Fan, head_ends, head_limit
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    limit = head_limit(site, 20.0)
    assert 24 < limit < 25, limit
    plain = Fan(site, 20.0, 3, equalise="buildable")
    for h in (5.0, 10.0, 20.0, limit - 0.05):
        f = Fan(site, 20.0, 3, equalise="buildable", head=h)
        f.audit()                                   # parts still make the whole
        assert abs(f.tally()["total"] - site.area_ft2) < 0.01
        # it is the last lot that pays, and the others do not move
        assert f.lots[-1].area < plain.lots[-1].area
        for i in (0, 1):
            assert abs(f.lots[i].area - plain.lots[i].area) < 1.0
        # and common ground grows by exactly the triangle
        assert abs(f.tally()["road"] - plain.tally()["road"] - f.head_poly.area) < 0.01
    # the head is a right triangle: leg along the road, then square down to BE
    W, V = head_ends(site, 20.0, 20.0)
    m = __import__("tslr.geometry", fromlist=["Massing"]).Massing(site, 20.0)
    import math
    a = (m.E[0] - W[0], m.E[1] - W[1])
    b = (V[0] - W[0], V[1] - W[1])
    assert abs(a[0] * b[0] + a[1] * b[1]) < 1e-6, "the drop is not square to the road"
    assert abs(math.dist(W, m.E) - 20.0) < 1e-6
    # past the limit the drop misses the east boundary, and it says so
    with pytest.raises(AssertionError, match="misses the east boundary"):
        Fan(site, 20.0, 3, head=limit + 1)


def test_the_turning_ray_carried_on_cuts_a_right_triangle_at_the_dead_end():
    """The 90 deg ray does not stop at the road. Carried on it meets the north
    boundary at Y, and everything east of it is the wedge L-Y-C."""
    import math
    from shapely.geometry import LineString, Polygon
    from tslr.geometry import Massing
    from tslr.optimize_lot import head_ends
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    _, _, C, D = site.corners
    m = Massing(site, 20.0)
    M, L = head_ends(site, 20.0, 20.0)
    n = (-(m.F[1] - m.E[1]), m.F[0] - m.E[0])
    k = math.hypot(*n)
    n = (n[0] / k, n[1] / k)
    ray = LineString([(M[0] - n[0] * 500, M[1] - n[1] * 500),
                      (M[0] + n[0] * 500, M[1] + n[1] * 500)])
    Y = ray.intersection(LineString([D, C])).coords[0]

    # DC runs parallel to the road's inner edge, so MY is exactly the road width
    assert abs(math.dist(M, Y) - 20.0) < 1e-6, math.dist(M, Y)
    assert abs(math.dist(L, Y) - math.dist(L, M) - 20.0) < 1e-6   # L, M, Y in line
    # which makes LYC right-angled at Y
    v1 = (L[0] - Y[0], L[1] - Y[1])
    v2 = (C[0] - Y[0], C[1] - Y[1])
    assert abs(v1[0] * v2[0] + v1[1] * v2[1]) < 1e-6
    wedge = Polygon([L, Y, C])
    assert abs(wedge.area - math.dist(Y, C) * math.dist(L, Y) / 2) < 0.01
    # and it is exactly the road past the ray plus the turning head
    assert abs(wedge.area - Polygon([M, Y, C, m.E]).area - Polygon([M, m.E, L]).area) < 0.01
    assert 925 < wedge.area < 940, wedge.area


def test_the_freecad_spec_carries_the_whole_plot():
    """FreeCAD has no shapely, so it is handed rings and told what they are. If
    the handover drops or distorts a piece, nothing downstream will notice."""
    import math
    from tslr.__main__ import freecad_spec
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    spec = freecad_spec(site, None, 20.0, 3, 20.0, "buildable")
    assert [round(spec["sides_m"][k], 2) for k in ("south", "east", "north", "west")] \
        == [63.20, 25.00, 72.60, 30.00]
    assert round(spec["diagonal_m"], 2) == 79.00
    # the sketch is driven by those five figures, so they must close on the corners
    q = spec["corners_ft"]
    got = [math.dist(q[i], q[(i + 1) % 4]) / M2FT for i in range(4)]
    assert [round(x, 2) for x in got] == [63.20, 25.00, 72.60, 30.00], got
    assert abs(math.dist(q[0], q[2]) / M2FT - 79.00) < 0.01

    def area(ring):
        n = len(ring)
        return abs(sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
                       for i in range(n))) / 2

    pieces = spec["lots"] + spec["common"]
    assert len(spec["lots"]) == 3 and len(spec["common"]) == 2      # road and head
    assert abs(sum(area(p["ring"]) for p in pieces) - site.area_ft2) < 0.5
    # every ring is a real polygon, and none repeats its first point
    for p in pieces + spec["buildable"]:
        assert len(p["ring"]) >= 3
        assert math.dist(p["ring"][0], p["ring"][-1]) > 1e-6
        assert area(p["ring"]) > 0.5
    # the buildable rectangles are equal, which is what the labels claim
    got = [round(area(b["ring"])) for b in spec["buildable"]]
    assert max(got) - min(got) <= 1, got


def test_the_dxf_carries_the_same_figures():
    """FreeCAD's window is unusable on this machine, so the DXF is how the
    drawing leaves the repo. It has to survive being read back."""
    import re
    import tempfile
    from pathlib import Path
    from tslr.__main__ import freecad_spec
    from tslr.dxf import write as write_dxf
    site = Plot(72.60, 25.00, 63.20, 30.00, diagonal=79.00, diagonal_ends="AC")
    spec = freecad_spec(site, None, 20.0, 3, 20.0, "buildable")
    with tempfile.TemporaryDirectory() as tmp:
        text = write_dxf(spec, Path(tmp) / "p.dxf").read_text()

    def rings(src):
        """Every LWPOLYLINE, as its list of points."""
        out = []
        for block in src.split("\n0\nLWPOLYLINE\n")[1:]:
            block = block.split("\n0\n")[0]
            xs = re.findall(r"\n10\n([-\d.]+)", block)
            ys = re.findall(r"\n20\n([-\d.]+)", block)
            out.append([(float(a), float(b)) for a, b in zip(xs, ys)])
        return out

    got = rings(text)
    assert len(got) == 1 + 3 + 2 + 3, len(got)      # boundary, lots, common, buildable
    assert "$INSUNITS" in text and "\n70\n6\n" in text, "the unit must be declared"

    def area(ring):
        n = len(ring)
        return abs(sum(ring[i][0] * ring[(i + 1) % n][1] - ring[(i + 1) % n][0] * ring[i][1]
                       for i in range(n))) / 2

    M2FT = 1 / 0.3048
    # written in metres, so the boundary must come back as the plot
    assert abs(area(got[0]) * M2FT ** 2 - site.area_ft2) < 1.0
    # and the lots and the common ground still make the whole
    assert abs(sum(area(r) for r in got[1:6]) * M2FT ** 2 - site.area_ft2) < 1.0
    for r in got:
        assert len(r) >= 3
    assert all(layer in text for layer in ("BOUNDARY", "LOTS", "ROAD", "HEAD", "BUILDABLE"))


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
