#!/usr/bin/env python3
"""plan_products.py INGDIR OUTDIR [--build] [--ext JOBFILE SECONDS SEEDBASE]

Catalogue of our own ternary strength-2 arrays in INGDIR (files s_N_k.txt, 0-based, with optional
s_N_k.txt.prov holding a one-line method; OA9 = Bose OA(9;2,4,3) built in). Products: two arrays
give N1+N2-min(3,d1+d2) rows and k1*k2 columns (prod2.py; generalized direct product of Colbourn and
Torres-Jimenez 2013, Cor. 4.3; d = largest set of pairwise disjoint rows); two levels allowed.

Default: print, per group-B target k, the smallest N reachable (CSV k,N_target,N_plan,plan).
--build: build the best product plan per target, cut to k columns: OUTDIR/prodplan_N_k.txt (+ .prov).
--ext JOBFILE SECONDS SEEDBASE: for every target whose best plan is above the target size, build for
  each N from N_target to N_best-1 the product with the most columns at <= N rows (if it has at least
  60% of the target columns) and write an ext2 column-extension job (to the target k) to JOBFILE;
  with --drop also a row-deletion job (the best plan's array minus its last row, repaired by ext2 at
  N_best-1); off by default: on CA(28;2,449,3) -> 27 rows it stayed at about 560 uncovered tuples.
"""
import sys, os, glob, re, itertools, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from prod2 import read, disjoint_set
T = [(20,15),(21,16),(29,17),(46,18),(49,19),(63,20),(93,21),(107,22),(138,23),(199,24),(216,25),(288,26),
     (435,27),(449,28),(610,29),(878,30),(964,31),(1308,32),(1964,33),(2700,35)]
a = sys.argv[1:]
ing, out = a[0], a[1]; build = '--build' in a
ext = None
DROP = '--drop' in a   # row-deletion jobs: off by default (a cloud test left ~560 tuples uncovered)
if '--ext' in a:
    i = a.index('--ext'); ext = (a[i+1], int(a[i+2]), int(a[i+3]))
os.makedirs(out, exist_ok=True)
prov = {'OA9': 'Bose OA(9;2,4,3) (rows (x,y,x+y,x+2y) mod 3)'}
cat = [('OA9', 9, 4, 1)]
for f in sorted(glob.glob(os.path.join(ing, 's_*_*.txt'))):
    m = re.search(r's_(\d+)_(\d+)\.txt$', f); N, k = int(m.group(1)), int(m.group(2))
    A, _ = read(f); d = len(disjoint_set(A, 3))
    cat.append((f, N, k, d))
    p = f + '.prov'
    prov[f] = open(p).read().strip() if os.path.exists(p) else 'our array ' + os.path.basename(f)
plans = [((x[0],), x[1], x[2], x[3]) for x in cat]
for x, y in itertools.combinations_with_replacement(cat, 2):
    plans.append(((x[0], y[0]), x[1] + y[1] - min(3, x[3] + y[3]), x[2] * y[2], 1))
for p in [p for p in plans if len(p[0]) == 2]:
    for x in cat:
        if p[2] * x[2] > 30000: continue
        plans.append(((p[0], x[0]), p[1] + x[1] - min(3, 1 + x[3]), p[2] * x[2], 1))
def name(x):
    if isinstance(x, tuple):
        return x[0] if len(x) == 1 and not isinstance(x[0], tuple) and False else '(' + ' x '.join(name(y) for y in x) + ')'
    return 'OA9' if x == 'OA9' else os.path.basename(x)[2:-4].replace('_', '@')
def leaves(x):
    if isinstance(x, tuple):
        r = []
        for y in x: r += leaves(y)
        return r
    return [x]
def mk(c, tag):
    """build the product tree c; returns file name"""
    if not isinstance(c, tuple): return c
    if len(c) == 1: return mk(c[0], tag)
    parts = [mk(x, tag + str(i)) for i, x in enumerate(c)]
    fn = os.path.join(out, f"tmp_{tag}.txt")
    subprocess.run(['python3', os.path.join(HERE, 'prod2.py'), parts[0], parts[1], fn], check=True, stdout=subprocess.DEVNULL)
    return fn
def write_cut(src, k, dst, comp):
    rows = [l.split() for l in open(src) if l.strip()]
    with open(dst, 'w') as f:
        for r in rows: f.write(' '.join(r[:k]) + '\n')
    lv = leaves(comp)
    if len(lv) == 1:
        method = prov[lv[0]] + (f' (cut to {k} columns)' if k < len(rows[0]) else '')
    else:
        method = ('generalized direct product (prod2.py; Colbourn-Torres-Jimenez 2013 Cor. 4.3) ' + name(comp)
              + f', cut to {k} columns; ingredients: ' + '; '.join(sorted(set(f"{name(l)} = {prov[l]}" for l in lv))))
    with open(dst + '.prov', 'w') as f:
        f.write(f"method={method}\ncommand=python3 plan_products.py (prod2.py {name(comp)})\nseed=none\n")
    return len(rows)
res = []
for k, Nt in T:
    best = min((p for p in plans if p[2] >= k), key=lambda p: (p[1], len(str(p[0]))))
    res.append((k, Nt, best))
    if not build and not ext: print(f"{k},{Nt},{best[1]},{name(best[0])}")
if build:
    for k, Nt, best in res:
        if len(best[0]) == 1: continue
        fn = mk(best[0], f"k{k}")
        N = write_cut(fn, k, os.path.join(out, f"prodplan_{len(open(fn).readlines())}_{k}.txt"), best[0])
        print(f"BUILT,{k},{N},{name(best[0])}")
if ext:
    jf, secs, seed = ext; jobs = []
    for k, Nt, best in res:
        if best[1] <= Nt: continue
        for N in range(Nt, best[1]):
            cands = [p for p in plans if p[1] <= N and p[2] < k and p[0] != ('OA9',)]
            if not cands: continue
            p = max(cands, key=lambda p: (p[2], -p[1]))
            if p[2] < 0.6 * k: continue
            fn = mk(p[0], f"e{k}_{N}")
            src = os.path.join(out, f"prodext_{p[1]}_{p[2]}_for{k}.txt")
            write_cut(fn, p[2], src, p[0])
            seed += 1
            pre = os.path.join(out, f"ext_{k}_{N}")
            jobs.append(f"ext_{k}_{N}|SAT={'0.35' if seed % 2 == 0 else '0.30'} NEWCOLTRY=10 SAVEK={k}|ext2 {N} {k} 3 {seed} {secs} {pre} {src} {p[2]}")
        if DROP and len(best[0]) > 1:
            fn = mk(best[0], f"d{k}")
            src = os.path.join(out, f"proddrop_{best[1]}_{k}.txt")
            write_cut(fn, k, src, best[0])
            seed += 1
            pre = os.path.join(out, f"drop_{k}_{best[1]-1}")
            jobs.append(f"drop_{k}_{best[1]-1}|SAT=0.35|ext2 {best[1]-1} {k} 3 {seed} {secs} {pre} {src}")
    with open(jf, 'w') as f:
        for j in jobs: f.write(j + '\n')
    print(f"{len(jobs)} jobs -> {jf}")
