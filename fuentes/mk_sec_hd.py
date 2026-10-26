"""Mapas de secciones censales en alta definición (un fichero por provincia y año).
mapas/sec/<año>/p<prov>.json.js = {w, h, q, s: [[mun3+dist2+sec3, d], ...]}
Coordenadas en una rejilla de Q metros relativa a la esquina de la provincia; contornos simplificados
con shapely.coverage_simplify (las secciones vecinas comparten exactamente el mismo borde)."""
import shapefile, json, glob, os, sys, collections, warnings
warnings.filterwarnings('ignore')
import shapely
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import make_valid
OUT = sys.argv[3] if len(sys.argv) > 3 else '/tmp/w/hd'
Y = sys.argv[1]; TOL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
Q = 2.0
SRC = {'2001': glob.glob('/tmp/w/sec/s2001/**/*01.shp', recursive=True), '2004': glob.glob('/tmp/w/sec/s2004/Nacional04/*.shp'),
       '2010': glob.glob('/tmp/w/sec/s2010/**/*2010.shp', recursive=True), '2014': glob.glob('/tmp/w/sec/s2014/*.shp'),
       '2019': glob.glob('/tmp/w/sec/s2019/*.shp'), '2024': glob.glob('/tmp/w/sec/s2024/*.shp')}
ENC = {'2024': 'utf8', '2019': 'utf8'}
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None

def polys(g):
    if g.geom_type == 'Polygon': return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'): return [x for p in g.geoms for x in polys(p)]
    return []

byp = collections.defaultdict(lambda: collections.defaultdict(list))
for f in SRC[Y]:
    r = shapefile.Reader(f, encoding=ENC.get(Y, 'latin1')); names = [x[0] for x in r.fields[1:]]
    for sr in r.iterShapeRecords():
        d = dict(zip(names, sr.record))
        if not sr.shape.points: continue
        if 'CUSEC' in d: p = d['CPRO']; key = d['CMUN'] + d['CDIS'] + d['CSEC']
        else:
            pm = (d['PROVMUN'] or '').strip()
            if len(pm) != 5 or not pm.isdigit(): continue
            p = pm[:2]; key = pm[2:] + str(d['DISTRITO']).zfill(2) + str(d['SECCION']).zfill(3)
        if ONLY and p not in ONLY: continue
        g = shape(sr.shape.__geo_interface__)
        if g.is_empty: continue
        if not g.is_valid: g = make_valid(g)
        g = unary_union(polys(g))
        if not g.is_empty: byp[p][key].append(g)

os.makedirs(f'{OUT}/mapas/sec/{Y}', exist_ok=True)
tot = 0; n = 0
for p, dd in sorted(byp.items()):
    keys = sorted(dd); G = [dd[k][0] if len(dd[k]) == 1 else unary_union(dd[k]) for k in keys]
    G = [make_valid(g) if not g.is_valid else g for g in G]
    G = [unary_union(polys(g)) for g in G]
    try:
        S = list(shapely.coverage_simplify(shapely.GeometryCollection(G).geoms, TOL))
    except Exception as ex:
        print('coverage_simplify falló en', p, ex, flush=True); S = [g.simplify(TOL, preserve_topology=True) for g in G]
    b = [g.bounds for g in G]; x0 = min(v[0] for v in b); y1 = max(v[3] for v in b); x1 = max(v[2] for v in b); y0 = min(v[1] for v in b)
    out = []
    for k, g, g0 in zip(keys, S, G):
        if g is None or g.is_empty: g = g0
        d = ''; R = polys(g)
        for poly in R:
            if poly.area < 4 * Q * Q and len(R) > 1: continue
            for ring in [poly.exterior] + list(poly.interiors):
                pts = [(round((x - x0) / Q), round((y1 - y) / Q)) for x, y in ring.coords[:-1]]
                q = [pts[0]] + [bb for aa, bb in zip(pts, pts[1:]) if aa != bb]
                if len(q) > 1 and q[-1] == q[0]: q.pop()
                if len(q) < 3: continue
                d += 'M%d %dl' % q[0] + ' '.join('%d %d' % (bb[0] - aa[0], bb[1] - aa[1]) for aa, bb in zip(q, q[1:])) + 'z'
        out.append([k, d]); n += 1
    rel = f'mapas/sec/{Y}/p{p}.json'
    s = json.dumps(dict(w=round((x1 - x0) / Q), h=round((y1 - y0) / Q), q=Q, s=out), separators=(',', ':'))
    open(f'{OUT}/{rel}.js', 'w').write('(window.__J=window.__J||{})[%s]=%s;' % (json.dumps(rel), s)); tot += len(s)
print(Y, 'tol', TOL, 'secciones', n, 'provincias', len(byp), 'MB', round(tot / 1e6, 2), flush=True)
