"""sms_theorem62.py - the strength-4 covering array of Shokri, Moura and Stevens,
arXiv:2510.13122v2, Theorem 6.2 (the array X of Table 4 there) with the ingredient size of
their Corollary 6.5 (Table 5), for an odd prime q (prime only: F_q arithmetic is mod q).

Theorem 6.2: if a CA(N; 3, (q^2+1)/2, q) exists, then X is a CA(3q^4 + N(q - 2); 4, q^2+1, q).
Rows of X, in blocks (half = (q^2+1)/2, column c = x + p*half):
  block 0:      A(G^{q+1}_{q^2+1})                          (all q^2+1 columns)
  block 1:      A(G^{2(q+1)}_half) | A(G^{2(q+1)}_half)
  block 2:      A(G^{4(q+1)}_half) | A(G^{4(q+1)}_half) + e_0
  block 2 + r:  R | R + e_r,  r = 1, ..., q - 2
with e_0, ..., e_{q-2} the nonzero elements of F_q (here e_r = r + 1), over F_{q^4}. A(G) is the
array of all F_q-linear combinations of the rows of G (Construction 2.4).

The ingredient R = CA(2q^3 - q; 3, half, q) has the size of their Theorem 3.4 and Remark 6.4 but is
built here differently: in the two blocks A(G^1), A(G^-1) over F_{q^3} of their Theorem 3.3
(a pair of orthogoval planes), keep the first `half` projective points whose column has nonzero
first coordinate in both blocks, scale each column within its block so that this coordinate is 1
(so c e_0 gives the constant row c in both blocks), and remove the q constant rows of the second
block. Scaling a column within a block keeps the rank of every set of its columns, and every 3 of
the points are independent in at least one of the two planes (orthogovality), so R is a strength-3
covering array; it is verified directly anyway. With N = 2q^3 - q, X has 3q^4 + (q - 2)(2q^3 - q)
rows: 294, 2610, 10598, 67782 for q = 3, 5, 7, 11.

Usage: python3 sms_theorem62.py q [--ingredient-only] [--ingredient-3.3] > out.txt
--ingredient-3.3 uses the 2q^3 - 1 array of Theorem 3.3 instead (3q^4 + (q - 2)(2q^3 - 1) rows).
Writes canonical text (0-based, space-separated, one row per line) to stdout; the primitive
polynomials are printed to stderr.
"""
import sys, itertools
import numpy as np

def mulmod(a, b, f, q, m):
    r = [0] * (2 * m - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                r[i + j] = (r[i + j] + x * y) % q
    for d in range(2 * m - 2, m - 1, -1):
        c = r[d]
        if c:
            r[d] = 0
            for k in range(m):
                r[d - m + k] = (r[d - m + k] - c * f[k]) % q
    return r[:m]

def primitive(q, m):
    order = q ** m - 1
    primes = [p for p in range(2, order + 1) if order % p == 0 and all(p % d for d in range(2, int(p ** 0.5) + 1))]
    one = [1] + [0] * (m - 1); x = [0, 1] + [0] * (m - 2)
    for coeffs in itertools.product(range(q), repeat=m):
        if coeffs[0] == 0:
            continue
        f = list(coeffs) + [1]
        def pw(e):
            res, base = one[:], x[:]
            while e:
                if e & 1: res = mulmod(res, base, f, q, m)
                base = mulmod(base, base, f, q, m); e >>= 1
            return res
        if pw(order) == one and all(pw(order // p) != one for p in primes):
            return f
    raise ValueError

def powers(q, m, f):
    n = q ** m - 1
    L = np.zeros((n, m), dtype=np.int64); cur = [1] + [0] * (m - 1); x = [0, 1] + [0] * (m - 2)
    for j in range(n):
        L[j] = cur; cur = mulmod(cur, x, f, q, m)
    return L

def span(G, q):
    m = G.shape[0]
    U = np.array(list(itertools.product(range(q), repeat=m)), dtype=np.int64)
    return (U @ G) % q

def main():
    q = int(sys.argv[1]); assert q % 2 == 1 and all(q % d for d in range(2, q))
    only_R = "--ingredient-only" in sys.argv
    small = "--ingredient-3.3" not in sys.argv   # default: the 2q^3 - q ingredient (Corollary 6.5 size)
    half = (q * q + 1) // 2
    # ingredient R from F_{q^3}: CA(2q^3 - 1; 3, q^2+q+1, q), first `half` columns
    f3 = primitive(q, 3); L3 = powers(q, 3, f3); n3 = q ** 3 - 1
    if small:
        # CA(2q^3 - q; 3, half, q), the size of their Theorem 3.4 / Remark 6.4: keep the first `half`
        # projective points j (0 <= j < q^2+q+1) whose column in A(G^1) has nonzero first coordinate and
        # whose column in A(G^-1) has nonzero first coordinate; scale each column of each block so that
        # the first coordinate is 1. Then u = c e_0 gives the constant row c in both blocks, and the q
        # constant rows of the second block are removed. Every 3 columns are linearly independent in one
        # of the two planes (orthogovality), and scaling a column within one block keeps that, so each
        # block still covers what it covered; the result is verified directly anyway.
        npts = q * q + q + 1
        cols = [j for j in range(npts) if L3[j % n3][0] and L3[(-j) % n3][0]][:half]
        assert len(cols) == half
        inv = lambda a: pow(int(a), q - 2, q)
        G1 = np.stack([(L3[j % n3] * inv(L3[j % n3][0])) % q for j in cols], axis=1)
        Gm = np.stack([(L3[(-j) % n3] * inv(L3[(-j) % n3][0])) % q for j in cols], axis=1)
        A1, A2 = span(G1, q), span(Gm, q)
        const2 = np.where((A2 == A2[:, :1]).all(axis=1))[0]; assert len(const2) == q
        R = np.vstack([A1, np.delete(A2, const2, axis=0)])
        assert R.shape[0] == 2 * q ** 3 - q
    else:
        G1 = np.stack([L3[j % n3] for j in range(half)], axis=1)
        Gm = np.stack([L3[(-j) % n3] for j in range(half)], axis=1)
        R = np.vstack([span(G1, q), span(Gm, q)])
        z = np.where(~R.any(axis=1))[0]; assert len(z) == 2
        R = np.delete(R, z[1:], axis=0)
    if only_R:
        out = sys.stdout
        for row in R: out.write(" ".join(map(str, row.tolist())) + "\n")
        sys.stderr.write("R: q=%d f3 low-first %s N=%d k=%d\n" % (q, f3, R.shape[0], R.shape[1])); return
    f4 = primitive(q, 4); L4 = powers(q, 4, f4); n4 = q ** 4 - 1
    B0 = span(np.stack([L4[((q + 1) * c) % n4] for c in range(q * q + 1)], axis=1), q)
    H2 = span(np.stack([L4[(2 * (q + 1) * i) % n4] for i in range(half)], axis=1), q)
    H4 = span(np.stack([L4[(4 * (q + 1) * i) % n4] for i in range(half)], axis=1), q)
    blocks = [B0, np.hstack([H2, H2]), np.hstack([H4, (H4 + 1) % q])]
    for r in range(1, q - 1):
        blocks.append(np.hstack([R, (R + (r + 1)) % q]))
    X = np.vstack(blocks)
    assert X.shape == (3 * q ** 4 + (q - 2) * R.shape[0], q * q + 1)
    sys.stderr.write("q=%d f4 low-first %s f3 low-first %s N=%d k=%d (R has %d rows)\n"
                     % (q, f4, f3, X.shape[0], X.shape[1], R.shape[0]))
    out = sys.stdout
    for row in X: out.write(" ".join(map(str, row.tolist())) + "\n")

if __name__ == "__main__":
    main()
