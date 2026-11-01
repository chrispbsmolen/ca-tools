"""derive_laws.py - lookups and the published constructions used by tools/derive_table.py.

Ported unchanged in arithmetic from the private audit engine of 2026-10-26 (calibrated there:
it reproduces the record at its own parameters), restricted to constructions published in the
literature; the laws proved only in that audit (U, T5, A, S and the COD refinement of the k-ary
Roux construction) are left out. Conventions:
  ecan(t, k, v): stair-step lookup, the smallest N over rows with k' >= k; None beyond the table.
  CAN(t', k', v) for k' < t' is 0 in a product cross term (the term is vacuous: no t-set has
  that many columns on that side); v^t' when k' == t'.
"""
import csv, bisect, collections, functools, math, os
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys as _sys
_sys.path.insert(0, os.path.join(_REPO, 'table'))
from ca_table import counted  # the one definition of the counted rows
ROOT = os.environ.get('CA_TABLE', os.path.join(_REPO, 'table', 'ca_table.csv'))
DCAN_CSV = os.environ.get('DCAN_CSV', os.path.join(_REPO, 'r', 'livingtable', 'data', 'dcan_table.csv'))
rows = list(csv.DictReader(open(ROOT)))

def load(sources=None):
    """stair-step data over the counted rows (table/ca_table.py counted())"""
    d = collections.defaultdict(list)
    for r in counted(rows):
        if sources and r['source_id'] not in sources: continue
        key = (int(r['t']), int(r['v']), int(r['k']), int(float(r['N'])))
        d[(key[0], key[1])].append((key[2], key[3], r['construction']))
    look = {}
    for tv, lst in d.items():
        lst.sort()
        ks = [x[0] for x in lst]; Ns = [x[1] for x in lst]
        suf = [0] * len(lst); m = 10 ** 18
        for i in range(len(lst) - 1, -1, -1):
            m = min(m, Ns[i]); suf[i] = m
        look[tv] = (ks, suf, lst)
    return look

def grid_of(look):
    return {tv: sorted(set(ks)) for tv, (ks, suf, lst) in look.items()}

def mk_ecan(look):
    @functools.lru_cache(maxsize=None)
    def ecan(t, k, v):
        if t <= 0: return 1
        if t == 1: return v
        if k < t: return 0          # vacuous cross term (Martirosyan-Colbourn convention)
        if k == t: return v ** t
        if (t, v) not in look: return None
        ks, suf, lst = look[(t, v)]
        i = bisect.bisect_left(ks, k)
        if i >= len(ks): return None
        return suf[i]
    return ecan

def row_source(look, t, v, k):
    """construction label of the row answering the stair-step lookup (t,v,k)"""
    ks, suf, lst = look[(t, v)]
    i = bisect.bisect_left(ks, k); best = suf[i]
    for j in range(i, len(lst)):
        if lst[j][1] == best: return lst[j][0], lst[j][2]
    return None

def is_pp(v):
    p = 2
    while v % p: p += 1
    while v % p == 0: v //= p
    return v == 1

PRIME_POWERS = [q for q in range(2, 20000) if is_pp(q)]

def qmin(v):
    f = []; p = 2; x = v
    while x > 1:
        if x % p == 0:
            q = 1
            while x % p == 0: x //= p; q *= p
            f.append(q)
        p += 1
    return min(f)

def turan(t, v):
    """Turan number T(t, v) as in arith_laws.R (edges of the balanced complete v-partite graph on t vertices)"""
    if v >= t: return t * (t - 1) // 2
    a = t // v; b = a + 1; nb = t - a * v; na = v - nb
    return t * (t - 1) // 2 - na * a * (a - 1) // 2 - nb * b * (b - 1) // 2

# Yin 2003 DCAN values (CMTW convention: nonzero differences; over the group named in the table)
DCAN = {}
for r in csv.DictReader(open(DCAN_CSV)):
    DCAN[(int(r['v']), int(r['k']))] = (int(r['DCAN_cmtw']), r['group'], r['over_Zv'] == 'TRUE')

# ---------------------------------------------------------------- laws
# each law: fn(ecan, t, v, k) -> (N, detail) or None

def law_fuse(e, t, v, k, vmax=25):
    """CKRS 2010 Lemma 3.1 applied m times: CAN(t,k,v) <= CAN(t,k,v+m) - 2m; free: m >= 1"""
    best = None
    for m in range(1, vmax - v + 1):
        x = e(t, k, v + m)
        if x is None or x == 0: continue
        N = x - 2 * m
        if best is None or N < best[0]: best = (N, ('m', m))
    return best

def law_derive(e, t, v, k):
    """CKRS 2010 (7): CAN(t,k,v) <= floor(CAN(t+1,k+1,v)/v)"""
    x = e(t + 1, k + 1, v)
    if not x: return None
    return (x // v, ())

def law_comp(e, t, v, k):
    """CKRS 2010 (3), composition: CAN(t,k,v1 v2) <= CAN(t,k,v1) CAN(t,k,v2); free: the factorisation"""
    best = None
    for v1 in range(2, int(math.isqrt(v)) + 1):
        if v % v1: continue
        v2 = v // v1
        a = e(t, k, v1); b = e(t, k, v2)
        if not a or not b: continue
        N = a * b
        if best is None or N < best[0]: best = (N, ('v1v2', v1, v2))
    return best

def law_ck(e, t, v, k):
    """Chateauneuf-Kreher doubling (CCL 2008 Thm 2): CAN(3,2h,v) <= CAN(3,h,v)+(v-1)CAN(2,h,v); free: h >= ceil(k/2)"""
    if t != 3: return None
    best = None
    for h in range(max(3, (k + 1) // 2), k):
        a = e(3, h, v); b = e(2, h, v)
        if not a or not b: continue
        N = a + (v - 1) * b
        if best is None or N < best[0]: best = (N, ('h', h))
        break   # ecan is monotone in h, so the first evaluable h is optimal
    return best

def law_cmtw34(e, t, v, k):
    """CMTW 2006 Thm 3.4, prime power v >= 3: CAN(3, v h, v) <= CAN(3,h,v)+(v-1)CAN(2,h,v)+v^3-v^2, h = ceil(k/v)"""
    if t != 3 or v < 3 or not is_pp(v): return None
    h = -(-k // v)
    if h < 3: h = 3
    a = e(3, h, v); b = e(2, h, v)
    if not a or not b: return None
    return (a + (v - 1) * b + v ** 3 - v ** 2, ('h', h))

def law_kroux(e, t, v, k):
    """k-ary Roux (CCL 2008 Thm 3 = CMTW Thm 3.3): CAN(3, h l, v) <= CAN(3,h,v)+CAN(3,l,v)+CAN(2,l,v) DCAN(2,h,v),
    DCAN from Yin 2003 (dcan_table.csv); free: h in Yin's domain, l >= ceil(k/h)"""
    if t != 3: return None
    best = None
    for (vv, h), (D, grp, cyc) in DCAN.items():
        if vv != v or h < 3: continue      # h = 2 is the doubling (law_ck)
        l = max(3, -(-k // h))
        a = e(3, h, v); b = e(3, l, v); c = e(2, l, v)
        if not a or not b or not c: continue
        N = a + b + c * D                  # CMTW 2006 Thm 3.3 as published
        if best is None or N < best[0]: best = (N, ('h', h, 'l', l, 'D', D, grp))
    return best

def nmax(v):
    if v == 2: return 1
    if is_pp(v): return v - 1
    return max(2, qmin(v) - 1)

def pct_candidates(t, v, kmax, qcap=128, ecap=7):
    out = []
    for q in PRIME_POWERS:
        if q > qcap or q > kmax: break
        for ee in range(2, ecap + 1):
            M = (ee - 1) * turan(t, v) + 1
            if M > q + 1: break
            out.append((q, ee, M))
    return out

def law_pct(e, t, v, k, cands):
    """Power CT, established part only: DHF(M; t, q^e, q) from the transposed OA(q^e; q+1, q, e) (Colbourn 2009 /
    CZ 2012 Lemma 2.4, M = (e-1)T(t,v)+1 <= q+1), p extra columns with fresh symbols (trivial extension), each row a
    CA(t, q+p, v) with one constant row (CZ 2012 Thm 2.1, rho_i = 1, chi = 0): N = M (CAN(t, q+p, v) - 1)."""
    best = None
    for q, ee, M in cands:
        p = max(0, k - q ** ee)
        w = q + p
        if w >= k: continue
        x = e(t, w, v)
        if not x: continue
        N = M * (x - 1)
        if best is None or N < best[0]: best = (N, ('q', q, 'e', ee, 'p', p, 'M', M, 'w', w))
    return best

def law_dp2(e, t, v, k):
    """Colbourn and Torres-Jimenez 2013 Cor 4.3 with one constant row each (Obs 3.2): CAN(2,k1 k2,v) <= CAN(2,k1)+CAN(2,k2)-2"""
    if t != 2: return None
    best = None
    for k1 in range(2, int(math.isqrt(k)) + 2):
        k2 = -(-k // k1)
        if k2 < 2 or k2 < k1: continue
        a = e(2, k1, v); b = e(2, k2, v)
        if not a or not b: continue
        N = a + b - 2
        if best is None or N < best[0]: best = (N, ('k1', k1, 'k2', k2))
    return best

def law_od(e, t, v, k):
    """Cohen-Colbourn-Ling 2008 Construction 1: v = q+1, q prime power: CAN(3, q+1, q+1) <= q^3 - q + C(q+1,2) (CAN(3,q+1,2) - 1)"""
    if t != 3 or k > v or not is_pp(v - 1): return None
    q = v - 1
    b = e(3, q + 1, 2)
    if not b: return None
    return (q ** 3 - q + (q + 1) * q // 2 * (b - 1), ('q', q, 'N2', b))

def law_sm(e, t, v, k):
    """Shokri-Moura (JCD 2025; thesis Thm 5.2.6) general theorem with the RMS CPHF(2; q^2+q+1, q, 3) and the
    DCA(n(q-1)+1; 2, q^n, q) of thesis Thm 5.1.13 (x = q^n), m = n(q-1)+1 rows including the zero difference:
    N = 2 q^3 + (m - 2) N1 + CAN(3, q^n, q) at k = q^n (q^2+q+1), N1 = min(CAN(2, q^2+q+1, q), 2q^2 - q)."""
    if t != 3 or not is_pp(v): return None
    q = v; K = q * q + q + 1; best = None
    for n in range(1, 8):
        x = q ** n
        if x * K < k: continue
        m = n * (q - 1) + 1
        n1 = e(2, K, q)
        n1 = min(n1, 2 * q * q - q) if n1 else 2 * q * q - q
        c = e(3, x, q) if x >= 3 else (v ** x if x == 2 else 0)
        if c is None: continue
        N = 2 * q ** 3 + max(m - 2, 0) * n1 + c
        if best is None or N < best[0]: best = (N, ('x', x, 'm', m))
        break   # larger n only costs more at the same k
    return best

def explain(e, law, t, v, k, params):
    """The arithmetic of a law at its chosen parameters, with every ingredient as CAN(t,k,v)=N
    (the lookup value used, a table row or itself a derived value)."""
    p = list(params)
    def C(tt, kk, vv): return f'CAN({tt},{kk},{vv})={e(tt, kk, vv)}'
    if law == 'fuse': return C(t, k, v + p[1]) + f' - 2x{p[1]}'
    if law == 'derive': return 'floor(' + C(t + 1, k + 1, v) + f' / {v})'
    if law == 'comp': return C(t, k, p[1]) + ' x ' + C(t, k, p[2])
    if law == 'CK': return C(3, p[1], v) + f' + ({v}-1)x' + C(2, p[1], v)
    if law == 'CMTW34': return C(3, p[1], v) + f' + ({v}-1)x' + C(2, p[1], v) + f' + {v}^3-{v}^2'
    if law == 'kRoux': return C(3, p[1], v) + ' + ' + C(3, p[3], v) + ' + ' + C(2, p[3], v) + f' x DCAN(2,{p[1]},{v})={p[5]} (Yin 2003, {p[6]})'
    if law == 'PCT': return f'M={p[7]} x (' + C(t, p[9], v) + f' - 1), q={p[1]}, e={p[3]}, p={p[5]}'
    if law == 'DP2': return C(2, p[1], v) + ' + ' + C(2, p[3], v) + ' - 2'
    if law == 'OD': return f'{p[1]}^3-{p[1]} + C({p[1]}+1,2)x(' + C(3, p[1] + 1, 2) + ' - 1)'
    if law == 'SM':
        q = v; K = q * q + q + 1
        return f'2x{q}^3 + ({p[3]}-2)x' + f'min(CAN(2,{K},{q})={e(2, K, q)}, 2q^2-q={2*q*q-q})' + ' + ' + C(3, p[1], q)
    return ''
