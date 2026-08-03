#!/usr/bin/env python3
"""ca_query - look up best-known covering array sizes (Colbourn tables).

Works off a CSV snapshot of the Colbourn catalogue (as preserved in Ulrike
Groemping's CAs R package, colbournBigFrame: November 2024 status). The tables
are stair-step records: a row (t, v, k, N) means "with N runs, up to k columns
are achievable". So the best known N for k' columns is the smallest N whose
row has k >= k'.

Usage:
  ca_query.py best T V K            best known N for a CA(t=T, v=V) on K columns
  ca_query.py steps T V [KMAX]      the full stair-step for (T, V)
  ca_query.py sources T V           which constructions hold the records for (T, V)
  ca_query.py params                list available (t, v) combinations

No dependencies beyond the standard library. Data file: colbourn_catalogue.csv
(same directory), columns t,v,k,N,Source.
"""
import csv
import os
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "colbourn_catalogue.csv")

def load():
    rows = []
    with open(DATA, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["t"]), int(r["v"]), int(r["k"]),
                         int(float(r["N"])), r["Source"]))
    return rows

def best(rows, t, v, k):
    cands = [(N, kk, src) for (tt, vv, kk, N, src) in rows
             if tt == t and vv == v and kk >= k]
    if not cands:
        return None
    return min(cands)          # smallest N; its k >= requested k

def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    cmd = sys.argv[1]
    rows = load()
    if cmd == "best" and len(sys.argv) == 5:
        t, v, k = map(int, sys.argv[2:5])
        r = best(rows, t, v, k)
        if r is None:
            print(f"no entry covers CA(t={t}, v={v}) with k={k} "
                  f"(beyond table range)"); return 1
        N, kk, src = r
        print(f"best known: CA({N}; {t}, {k}, {v})   "
              f"[record row: k up to {kk}, source: {src}]")
    elif cmd == "steps" and len(sys.argv) >= 4:
        t, v = int(sys.argv[2]), int(sys.argv[3])
        kmax = int(sys.argv[4]) if len(sys.argv) > 4 else None
        sel = sorted([(N, kk, src) for (tt, vv, kk, N, src) in rows
                      if tt == t and vv == v])
        for N, kk, src in sel:
            if kmax and kk > kmax: continue
            print(f"  N={N:>8}  k<={kk:<8}  {src}")
        if not sel: print("no entries"); return 1
    elif cmd == "sources" and len(sys.argv) == 4:
        t, v = int(sys.argv[2]), int(sys.argv[3])
        from collections import Counter
        c = Counter(src for (tt, vv, kk, N, src) in rows if tt == t and vv == v)
        for src, n in c.most_common():
            print(f"  {n:>4}  {src}")
        if not c: print("no entries"); return 1
    elif cmd == "params":
        combos = sorted(set((tt, vv) for (tt, vv, kk, N, src) in rows))
        cur_t = None
        for tt, vv in combos:
            if tt != cur_t:
                if cur_t is not None: print()
                print(f"t={tt}: v =", end=""); cur_t = tt
            print(f" {vv}", end="")
        print()
    else:
        print(__doc__); return 2
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:     # output piped into head etc.
        sys.exit(0)
