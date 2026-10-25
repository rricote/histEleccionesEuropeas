"""Contornos exteriores (sin límites internos): mapas/ccaa.json 'ES', mapas/ccaa_mun/<cc> 'out', mapas/prov_out.json"""
import json, re, sys
from shapely.geometry import Polygon
from shapely.ops import unary_union
O = sys.argv[1]
def L(f):
    s = open(f).read(); i = s.index(']=') + 2; return s[:i], json.loads(s[i:].rstrip().rstrip(';'))
def W(f, head, obj): open(f, 'w').write(head + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ';')
def rel_polys(d):
    out = []
    for sp in re.findall(r'M[^M]*', d):
        nums = list(map(float, re.findall(r'-?\d+\.?\d*', sp)))
        if len(nums) < 6: continue
        x, y = nums[0], nums[1]; pts = [(x, y)]
        for k in range(2, len(nums) - 1, 2): x += nums[k]; y += nums[k + 1]; pts.append((x, y))
        if len(pts) >= 3: out.append(Polygon(pts).buffer(0))
    return out
def abs_polys(d):
    out = []
    for sp in re.findall(r'M[^M]*', d):
        pts = [tuple(map(float, p.split(','))) for p in re.findall(r'-?[\d.]+,-?[\d.]+', sp)]
        if len(pts) >= 3: out.append(Polygon(pts).buffer(0))
    return out
def merge(ps, eps):
    g = unary_union([p.buffer(eps, join_style=2) for p in ps]).buffer(-eps, join_style=2)
    return [g] if g.geom_type == 'Polygon' else list(g.geoms)
def enc_rel(polys, minarea):
    d = ''
    for poly in polys:
        if poly.area < minarea: continue
        for ring in [poly.exterior] + list(poly.interiors):
            c = [(round(x), round(y)) for x, y in list(ring.coords)[:-1]]
            q = [c[0]] + [b for a, b in zip(c, c[1:]) if a != b]
            if len(q) < 3: continue
            d += 'M%d %dl' % q[0] + ' '.join('%d %d' % (b[0] - a[0], b[1] - a[1]) for a, b in zip(q, q[1:])) + 'z'
    return d
# España
h, C = L(f'{O}/mapas/ccaa.json.js')
ps = [p for cc, v in C.items() if cc != 'ES' for p in abs_polys(v['d'])]
g = merge(ps, 1.0); d = ''
for poly in g:
    if poly.area < 4: continue
    for ring in [poly.exterior] + list(poly.interiors):
        c = list(ring.coords)[:-1]; d += 'M' + 'L'.join('%s,%s' % (round(x, 1), round(y, 1)) for x, y in c) + 'Z'
C['ES'] = dict(d=d); W(f'{O}/mapas/ccaa.json.js', h, C); print('ES', len(d))
# comunidades
import glob
for f in sorted(glob.glob(f'{O}/mapas/ccaa_mun/*.json.js')):
    h, M = L(f); ps = [p for _, _, d in M['ms'] for p in rel_polys(d)]
    M['out'] = enc_rel(merge(ps, 1.5), 4); W(f, h, M); print(f[-10:], len(M['out']))
# provincias (marco de mapas/mun.json)
h, MU = L(f'{O}/mapas/mun.json.js'); P = {}
for pid, v in MU.items():
    ps = [p for _, _, d in v['ms'] for p in rel_polys(d)]
    P[pid] = enc_rel(merge(ps, 2.0), 6)
W(f'{O}/mapas/prov_out.json.js', '(window.__J=window.__J||{})["mapas/prov_out.json"]=', P); print('prov', sum(map(len, P.values())))
