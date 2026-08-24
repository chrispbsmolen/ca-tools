#!/usr/bin/env python3
"""ca_table - query the provenance-tracked covering array table.

The table (ca_table.csv, same directory) is append-only: one row per
evidence event. Tiers: CITED (traceable to a dated snapshot or paper),
VERIFIED (an explicit array is in hand and machine-checked, row carries
its SHA-256 and a verification stamp), FAILED_PENDING_RECHECK (a
verification attempt that failed its dimension check; each such row is
superseded by a later resolution row), DISPUTED (reserved; none at
publication). Stair-step semantics: a row (t, v, k, N) means N runs
suffice for up to k columns.

Usage:
  ca_table.py best T V K       best known N for strength T, V levels, K columns
  ca_table.py verified T V     verified rows for (T, V), with stamps
  ca_table.py steps T V [KMAX] the full stair-step for (T, V)
  ca_table.py params           list available (t, v) combinations
"""
import csv, os, sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ca_table.csv")

def load():
    with open(DATA, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]

def evidence(rows):
    return [r for r in rows if r["tier"] in ("CITED", "VERIFIED")]

def best(rows, t, v, k):
    cand = [int(float(r["N"])) for r in evidence(rows)
            if int(r["t"]) == t and int(r["v"]) == v and int(r["k"]) >= k]
    return min(cand) if cand else None

def main(argv):
    rows = load()
    if len(argv) >= 4 and argv[0] == "best":
        t, v, k = map(int, argv[1:4])
        n = best(rows, t, v, k)
        print(n if n is not None else "no entry")
    elif len(argv) >= 3 and argv[0] == "verified":
        t, v = int(argv[1]), int(argv[2])
        for r in rows:
            if r["tier"] == "VERIFIED" and int(r["t"]) == t and int(r["v"]) == v:
                print(r["k"], r["N"], r["array_sha256"][:12], r["verify_stamp"],
                      "|", r["notes"])
    elif len(argv) >= 3 and argv[0] == "steps":
        t, v = int(argv[1]), int(argv[2])
        kmax = int(argv[3]) if len(argv) > 3 else 10**9
        ev = sorted({(int(float(r["N"])), int(r["k"])) for r in evidence(rows)
                     if int(r["t"]) == t and int(r["v"]) == v and int(r["k"]) <= kmax})
        bestk = 0
        for n, k in ev:
            if k > bestk:
                print(n, k)
                bestk = k
    elif argv and argv[0] == "params":
        for t, v in sorted({(int(r["t"]), int(r["v"])) for r in rows}):
            print(t, v)
    else:
        print(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
