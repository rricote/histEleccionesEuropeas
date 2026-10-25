"""Mapas para Europeas:
  sec <año>  -> mapas/sec/<año>/b<k>.json.js (seccionado INE, mismo formato que Generales)
  ccaa       -> mapas/ccaa_mun/<cc>.json.js (municipios de cada comunidad en un marco común, seccionado 2024)
  nat        -> mapas/ccaa.json.js (contornos de comunidades en el marco de mapas/provincias.json)
"""
import shapefile, json, glob, os, math, sys, collections, warnings, re
warnings.filterwarnings('ignore')
import shapely
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
OUT = '/tmp/w/out'
REF = json.load(open('/tmp/w/build/ref_general.json')); PCC = {p['id']: p['cc'] for p in REF['prov']}
SRC = {'2010': ['/tmp/w/sec/s2010/Espa#U00f1a10/PeninsulayBaleares2010.shp', '/tmp/w/sec/s2010/Espa#U00f1a10/Canarias2010.shp'], '2009': ['/tmp/w/sec/s2009/Nacional09/PeninsulayBaleares.shp', '/tmp/w/sec/s2009/Nacional09/Canarias.shp'],
       '2014': ['/tmp/w/sec/s2014/SECC_CE_20140101_01_R_INE.shp'], '2024': ['/tmp/w/sec/s2024/SECC_CE_20240101.shp']}
ENC = {'2024': 'utf8'}

def read(Y):
    byp = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in SRC[Y]:
        r = shapefile.Reader(f, encoding=ENC.get(Y, 'latin1')); names = [x[0] for x in r.fields[1:]]
        for sr in r.iterShapeRecords():
            d = dict(zip(names, sr.record))
            if not sr.shape.points: continue
            g = shape(sr.shape.__geo_interface__)
            if g.is_empty: continue
            if not g.is_valid: g = make_valid(g)
            if 'CUSEC' in d: p = d['CPRO']; key = d['CMUN'] + d['CDIS'] + d['CSEC']
            else:
                pm = (d['PROVMUN'] or '').strip()
                if len(pm) != 5 or not pm.isdigit(): continue
                p = pm[:2]; key = pm[2:] + d['DISTRITO'].zfill(2) + d['SECCION'].zfill(3)
            byp[p][key].append(g)
    return byp

def polys(g):
    if g.geom_type == 'Polygon': return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'): return [x for p in g.geoms for x in polys(p)]
    return []

def enc(g, x0, y1, sc, minarea=1.5):
    d = ''; R = polys(g)
    for poly in R:
        if poly.area * sc * sc < minarea and len(R) > 1: continue
        for ring in [poly.exterior] + list(poly.interiors):
            pts = [(round((x - x0) * sc), round((y1 - y) * sc)) for x, y in ring.coords[:-1]]
            q = [pts[0]]
            for a in pts[1:]:
                if a != q[-1]: q.append(a)
            if len(q) < 3: continue
            d += 'M%d %dl' % q[0] + ' '.join('%d %d' % (b[0] - a[0], b[1] - a[1]) for a, b in zip(q, q[1:])) + 'z'
    return d

def wjs(rel, obj):
    os.makedirs(os.path.dirname(f'{OUT}/{rel}'), exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    open(f'{OUT}/{rel}.js', 'w', encoding='utf8').write('(window.__J=window.__J||{})[%s]=%s;' % (json.dumps(rel), s))
    return len(s)

def sec(Y):
    byp = read(Y); buckets = collections.defaultdict(dict); n = 0
    for p, dd in sorted(byp.items()):
        L = [(k, gs[0] if len(gs) == 1 else unary_union(gs)) for k, gs in dd.items()]; n += len(L)
        allb = [g.bounds for _, g in L]
        x0 = min(b[0] for b in allb); y1 = max(b[3] for b in allb); x1 = max(b[2] for b in allb); y0 = min(b[1] for b in allb)
        sc = 3000 / max(x1 - x0, y1 - y0); out = []
        for key, g in L:
            tol = min(60, max(4, math.sqrt(g.area) * 0.02))
            gs_ = g.simplify(tol, preserve_topology=True)
            if gs_.is_empty: gs_ = g
            out.append([key, enc(gs_, x0, y1, sc)])
        buckets[int(p) // 9][p] = dict(w=round((x1 - x0) * sc), h=round((y1 - y0) * sc), s=out)
    tot = sum(wjs(f'mapas/sec/{Y}/b{k}.json', d) for k, d in buckets.items())
    print(Y, 'secciones', n, 'provincias', len(byp), 'MB', round(tot / 1e6, 2))

NAMES = {}
def ccaa_mun():
    byp = read('2024')
    r = shapefile.Reader(SRC['2024'][0], encoding='utf8'); names = [x[0] for x in r.fields[1:]]
    for rec in r.iterRecords():
        d = dict(zip(names, rec)); NAMES[d['CUMUN']] = d['NMUN']
    bycc = collections.defaultdict(dict)
    for p, dd in byp.items():
        mm = collections.defaultdict(list)
        for k, gs in dd.items(): mm[p + k[:3]] += gs
        for m, gs in mm.items(): bycc[PCC[p]][m] = unary_union(gs)
    tot = 0
    for cc, D in sorted(bycc.items()):
        keys = sorted(D); G = [D[k] for k in keys]
        allb = [g.bounds for g in G]
        x0 = min(b[0] for b in allb); y1 = max(b[3] for b in allb); x1 = max(b[2] for b in allb); y0 = min(b[1] for b in allb)
        ext = max(x1 - x0, y1 - y0); sc = 2000 / ext
        tol = ext / 2000 * 1.1
        try: S = list(shapely.coverage_simplify(shapely.GeometryCollection(G).geoms, tol))
        except Exception as ex: print('cov fail', cc, ex); S = [g.simplify(tol) for g in G]
        ms = []
        for k, g in zip(keys, S):
            if g.is_empty: g = D[k]
            ms.append([k, NAMES.get(k, k), enc(g, x0, y1, sc, 0.8)])
        # contornos de provincia
        byprov = collections.defaultdict(list)
        for k, g in zip(keys, S): byprov[k[:2]].append(g)
        pr = [[p, enc(unary_union(gs).buffer(0), x0, y1, sc, 3)] for p, gs in sorted(byprov.items())] if len(byprov) > 1 else []
        tot += wjs(f'mapas/ccaa_mun/{cc}.json', dict(w=round((x1 - x0) * sc), h=round((y1 - y0) * sc), ms=ms, pr=pr))
        print(cc, len(ms), 'municipios')
    print('ccaa_mun MB', round(tot / 1e6, 2))

def nat():
    s = open('/tmp/w/build/provincias.json.js').read(); M = json.loads(s[s.index(']=') + 2:].rstrip().rstrip(';'))
    by = collections.defaultdict(list)
    for pid, d in M['paths'].items():
        rings = [[tuple(map(float, xy.split(','))) for xy in re.findall(r'(-?[\d.]+,-?[\d.]+)', sp)] for sp in re.split(r'(?=M)', d) if sp.strip()]
        ps = [Polygon(r).buffer(0) for r in rings if len(r) >= 3]
        by[PCC[pid]].append(unary_union(ps))
    out = {}
    for cc, gs in by.items():
        g = unary_union([x.buffer(0.8, join_style=2) for x in gs]).buffer(-0.8, join_style=2).simplify(0.3)
        d = ''
        for poly in polys(g):
            if poly.area < 4: continue
            for ring in [poly.exterior] + list(poly.interiors):
                c = list(ring.coords)[:-1]
                if len(c) < 3: continue
                d += 'M' + 'L'.join('%s,%s' % (round(x, 1), round(y, 1)) for x, y in c) + 'Z'
        big = max(polys(g), key=lambda p: p.area); rp = big.representative_point()
        out[cc] = dict(d=d, l=[round(rp.x), round(rp.y)])
    print('ccaa', len(out), wjs('mapas/ccaa.json', out))

if __name__ == '__main__':
    a = sys.argv[1]
    if a == 'sec': sec(sys.argv[2])
    elif a == 'ccaa': ccaa_mun()
    elif a == 'nat': nat()
