#!/usr/bin/env python3
"""independent exact check: chk.py FILE t v"""
import sys, itertools
A = [list(map(int, l.split())) for l in open(sys.argv[1]) if l.strip()]
t = int(sys.argv[2]); v = int(sys.argv[3])
N = len(A); k = len(A[0]); assert all(len(r) == k for r in A)
assert all(0 <= x < v for r in A for x in r)
cols = list(zip(*A)); miss = 0
for cs in itertools.combinations(range(k), t):
    seen = set(zip(*[cols[c] for c in cs]))
    miss += v ** t - len(seen)
print(f"N={N} k={k} t={t} v={v} missing={miss}", "VERIFIED" if miss == 0 else "NOT A CA")
