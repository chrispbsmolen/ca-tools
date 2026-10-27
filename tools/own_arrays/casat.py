#!/usr/bin/env python3
"""casat.py - exact SAT construction of a covering array CA(N; t, k, v).

Usage: casat.py N t k v outfile [solver] [timeout_s] [--nosym] [--const=C]
Encoding: one-hot x[r,c,s] (for v = 2 a single boolean per cell); for every t-set of columns
and every tuple an auxiliary y[r] with y[r] -> x[r,c_i,s_i], and clause OR_r y[r].
Symmetry breaking (safe): row 0 is all zero (after renaming symbols in each column) and column 0
is sorted (after permuting rows); every covering array admits both.
Exit code 0 = found and written, 1 = UNSAT (proof that no CA(N; t, k, v) exists), 3 = timeout.
Written for this project (2026-10-27); no external ingredient.
"""
import sys, itertools, time, threading
from pysat.solvers import Solver

def main():
    a = sys.argv[1:]
    N, t, k, v = map(int, a[:4]); out = a[4]
    solver_name = a[5] if len(a) > 5 else 'cadical153'
    timeout = float(a[6]) if len(a) > 6 else 1e9
    nosym = '--nosym' in a
    nconst = 1
    for x in a:
        if x.startswith('--const='): nconst = int(x.split('=')[1])
    nv = [0]
    def new():
        nv[0] += 1; return nv[0]
    # x[r][c][s]
    if v == 2:
        X = [[[None, new()] for c in range(k)] for r in range(N)]
        def lit(r, c, s): return X[r][c][1] if s == 1 else -X[r][c][1]
    else:
        X = [[[new() for s in range(v)] for c in range(k)] for r in range(N)]
        def lit(r, c, s): return X[r][c][s]
    cls = []
    if v > 2:
        for r in range(N):
            for c in range(k):
                cls.append([X[r][c][s] for s in range(v)])
                for s1 in range(v):
                    for s2 in range(s1 + 1, v):
                        cls.append([-X[r][c][s1], -X[r][c][s2]])
    if not nosym:
        # rows 0..nconst-1 constant (row i = symbol i); nconst = 1 is always safe, more is an assumption
        for i in range(nconst):
            for c in range(k):
                cls.append([lit(i, c, i)])
        # column 0 sorted non-decreasing: value(r) <= value(r+1)
        for r in range(nconst, N - 1):
            for s in range(v):
                for s2 in range(s):
                    # not (row r = s and row r+1 = s2 < s)
                    cls.append([-lit(r, 0, s), -lit(r + 1, 0, s2)])
    for cols in itertools.combinations(range(k), t):
        for tup in itertools.product(range(v), repeat=t):
            ys = []
            for r in range(N):
                y = new(); ys.append(y)
                for c, s in zip(cols, tup):
                    cls.append([-y, lit(r, c, s)])
            cls.append(ys)
    print(f"vars={nv[0]} clauses={len(cls)}", file=sys.stderr)
    s = Solver(name=solver_name, bootstrap_with=cls)
    t0 = time.time()
    timer = threading.Timer(timeout, lambda: s.interrupt())
    timer.start()
    res = s.solve_limited(expect_interrupt=True)
    timer.cancel()
    el = time.time() - t0
    if res is None:
        print(f"TIMEOUT after {el:.1f}s", file=sys.stderr); sys.exit(3)
    if res is False:
        print(f"UNSAT: no CA({N}; {t}, {k}, {v}) exists" + (f" with {nconst} constant rows" if nconst > 1 else "") + f" ({el:.1f}s)", file=sys.stderr); sys.exit(1)
    m = set(l for l in s.get_model() if l > 0)
    rows = []
    for r in range(N):
        row = []
        for c in range(k):
            if v == 2:
                row.append(1 if X[r][c][1] in m else 0)
            else:
                row.append([s_ for s_ in range(v) if X[r][c][s_] in m][0])
        rows.append(row)
    with open(out, 'w') as f:
        for row in rows:
            f.write(' '.join(map(str, row)) + '\n')
    print(f"SAT: CA({N}; {t}, {k}, {v}) written to {out} ({el:.1f}s)", file=sys.stderr)

if __name__ == '__main__':
    main()
