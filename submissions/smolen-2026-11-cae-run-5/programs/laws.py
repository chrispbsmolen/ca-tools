"""laws.py - construction laws of the engine, each with its size rule AND its builder (F26: code, not arrays).
Every builder takes ingredient arrays (lists of rows, symbols 0..v-1) and returns the rows of the result.
All are published constructions; references are ids of ca-tools table/references.csv.
PRIVATE engine code (F24); the builders are also copied into submissions as the program of a result."""
import itertools, math

# ----------------------------------------------------------------------------------------------- small fields
def is_prime(n): return n > 1 and all(n % p for p in range(2, int(n ** .5) + 1))
def pp(v):
    for p in range(2, v + 1):
        if is_prime(p):
            x, e = p, 1
            while x < v: x *= p; e += 1
            if x == v: return p, e
            if v % p == 0: return None
    return None
def gf(q):
    """addition and multiplication tables of GF(q), q a prime power <= 64 (polynomial basis)"""
    p, e = pp(q)
    if e == 1:
        return [[(a + b) % q for b in range(q)] for a in range(q)], [[a * b % q for b in range(q)] for a in range(q)]
    polys = {4: [1, 1, 1], 8: [1, 1, 0, 1], 9: [2, 2, 1], 16: [1, 1, 0, 0, 1], 25: [2, 4, 1], 27: [1, 2, 0, 1], 32: [1, 0, 1, 0, 0, 1], 49: [3, 6, 1], 64: [1, 1, 0, 0, 0, 0, 1]}
    mod = polys[q]   # monic irreducible, coefficients low degree first (x^e term last)
    def dig(a): return [(a // p ** i) % p for i in range(e)]
    def num(d): return sum(x * p ** i for i, x in enumerate(d))
    def mul(a, b):
        A, B = dig(a), dig(b); r = [0] * (2 * e - 1)
        for i, x in enumerate(A):
            for j, y in enumerate(B): r[i + j] = (r[i + j] + x * y) % p
        for d in range(2 * e - 2, e - 1, -1):
            c = r[d]
            if c:
                for i in range(e + 1): r[d - e + i] = (r[d - e + i] - c * mod[i]) % p
        return num(r[:e])
    add = [[num([(x + y) % p for x, y in zip(dig(a), dig(b))]) for b in range(q)] for a in range(q)]
    return add, [[mul(a, b) for b in range(q)] for a in range(q)]

# ----------------------------------------------------------------------------------------------- builders
def cut(A, k): return [r[:k] for r in A]

def fuse(A, v_from, v_to):
    """CKRS 2010 Lemma 3.1, applied v_from - v_to times: CA(N; t, k, v+1) -> CA(N - 2; t, k, v)"""
    X = [list(r) for r in A]; vv = v_from
    while vv > v_to:
        top = vv - 1; Z, R0 = X[0], X[1]
        tau = lambda x, j: top if x == Z[j] else (Z[j] if x == top else x)
        R = [tau(x, j) for j, x in enumerate(R0)]
        Y = []
        for row in X[2:]:
            out = []
            for j, x in enumerate(row):
                y = tau(x, j)
                if y == top: y = R[j] if R[j] != top else 0
                out.append(y)
            Y.append(out)
        X = Y; vv -= 1
    return X

def derive(A, v):
    """a CA(N; t+1, k+1, v) -> CA(<= N/v; t, k, v): the rows with the rarest symbol in its column, that column removed"""
    best = None
    for c in range(len(A[0])):
        for s in range(v):
            n = sum(1 for r in A if r[c] == s)
            if best is None or n < best[0]: best = (n, c, s)
    _, c, s = best
    return [r[:c] + r[c + 1:] for r in A if r[c] == s]

def constant_row(A, r):
    """symbols permuted per column so that row r reads 0 everywhere"""
    Z = A[r]
    return [[0 if x == Z[j] else (Z[j] if x == 0 else x) for j, x in enumerate(row)] for row in A]

def direct_product(A, B, cA=None, cB=None):
    """strength 2 direct product (CMMSSY 2006), with the generalized saving of Colbourn and Torres-Jimenez 2013
    Cor 4.3 for one constant row on each side (row cA of A and cB of B made all-0; the duplicate constant row
    dropped): CA(N1 + N2 - 1; 2, k1 k2, v), or N1 + N2 when no constant rows are given"""
    if cA is not None: A = constant_row(A, cA)
    if cB is not None: B = constant_row(B, cB)
    k1, k2 = len(A[0]), len(B[0])
    out = [[a[i] for i in range(k1) for _ in range(k2)] for a in A]
    cz = {row[0] for row in A if len(set(row)) == 1}
    for b in B:
        if len(set(b)) == 1 and b[0] in cz: continue
        out.append([b[j] for _ in range(k1) for j in range(k2)])
    return out

def add_column(A, C, v):
    """CKRS 2010 Thm 3.2 (8), one column: CA(N; t, k-1, v) and CA(M; t-2, k-2, v) give
    CA(N + v(v-1) M; t, k, v): the last column duplicated; for every ordered pair a != b, the strength t-2 array on
    the other k-2 columns with the two copies set to a and b. For t = 3, C is the strength-1 array: v constant rows."""
    k1 = len(A[0]); out = [r + [r[-1]] for r in A]
    for a in range(v):
        for b in range(v):
            if a == b: continue
            for c in C: out.append(list(c[:k1 - 1]) + [a, b])
    return out

def strength1(k, v): return [[s] * k for s in range(v)]

def composition(A, B, v2):
    """CKRS 2010 (3): CA(N1; t, k, v1) x CA(N2; t, k, v2) -> CA(N1 N2; t, k, v1 v2), symbol x1 v2 + x2"""
    return [[x * v2 + y for x, y in zip(a, b)] for a in A for b in B]

def ck_doubling(A, B, v):
    """Chateauneuf-Kreher doubling (CCL 2008 Thm 2): CA(N; 3, h, v), CA(M; 2, h, v) -> CA(N + (v-1)M; 3, 2h, v):
    [A | A] and, for d = 1..v-1, [B | B + d mod v]"""
    out = [list(r) + list(r) for r in A]
    for d in range(1, v):
        for r in B: out.append(list(r) + [(x + d) % v for x in r])
    return out

def cmtw34(A, B, q):
    """Colbourn, Martirosyan, Trung van, Walker 2006 Thm 3.4 (q a prime power): CA(N; 3, h, q), CA(M; 2, h, q) ->
    CA(N + (q-1)M + q^3 - q^2; 3, q h, q). Columns (i, g), i < h, g in GF(q). Rows: A copied into every block g;
    for lambda != 0, B + lambda g in column (i, g); for a != 0, b, c: a g^2 + b g + c in every column (i, g)."""
    add, mul = gf(q); h = len(A[0])
    out = [[r[i] for g in range(q) for i in range(h)] for r in A]
    for lam in range(1, q):
        for r in B: out.append([add[r[i]][mul[lam][g]] for g in range(q) for i in range(h)])
    for a in range(1, q):
        for b in range(q):
            for c in range(q):
                out.append([add[add[mul[a][mul[g][g]]][mul[b][g]]][c] for g in range(q) for i in range(h)])
    return out

# ----------------------------------------------------------------------------------------------- registry
# name: (references, short description)
# ------------------------------------------------------------------------------- profile product (W17), v = 3
def min_agreement(A):
    """two rows of A that agree in the fewest columns: (d, i, j)"""
    best = None
    for i in range(len(A)):
        for j in range(i + 1, len(A)):
            d = sum(1 for x, y in zip(A[i], A[j]) if x == y)
            if best is None or d < best[0]: best = (d, i, j)
    return best

def profile_product(A, i, j, B, p, q):
    """Colbourn and Torres-Jimenez 2013, Thm 4.2 / Cor 4.5, for 3 symbols (own code, as pprod.py of the submission
    smolen-2026-11-t2v3-26rows): A = CA(N;2,k,3) whose rows i, j agree in d1 columns (set K2), B = CA(M;2,l,3) whose
    rows p, q agree in d2 columns (set L2). Rename per column so that A[i] = 0 everywhere and A[j] = 2 off K2,
    B[p] = 1 everywhere and B[q] = 2 off L2. Drop rows A[i] and B[p], merge A[j] and B[q] into one row, drop the
    columns K2 x L2: CA(N + M - 3; 2, k l - d1 d2, 3)."""
    def ren(A, i, j, vi, vj):
        B = [r[:] for r in A]
        for c in range(len(A[0])):
            perm = {A[i][c]: vi}
            if A[j][c] != A[i][c]: perm[A[j][c]] = vj
            src = [s for s in range(3) if s not in perm]; dst = [s for s in range(3) if s not in perm.values()]
            for s_, d_ in zip(src, dst): perm[s_] = d_
            for r in range(len(A)): B[r][c] = perm[A[r][c]]
        return B
    A = ren(A, i, j, 0, 2); B = ren(B, p, q, 1, 2); k, l = len(A[0]), len(B[0])
    K2 = set(c for c in range(k) if A[j][c] == 0); L2 = set(c for c in range(l) if B[q][c] == 1)
    cols = [(a, b) for a in range(k) for b in range(l) if not (a in K2 and b in L2)]
    rows = [[A[r][a] for a, b in cols] for r in range(len(A)) if r not in (i, j)]
    rows += [[B[r][b] for a, b in cols] for r in range(len(B)) if r not in (p, q)]
    rows.append([A[j][a] if a in K2 else B[q][b] if b in L2 else 2 for a, b in cols])
    return rows

REFS = {
    "cut": ("", "first k columns of a wider array"),
    "fuse": ("fuse-ckrs2010", "fusing symbols, CKRS 2010 Lemma 3.1"),
    "derive": ("fuse-ckrs2010", "derived array, CKRS 2010 (7)"),
    "dp2": ("product-cmmssy2006;pca-ct2013", "direct product with constant rows, Colbourn-Torres-Jimenez 2013 Cor 4.3"),
    "add1": ("fuse-ckrs2010", "one column added, CKRS 2010 Thm 3.2"),
    "comp": ("fuse-ckrs2010", "composition of alphabets, CKRS 2010 (3)"),
    "ck": ("ck-ck2002", "Chateauneuf-Kreher doubling"),
    "cmtw34": ("roux-cmtw2006", "CMTW 2006 Thm 3.4"),
    "hartman4": ("roux-cmtw2006", "doubling at strength 4, Hartman (CMTW 2006 Theorem 4.7)"),
    "kroux": ("sa-ccl2008", "k-ary Roux, Cohen-Colbourn-Ling 2008 Theorem 3 (DCA from the field)"),
    "od": ("sa-ccl2008", "ordered design plus binary patches, Cohen-Colbourn-Ling 2008 Construction 1"),
    "phf": ("power-ct2010", "perfect hash family (Reed-Solomon) with a strength t array in every row"),
    "pdouble": ("ck-ck2002;binary-ks1973", "partial doubling with Kleitman-Spencer helper rows (twin law)"),
    "pprod": ("pca-ct2013", "profile product of Colbourn and Torres-Jimenez 2013 (Thm 4.2 / Cor 4.5), 3 symbols"),
    "ctj": ("pca-ct2013;product-cmmssy2006", "product of Colbourn and Torres-Jimenez 2013 Cor 4.3 (rows differing in every column removed)"),
}

# ----------------------------------------------------------------------------------------------- CTJ product
def disagreeing_rows(A, cap):
    """a largest-found set of rows that pairwise differ in every column (greedy over every start row)"""
    best = []
    for s in range(len(A)):
        S = [s]
        for r in range(len(A)):
            if r in S: continue
            if all(all(x != y for x, y in zip(A[r], A[q])) for q in S): S.append(r)
            if len(S) >= cap: break
        if len(S) > len(best): best = S
        if len(best) >= cap: break
    return best

def _relabel(M, S, base, v):
    k = len(M[0]); maps = []
    for j in range(k):
        perm = {}
        for r, s in enumerate(S): perm.setdefault(M[s][j], base + r)
        tgt = set(perm.values()); rs = [x for x in range(v) if x not in perm]; rt = [y for y in range(v) if y not in tgt]
        for x, y in zip(rs, rt): perm[x] = y
        maps.append(perm)
    return [[maps[j][x] for j, x in enumerate(row)] for row in M]

def ctj_product(A, B, v, S=None, T=None):
    """Colbourn and Torres-Jimenez 2013, Cor 4.3 (the product-ctj-1 construction of ca-tools): with s rows of A and
    r rows of B that pairwise differ in every column, s + r <= v, CA(N1 + N2 - (s + r); 2, k1 k2, v): the s rows of A
    become constant rows 0..s-1, the r rows of B constant rows s..s+r-1, all s + r rows are removed, and the rest
    is the direct product."""
    if S is None: S = disagreeing_rows(A, v - 1)
    if T is None: T = disagreeing_rows(B, v - len(S))
    A2 = _relabel(A, S, 0, v); B2 = _relabel(B, T, len(S), v); k1, k2 = len(A[0]), len(B[0])
    rows = [[a[i] for i in range(k1) for _ in range(k2)] for x, a in enumerate(A2) if x not in set(S)]
    rows += [b * k1 for y, b in enumerate(B2) if y not in set(T)]
    return rows

# ----------------------------------------------------------------------------------------------- direct constructions
def ksk_k(N):
    """columns of the Kleitman-Spencer / Katona binary strength-2 array on N rows"""
    import math
    return math.comb(N - 1, (N - 1) // 2 + 1) if N >= 4 else (1 if N == 4 else 0)

def ksk(N, k=None):
    """W1: binary CA(N; 2, C(N-1, floor((N-1)/2)+1), 2): columns = sets of size floor((N-1)/2)+1 of rows 1..N-1"""
    import itertools
    m = (N - 1) // 2 + 1; cols = []
    for S in itertools.combinations(range(1, N), m):
        cols.append(S)
        if k and len(cols) >= k: break
    return [[1 if r in S else 0 for S in cols] for r in range(N)]

def bush(q, t, k=None):
    """W2: Bush / Bose OA(q^t; t, q+1, q) for t <= q (columns: field points, then the top coefficient), q columns if t > q"""
    add, mul = gf(q); rows = []
    for co in itertools.product(range(q), repeat=t):
        r = []
        for x in range(q):
            s, xp = 0, 1
            for c in co: s = add[s][mul[c][xp]]; xp = mul[xp][x]
            r.append(s)
        if t <= q: r.append(co[-1])
        rows.append(r)
    return cut(rows, k) if k else rows

def weight_sets(k, t):
    """cheapest set of weights W (sum of C(k, w)) such that every interval [w, w + k - t], w = 0..t, meets W (exact DP)"""
    d = k - t; memo = {}
    def f(w):
        if w > t: return (0, [])
        if w in memo: return memo[w]
        best = None
        for x in range(w, w + d + 1):
            c, L = f(x + 1); c += math.comb(k, x)
            if best is None or c < best[0]: best = (c, [x] + L)
        memo[w] = best; return best
    return f(0)[1]

def weight_class(k, t):
    """W3: binary vectors whose weight lies in weight_sets(k, t): a CA(sum C(k, W); t, k, 2)"""
    W = set(weight_sets(k, t))
    return [[(m >> j) & 1 for j in range(k)] for m in range(2 ** k) if bin(m).count("1") in W]

def weight_class_N(k, t):
    import math
    return sum(math.comb(k, w) for w in weight_sets(k, t) if w <= k)

def pgl2(q):
    """the q^3 - q elements of PGL(2, q) acting on the projective line (points 0..q-1, infinity = q)"""
    add, mul = gf(q); inv = [0] + [next(b for b in range(1, q) if mul[a][b] == 1) for a in range(1, q)]
    neg = [next(b for b in range(q) if add[a][b] == 0) for a in range(q)]
    def sub(a, b): return add[a][neg[b]]
    seen = set(); rows = []
    for a, b, c, d in itertools.product(range(q), repeat=4):
        if sub(mul[a][d], mul[b][c]) == 0: continue
        img = []
        for x in range(q + 1):
            if x == q: num, den = a, c
            else: num, den = add[mul[a][x]][b], add[mul[c][x]][d]
            img.append(q if den == 0 else mul[num][inv[den]])
        tup = tuple(img)
        if tup not in seen: seen.add(tup); rows.append(list(tup))
    return rows

def ordered_design(q, B, k=None):
    """W13, Cohen-Colbourn-Ling 2008 Construction 1: v = q + 1, k <= q + 1: PGL(2,q) on the projective line (every
    triple of distinct symbols once on every 3 columns) plus, for every pair of symbols {x, y}, the binary
    CA(N2; 3, q+1, 2) B with its row 0 made all-0 and then removed, 0 -> x and 1 -> y, oriented so that every symbol
    is the '1' symbol of some pair: q^3 - q + C(q+1, 2)(N2 - 1) rows."""
    v = q + 1; k = k or v; B = constant_row(cut(B, k), 0)[1:]
    out = [r[:k] for r in pgl2(q)]
    for x in range(v):
        for y in range(x + 1, v):
            lo, hi = (y, x) if (x == 0 and y == v - 1) else (x, y)     # pair (0, q): 0 is the '1' symbol
            for b in B: out.append([hi if z else lo for z in b])
    return out

def turan(t, v):
    """edges of the Turan graph T(t, v): the most pairs of t positions with unequal values when t values come from v symbols"""
    a, r = divmod(t, v); sizes = [a + 1] * r + [a] * (v - r)
    return (t * t - sum(x * x for x in sizes)) // 2

def power_phf(q, e, t, C, v, k=None, M=None):
    """W23 (perfect hash family form): columns = polynomials of degree < e over GF(q) (q^e columns), rows = for each of
    M = C(t,2)(e-1)+1 evaluation points the rows of a CA(x; t, q, v) C (its row 0 made all-0; the all-0 row kept
    once): CA(M (x - 1) + 1; t, q^e, v). Two polynomials agree in at most e-1 points, so some point separates all t."""
    import math
    M = M or (turan(t, v) * (e - 1) + 1)   # only pairs with unequal targets need separating (DHF / Power CT form)
    if M > q: return None
    add, mul = gf(q); C0 = constant_row(C, 0); polys = list(itertools.product(range(q), repeat=e))
    if k: polys = polys[:k]
    out = [[0] * len(polys)]
    for x in range(M):
        vals = []
        for co in polys:
            s, xp = 0, 1
            for c in co: s = add[s][mul[c][xp]]; xp = mul[xp][x]
            vals.append(s)
        for row in C0[1:]: out.append([row[a] for a in vals])
    return out

def partial_doubling(A, r, s):
    """W19 (own, item120; Chateauneuf-Kreher / Roux family): binary CA(N0; 3, k0, 2) A, r helper rows: s columns get a
    twin; on the helper rows twinned column i carries vector F_i, its twin the complement, every other column the
    common vector p; F_1..F_s, p pairwise qualitatively independent on r rows (Kleitman-Spencer family).
    CA(N0 + r; 3, k0 + s, 2) when s + 1 <= C(r-1, floor((r-1)/2)+1)."""
    fam = [list(c) for c in zip(*ksk(r))]       # columns of the KSK array on r rows, each a vector of length r
    if s + 1 > len(fam): return None
    k0 = len(A[0]); p = fam[s]
    top = [row + [row[i] for i in range(s)] for row in A]
    bot = []
    for j in range(r):
        bot.append([fam[i][j] if i < s else p[j] for i in range(k0)] + [1 - fam[i][j] for i in range(s)])
    return top + bot

# ----------------------------------------------------------------------------------------------- cyclotomy, Paley
def primitive_root(p):
    fac = [f for f in range(2, p) if (p - 1) % f == 0 and is_prime(f)]
    for g in range(2, p):
        if all(pow(g, (p - 1) // f, p) != 1 for f in fac): return g
    return 1

def cyclotomic(p, v, k=None, diag=0):
    """W12 (Colbourn 2010): p prime, p = 1 mod v. Rows and columns are GF(p); entry = the cyclotomic class of c - r
    (discrete log mod v), diag on c = r. For v = 2 this is the Paley circulant (W11). Strength is checked, not assumed."""
    g = primitive_root(p); cls = [0] * p; x = 1
    for e in range(p - 1): cls[x] = e % v; x = x * g % p
    k = k or p
    return [[diag if c == r else cls[(c - r) % p] for c in range(k)] for r in range(p)]

def cyclo_primes(v, lo, hi):
    return [p for p in range(max(lo, 3), hi + 1) if is_prime(p) and (p - 1) % v == 0]

def cyclotomic_shifted(p, v, k=None, diag=0):
    """W12, Colbourn 2010 form with the point at infinity: for every shift s in Z_v the cyclotomic p x p array plus s,
    and an extra column equal to s: v p rows, p + 1 columns (reproduces the table's CA(212;3,54,4) at p = 53)."""
    X = cyclotomic(p, v, diag=diag); out = []
    for s in range(v):
        for r in X: out.append([(x + s) % v for x in r] + [s])
    return cut(out, k) if k else out

# ----------------------------------------------------------------------------------------------- RMS (W6)
def _ext_powers(q, deg):
    """powers alpha^j (j = 0 .. q^deg - 2) of a root of a primitive polynomial of degree deg over GF(q), as coordinate
    vectors (low degree first)"""
    add, mul = gf(q); n = q ** deg - 1
    neg = [next(b for b in range(q) if add[a][b] == 0) for a in range(q)]
    for co in itertools.product(range(q), repeat=deg):
        if co[0] == 0: continue                                   # constant term nonzero
        x = [0] * deg; x[0] = 1; seen = []
        ok = True
        for j in range(n):
            seen.append(tuple(x))
            # multiply by alpha: shift up, reduce alpha^deg = -(co[0] + co[1] a + ...)
            top = x[-1]; x = [0] + x[:-1]
            if top:
                for i in range(deg): x[i] = add[x[i]][mul[neg[top]][co[i]]]
            if tuple(x) == tuple([1] + [0] * (deg - 1)) and j < n - 1: ok = False; break
        if ok and len(set(seen)) == n: return seen
    return None

def rms(q, k=None):
    """W6, Raaphorst, Moura and Stevens 2014: CA(2q^3 - 1; 3, q^2+q+1, q). Column j: the points L(alpha^j) and
    L(alpha^-j) of PG(2,q) (alpha a root of a primitive cubic); two blocks of all F_q-combinations u . L, one zero row
    removed. Three points collinear in one plane are not in the other (orthogoval planes)."""
    add, mul = gf(q); P = _ext_powers(q, 3); n = q ** 3 - 1; K = q * q + q + 1; k = k or K
    out = []
    for blk in (1, -1):
        cols = [P[(blk * j) % n] for j in range(k)]
        for u in itertools.product(range(q), repeat=3):
            if blk == -1 and not any(u): continue
            row = []
            for L in cols:
                s = 0
                for a, b in zip(u, L): s = add[s][mul[a][b]]
                row.append(s)
            out.append(row)
    return out

# ----------------------------------------------------------------------------------------------- k-ary Roux (W21)
def kary_roux(A, B, C, v, h, l):
    """Cohen, Colbourn and Ling 2008 Theorem 3 (k-ary Roux) with the improvement that zero differences need no row:
    A = CA(3, h, v), B = CA(3, l, v), C = CA(2, l, v), D = the multiplication-table DCA over GF(v) without its zero row
    (v - 1 rows, h <= v, v a prime power). Columns (i, j), i < h, j < l. Rows: A[i] for every j; B[j] for every i;
    for every row c of C and nonzero lambda: c[j] + lambda * a_i. CA(N_A + N_B + (v - 1) N_C; 3, h l, v)."""
    add, mul = gf(v)
    out = [[a[i] for i in range(h) for j in range(l)] for a in A]
    out += [[b[j] for i in range(h) for j in range(l)] for b in B]
    for lam in range(1, v):
        for c in C: out.append([add[c[j]][mul[lam][i]] for i in range(h) for j in range(l)])
    return out

def hartman4(A, B, C, v):
    """Hartman's doubling at strength 4 (CMTW 2006 Theorem 4.7): A = CA(4, k, v), B = CA(3, k, v), C = CA(2, k, v^2).
    Columns (i, side). Rows [A | A]; for d = 1..v-1 [B | B + d]; and [C div v | C mod v] (each v^2 symbol is a pair
    (x, y), x on side 0, y on side 1), which covers every pattern on two twin pairs. CA(N_A + (v-1) N_B + N_C; 4, 2k, v)."""
    out = [list(r) + list(r) for r in A]
    for d in range(1, v):
        for r in B: out.append(list(r) + [(x + d) % v for x in r])
    for r in C: out.append([x // v for x in r] + [x % v for x in r])
    return out

def paley_doubled(p, k=None):
    """W11 doubled Paley: M the binary Paley circulant over GF(p); rows [0 | M] and [1 | 1 - M]: 2p rows, p + 1 columns
    (one strength higher than M when it holds; checked, not assumed)"""
    M = cyclotomic(p, 2)
    out = [[0] + r for r in M] + [[1] + [1 - x for x in r] for r in M]
    return cut(out, k) if k else out
