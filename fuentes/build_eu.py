"""Europeas: ficheros de mesa del Ministerio del Interior (tipo 07) -> datos/<aaaa-mm>/...
Circunscripción única: D'Hondt nacional sin barrera."""
import sys, os, re, json, collections
import numpy as np, pandas as pd
R = '/tmp/w/raw'
OUT = '/tmp/w/out'
DIRS = {d[2:6] + '-' + d[6:8]: d for d in sorted(os.listdir(R)) if d.endswith('_MESA')}
DATES = {'1987-06': '10 de junio de 1987', '1989-06': '15 de junio de 1989', '1994-06': '12 de junio de 1994', '1999-06': '13 de junio de 1999',
         '2004-06': '13 de junio de 2004', '2009-06': '7 de junio de 2009', '2014-05': '25 de mayo de 2014', '2019-05': '26 de mayo de 2019', '2024-06': '9 de junio de 2024'}
MAPYEAR = {'1987-06': 2001, '1989-06': 2001, '1994-06': 2001, '1999-06': 2001, '2004-06': 2004, '2009-06': 2010, '2014-05': 2014, '2019-05': 2019, '2024-06': 2024}
# referencia de nombres (Generales 2023)
REF = json.load(open('/tmp/w/build/ref_general.json'))
PNAME = {p['id']: p['n'] for p in REF['prov']}; PCC = {p['id']: p['cc'] for p in REF['prov']}
CCAA = REF['ccaa']

# clave -> (nombre, color claro, color oscuro)
STY = {
 'PSOE': ('PSOE', '#e30613', '#f0535b'), 'PP': ('PP', '#1d84ce', '#4aa3e8'), 'CDS': ('CDS', '#2faa6a', '#4fcb8a'),
 'IU': ('IU', '#8f2d56', '#c0628a'), 'PODEMOS': ('Podemos', '#7b3f98', '#a678c6'), 'SUMAR': ('Sumar', '#e6007e', '#f2489f'),
 'CS': ('Cs', '#eb6109', '#f58a3d'), 'UPYD': ('UPyD', '#cc3399', '#e060b4'), 'VOX': ('Vox', '#5aa31f', '#7cc43a'),
 'CIU': ('CiU', '#1d3f94', '#5577cc'), 'JUNTS': ('Junts', '#00a99d', '#2bc7ba'), 'ERC': ('ERC', '#e8890c', '#f29a2a'),
 'HB': ('HB', '#6b7d12', '#98ad3a'), 'BNG': ('BNG', '#3aa0c4', '#5bbbdc'), 'PA': ('PA', '#2e7d32', '#5fa863'),
 'PACMA': ('PACMA', '#7fb800', '#9fd32b'), 'SALF': ('SALF', '#b8860b', '#d6a428'), 'FN': ('Frente Nacional', '#6b5b3a', '#a08f66'),
 'UV': ('UV', '#c7691d', '#e0924e'), 'PAR': ('PAR', '#7b5ea7', '#a089c8'), 'CC': ('AIC', '#d9b800', '#ecc82a'),
 'VERDES': ('Los Verdes', '#4caf50', '#74c878'), 'PDP': ('PDP', '#3f6fb5', '#6f97d4'),
 # coaliciones propias de las europeas
 'RM': ('Ruiz-Mateos', '#a4762c', '#c99a50'), 'CN': ('Coalición Nacionalista', '#0b6b3a', '#3aa56a'),
 'PEP': ('Europa de los Pueblos', '#c2410c', '#e0703a'), 'IP': ('Izquierda de los Pueblos', '#a04a6a', '#c77593'),
 'CE': ('Coalición Europea', '#c49a00', '#dfb92a'), 'GALEUSCA': ('Galeusca', '#2a6f97', '#5a9cc4'),
 'CEU': ('CEU', '#2a6ebb', '#5b9be0'), 'II': ('Iniciativa Internacionalista', '#8a9a0a', '#adc12a'),
 'LPD': ('Los Pueblos Deciden', '#8a9a0a', '#adc12a'), 'PRIMAVERA': ('Primavera Europea', '#d9792a', '#ec9b55'),
 'AHORA': ('Ahora Repúblicas', '#f0a020', '#f5b84f'), 'COMPROMIS': ('Compromís', '#e08a1e', '#f0a850'),
 'PNVUE': ('Unión Europeísta', '#4aae4a', '#6fc86f'), 'EB': ('Escaños en Blanco', '#9e9e9e', '#b0b0b0'),
 'PTE': ('PTE-UC', '#b03a2e', '#d0645a'),
}
# (año, código de candidatura) -> (clave, nombre visible)
MAP = {
 1987: {1: ('PSOE', 'PSOE'), 2: ('PP', 'AP'), 3: ('CDS', 'CDS'), 4: ('IU', 'IU'), 10: ('CIU', 'CiU'), 9: ('HB', 'HB'), 108: ('PEP', 'Europa de los Pueblos'),
        112: ('IP', 'Izquierda de los Pueblos'), 109: ('PNVUE', 'Unión Europeísta (PNV)'), 37: ('PTE', 'PTE-UC'), 82: ('PA', 'PA'), 5: ('PDP', 'PDP'), 34: ('UV', 'UV'),
        105: ('FN', 'Frente Nacional'), 20: ('VERDES', 'Los Verdes'), 22: ('PAR', 'PAR'), 13: ('CC', 'AIC')},
 1989: {11: ('PSOE', 'PSOE'), 10: ('PP', 'PP'), 25: ('CDS', 'CDS'), 17: ('IU', 'IU'), 24: ('CIU', 'CiU'), 15: ('RM', 'Ruiz-Mateos'), 5: ('CN', 'Coalición Nacionalista'),
        6: ('PA', 'PA'), 1: ('IP', 'Izquierda de los Pueblos'), 8: ('HB', 'HB'), 14: ('PEP', 'Europa de los Pueblos'), 3: ('PTE', 'PTE-UC'), 31: ('VERDES', 'Lista Verde')},
 1994: {29: ('PP', 'PP'), 33: ('PSOE', 'PSOE'), 4: ('IU', 'IU'), 18: ('CIU', 'CiU'), 2: ('CN', 'Coalición Nacionalista'), 7: ('PEP', 'Europa de los Pueblos'),
        27: ('CDS', 'Foro-CDS'), 12: ('HB', 'HB'), 36: ('PA', 'PA-PAP'), 8: ('BNG', 'BNG'), 14: ('RM', 'Ruiz-Mateos'), 10: ('VERDES', 'Grupo Verde')},
 1999: {1: ('PP', 'PP'), 19: ('PSOE', 'PSOE-Progresistas'), 122: ('IU', 'IU-EUiA'), 4: ('CIU', 'CiU'), 131: ('CE', 'Coalición Europea'), 123: ('CN', 'CN-Europa de los Pueblos'),
        8: ('BNG', 'BNG'), 7: ('HB', 'EH'), 137: ('VERDES', 'Los Verdes-IP')},
 2004: {42: ('PSOE', 'PSOE'), 43: ('PP', 'PP'), 13: ('GALEUSCA', 'Galeusca'), 78: ('IU', 'IU-ICV-EUiA'), 1: ('PEP', 'Europa de los Pueblos'), 11: ('CE', 'Coalición Europea'),
        19: ('VERDES', 'Los Verdes')},
 2009: {8: ('PP', 'PP'), 28: ('PSOE', 'PSOE'), 2: ('CEU', 'CEU'), 21: ('IU', 'IU-ICV-EUiA-BA'), 17: ('UPYD', 'UPyD'), 6: ('PEP', 'EdP-Verdes'),
        31: ('II', 'Iniciativa Internacionalista'), 25: ('VERDES', 'Los Verdes')},
 2014: {3: ('PP', 'PP'), 12: ('PSOE', 'PSOE'), 55: ('IU', 'La Izquierda Plural'), 45: ('PODEMOS', 'Podemos'), 4: ('UPYD', 'UPyD'), 17: ('CEU', 'CEU'),
        43: ('ERC', 'EPDD (ERC)'), 11: ('CS', 'Cs'), 49: ('LPD', 'Los Pueblos Deciden'), 52: ('PRIMAVERA', 'Primavera Europea'), 53: ('VOX', 'Vox'), 8: ('PACMA', 'PACMA'),
        25: ('EB', 'Escaños en Blanco')},
 2019: {3: ('PSOE', 'PSOE'), 30: ('PP', 'PP'), 23: ('CS', 'Cs'), 20: ('PODEMOS', 'Unidas Podemos'), 25: ('VOX', 'Vox'), 6: ('AHORA', 'Ahora Repúblicas'),
        24: ('JUNTS', 'Junts'), 2: ('CEU', 'CEUS'), 16: ('COMPROMIS', 'Compromís'), 9: ('PACMA', 'PACMA')},
 2024: {22: ('PP', 'PP'), 17: ('PSOE', 'PSOE'), 21: ('VOX', 'Vox'), 10: ('AHORA', 'Ahora Repúblicas'), 32: ('SUMAR', 'Sumar'), 42: ('SALF', 'SALF'),
        25: ('PODEMOS', 'Podemos'), 60: ('JUNTS', 'Junts'), 2: ('CEU', 'CEUS'), 39: ('PACMA', 'PACMA'), 46: ('CS', 'Cs')},
}
EXTRA = ['#7b3f98', '#a0522d', '#5f6caf', '#c0733f', '#2e8b8b', '#9c9c3c', '#b34a6e', '#6b8e23']

def rdf(e, n):
    d = DIRS[e]; return open(f'{R}/{d}/{n}07{d[4:8]}.DAT', encoding='latin1').read().splitlines()
def fixname(nm):
    nm = nm.strip()
    m = re.match(r"^(.*), (El|La|Los|Las|A|O|Os|As|L'|Els|Les|Sa|Ses|Es|Na)$", nm)
    return (m.group(2) + ('' if m.group(2).endswith("'") else ' ') + m.group(1)) if m else nm
def titl(s):
    s = s.title()
    return re.sub(r"\b(De|Del|La|Las|Los|Y|E|I|Per|Por|El|En|Para|Con|A)\b", lambda m: m.group(1).lower(), s)

# nombres de municipio actuales (europeas 2024)
_M24 = {}
for l in rdf('2024-06', '05'):
    if l[16:18] == '99': _M24[l[11:13] + l[13:16]] = fixname(l[18:118])

def js(path, obj):
    os.makedirs(os.path.dirname(f'{OUT}/{path}'), exist_ok=True)
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    open(f'{OUT}/{path}.js', 'w', encoding='utf8').write('(window.__J=window.__J||{})[%s]=%s;' % (json.dumps(path), s))
    return len(s)

def dhondt(v, seats):
    q = sorted(((int(v[i]) / d, int(v[i]), i) for i in range(len(v)) if v[i] > 0 for d in range(1, seats + 1)), reverse=True)[:seats]
    se = np.zeros(len(v), dtype=int)
    for _, _, i in q: se[i] += 1
    return se

def build(e):
    year = int(e[:4]); M = MAP[year]
    cand = {}
    for l in rdf(e, '03'): cand[int(l[8:14])] = (l[14:64].strip(), l[64:214].strip(), int(l[226:232]))
    # 08: votos y escaños por provincia y nacionales
    V08 = collections.defaultdict(lambda: collections.defaultdict(int)); NAT = {}; SEAT = {}
    for l in rdf(e, '08'):
        c, p = l[9:11], l[11:13]; k = int(l[14:20]); v = int(l[20:28]); s = int(l[28:33])
        if c == '99': NAT[k] = v; SEAT[k] = s
        elif p != '99': V08[p][k] += v
    T = sum(NAT.values())
    order = sorted(NAT, key=lambda k: -NAT[k])
    # agrupa por clave (cada candidatura es una lista nacional; la clave solo da nombre/color)
    parties = []; nidx = {}; ex = 0; usedk = set()
    for k in order:
        if k in M:
            key, name = M[k]; c, d = STY[key][1], STY[key][2]
        else:
            sig = cand[k][0]; key = 'C%d' % k; name = sig if len(sig) <= 16 else titl(sig)[:28]
            if NAT[k] > 0.004 * T: c = d = EXTRA[ex % len(EXTRA)]; ex += 1
            else: c, d = '#8a94a1', '#7a8593'
        assert key not in usedk, (e, key); usedk.add(key)
        nm = cand[k][1]
        nidx[k] = len(parties)
        parties.append(dict(k=key, n=name, full=titl(nm) if nm.isupper() else nm, cod=k, c=c, d=d))
    NP = len(parties)
    cod2i = {k: nidx.get(c[2]) for k, c in cand.items()}
    for k in NAT: cod2i.setdefault(k, nidx[k])
    # 07: provincias, comunidades y nación
    P07 = {}; NAT07 = None
    for l in rdf(e, '07'):
        c, p, dg = l[9:11], l[11:13], l[13]
        rec = dict(censo=int(l[85:93]), bl=int(l[125:133]), nu=int(l[133:141]), vc=int(l[141:149]))
        if c == '99': NAT07 = rec
        elif dg == '9' and p != '99': P07[p] = rec
    seats = sum(SEAT.values())
    # mesas
    sec3 = (lambda s: s[1:4]) if year <= 1989 else (lambda s: s[:3])
    mesas = []
    for l in rdf(e, '09'):
        if l[11:13] == '99': continue
        mesas.append((l[11:13], l[13:16], l[16:18] + sec3(l[18:22]), int(l[30:37]), int(l[65:72]), int(l[72:79]), int(l[79:86])))
    mesa = pd.DataFrame(mesas, columns='prov mun cus censo bl nu vc'.split())
    VV = []; unk = 0
    for l in rdf(e, '10'):
        if l[11:13] == '99': continue
        c_ = int(l[23:29]); vv_ = int(l[29:36])
        if cod2i.get(c_) is None:
            unk += vv_; continue
        VV.append((l[11:13], l[13:16], l[16:18] + sec3(l[18:22]), cod2i[c_], vv_))
    vot = pd.DataFrame(VV, columns='prov mun cus pi votos'.split())
    mesa['cera'] = mesa.mun.eq('999'); vot['cera'] = vot.mun.eq('999')
    S = mesa[~mesa.cera].groupby(['prov', 'mun', 'cus']).agg(censo=('censo', 'sum'), bl=('bl', 'sum'), nu=('nu', 'sum'), vc=('vc', 'sum')).reset_index()
    SV = vot[~vot.cera].groupby(['prov', 'mun', 'cus', 'pi']).votos.sum().reset_index()
    chk = SV.groupby(['prov', 'mun', 'cus']).votos.sum().rename('sv').reset_index().merge(S, on=['prov', 'mun', 'cus'], how='outer').fillna(0)
    CE = mesa[mesa.cera].groupby('prov').agg(censo=('censo', 'sum'), bl=('bl', 'sum'), nu=('nu', 'sum'))
    CV = vot[vot.cera].groupby(['prov', 'pi']).votos.sum().reset_index()
    # provincias: votos oficiales (08), censo/blancos/nulos oficiales (07)
    provs = []; dev = 0
    for p in sorted(P07):
        v = np.zeros(NP, dtype=np.int64)
        for k, x in V08[p].items():
            if cod2i.get(k) is not None: v[cod2i[k]] += x
        mv = np.zeros(NP, dtype=np.int64)
        for i, x in SV[SV.prov == p].groupby('pi').votos.sum().items(): mv[i] += x
        cvv = np.zeros(NP, dtype=np.int64)
        for r in CV[CV.prov == p].itertuples(): mv[r.pi] += r.votos; cvv[r.pi] += r.votos
        dev += int(np.abs(mv - v).sum())
        ce = CE.loc[p] if p in CE.index else None
        provs.append(dict(id=p, n=PNAME[p], cc=PCC[p], s=0, censo=P07[p]['censo'], bl=P07[p]['bl'], nu=P07[p]['nu'], v=[int(x) for x in v], cera=[int(x) for x in cvv],
                          cera_bl=int(ce.bl) if ce is not None else 0, cera_nu=int(ce.nu) if ce is not None else 0, cera_censo=int(ce.censo) if ce is not None else 0))
    natv = np.sum([p['v'] for p in provs], axis=0)
    # comprobaciones
    offv = np.zeros(NP, dtype=np.int64)
    for k, x in NAT.items(): offv[nidx[k]] += x
    offs = np.zeros(NP, dtype=int)
    for k, x in SEAT.items(): offs[nidx[k]] += x
    mine = dhondt(natv, seats)
    print(e, 'cand', NP, 'escaños', seats, 'D\'Hondt==oficial:', bool((mine == offs).all()), 'votos prov==nac:', bool((natv == offv).all()),
          'censo', sum(p['censo'] for p in provs), NAT07['censo'], 'secciones', len(S), 'descuadre vcand', int((chk.sv != chk.vc).sum()),
          'desv. mesas %.3f%%' % (dev / natv.sum() * 100), 'votos sin candidatura', unk, 'mesas', len(mesa))
    if not (mine == offs).all():
        print('   DIF', [(parties[i]['k'], int(mine[i]), int(offs[i])) for i in range(NP) if mine[i] != offs[i]])
    notas = []
    d_ = dev / natv.sum()
    if d_ > 0.0005:
        notas.append('Los resultados de municipios y secciones proceden de los ficheros de mesa del Ministerio del Interior, que difieren un %s %% del escrutinio oficial; provincias, comunidades, escaños y totales son los oficiales.' % (('%.2f' % (d_ * 100)).replace('.', ',')))
    if e == '2019-05':
        notas.append('España eligió 54 eurodiputados en 2019; tras la salida del Reino Unido (febrero de 2020) se le asignaron 5 más (PSOE, PP, Cs, Vox y Junts, uno cada uno). Aquí se muestra el reparto de 54 proclamado tras la elección.')
    if e == '2024-06':
        pass
    gen = dict(id=e, title='Elecciones al Parlamento Europeo', date=DATES[e], year=year, sections=True, mapyear=MAPYEAR[e], seats=seats,
               parties=parties, ccaa=CCAA, prov=provs,
               nat=dict(censo=int(NAT07['censo']), bl=int(NAT07['bl']), nu=int(NAT07['nu']), v=[int(x) for x in natv], es=[int(x) for x in offs]),
               notas=notas, mesas=len(mesa))
    tot = js(f'datos/{e}/general.json', gen)
    # ficheros por provincia
    buckets = collections.defaultdict(dict); mlist = []
    Sg = {p: g for p, g in S.groupby('prov')}; SVg = {p: g for p, g in SV.groupby('prov')}
    M05 = {}
    for l in rdf(e, '05'):
        if l[16:18] == '99': M05[l[11:13] + l[13:16]] = dict(name=fixname(l[18:118]), pob=int(l[128:136] or 0))
    for pr in provs:
        p = pr['id']; s = Sg.get(p); sv = SVg.get(p)
        used = sorted(sv.pi.unique()); loc = {g: j for j, g in enumerate(used)}
        secv = {}
        for (m, c), g in sv.groupby(['mun', 'cus']):
            a = [0] * len(used)
            for i, x in zip(g.pi, g.votos): a[loc[i]] = int(x)
            secv[(m, c)] = a
        muns = []
        for m, g in s.groupby('mun'):
            secs = []; mv = [0] * len(used)
            for rr in g.sort_values('cus').itertuples():
                a = secv.get((m, rr.cus), [0] * len(used)); secs.append([rr.cus, int(rr.censo), int(rr.bl), int(rr.nu)] + a)
                for j, x in enumerate(a): mv[j] += x
            info = M05.get(p + m, dict(name=p + m, pob=0))
            muns.append([m, _M24.get(p + m, info['name']), int(g.censo.sum()), int(g.bl.sum()), int(g.nu.sum()), mv, secs, info['pob']])
        for m in muns: mlist.append([p + m[0], m[1], m[7], m[2]])
        buckets[int(p) // 9][p] = dict(p=p, parties=[int(u) for u in used], m=muns)
    for k, d in sorted(buckets.items()): tot += js(f'datos/{e}/prov_b{k}.json', d)
    tot += js(f'datos/{e}/municipios.json', mlist)
    # cuadre municipio x candidatura con el fichero 06 oficial
    OFF = collections.Counter()
    for l in rdf(e, '06'):
        if l[14:16] == '99' and l[11:14] != '999' and l[9:11] != '99':
            k = cod2i.get(int(l[16:22]))
            if k is not None: OFF[(l[9:11] + l[11:14], k)] += int(l[22:30])
    mine = collections.Counter()
    for r in SV.itertuples(): mine[(r.prov + r.mun, r.pi)] += r.votos
    diff = [k for k in set(mine) | set(OFF) if mine[k] != OFF[k]]
    print('   MB', round(tot / 1e6, 2), 'municipios', len(mlist), 'mun×cand distintos del 06:', len(diff), 'de', len(OFF))
    return gen

if __name__ == '__main__':
    els = sys.argv[1:] or sorted(DIRS, reverse=True)
    for e in els: build(e)
    EL = [dict(id=e, label='Elecciones europeas %d' % int(e[:4]), kind='Europeas') for e in sorted(DIRS, reverse=True)]
    js('datos/elecciones.json', EL)
