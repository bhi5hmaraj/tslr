"""Putting the carve on the earth.

The drawing is exact but placeless: `Plot` builds its corners in a local frame
with A at the origin. `Georef` fits that frame onto observed corner coordinates
-- rotation and translation only, **scale locked to the tape**, because a survey
tape is far more trustworthy than satellite imagery. The imagery supplies where
and which-way; the tape supplies everything else, and the leftover residuals are
then an honest error bar on the pins rather than something absorbed by a fudged
scale.

`best_diagonal` runs the same fit across the whole one-parameter family of
closures and reports which diagonal the observations actually support -- the
measurement that would otherwise have to be taken with a tape.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from pyproj import Transformer

from .geometry import CENT, FT2, M2FT, Carve, Plot, fan, sides

UTM44N = 32644          # Madurai; metres, so QGIS measures in metres


def helmert(src, dst, fix_scale=True):
    """Best rotation (+translation, +optional scale) taking src onto dst."""
    n = len(src)
    cs = [sum(p[i] for p in src) / n for i in (0, 1)]
    cd = [sum(p[i] for p in dst) / n for i in (0, 1)]
    S = [(p[0] - cs[0], p[1] - cs[1]) for p in src]
    D = [(p[0] - cd[0], p[1] - cd[1]) for p in dst]
    a = sum(s[0] * d[0] + s[1] * d[1] for s, d in zip(S, D))
    b = sum(s[0] * d[1] - s[1] * d[0] for s, d in zip(S, D))
    th = math.atan2(b, a)
    k = 1.0 if fix_scale else math.hypot(a, b) / sum(s[0] ** 2 + s[1] ** 2 for s in S)
    return th, k, cs, cd


@dataclass
class Georef:
    """Ties a Plot's local frame to real coordinates using observed corners.

    `pins` maps corner name (A/B/C/D) to (lat, lon) in WGS84.
    """
    plot: Plot
    pins: dict
    epsg: int = UTM44N
    rms: float = field(init=False)
    residuals: dict = field(init=False)
    bearing: float = field(init=False)      # of A->B, degrees from grid north

    def __post_init__(self):
        self._fwd = Transformer.from_crs("EPSG:4326", f"EPSG:{self.epsg}", always_xy=True)
        self._inv = Transformer.from_crs(f"EPSG:{self.epsg}", "EPSG:4326", always_xy=True)
        obs = [self._fwd.transform(self.pins[k][1], self.pins[k][0]) for k in "ABCD"]
        src = [(x / M2FT, y / M2FT) for x, y in self.plot.corners]
        self._th, _, self._cs, self._cd = helmert(src, obs)
        got = [self.to_utm(c) for c in self.plot.corners]
        res = [math.dist(p, q) for p, q in zip(got, obs)]
        self.residuals = dict(zip("ABCD", res))
        self.rms = math.sqrt(sum(r * r for r in res) / len(res))
        (ax, ay), (bx, by) = got[0], got[1]
        self.bearing = (math.degrees(math.atan2(bx - ax, by - ay)) + 360) % 360

    def to_utm(self, pt_ft):
        """local feet -> projected metres."""
        x, y = pt_ft[0] / M2FT - self._cs[0], pt_ft[1] / M2FT - self._cs[1]
        c, s = math.cos(self._th), math.sin(self._th)
        return (self._cd[0] + c * x - s * y, self._cd[1] + s * x + c * y)

    def to_wgs84(self, pt_ft):
        e, n = self.to_utm(pt_ft)
        return self._inv.transform(e, n)          # (lon, lat)

    def ring(self, poly):
        return [list(self.to_utm(p)) for p in list(poly.exterior.coords)]


def best_diagonal(north, east, south, west, pins, ends="AC", steps=2500, **kw):
    """Which member of the closure family do the observed corners support?

    Returns (diagonal, rms, area_m2, band) where band is the (lo, hi) diagonal
    range fitting within 0.25 m rms of the best -- an honest uncertainty, since
    the pins themselves are only good to about that.
    """
    pair = ((south, east), (north, west)) if ends.upper() == "AC" \
        else ((south, west), (north, east))
    lo = max(abs(a - b) for a, b in pair) + 0.01
    hi = min(a + b for a, b in pair) - 0.01
    curve = []
    for i in range(1, steps):
        d = lo + (hi - lo) * i / steps
        try:
            p = Plot(north, east, south, west, diagonal=d, diagonal_ends=ends, **kw)
        except Exception:
            continue
        curve.append((Georef(p, pins).rms, d, p.area_m2))
    if not curve:
        raise ValueError("no closure fits those pins")
    best = min(curve)
    band = [c for c in curve if c[0] <= best[0] + 0.25]
    return best[1], best[0], best[2], (min(c[1] for c in band), max(c[1] for c in band))


# ------------------------------------------------------------------ export
def _feat(geom, props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [geom]}
            if isinstance(geom[0], list) else {"type": "Point", "coordinates": geom}}


def layers(georef: Georef, carves: dict, survey="TS 11/14/18"):
    """One GeoJSON FeatureCollection per QGIS layer."""
    g, p = georef, georef.plot
    trio = lambda a: {"area_ft2": round(a, 1), "area_m2": round(a / FT2, 1),
                      "cents": round(a / CENT, 3)}
    out = {}
    out["plot_boundary"] = [_feat(g.ring(p.quad), dict(
        survey=survey, north_m=p.north, east_m=p.east, south_m=p.south, west_m=p.west,
        diagonal_ac_m=round(p.diagonals_m["AC"], 3), diagonal_bd_m=round(p.diagonals_m["BD"], 3),
        registered_m2=p.registered, cyclic=p.is_cyclic, fit_rms_m=round(g.rms, 3),
        bearing_ab=round(g.bearing, 2), closure=p.derivation, **trio(p.area_ft2)))]
    out["lots"], out["road"], out["offcuts"] = [], [], []
    for variant, c in carves.items():
        for k, piece in enumerate(c.lot_pieces):
            out["lots"].append(_feat(g.ring(piece.poly), dict(
                variant=variant, name=f"Lot {k + 1}",
                width_ft=round(c.cuts[k + 1] - c.cuts[k], 2), depth_ft=round(c.depths[k], 2),
                formula=piece.why, **trio(piece.area))))
        out["road"].append(_feat(g.ring(c.road), dict(
            variant=variant, width_min_ft=c.road_w, width_max_ft=round(c.road_west, 2),
            **trio(c.road.area))))
        for piece in c.offcut_pieces:
            out["offcuts"].append(_feat(g.ring(piece.poly), dict(
                variant=variant, name=piece.name, formula=piece.why,
                sides_ft=" x ".join(f"{ln:.2f}" for _, _, ln in sides(piece.poly)),
                **trio(piece.area))))
    out["corners"] = [_feat(list(g.to_utm(pt)), dict(
        name=n, lat=round(g.to_wgs84(pt)[1], 7), lon=round(g.to_wgs84(pt)[0], 7),
        easting=round(g.to_utm(pt)[0], 2), northing=round(g.to_utm(pt)[1], 2)))
        for n, pt in zip("ABCD", p.corners)]
    out["pins_observed"] = [_feat(list(g._fwd.transform(lo, la)), dict(
        name=n, lat=la, lon=lo, residual_m=round(g.residuals[n], 2)))
        for n, (la, lo) in g.pins.items()]
    return {k: {"type": "FeatureCollection",
                "crs": {"type": "name",
                        "properties": {"name": f"urn:ogc:def:crs:EPSG::{g.epsg}"}},
                "features": v} for k, v in out.items()}


def write_geojson(dirpath, georef, carves, **kw):
    d = Path(dirpath)
    d.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, fc in layers(georef, carves, **kw).items():
        paths[name] = d / f"{name}.geojson"
        paths[name].write_text(json.dumps(fc, indent=1))
    return paths


def load_site(path="tslr/site.json"):
    """The durable record: sides, registered extent, corner pins, provenance."""
    return json.loads(Path(path).read_text())


def plot_from_site(site, use_pins=True):
    """Build the Plot the site record supports: a taped diagonal if there is one,
    otherwise the one the corner pins point to, otherwise sides alone."""
    s = site["sides_m"]
    args = (s["north"], s["east"], s["south"], s["west"])
    kw = dict(registered=site["registered_m2"])
    d = site.get("diagonal_m", {})
    if d.get("measured"):
        return Plot(*args, diagonal=d["measured"],
                    diagonal_ends=d.get("measured_ends", "AC"), **kw), "taped diagonal"
    if use_pins and site.get("pins_wgs84"):
        pins = {k: tuple(v) for k, v in site["pins_wgs84"].items()}
        best, _, _, _ = best_diagonal(*args, pins, **kw)
        return Plot(*args, diagonal=round(best, 2), **kw), "diagonal inferred from map pins"
    return Plot(*args, **kw), "four sides only, shape assumed from the sketch angles"


def overlay_js(georef: Georef, carves: dict, variant="level"):
    """A snippet to paste into the browser console on Google Maps satellite view.

    It reads the map centre and zoom straight out of the URL and redraws four
    times a second, so it follows panning and zooming instead of drifting off
    the moment the map moves.
    """
    g, c = georef, carves[variant]
    ll = lambda poly: [[round(v, 7) for v in g.to_wgs84(p)[::-1]]
                       for p in list(poly.exterior.coords)[:-1]]
    data = dict(quad=ll(g.plot.quad), road=ll(c.road), lots=[ll(l) for l in c.lots],
                pins={k: list(v) for k, v in g.pins.items()})
    return _OVERLAY_JS.replace("__DATA__", json.dumps(data))


_OVERLAY_JS = r"""
// TS 11/14/18 overlay for Google Maps satellite view. Paste into the console.
// Anchored to the @lat,lon,Zm token in the URL, so it tracks pan and zoom.
(() => {
const D = __DATA__;
const R0 = 1866/1478, LAT0 = -1.6675e-6/R0, LON0 = 1.6952941e-6/R0, Z0 = 154;
const ns = 'http://www.w3.org/2000/svg';
function draw(){
  const m = location.pathname.match(/@(-?[\d.]+),(-?[\d.]+),([\d.]+)m/);
  if(!m) return;
  const clat=+m[1], clon=+m[2], k=+m[3]/Z0;
  const latPer=LAT0*k, lonPer=LON0*k, cx=innerWidth/2, cy=innerHeight/2;
  const XY=(la,lo)=>[cx+(lo-clon)/lonPer, cy+(la-clat)/latPer];
  document.getElementById('tslr-ov')?.remove();
  const s=document.createElementNS(ns,'svg'); s.id='tslr-ov';
  s.setAttribute('style','position:fixed;inset:0;width:100vw;height:100vh;z-index:99999;pointer-events:none');
  const poly=(pts,fill,stroke,w,dash)=>{const p=document.createElementNS(ns,'polygon');
    p.setAttribute('points',pts.map(([a,b])=>XY(a,b).join(',')).join(' '));
    p.setAttribute('fill',fill);p.setAttribute('stroke',stroke);p.setAttribute('stroke-width',w);
    if(dash)p.setAttribute('stroke-dasharray',dash);s.appendChild(p);};
  const label=(x,y,t,col,sz)=>{const e=document.createElementNS(ns,'text');
    e.setAttribute('x',x);e.setAttribute('y',y);e.setAttribute('fill',col);
    e.setAttribute('font-size',sz);e.setAttribute('font-weight','700');
    e.setAttribute('text-anchor','middle');e.textContent=t;s.appendChild(e);};
  poly(D.quad,'none','#00e5ff',3);
  poly(D.road,'rgba(255,255,255,.3)','#fff',1.6,'6 4');
  D.lots.forEach((l,i)=>{poly(l,'rgba(0,229,255,.15)','#00e5ff',1.6);
    const c=l.reduce((a,[la,lo])=>[a[0]+la/l.length,a[1]+lo/l.length],[0,0]);
    label(...XY(...c),'LOT '+(i+1),'#00e5ff',22);});
  Object.entries(D.pins).forEach(([n,p])=>{const [x,y]=XY(...p);
    const c=document.createElementNS(ns,'circle');c.setAttribute('cx',x);c.setAttribute('cy',y);
    c.setAttribute('r','5');c.setAttribute('fill','#ff2d55');s.appendChild(c);
    label(x+12,y-7,n,'#ff2d55',20);});
  document.body.appendChild(s);
}
clearInterval(window.__tslrTimer); window.__tslrTimer=setInterval(draw,400); draw();
})();
"""
