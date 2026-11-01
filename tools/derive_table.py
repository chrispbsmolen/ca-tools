#!/usr/bin/env python3
"""derive_table - sizes that follow from the table by published constructions.

Starting from the counted rows (table/ca_table.py counted(): CITED and VERIFIED, less
disputed and retracted rows), every published construction in tools/derive_laws.py is
applied at every table point (t, v, k) with its free parameters searched, and repeated
until nothing changes (a fixpoint). The result is written to table/derived.csv: one line
per point where the derived size is below the counted stair-step lookup, with the
construction, its arithmetic and every ingredient value used.

These are computed sizes, not arrays. They are kept apart from ca_table.csv: the counted
lookup is unchanged, and derived.csv is regenerated from scratch on every run, so it
always follows the current table (a derived size moves whenever an ingredient improves,
which is why it is not an append-only row). The page shows them as a second lookup.

Constructions (published): fuse (CKRS 2010 Lemma 3.1), derive (CKRS 2010 (7)),
composition (CKRS 2010 (3)), Chateauneuf-Kreher doubling (CCL 2008 Thm 2), CMTW 2006
Thm 3.4, k-ary Roux (CMTW 2006 Thm 3.3 with Yin 2003 DCAN values), Power CT (CZ 2012
Thm 2.1 with Lemma 2.4, one constant row per copy, CTJ 2013 Obs 3.2), direct product
(CTJ 2013 Cor 4.3), ordered design (CCL 2008 Construction 1), Shokri-Moura (JCD 2025).

Usage: derive_table.py [--out table/derived.csv] [--check]
--check regenerates into a temporary file and fails if table/derived.csv differs.
"""
import bisect
import functools
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import derive_laws as L  # noqa: E402

HEADER = "t,v,k,N,lookup_N,gain_pct,law,arithmetic,round\n"
LAWS = [("fuse", L.law_fuse), ("derive", L.law_derive), ("comp", L.law_comp), ("CK", L.law_ck),
        ("CMTW34", L.law_cmtw34), ("kRoux", L.law_kroux), ("PCT", None), ("DP2", L.law_dp2),
        ("OD", L.law_od), ("SM", L.law_sm)]


def compute(log=sys.stderr):
    look = L.load()
    grid = L.grid_of(look)
    e0 = L.mk_ecan(look)
    # add the points the constructions land on: fusing keeps k (from t, v' > v), deriving
    # gives k - 1 (from t + 1, v); repeated so that chains (derive then fuse) are covered
    for _ in range(4):
        add = {}
        for (t, v), ks in grid.items():
            for v2 in range(2, v):
                if (t, v2) in grid:
                    add.setdefault((t, v2), set()).update(k for k in ks if k > t)
            if t >= 3 and (t - 1, v) in grid:
                add.setdefault((t - 1, v), set()).update(k - 1 for k in ks if k - 1 > t - 1)
        grown = 0
        for tv, s in add.items():
            new = s - set(grid[tv])
            if new:
                grid[tv] = sorted(set(grid[tv]) | new); grown += len(new)
        if not grown:
            break
    best = {(t, v, k): e0(t, k, v) for (t, v), ks in grid.items() for k in ks}
    orig = dict(best)
    suf = {}

    def rebuild():
        suf.clear()
        for (t, v), ks in grid.items():
            m = 10 ** 18; s = [0] * len(ks)
            for i in range(len(ks) - 1, -1, -1):
                m = min(m, best[(t, v, ks[i])]); s[i] = m
            suf[(t, v)] = s

    def mk():
        @functools.lru_cache(maxsize=None)
        def e(t, k, v):
            if t <= 0: return 1
            if t == 1: return v
            if k < t: return 0
            if k == t: return v ** t
            ks = grid.get((t, v))
            if not ks: return None
            i = bisect.bisect_left(ks, k)
            if i >= len(ks): return None
            return suf[(t, v)][i]
        return e

    cands = {tv: L.pct_candidates(tv[0], tv[1], max(ks)) for tv, ks in grid.items()}
    rnd = {}
    rounds = 0; t0 = time.time()
    while True:
        rounds += 1; rebuild(); e = mk(); changed = 0
        for key in sorted(best):
            t, v, k = key; cur = best[key]
            for name, fn in LAWS:
                r = fn(e, t, v, k) if fn else L.law_pct(e, t, v, k, cands[(t, v)])
                if r and r[0] < cur:
                    cur = r[0]; best[key] = cur; rnd[key] = rounds; changed += 1
        print("round %d: %d changed (%.0f s)" % (rounds, changed, time.time() - t0), file=log, flush=True)
        if not changed:
            break
    rebuild(); e = mk()
    out = []
    lookup_points = 0
    for (t, v), ks in sorted(grid.items()):
        m0 = 10 ** 18
        stair0 = {}
        for kk in reversed(ks):
            m0 = min(m0, orig[(t, v, kk)]); stair0[kk] = m0
        # keep a derived point only if it sets the combined stair-step: smaller than
        # everything (counted or derived) at every larger k
        keep = set(); m1 = 10 ** 18
        for kk in reversed(ks):
            if best[(t, v, kk)] < m1 and best[(t, v, kk)] < stair0[kk]:
                keep.add(kk)
            m1 = min(m1, best[(t, v, kk)])
        # integer k whose lookup the derived values lower (for the summary)
        prev = t
        for kk in ks:
            if suf[(t, v)][ks.index(kk)] < stair0[kk]:
                lookup_points += kk - prev
            prev = kk
        for kk in ks:
            if kk not in keep:
                continue
            N = best[(t, v, kk)]
            # the construction that gives N at the fixpoint, re-evaluated on the final lookup
            law, arith = "", ""
            for name, fn in LAWS:
                r = fn(e, t, v, kk) if fn else L.law_pct(e, t, v, kk, cands[(t, v)])
                if r and r[0] == N:
                    law, arith = name, L.explain(e, name, t, v, kk, r[1]); break
            if not law:
                raise SystemExit("no construction reproduces N=%d at t=%d v=%d k=%d" % (N, t, v, kk))
            out.append((t, v, kk, N, stair0[kk], law, arith, rnd.get((t, v, kk), 0)))
    print("integer k lowered by derived values: %d" % lookup_points, file=log)
    return out


def write(rows, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEADER)
        for t, v, k, N, l0, law, arith, r in rows:
            f.write('%d,%d,%d,%d,%d,%.2f,%s,"%s",%d\n' % (t, v, k, N, l0, 100.0 * (l0 - N) / l0, law,
                                                          arith.replace('"', "'"), r))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out = os.path.join(L._REPO, "table", "derived.csv")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    rows = compute()
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "derived.csv")
            write(rows, p)
            same = os.path.exists(out) and open(p).read() == open(out).read()
        print("%s is %s" % (out, "current" if same else "OUT OF DATE; run python3 tools/derive_table.py"))
        return 0 if same else 1
    write(rows, out)
    print("wrote %s: %d points below the counted lookup" % (out, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
