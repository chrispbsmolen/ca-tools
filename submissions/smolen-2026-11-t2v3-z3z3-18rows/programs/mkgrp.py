#!/usr/bin/env python3
"""mkgrp.py NAME ... > spec : row-group spec files for orbq7 (non-cyclic groups). item123 step 10.
  mkgrp.py f21 A B F      rows: A copies of the 7-point action of the Frobenius group of order 21 (x->x+1, x->2x on Z7),
                          B copies of its 3-point action (x->x+1 trivial, x->2x a 3-cycle), F fixed rows
  mkgrp.py d N F          dihedral group of order 2N on N rows (x->x+1, x->-x) plus F fixed rows
  mkgrp.py z3z3 K1,K2,... F   Z3 x Z3 on the cosets of the listed subgroups; K = 0 (trivial: 9 rows) or one of
                          a b c d = the four subgroups of order 3 (<(1,0)>, <(0,1)>, <(1,1)>, <(1,2)>: 3 rows each); F fixed rows
Lines 'g' generate the group; lines 'h' are normaliser elements used only to cut the search by symmetry
(the program checks that each maps the vertex set to itself)."""
import sys, itertools
def out(N, gens, hs):
    print(N)
    for g in gens: print('g', *g)
    seen = set()
    for h in hs:
        t = tuple(h)
        if t != tuple(range(N)) and t not in seen and tuple(gens[0]) != t:
            seen.add(t); print('h', *h)
name = sys.argv[1]
if name == 'f21':
    A, B, F = map(int, sys.argv[2:5]); N = 7 * A + 3 * B + F
    a = list(range(N)); b = list(range(N)); c = list(range(N)); hs = []
    for i in range(A):
        for x in range(7):
            a[7 * i + x] = 7 * i + (x + 1) % 7; b[7 * i + x] = 7 * i + (2 * x) % 7; c[7 * i + x] = 7 * i + (3 * x) % 7
    for j in range(B):
        o = 7 * A + 3 * j
        for x in range(3): b[o + x] = o + (x + 1) % 3
        h = list(range(N))
        for x in range(3): h[o + x] = o + (x + 1) % 3
        hs.append(h)
    hs.append(c)
    for i in range(A - 1):
        h = list(range(N))
        for x in range(7): h[7 * i + x] = 7 * (i + 1) + x; h[7 * (i + 1) + x] = 7 * i + x
        hs.append(h)
    for j in range(B - 1):
        h = list(range(N)); o = 7 * A + 3 * j
        for x in range(3): h[o + x] = o + 3 + x; h[o + 3 + x] = o + x
        hs.append(h)
    for f in range(F - 1):
        h = list(range(N)); o = 7 * A + 3 * B + f; h[o] = o + 1; h[o + 1] = o; hs.append(h)
    out(N, [a, b], hs)
elif name == 'd':
    n, F = int(sys.argv[2]), int(sys.argv[3]); N = n + F
    a = list(range(N)); b = list(range(N)); hs = []
    for x in range(n): a[x] = (x + 1) % n; b[x] = (-x) % n
    from math import gcd
    for j in range(2, n):
        if gcd(j, n) == 1:
            h = list(range(N))
            for x in range(n): h[x] = (j * x) % n
            hs.append(h)
    for f in range(F - 1):
        h = list(range(N)); h[n + f] = n + f + 1; h[n + f + 1] = n + f; hs.append(h)
    out(N, [a, b], hs)
elif name == 'z3z3':
    Ks = sys.argv[2].split(','); F = int(sys.argv[3])
    sub = {'0': [(0, 0)], 'a': [(0, 0), (1, 0), (2, 0)], 'b': [(0, 0), (0, 1), (0, 2)],
           'c': [(0, 0), (1, 1), (2, 2)], 'd': [(0, 0), (1, 2), (2, 1)]}
    V = [(x, y) for x in range(3) for y in range(3)]
    add = lambda u, v: ((u[0] + v[0]) % 3, (u[1] + v[1]) % 3)
    coset = lambda v, K: frozenset(add(v, k) for k in sub[K])
    rows = []; start = []
    for i, K in enumerate(Ks):
        start.append(len(rows))
        cs = sorted(set(coset(v, K) for v in V), key=lambda s: sorted(s))
        rows += [(i, c) for c in cs]
    idx = {r: n for n, r in enumerate(rows)}; N = len(rows) + F
    def perm(f):  # f maps (orbit i, coset) -> (orbit j, coset)
        p = list(range(N))
        for r, n in idx.items(): p[n] = idx[f(r)]
        return p
    gens = [perm(lambda r, w=w: (r[0], frozenset(add(v, w) for v in r[1]))) for w in [(1, 0), (0, 1)]]
    hs = []
    for i in range(len(Ks)):   # translate one orbit only
        for w in [(1, 0), (0, 1)]:
            hs.append(perm(lambda r, i=i, w=w: (r[0], frozenset(add(v, w) for v in r[1])) if r[0] == i else r))
    for i in range(len(Ks)):   # swap equal orbits
        for j in range(i + 1, len(Ks)):
            if Ks[i] == Ks[j]:
                hs.append(perm(lambda r, i=i, j=j: (j, r[1]) if r[0] == i else ((i, r[1]) if r[0] == j else r)))
    # automorphisms: matrices in GL(2,3) that permute the kernels of the orbits compatibly
    for m in itertools.product(range(3), repeat=4):
        if (m[0] * m[3] - m[1] * m[2]) % 3 == 0: continue
        A = lambda v: ((m[0] * v[0] + m[1] * v[1]) % 3, (m[2] * v[0] + m[3] * v[1]) % 3)
        img = {K: frozenset(A(v) for v in sub[K]) for K in set(Ks)}
        back = {frozenset(sub[K]): K for K in sub}
        tgt = {K: back.get(img[K]) for K in img}
        # need a bijection of orbits i -> j with Ks[j] == tgt[Ks[i]]
        if sorted(tgt[K] for K in Ks if tgt[K]) != sorted(Ks): continue
        used = set(); mp = {}
        for i, K in enumerate(Ks):
            j = next(j for j in range(len(Ks)) if Ks[j] == tgt[K] and j not in used); used.add(j); mp[i] = j
        hs.append(perm(lambda r: (mp[r[0]], frozenset(A(v) for v in r[1]))))
    for f in range(F - 1):
        h = list(range(N)); o = len(rows) + f; h[o] = o + 1; h[o + 1] = o; hs.append(h)
    out(N, gens, hs)
