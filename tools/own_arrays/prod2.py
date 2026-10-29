#!/usr/bin/env python3
"""prod2.py A B out [kcut]  -  strength-2 product with constant-row removal.

Direct product of A = CA(N1;2,k1,v) and B = CA(N2;2,k2,v): rows of A with each column repeated
k2 times (column (i,j) <- A[.,i]) over rows of B tiled (column (i,j) <- B[.,j]); N1+N2 rows,
k1*k2 columns. Rows of A that are constant can be deleted when the deleted constant values of A
and of B are distinct (at most v rows in total): this is the generalized direct product of
Colbourn and Torres-Jimenez (2013, Cor. 4.3), as in CAs::productCA. Here a set of pairwise
disjoint rows (rows differing in every column) is first made constant by renaming symbols in
each column, so the saving is min(v, a + b) with a, b the largest disjoint row sets found.
"OA9" names the Bose OA(9;2,4,3) (rows (x, y, x+y, x+2y) mod 3). Output 0-based, duplicates removed.
"""
import sys, itertools

def read(fn):
    if fn == 'OA9':
        return [[x, y, (x + y) % 3, (x + 2 * y) % 3] for x in range(3) for y in range(3)], 3
    A = [list(map(int, l.split())) for l in open(fn) if l.strip()]
    if min(map(min, A)) == 1: A = [[x - 1 for x in r] for r in A]
    return A, max(map(max, A)) + 1

def disjoint_set(A, cap):
    N, k = len(A), len(A[0])
    adj = [[all(A[i][c] != A[j][c] for c in range(k)) for j in range(N)] for i in range(N)]
    best = [0]
    def rec(cur, start):
        nonlocal best
        if len(cur) > len(best): best = cur[:]
        if len(best) >= cap: return
        for j in range(start, N):
            if all(adj[i][j] for i in cur):
                cur.append(j); rec(cur, j + 1); cur.pop()
                if len(best) >= cap: return
    rec([], 0)
    return best

def make_const(A, rows, vals, v):
    """rename symbols per column so that rows[i] has value vals[i] in every column"""
    k = len(A[0]); B = [r[:] for r in A]
    for c in range(k):
        perm = {}
        for r, val in zip(rows, vals): perm[A[r][c]] = val
        rest_src = [s for s in range(v) if s not in perm]; rest_dst = [s for s in range(v) if s not in perm.values()]
        for s, d in zip(rest_src, rest_dst): perm[s] = d
        for r in range(len(A)): B[r][c] = perm[A[r][c]]
    return B

def main():
    A, v1 = read(sys.argv[1]); B, v2 = read(sys.argv[2]); out = sys.argv[3]
    v = max(v1, v2, 3)
    SA = disjoint_set(A, v); SB = disjoint_set(B, v)
    ra = min(len(SA), v); rb = min(len(SB), v - ra)
    if rb == 0 and ra == v and len(SB) > 0:  # prefer a split that leaves at least ... (no effect on size)
        pass
    A2 = make_const(A, SA[:ra], list(range(ra)), v)
    B2 = make_const(B, SB[:rb], list(range(ra, ra + rb)), v)
    Ar = [r for i, r in enumerate(A2) if i not in SA[:ra]]
    Br = [r for i, r in enumerate(B2) if i not in SB[:rb]]
    k1, k2 = len(A[0]), len(B[0])
    rows = [[a[i] for i in range(k1) for j in range(k2)] for a in Ar] + [[b[j] for i in range(k1) for j in range(k2)] for b in Br]
    seen = set(); P = []
    for r in rows:
        t = tuple(r)
        if t not in seen: seen.add(t); P.append(r)
    if len(sys.argv) > 4: kc = int(sys.argv[4]); P = [r[:kc] for r in P]
    with open(out, 'w') as f:
        for r in P: f.write(' '.join(map(str, r)) + '\n')
    print(f"product {sys.argv[1]} (N={len(A)},k={k1},disjoint={len(SA)}) x {sys.argv[2]} (N={len(B)},k={k2},disjoint={len(SB)}): removed {ra}+{rb} -> N={len(P)} k={len(P[0])} -> {out}")

if __name__ == '__main__':
    main()
