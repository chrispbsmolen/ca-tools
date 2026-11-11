#!/usr/bin/env python3
"""make_leaves.py - the small strength-2 ingredient arrays of the product certificates, built from
their published constructions with this file's own code (standard library only). The functions:

  bose Q            Bose 1938: OA(Q^2; 2, Q+1, Q) over GF(Q), Q a prime power. Row (a, b) reads
                    a x_j + b in column j < Q (x_j the field element numbered j) and a in column Q;
                    rows in the order a = 0..Q-1, b = 0..Q-1, so rows 0..Q-1 read b in the first Q
                    columns and 0 in the last.
  fused Q V         the Bose OA(Q^2; 2, Q+1, Q) with Q - V symbols fused away one at a time by
                    Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1, rows z = 0 and
                    r = 1 each time (fuse_once below): CA(Q^2 - 2(Q - V); 2, Q+1, V)
  projection Q C    Colbourn 2008, Theorem 2.3 (projection): CA(Q^2 - C; 2, Q+1+C, Q-C) from the
                    Bose OA, with the free choices of the construction made so that, besides its
                    Q - C constant rows, a second set of Q - C rows differ pairwise in every column
                    (projection_clique below)
  pca V D           the PCA product of Colbourn and Torres-Jimenez 2013 applied D - 1 times to the
                    Bose OA(V^2; 2, V+1, V) (PCAx2PCA; below)
  ms V K STARTER    Meagher and Stevens 2005: the all-zero row and the K cyclic shifts of the
                    starter vector, each under the V - 1 powers g^0..g^(V-2) of the symbol
                    permutation g fixing 0 and taking x to x + 1 for 1 <= x <= V-2 and V-1 to 1
                    (the cyclic group of order V - 1 on the symbols other than 0): CA(1 + K(V-1); 2, K, V)

Usage: make_leaves.py OUTDIR [FILE ...]   writes the arrays (all, or the FILEs named) and LEAVES.csv
(file, construction, N, k, v, sha256): every leaf of the certificates of smolen-2026-11-t2-gaps except
CA_157_2_14_11.txt (the array of Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, taken from the R
package CAs, data CKRS_CAs), and CA_341_2_1705_11.txt of smolen-2026-11-t2-pca341.
"""
import hashlib
import itertools
import os
import sys


# ---------------------------------------------------------------------------- GF(q)

def factor_prime_power(q):
    for p in range(2, q + 1):
        if q % p == 0:
            m, x = 0, q
            while x % p == 0:
                x //= p
                m += 1
            if x != 1:
                raise ValueError("%d is not a prime power" % q)
            return p, m
    raise ValueError(q)


def first_irreducible(p, m):
    """the first monic irreducible polynomial of degree m over GF(p), coefficients c_0..c_{m-1}
    (x^m + c_{m-1} x^{m-1} + ... + c_0) in lexicographic order of (c_0, ..., c_{m-1}) read as a
    number c_0 + p c_1 + ...; irreducible = no root and no factor of degree 2..m/2, tested by
    trial division by every monic polynomial of degree 1..m/2"""
    def polymod(a, b):           # a, b lists low to high, b monic
        a = list(a)
        while len(a) >= len(b):
            f = a[-1]
            if f:
                off = len(a) - len(b)
                for i, x in enumerate(b):
                    a[off + i] = (a[off + i] - f * x) % p
            a.pop()
        return a
    for num in range(p ** m):
        c = [(num // p ** i) % p for i in range(m)]
        f = c + [1]
        ok = True
        for d in range(1, m // 2 + 1):
            for gnum in range(p ** d):
                g = [(gnum // p ** i) % p for i in range(d)] + [1]
                if not any(polymod(f, g)):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return c
    raise ValueError("no irreducible polynomial")


class GF:
    """GF(q), the element numbered e = a_0 + p a_1 + ... being a_0 + a_1 y + ..., y a root of the first
    monic irreducible polynomial (first_irreducible)"""

    def __init__(self, q):
        self.q = q
        self.p, self.m = factor_prime_power(q)
        p, m = self.p, self.m
        self.poly = first_irreducible(p, m) if m > 1 else []
        dig = [[(e // p ** i) % p for i in range(m)] for e in range(q)]
        self.add = [[sum(((x + y) % p) * p ** i for i, (x, y) in enumerate(zip(dig[a], dig[b])))
                     for b in range(q)] for a in range(q)]
        self.mul = [[self._mul(dig[a], dig[b]) for b in range(q)] for a in range(q)]

    def _mul(self, a, b):
        p, m = self.p, self.m
        prod = [0] * (2 * m - 1)
        for i, x in enumerate(a):
            for j, y in enumerate(b):
                prod[i + j] = (prod[i + j] + x * y) % p
        for d in range(2 * m - 2, m - 1, -1):    # y^m = -(c_0 + ... + c_{m-1} y^{m-1})
            f = prod[d]
            if f:
                prod[d] = 0
                for i, c in enumerate(self.poly):
                    prod[d - m + i] = (prod[d - m + i] - f * c) % p
        return sum(x * p ** i for i, x in enumerate(prod[:m]))


# ---------------------------------------------------------------------------- constructions

def bose(q):
    F = GF(q)
    return [[F.add[F.mul[a][x]][b] for x in range(q)] + [a] for a in range(q) for b in range(q)]


def fuse_once(A, v):
    """CKRS 2010 Lemma 3.1 with rows z = 0, r = 1: A over 0..v (v+1 symbols) -> N-2 rows over 0..v-1.
    An entry v in a column where row r reads v after the exchange may be replaced by any symbol (the
    proof of the lemma uses the replacement only where row r does not read v); here those entries get
    0, 1, ..., v-1 in turn down the column (the choice of CAs::fuse), which keeps the rows that read
    one symbol in every column but the last pairwise different in that column too."""
    top = v
    Z = A[0]

    def tau(x, j):
        return top if x == Z[j] else Z[j] if x == top else x
    R = [tau(x, j) for j, x in enumerate(A[1])]
    out = []
    count = [0] * len(Z)                 # entries top met so far in each column with R[j] = top
    for row in A[2:]:
        nr = []
        for j, x in enumerate(row):
            y = tau(x, j)
            if y == top:
                if R[j] != top:
                    y = R[j]
                else:                    # free choice in the lemma: 0, 1, ..., v-1 in turn
                    y = count[j] % v
                    count[j] += 1
            nr.append(y)
        out.append(nr)
    return out


def fused(q, v):
    A = bose(q)
    for w in range(q - 1, v - 1, -1):
        A = fuse_once(A, w)
    return A


def projection(q, c):
    """Colbourn 2008, Theorem 2.3, with s = q - c. Start from the Bose OA (rows 0..q-1 read b in columns
    0..q-1). For each removed row j < c and each column x < q - c, the q - 1 other rows with symbol j in
    column x get the new column q + 1 + j set to x, and their entries in column x are replaced by the
    symbols c..q-1 in increasing order of row (the remaining c - 1 of them are don't-care). In columns
    q - c..q the entries j < c become don't-care. Then rows 0..c-1 are deleted, c is subtracted from
    every symbol, and the rows c..q-1 of the OA (now 0..q-c-1) read their symbol in columns q..q+c.
    Don't-care entries are set to 0."""
    s = q - c
    A = [list(r) + [None] * c for r in bose(q)]
    for j in range(c):
        for x in range(s):
            rows = [i for i in range(c, q * q) if A[i][x] == j]
            for n, i in enumerate(rows):
                A[i][q + 1 + j] = x + c
                A[i][x] = c + n if n < q - c else None
        for i in range(c, q * q):
            for x in range(s, q + 1):
                if A[i][x] == j:
                    A[i][x] = None
    out = [[None if y is None else y - c for y in r] for r in A[c:]]
    for i in range(q - c):
        for x in range(q, q + 1 + c):
            out[i][x] = i
    return [[0 if y is None else y for y in r] for r in out]


def projection_clique(q, c, fam=1):
    """Colbourn 2008, Theorem 2.3 as in projection(), with the free choices (which of the symbols c..q-1
    each row of a group (j, x) gets, and the don't-care entries) made so that the q - c rows (fam, b),
    b = 0..q-c-1, of the Bose OA (fam < c, so their entry in column q is don't-care) differ pairwise in
    every column. In every column the members whose entry is replaced or don't-care take, in member
    order, the symbols no other member uses there; in a group (j, x) the member row (if any) takes its
    symbol first and the other rows the remaining symbols c..q-1 in increasing order of row, the last
    c - 1 rows of the group being don't-care (set to 0). The q - c constant rows are kept as in
    projection()."""
    assert 0 < fam < c
    s, v = q - c, q - c
    B = bose(q)
    members = [fam * q + b for b in range(v)]
    mpos = {r: n for n, r in enumerate(members)}
    width = q + 1 + c
    # the members' final entries (after the subtraction of c), column by column
    want = {r: [None] * width for r in members}
    for x in range(q + 1):
        need = []
        for r in members:
            y = B[r][x]
            if y >= c:
                want[r][x] = y - c
            else:
                need.append(r)
        used = {want[r][x] for r in members if want[r][x] is not None}
        free = [y for y in range(v) if y not in used]
        for r, y in zip(need, free):
            want[r][x] = y
    for j in range(c):
        col = q + 1 + j
        need = []
        for r in members:
            xs = [x for x in range(q) if B[r][x] == j]
            if xs and xs[0] < s:
                want[r][col] = xs[0]
            else:
                need.append(r)
        used = {want[r][col] for r in members if want[r][col] is not None}
        free = [y for y in range(v) if y not in used]
        for r, y in zip(need, free):
            want[r][col] = y
    A = [list(r) + [None] * c for r in B]
    for j in range(c):
        for x in range(s):
            rows = [i for i in range(c, q * q) if A[i][x] == j]
            rows.sort(key=lambda i: (i not in mpos, i))
            taken = {want[i][x] + c for i in rows if i in mpos}
            pool = [y for y in range(c, q) if y not in taken]
            n = 0
            for i in rows:
                A[i][q + 1 + j] = x + c
                if i in mpos:
                    A[i][x] = want[i][x] + c
                elif n < len(pool):
                    A[i][x] = pool[n]
                    n += 1
                else:
                    A[i][x] = None
        for i in range(c, q * q):
            for x in range(s, q + 1):
                if A[i][x] == j:
                    A[i][x] = None
    out = [[None if y is None else y - c for y in r] for r in A[c:]]
    for i in range(q - c):
        for x in range(q, q + 1 + c):
            out[i][x] = i
    for r in members:
        out[r - c] = list(want[r])
    return [[0 if y is None else y for y in r] for r in out]


def pca_status(D, v):
    """the PCA normal form used here: the first v rows are the rows P; the columns in which P shows v
    distinct symbols come first (in their order), the others after; in each of the first columns the
    symbols are exchanged so that row r of P reads r. Returns (D', k1)."""
    k = len(D[0])
    good = [j for j in range(k) if len({D[r][j] for r in range(v)}) == v]
    rest = [j for j in range(k) if j not in set(good)]
    order = good + rest
    maps = []
    for j in order:
        if j in set(good):
            m = {D[r][j]: r for r in range(v)}
        else:
            m = {x: x for x in range(v)}
        maps.append(m)
    out = [[maps[n][row[j]] for n, j in enumerate(order)] for row in D]
    return out, len(good)


def pca_product(D1, k1, D2, l1, v):
    """Colbourn and Torres-Jimenez 2013, the product of two partitioned covering arrays: D1 (N x k, first
    v rows reading r on its first k1 columns) and D2 (M x l, the same with l1). Columns: (i, j) for i < k1,
    j < l1 (order j k1 + i), then i >= k1, j < l1 (order j (k - k1) + i - k1), then i < k1, j >= l1 (order
    (j - l1) k1 + i). Rows: the v rows r (D1[r][i] if j < l1, else D2[r][j]), the other rows of D1
    (D1[x][i]) and the other rows of D2 (D2[y][j]): N + M - v rows."""
    k, l = len(D1[0]), len(D2[0])
    cols = [(i, j) for j in range(l1) for i in range(k1)]
    cols += [(i, j) for j in range(l1) for i in range(k1, k)]
    cols += [(i, j) for j in range(l1, l) for i in range(k1)]
    out = []
    for r in range(v):
        out.append([D1[r][i] if j < l1 else D2[r][j] for i, j in cols])
    for x in range(v, len(D1)):
        out.append([D1[x][i] for i, j in cols])
    for y in range(v, len(D2)):
        out.append([D2[y][j] for i, j in cols])
    return out


def pca(v, d):
    """recursion of Colbourn and Torres-Jimenez 2013 (PCAx2PCA) on the Bose OA: A_1 = Bose OA with its
    first v rows and first v columns as the partition (k1 = v); A_{i+1} = A_i x Bose, then the rows
    (i)v..(i+1)v-1 of the product (the first v of its rows from A_i other than P) are moved to the
    front and the result is put in PCA normal form"""
    B = bose(v)
    A, k1 = B, v
    for i in range(2, d + 1):
        P = pca_product(A, k1, B, v, v)
        pick = list(range((i - 1) * v, i * v))
        P = [P[r] for r in pick] + [P[r] for r in range(len(P)) if r not in set(pick)]
        A, k1 = pca_status(P, v)
    return A


def ms(v, starter):
    k = len(starter)
    g = {0: 0, v - 1: 1}
    for x in range(1, v - 1):
        g[x] = x + 1

    def gpow(x, e):
        for _ in range(e):
            x = g[x]
        return x
    rows = [[0] * k]
    for e in range(v - 1):
        for sft in range(k):
            shifted = [starter[(j - sft) % k] for j in range(k)]
            rows.append([gpow(x, e) for x in shifted])
    return rows


# ---------------------------------------------------------------------------- the leaves

MS_STARTERS = {   # Meagher and Stevens 2005, v = 11 (as listed in the R package CAs, MeagherStevensStarters)
    17: [0, 1, 1, 1, 1, 1, 3, 10, 6, 9, 4, 10, 9, 7, 1, 4, 5],
    18: [0, 1, 1, 1, 1, 1, 1, 2, 5, 8, 3, 1, 3, 10, 6, 5, 8, 2],
    19: [0, 1, 1, 1, 1, 1, 1, 1, 2, 5, 8, 3, 1, 3, 10, 6, 5, 8, 2],
    20: [0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 5, 8, 3, 1, 3, 10, 6, 5, 8, 2],
}

LEAVES = [
    ("OA_121_2_12_11.txt", "Bose OA(121; 2, 12, 11)", lambda: bose(11)),
    ("OA_625_2_26_25.txt", "Bose OA(625; 2, 26, 25)", lambda: bose(25)),
    ("CA_621_2_26_23.txt", "Bose OA(625; 2, 26, 25) fused twice (CKRS 2010 Lemma 3.1)", lambda: fused(25, 23)),
    ("CA_725_2_28_25.txt", "Bose OA(729; 2, 28, 27) fused twice (CKRS 2010 Lemma 3.1)", lambda: fused(27, 25)),
    ("CA_167_2_16_11.txt", "projection of OA(169; 2, 14, 13), c = 2 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(13, 2)),
    ("CA_623_2_28_23.txt", "projection of OA(625; 2, 26, 25), c = 2 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(25, 2)),
    ("CA_725_2_32_23.txt", "projection of OA(729; 2, 28, 27), c = 4 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(27, 4)),
    ("CA_727_2_30_25.txt", "projection of OA(729; 2, 28, 27), c = 2 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(27, 2)),
    ("CA_837_2_34_25.txt", "projection of OA(841; 2, 30, 29), c = 4 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(29, 4)),
    ("CA_1017_2_40_25.txt", "projection of OA(1024; 2, 33, 32), c = 7 (Colbourn 2008 Thm 2.3)", lambda: projection_clique(32, 7)),
    ("CA_231_2_143_11.txt", "PCAx2PCA, d = 2, from OA(121; 2, 12, 11) (Colbourn and Torres-Jimenez 2013)", lambda: pca(11, 2)),
    ("CA_341_2_1705_11.txt", "PCAx2PCA, d = 3, from OA(121; 2, 12, 11) (Colbourn and Torres-Jimenez 2013)", lambda: pca(11, 3)),
] + [("CA_%d_2_%d_11.txt" % (1 + 10 * k, k), "Meagher and Stevens 2005 starter, k = %d" % k,
      (lambda k=k: ms(11, MS_STARTERS[k]))) for k in (17, 18, 19, 20)]


def text_of(rows):
    return "".join(" ".join(map(str, r)) + "\n" for r in rows)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    out = sys.argv[1]
    only = set(sys.argv[2:])
    os.makedirs(out, exist_ok=True)
    lines = ["file,construction,N,k,v,sha256"]
    for fn, what, fun in LEAVES:
        if only and fn not in only:
            continue
        rows = fun()
        v = max(max(r) for r in rows) + 1
        t = text_of(rows)
        with open(os.path.join(out, fn), "w", newline="\n") as f:
            f.write(t)
        h = hashlib.sha256(t.encode()).hexdigest()
        lines.append('%s,"%s",%d,%d,%d,%s' % (fn, what, len(rows), len(rows[0]), v, h))
        print(lines[-1], flush=True)
    with open(os.path.join(out, "LEAVES.csv"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
