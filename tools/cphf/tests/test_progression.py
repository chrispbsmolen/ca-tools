#!/usr/bin/env python3
"""Test suite for the modes "progression" and "fullfast" of cphfcheck.c (standard library only).

Usage: python3 test_cphf.py [--quick] [--seed S] [--no-mutations] [--no-timing] [--no-medium]

Builds cphfcheck.c (OpenMP and plain builds) and the original source (cphfcheck_orig.c.ref), then
  legacy      modes full, cyclic, sample and expand byte-for-byte identical to the original build
  diff        random families: full (1 thread, the reference) vs progression vs fullfast: the count,
              the first uncovered set and, when there are at most LISTCAP, the full sorted list
  planted     faults planted so that they fail in every progression and every other row, at shift
              0, a middle shift and the last shift, with and without WILD columns
  negatives   corrupted progression rows (first, middle, last column), singular A, non-spanning
              rows: "P=" must exit 3, results must still agree with full
  real        a few real families from the submission folder (if present)
  medium      t=4, q=7, k=300: progression and fullfast vs full, full lists
  mutations   each mutation of the source must make at least one test fail
  timing      full vs fullfast vs progression; fitted extrapolation
Prints PASS/FAIL per test and a summary; exit status 0 only if everything passed.
"""
import argparse
import math
import itertools
import os
import random
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "cphfcheck.c")
# the checker as first published (commit a5ad0b7), for the regression tests of the old modes
ORIG = os.path.join(HERE, "cphfcheck_a5ad0b7.c.ref")
WORK = os.environ.get("CPHF_TEST_WORK", os.path.join(HERE, "work"))
# optional: a folder of real family files (CPHF_TEST_REAL); skipped when absent
REAL = os.environ.get("CPHF_TEST_REAL", os.path.join(HERE, "real_families"))
LEGACY_DIR = os.path.join(HERE, "legacy")
LISTCAP = 20000

# ---------------------------------------------------------------- field GF(q), independent of the C code
CONWAY = {4: (2, [1, 1]), 8: (2, [1, 1, 0]), 9: (3, [2, 2]), 16: (2, [1, 1, 0, 0]), 25: (5, [2, 4]),
          27: (3, [1, 2, 0]), 32: (2, [1, 0, 1, 0, 0])}   # x^e + f_{e-1} x^{e-1} + ... + f_0, f low first


class GF:
    def __init__(self, q):
        self.q = q
        if q in CONWAY:
            self.p, f = CONWAY[q]; self.e = len(f); self.f = f
        else:
            self.p, self.e, self.f = q, 1, []
        Q = range(q)
        self.add = [[self._add(a, b) for b in Q] for a in Q]
        self.mul = [[self._mul(a, b) for b in Q] for a in Q]
        self.neg = [next(b for b in Q if self.add[a][b] == 0) for a in Q]
        self.inv = [0] + [next(b for b in Q if self.mul[a][b] == 1) for a in range(1, q)]

    def _digits(self, a):
        return [(a // self.p ** i) % self.p for i in range(self.e)]

    def _code(self, d):
        return sum(c * self.p ** i for i, c in enumerate(d))

    def _add(self, a, b):
        return self._code([(x + y) % self.p for x, y in zip(self._digits(a), self._digits(b))])

    def _mul(self, a, b):
        A, B = self._digits(a), self._digits(b); pr = [0] * (2 * self.e)
        for i in range(self.e):
            for j in range(self.e):
                pr[i + j] = (pr[i + j] + A[i] * B[j]) % self.p
        for d in range(2 * self.e - 2, self.e - 1, -1):
            c = pr[d]; pr[d] = 0
            for i in range(self.e):
                pr[d - self.e + i] = (pr[d - self.e + i] - c * self.f[i]) % self.p
        return self._code(pr[:self.e])

    # linear algebra on lists of tuples
    def rref(self, rows, ncols):
        M = [list(r) for r in rows]; r = 0; piv = []
        for c in range(ncols):
            p = next((i for i in range(r, len(M)) if M[i][c]), None)
            if p is None:
                continue
            M[r], M[p] = M[p], M[r]
            iv = self.inv[M[r][c]]; M[r] = [self.mul[x][iv] for x in M[r]]
            for i in range(len(M)):
                if i != r and M[i][c]:
                    f = self.neg[M[i][c]]
                    M[i] = [self.add[x][self.mul[f][y]] for x, y in zip(M[i], M[r])]
            piv.append(c); r += 1
        return M, piv

    def rank(self, rows):
        if not rows:
            return 0
        return len(self.rref(rows, len(rows[0]))[1])

    def matvec(self, A, v):
        out = []
        for row in A:
            s = 0
            for a, x in zip(row, v):
                s = self.add[s][self.mul[a][x]]
            out.append(s)
        return tuple(out)

    def matmul(self, A, B):
        n = len(B[0])
        return [[self._dotcol(A[i], B, j) for j in range(n)] for i in range(len(A))]

    def _dotcol(self, row, B, j):
        s = 0
        for l, a in enumerate(row):
            s = self.add[s][self.mul[a][B[l][j]]]
        return s

    def inverse(self, A):
        t = len(A)
        M, piv = self.rref([list(A[i]) + [int(i == j) for j in range(t)] for i in range(t)], t)
        if len(piv) < t or piv != list(range(t)):
            return None
        return [row[t:] for row in M]

    def combo(self, coeffs, vecs, t):
        out = [0] * t
        for c, v in zip(coeffs, vecs):
            for j in range(t):
                out[j] = self.add[out[j]][self.mul[c][v[j]]]
        return tuple(out)


FIELDS = {}


def field(q):
    if q not in FIELDS:
        FIELDS[q] = GF(q)
    return FIELDS[q]


def encode(v, q):
    x = 0
    for d in v:
        x = x * q + d
    return x


# ---------------------------------------------------------------- independent row classification
def classify_py(F, row, t):
    """dead / progression / other. Progression: solve the k-1 equations A u_{c-1} = u_c for the t*t entries
    of A (each output coordinate separately, all equations, exact), require a unique consistent solution
    with A invertible."""
    if F.rank(list(row)) < t:
        return "dead"
    k = len(row)
    if k < 2:
        return "other"
    A = []
    for i in range(t):
        # unknowns a_i (t of them): sum_j a_ij u_{c-1}[j] = u_c[i], c = 1..k-1; augmented matrix
        aug = [list(row[c - 1]) + [row[c][i]] for c in range(1, k)]
        M, piv = F.rref(aug, t + 1)
        if t in piv:                     # inconsistent
            return "other"
        if len(piv) < t:                 # not unique: columns 0..k-2 do not span
            return "other"
        a = [0] * t
        for r_i, pc in enumerate(piv):
            a[pc] = M[r_i][t]
        A.append(a)
    if F.rank(A) < t:
        return "other"
    return "progression"


# ---------------------------------------------------------------- generators
def rand_vec(F, rng, t, nonzero=True):
    while True:
        v = tuple(rng.randrange(F.q) for _ in range(t))
        if not nonzero or any(v):
            return v


def rand_inv(F, rng, t):
    while True:
        A = [[rng.randrange(F.q) for _ in range(t)] for _ in range(t)]
        if F.rank(A) == t:
            return A


def monomial(F, rng, t):
    perm = list(range(t)); rng.shuffle(perm)
    return [[(rng.randrange(1, F.q) if rng.random() < 0.5 else 1) if perm[i] == j else 0 for j in range(t)] for i in range(t)]


def conj(F, rng, M, t):
    P = rand_inv(F, rng, t); Pi = F.inverse(P)
    return F.matmul(F.matmul(P, M), Pi), P


def orbit(F, A, u0, k):
    row = []; u = tuple(u0)
    for _ in range(k):
        row.append(u); u = F.matvec(A, u)
    return row


def prog_row(F, rng, t, k, kind, shared=None):
    q = F.q
    if kind == "generic":
        A = rand_inv(F, rng, t); u0 = rand_vec(F, rng, t)
    elif kind == "shared":
        A = shared; u0 = rand_vec(F, rng, t)
    elif kind == "monomial":                   # permutation matrices with scalars: small order
        A = monomial(F, rng, t); u0 = rand_vec(F, rng, t)
    elif kind == "conjmonomial":               # small order, generic looking
        A, _ = conj(F, rng, monomial(F, rng, t), t); u0 = rand_vec(F, rng, t)
    elif kind == "negI":
        A = [[F.neg[1] if i == j else 0 for j in range(t)] for i in range(t)]; u0 = rand_vec(F, rng, t)
    elif kind == "const":
        A = [[int(i == j) for j in range(t)] for i in range(t)]; u0 = rand_vec(F, rng, t)
    elif kind == "fixed":                      # u0 an eigenvector: projectively constant row (dead)
        lam = rng.randrange(1, q)
        while True:
            M = rand_inv(F, rng, t)
            M = [[(lam if i == 0 else 0) if j == 0 else M[i][j] for j in range(t)] for i in range(t)]
            if F.rank(M) == t:
                break
        A, P = conj(F, rng, M, t); u0 = tuple(P[i][0] for i in range(t))   # A u0 = lam u0
    elif kind == "affine":                     # affine points: u = (1, x), x -> M x + b
        M = rand_inv(F, rng, t - 1); b = [rng.randrange(q) for _ in range(t - 1)]
        A = [[1] + [0] * (t - 1)] + [[b[i]] + M[i] for i in range(t - 1)]
        u0 = tuple([1] + [rng.randrange(q) for _ in range(t - 1)])
    elif kind == "translation":                # x -> x + b: a line, dead for t >= 3
        b = [rng.randrange(q) for _ in range(t - 1)]
        A = [[1] + [0] * (t - 1)] + [[b[i]] + [int(i == j) for j in range(t - 1)] for i in range(t - 1)]
        u0 = tuple([1] + [rng.randrange(q) for _ in range(t - 1)])
    elif kind == "invariant":                  # u0 in an invariant subspace: non-spanning (dead)
        d = rng.randrange(1, t)
        B1 = rand_inv(F, rng, d); B2 = rand_inv(F, rng, t - d)
        M = [[0] * t for _ in range(t)]
        for i in range(d):
            for j in range(d):
                M[i][j] = B1[i][j]
        for i in range(t - d):
            for j in range(t - d):
                M[d + i][d + j] = B2[i][j]
        for i in range(d):                     # upper block may couple; keeps span of e_0..e_{d-1} invariant
            for j in range(d, t):
                M[i][j] = rng.randrange(q)
        A, P = conj(F, rng, M, t)
        x = [rng.randrange(q) for _ in range(d)] + [0] * (t - d)
        if not any(x):
            x[0] = 1
        u0 = F.matvec(P, x)
    else:
        raise ValueError(kind)
    return orbit(F, A, u0, k)


def singular_row(F, rng, t, k):
    """u_c = A u_{c-1} with A singular (rank t-1) and the row spanning GF(q)^t, if possible"""
    for _ in range(200):
        M = rand_inv(F, rng, t)
        M = [M[i] if i < t - 1 else [0] * t for i in range(t)]          # rank t-1 (image e_0..e_{t-2})
        A, P = conj(F, rng, M, t)
        u0 = rand_vec(F, rng, t)
        row = orbit(F, A, u0, k)
        if F.rank(row) == t and F.rank(A) == t - 1:
            return row
    return None


def other_row(F, rng, t, k, kind):
    if kind == "random":
        return [rand_vec(F, rng, t, nonzero=rng.random() < 0.9) for _ in range(k)]
    if kind == "affine":
        return [tuple([1] + [rng.randrange(F.q) for _ in range(t - 1)]) for _ in range(k)]
    if kind == "few":
        pool = [rand_vec(F, rng, t) for _ in range(rng.randrange(t, 2 * t + 3))]
        return [rng.choice(pool) for _ in range(k)]
    if kind == "corrupt":
        row = prog_row(F, rng, t, k, "generic")
        c = rng.randrange(k); row[c] = rand_vec(F, rng, t)
        return row
    if kind == "singular":
        r = singular_row(F, rng, t, k)
        return r if r else [rand_vec(F, rng, t) for _ in range(k)]
    raise ValueError(kind)


P_KINDS = ["generic"] * 4 + ["shared"] * 2 + ["monomial", "conjmonomial", "affine", "affine",
                                               "negI", "const", "fixed", "translation", "invariant"]
O_KINDS = ["random"] * 3 + ["affine", "few", "corrupt", "singular"]


def gen_family(rng, t, q, k, npg, no):
    F = field(q)
    shared = rand_inv(F, rng, t)
    rows = [prog_row(F, rng, t, k, rng.choice(P_KINDS), shared) for _ in range(npg)]
    rows += [other_row(F, rng, t, k, rng.choice(O_KINDS)) for _ in range(no)]
    if not rows:
        rows = [other_row(F, rng, t, k, "random")]
    rng.shuffle(rows)
    return rows


# ---------------------------------------------------------------- running
class Bins:
    pass


BIN = Bins()


def build(src, out, omp=True, extra=()):
    cmd = ["gcc", "-O2"] + (["-fopenmp"] if omp else []) + list(extra) + ["-x", "c", "-o", out, src]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode:
        raise SystemExit("build failed: %s\n%s" % (" ".join(cmd), p.stderr))
    return out


def write_family(rows, q, path):
    with open(path, "w") as f:
        f.write("# test family\n")
        for row in rows:
            f.write(" ".join(str(encode(v, q)) for v in row) + "\n")


def run(exe, fam, t, q, mode_args, listing=False, timeout=600):
    env = dict(os.environ)
    if listing:
        env["CPHFCHECK_LIST"] = "1"
    else:
        env.pop("CPHFCHECK_LIST", None)
    p = subprocess.run([exe, fam, str(t), str(q)] + [str(x) for x in mode_args], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=timeout)
    res = {"code": p.returncode, "out": p.stdout, "err": p.stderr, "count": None, "first": None, "rows": {},
           "list": None}
    for line in p.stdout.splitlines():
        m = re.match(r"checked (\d+) t-sets.*, uncovered (\d+)$", line)
        if m:
            res["count"] = int(m.group(2)); res["checked"] = int(m.group(1))
        m = re.match(r"first uncovered: (.*)$", line)
        if m:
            res["first"] = tuple(int(x) for x in m.group(1).split())
        m = re.match(r"row (\d+): (progression|dead|other)", line)
        if m:
            res["rows"][int(m.group(1))] = m.group(2)
    if listing:
        res["list"] = sorted(tuple(int(x) for x in l.split()[1:]) for l in p.stdout.splitlines() if l.startswith("U "))
    return res


class Suite:
    def __init__(self, exe_new, exe_noomp, verbose=True):
        self.exe = exe_new; self.noomp = exe_noomp; self.verbose = verbose
        self.results = []          # (section, name, ok, detail)
        self.nid = 0

    def record(self, section, name, ok, detail=""):
        self.results.append((section, name, ok, detail))
        if self.verbose:
            print("%s %s %s %s" % ("PASS" if ok else "FAIL", section, name, detail), flush=True)

    def tmpfile(self):
        self.nid += 1
        return os.path.join(WORK, "fam_%d_%d.txt" % (os.getpid(), self.nid))

    # one differential comparison; returns (ok, detail, info)
    def compare(self, rows, t, q, rng, must_contain=None, threads=None, listcap=LISTCAP):
        fam = self.tmpfile(); write_family(rows, q, fam)
        F = field(q)
        try:
            ref = run(self.exe, fam, t, q, ["full", 1])
            if ref["code"] not in (0, 1) or ref["count"] is None:
                return False, "full failed: %s %s" % (ref["code"], ref["err"][:200]), {}
            th = threads if threads else rng.choice([1, 2, 3])
            exe2 = self.noomp if rng.random() < 0.15 else self.exe
            pr = run(exe2, fam, t, q, ["progression", th])
            ff = run(exe2, fam, t, q, ["fullfast", th])
            info = {"count": ref["count"], "rows": pr["rows"]}
            for name, r in (("progression", pr), ("fullfast", ff)):
                if r["code"] != ref["code"] or r["count"] != ref["count"] or r["first"] != ref["first"]:
                    return False, "%s: exit %s count %s first %s vs full exit %s count %s first %s %s" % (
                        name, r["code"], r["count"], r["first"], ref["code"], ref["count"], ref["first"],
                        (r["out"] + r["err"])[-300:]), info
                if "INTERNAL" in r["out"] or "completeness" not in r["out"]:
                    return False, "%s: no completeness line or internal failure" % name, info
                m = re.search(r"= (\d+) \(expected (\d+)\)", r["out"])
                if not m or m.group(1) != m.group(2) or r.get("checked") != ref.get("checked"):
                    return False, "%s: completeness count mismatch" % name, info
            # independent classification of the rows
            for i, row in enumerate(rows):
                want = classify_py(F, row, t)
                if pr["rows"].get(i) != want:
                    return False, "row %d classified %s by C, %s by Python" % (i, pr["rows"].get(i), want), info
            if ref["count"] <= listcap:
                L = run(self.exe, fam, t, q, ["full", 1], listing=True)["list"]
                if len(L) != ref["count"] or (L and tuple(L[0]) != ref["first"]):
                    return False, "full listing inconsistent with its count", info
                for mode in ("progression", "fullfast"):
                    L2 = run(exe2, fam, t, q, [mode, th], listing=True)["list"]
                    if L2 != L:
                        miss = sorted(set(L) - set(L2))[:3]; extra = sorted(set(L2) - set(L))[:3]
                        return False, "%s list differs: missing %s extra %s" % (mode, miss, extra), info
                info["list"] = L
                if must_contain is not None and tuple(must_contain) not in set(L):
                    return False, "planted set %s not reported" % (must_contain,), info
            elif must_contain is not None:
                return False, "too many uncovered sets to confirm the planted one", info
            return True, "uncovered %d" % ref["count"], info
        finally:
            os.remove(fam)


# ---------------------------------------------------------------- sections
def k_for(rng, t, q):
    if t == 2:
        return rng.randint(3, 40)
    if t == 3:
        return rng.randint(4, 60) if rng.random() < 0.85 else rng.randint(60, 90)
    if t == 4:
        return rng.randint(5, 60)
    if t == 5:
        return rng.randint(6, 40) if rng.random() < 0.8 else rng.randint(40, 55)
    return rng.randint(7, 26)


def section_diff(S, rng, ncases):
    stats = {"repeat_points": 0, "faulty": 0, "clean": 0, "P": 0, "O": 0, "dead": 0}
    for i in range(ncases):
        t = rng.choice([3, 3, 4, 4, 5, 5, 6] * 4 + [2])
        q = rng.choice([3, 4, 5, 7, 8, 9])
        if t >= 5 and q >= 7 and rng.random() < 0.5:
            q = rng.choice([3, 4, 5])
        k = k_for(rng, t, q)
        npg = rng.randint(0, 4); no = rng.randint(0, 3)
        if rng.random() < 0.3:                  # near-CPHF families: more rows, spanning kinds only
            npg = rng.randint(3, 4); no = rng.randint(2, 3)
            F = field(q); shared = rand_inv(F, rng, t)
            rows = [prog_row(F, rng, t, k, rng.choice(["generic", "shared", "conjmonomial", "affine"]), shared)
                    for _ in range(npg)] + [other_row(F, rng, t, k, rng.choice(["random", "affine"])) for _ in range(no)]
            rng.shuffle(rows)
        else:
            rows = gen_family(rng, t, q, k, npg, no)
        ok, detail, info = S.compare(rows, t, q, rng)
        for v in info.get("rows", {}).values():
            stats[{"progression": "P", "other": "O", "dead": "dead"}[v]] += 1
        if k > q ** (t - 1):
            stats["repeat_points"] += 1
        stats["faulty" if info.get("count") else "clean"] += 1
        S.record("diff", "#%d t=%d q=%d k=%d np=%d no=%d" % (i, t, q, k, npg, no), ok, detail)
    return stats


def wild_kind(F, rows, prow, S, t):
    """does S use a WILD column or a wildcard row in some progression row (for its prefix S[:t-2])"""
    for r in prow:
        pre = [rows[r][c] for c in S[:t - 2]]
        if t > 2 and F.rank(pre) < t - 2:
            return True
        for c in S[t - 2:]:
            if F.rank(pre + [rows[r][c]]) < t - 1:
                return True
    return False


def section_planted(S, rng, per_cat):
    cats = {(pos, w): 0 for pos in ("a=0", "middle", "last") for w in (False, True)}
    tries = 0
    while min(cats.values()) < per_cat and tries < per_cat * 400:
        tries += 1
        t = rng.choice([3, 3, 4, 4, 5])
        q = rng.choice([3, 4, 5, 7, 8, 9])
        if t == 5:
            q = rng.choice([3, 4, 5])
        k = {3: rng.randint(12, 60), 4: rng.randint(10, 40), 5: rng.randint(10, 26)}[t]
        F = field(q)
        npg = rng.randint(1, 4)
        shared = rand_inv(F, rng, t)
        kinds = ["generic", "shared", "monomial", "conjmonomial", "affine"]
        prow_rows = [prog_row(F, rng, t, k, rng.choice(kinds), shared) for _ in range(npg)]
        prow_rows = [r for r in prow_rows if classify_py(F, r, t) == "progression"]
        if not prow_rows:
            continue
        fam = S.tmpfile(); write_family(prow_rows, q, fam)
        try:
            ref = run(S.exe, fam, t, q, ["full", 1])
            if ref["count"] is None or ref["count"] == 0 or ref["count"] > 60000:
                continue
            pool = run(S.exe, fam, t, q, ["full", 1], listing=True)["list"]
        finally:
            os.remove(fam)
        want = [c for c, v in cats.items() if v < per_cat]
        rng.shuffle(want)
        chosen = None
        for pos, w in want:
            cand = [X for X in pool if (pos == "a=0" and X[0] == 0) or (pos == "last" and X[-1] == k - 1)
                    or (pos == "middle" and X[0] > 0 and X[-1] < k - 1)]
            rng.shuffle(cand)
            for X in cand[:300]:
                if wild_kind(F, prow_rows, range(len(prow_rows)), X, t) == w:
                    chosen = (X, pos, w); break
            if chosen:
                break
        if not chosen:
            continue
        X, pos, w = chosen
        no = rng.randint(1, 3)
        orows = [other_row(F, rng, t, k, rng.choice(["random", "affine", "few"])) for _ in range(no)]
        for row in orows:                      # make X fail in this row
            j = rng.randrange(t)
            others = [row[c] for i, c in enumerate(X) if i != j]
            coeffs = [rng.randrange(q) for _ in others]
            row[X[j]] = F.combo(coeffs, others, t)
            assert F.rank([row[c] for c in X]) < t
        rows = prow_rows + orows
        ok, detail, info = S.compare(rows, t, q, rng, must_contain=X, listcap=400000)
        cats[(pos, w)] += 1
        S.record("planted", "t=%d q=%d k=%d P=%d O=%d set=%s shift=%s(a=%d) wild=%s" % (
            t, q, k, len(prow_rows), no, X, pos, X[0], w), ok, detail)
    return cats


def section_negatives(S, rng, nrep):
    for i in range(nrep):
        t = rng.choice([3, 4, 5]); q = rng.choice([3, 4, 5, 7, 8, 9])
        if t == 5:
            q = rng.choice([3, 4, 5])
        k = rng.randint(t + 6, {3: 50, 4: 35, 5: 22}[t])
        F = field(q)
        base = prog_row(F, rng, t, k, "generic")
        while classify_py(F, base, t) != "progression":
            base = prog_row(F, rng, t, k, "generic")
        good = prog_row(F, rng, t, k, "generic")
        while classify_py(F, good, t) != "progression":
            good = prog_row(F, rng, t, k, "generic")
        other = other_row(F, rng, t, k, "random")
        cases = []
        for where, c in (("first", 0), ("middle", k // 2), ("last", k - 1)):
            row = list(base)
            v = row[c]
            while v == row[c]:
                v = rand_vec(F, rng, t)
            row[c] = v
            cases.append(("corrupt-%s" % where, row))
        sing = singular_row(F, rng, t, k)
        if sing:
            cases.append(("singularA", sing))
        cases.append(("nonspanning", prog_row(F, rng, t, k, "invariant")))
        cases.append(("constant", prog_row(F, rng, t, k, "const")))
        for name, bad in cases:
            rows = [good, bad, other]
            want = classify_py(F, bad, t)
            if name.startswith("corrupt") and want == "progression":
                S.record("negative", "%s t=%d q=%d k=%d" % (name, t, q, k), True, "skipped: still a progression")
                continue
            fam = S.tmpfile(); write_family(rows, q, fam)
            try:
                r = run(S.exe, fam, t, q, ["progression", 2, "P=0,1"])
                ok = r["code"] == 3 and "PROGRESSION NOT CERTIFIED: row 1" in r["out"]
                exp_class = "dead" if name in ("nonspanning", "constant") else "other"
                ok = ok and r["rows"].get(1) == exp_class == want
                if name == "singularA":
                    ok = ok and "singular" in r["out"]
                r0 = run(S.exe, fam, t, q, ["progression", 2, "P=0"])      # the good row alone certifies
                ok = ok and r0["code"] in (0, 1) and r0["rows"].get(0) == "progression"
                S.record("negative", "%s t=%d q=%d k=%d (P= exit 3)" % (name, t, q, k), ok,
                         "exit %d, row 1 %s" % (r["code"], r["rows"].get(1)))
            finally:
                os.remove(fam)
            ok, detail, _ = S.compare(rows, t, q, rng)
            S.record("negative", "%s t=%d q=%d k=%d (vs full)" % (name, t, q, k), ok, detail)
    # bad arguments
    one = prog_row(field(5), rng, 3, 10, "generic")
    while classify_py(field(5), one, 3) != "progression":
        one = prog_row(field(5), rng, 3, 10, "generic")
    fam = S.tmpfile(); write_family([one], 5, fam)
    try:
        r = run(S.exe, fam, 3, 5, ["progression", "P=3"])
        S.record("negative", "P= row out of range exits 2", r["code"] == 2, "exit %d" % r["code"])
        r = run(S.exe, fam, 3, 5, ["progression", "P=0"])
        S.record("negative", "single progression row with P=0", r["code"] in (0, 1) and r["rows"].get(0) == "progression",
                 "exit %d" % r["code"])
    finally:
        os.remove(fam)


def section_legacy(S, orig_exe, rng):
    """full, cyclic, sample, expand: identical stdout, stderr, exit code and expanded files"""
    cases = []
    L = LEGACY_DIR
    if os.path.isdir(L):
        cases += [(os.path.join(L, "cyc.txt"), 3, 7, a) for a in (["full", 1], ["full", 2], ["cyclic", 1, 2], ["cyclic", 3, 1],
                                                                  ["sample", 1000, 5, 1])]
        cases += [(os.path.join(L, "cyc_bad.txt"), 3, 7, a) for a in (["full", 1], ["cyclic", 1, 1], ["cyclic", 19, 1])]
        cases += [(os.path.join(L, "rnd.txt"), 4, 7, ["full", 1]), (os.path.join(L, "aff.txt"), 2, 7, ["full", 1])]
    tmpfiles = []
    for i in range(12):
        t = rng.choice([2, 3, 4]); q = rng.choice([3, 4, 5, 7, 8, 9]); k = rng.randint(6, 30)
        rows = gen_family(rng, t, q, k, rng.randint(0, 3), rng.randint(0, 2))
        fam = S.tmpfile(); write_family(rows, q, fam); tmpfiles.append(fam)
        cases.append((fam, t, q, ["full", 1]))
        cases.append((fam, t, q, ["cyclic", rng.choice([1, 2, 3]), 1]))
        cases.append((fam, t, q, ["sample", 500, 7, 1]))
        cases.append((fam, t, q, ["expand", "EXP"] + (["affine"] if rng.random() < 0.3 else [])))
    cases.append((tmpfiles[0], 9, 5, ["full"]))          # usage errors
    cases.append((tmpfiles[0], 3, 6, ["full"]))
    cases.append((tmpfiles[0], 3, 5, ["nosuchmode"]))
    try:
        for fam, t, q, args in cases:
            outs = []
            for exe in (orig_exe, S.exe):
                a = list(args)
                expf = None
                if "EXP" in a:
                    expf = S.tmpfile(); a[a.index("EXP")] = expf
                p = subprocess.run([exe, fam, str(t), str(q)] + [str(x) for x in a], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, universal_newlines=True,
                                   env={k_: v for k_, v in os.environ.items() if k_ != "CPHFCHECK_LIST"})
                body = open(expf).read() if expf and os.path.exists(expf) else None
                if expf and os.path.exists(expf):
                    os.remove(expf)
                o = p.stdout.replace(expf, "EXP") if expf else p.stdout
                outs.append((p.returncode, o, p.stderr, body))
            S.record("legacy", "%s t=%d q=%d %s" % (os.path.basename(fam)[:12], t, q, " ".join(map(str, args))),
                     outs[0] == outs[1], "exit %d" % outs[0][0])
    finally:
        for f in tmpfiles:
            os.remove(f)
    # the interface check_certificates.py relies on, for the new modes
    rows = gen_family(rng, 3, 7, 20, 3, 1)
    fam = S.tmpfile(); write_family(rows, 7, fam)
    try:
        for mode in ("progression", "fullfast"):
            r = run(S.exe, fam, 3, 7, [mode, 2])
            head = r["out"].splitlines()[0]
            ok = bool(re.search(r"n=(\d+) k=(\d+) q=(\d+) t=(\d+)", head)) and \
                any(l.startswith("checked ") for l in r["out"].splitlines())
            S.record("legacy", "interface of %s (header, 'checked' line)" % mode, ok, head)
    finally:
        os.remove(fam)


def section_real(S, rng):
    files = [("CA_16360_4_74_8.txt", 4, 8), ("CA_26217_4_87_9.txt", 4, 9), ("CA_2024_3_313_8.txt", 3, 8),
             ("CA_114205_4_145_13.txt", 4, 13)]
    for fn, t, q in files:
        path = os.path.join(REAL, fn)
        if not os.path.exists(path):
            S.record("real", fn, True, "skipped: not present"); continue
        ref = run(S.exe, path, t, q, ["full", 2])
        pr = run(S.exe, path, t, q, ["progression", 2])
        ff = run(S.exe, path, t, q, ["fullfast", 2])
        np_ = sum(1 for v in pr["rows"].values() if v == "progression")
        ok = ref["count"] == pr["count"] == ff["count"] and ref["code"] == pr["code"] == ff["code"]
        S.record("real", fn, ok, "uncovered full/progression/fullfast %s/%s/%s, progression rows %d of %d" % (
            ref["count"], pr["count"], ff["count"], np_, len(pr["rows"])))


def section_medium(S, rng):
    t, q, k = 4, 7, 300
    F = field(q)
    rows = [prog_row(F, rng, t, k, "generic") for _ in range(4)] + [prog_row(F, rng, t, k, "affine") for _ in range(2)] + \
           [other_row(F, rng, t, k, "random") for _ in range(3)]
    fam = S.tmpfile(); write_family(rows, q, fam)
    try:
        t0 = time.time(); ref = run(S.exe, fam, t, q, ["full", 2], listing=False); tf = time.time() - t0
        t0 = time.time(); pr = run(S.exe, fam, t, q, ["progression", 2]); tp = time.time() - t0
        t0 = time.time(); ff = run(S.exe, fam, t, q, ["fullfast", 2]); tff = time.time() - t0
        ok = ref["count"] == pr["count"] == ff["count"] and ref["code"] == pr["code"] == ff["code"]
        detail = "uncovered %s; full %.1fs, fullfast %.2fs, progression %.2fs (2 threads)" % (ref["count"], tf, tff, tp)
        if ok and ref["count"] <= 200000:
            ref1 = run(S.exe, fam, t, q, ["full", 1])
            L = run(S.exe, fam, t, q, ["full", 1], listing=True)["list"]
            L2 = run(S.exe, fam, t, q, ["progression", 2], listing=True)["list"]
            L3 = run(S.exe, fam, t, q, ["fullfast", 2], listing=True)["list"]
            ok = L == L2 == L3 and ref1["first"] == pr["first"] == ff["first"]
            detail += "; lists identical %s" % ok
        S.record("medium", "t=4 q=7 k=300 n=9 (6 progression-built rows, 3 random)", ok, detail)
    finally:
        os.remove(fam)


# ---------------------------------------------------------------- mutations
MUTATIONS = [
    ("no WILD handling (zero image treated as class [1:0])",
     "    if (!a && !b) return WILDC;\n", "    if (!a && !b) return q;\n"),
    ("no invertibility check of A",
     "if (rank_of(rowsA, t) != t) { snprintf", "if (0) { snprintf"),
    ("shift range off by one (last shift skipped)",
     "for (int a = 0; a <= k - 1 - D[t - 1]; a++)", "for (int a = 0; a < k - 1 - D[t - 1]; a++)"),
    ("shift a = 0 skipped",
     "for (int a = 0; a <= k - 1 - D[t - 1]; a++)", "for (int a = 1; a <= k - 1 - D[t - 1]; a++)"),
    ("extra: WILD-with-WILD subproblem dropped",
     "    if (cntA[W]) split(X, depth + 1, sA + offA[W], cntA[W], B, nB);", "    if (0) split(X, depth + 1, sA + offA[W], cntA[W], B, nB);"),
    ("extra: B_w left out of the class subproblems",
     "        for (int i = 0; i < cntB[W]; i++) cb[j++] = sB[offB[W] + i];\n", "        nb -= cntB[W];\n"),
    ("extra: progression check skips the last column",
     "for (int c = 1; c <= k - 1; c++) {", "for (int c = 1; c <= k - 2; c++) {"),
]


def section_mutations(S, seed, quick):
    src = open(SRC).read()
    summary = []
    for name, old, new in MUTATIONS:
        cnt = src.count(old)
        if cnt != 1:
            S.record("mutation", name, False, "patch target found %d times" % cnt); summary.append((name, None)); continue
        mpath = os.path.join(WORK, "mutant.c"); open(mpath, "w").write(src.replace(old, new))
        exe = build(mpath, os.path.join(WORK, "mutant"))
        os.remove(mpath)
        M = Suite(exe, exe, verbose=False)
        rng = random.Random(seed + 1000)
        section_diff(M, rng, 40 if quick else 150)
        section_planted(M, random.Random(seed + 2000), 2 if quick else 6)
        section_negatives(M, random.Random(seed + 3000), 2 if quick else 4)
        fails = sum(1 for r in M.results if not r[2])
        tot = len(M.results)
        sections = sorted(set(r[0] for r in M.results if not r[2]))
        modes = sorted(set(m_ for r in M.results if not r[2] for m_ in ("progression", "fullfast")
                           if r[3].startswith(m_)))
        S.record("mutation", name, fails > 0, "caught by %d of %d tests (sections %s; mode mismatches %s)" % (
            fails, tot, ",".join(sections), ",".join(modes) or "none"))
        summary.append((name, fails, tot))
        os.remove(exe)
    return summary


# ---------------------------------------------------------------- timing
def timed(exe, fam, t, q, args):
    t0 = time.time(); r = run(exe, fam, t, q, args, timeout=3600); return time.time() - t0, r


def section_timing(S, rng, quick):
    """single-thread unit costs on q=23 families (6 progression rows + 2 random rows), and extrapolation"""
    F = field(23); q = 23
    fams = {}

    def fam_for(t, k):
        if (t, k) not in fams:
            rr = random.Random(1000 * t + k)
            rows = []
            while len(rows) < 6:
                r = prog_row(F, rr, t, k, "generic")
                if classify_py(F, r, t) == "progression":
                    rows.append(r)
            rows += [other_row(F, rr, t, k, "random") for _ in range(2)]
            path = S.tmpfile(); write_family(rows, q, path); fams[(t, k)] = path
        return fams[(t, k)]
    plan = {"full": [(4, 120), (4, 240), (5, 60), (5, 100)], "fullfast": [(4, 120), (4, 240), (5, 60), (5, 120)],
            "progression": [(5, 300), (5, 600), (6, 80), (6, 160)]}
    if not quick:
        plan["fullfast"] += [(5, 200)]
        plan["progression"] += [(5, 1200), (6, 240)]
    unit = {}
    lines = []
    try:
        for mode, cases in plan.items():
            for t, k in cases:
                sec, r = timed(S.exe, fam_for(t, k), t, q, [mode, 1])
                units = {"full": binom(k, t), "fullfast": binom(k, t - 1), "progression": binom(k - 1, t - 2)}[mode]
                m = re.search(r"shifts tested in other rows (\d+)", r["out"])
                extra = ", shifts %s" % m.group(1) if m else ""
                unit.setdefault((mode, t), []).append((k, sec / units))
                line = "%-11s t=%d k=%4d: %7.2fs, %.1f ns per unit (%s units%s), uncovered %s" % (
                    mode, t, k, sec, 1e9 * sec / units, units, extra, r["count"])
                lines.append(line)
                S.record("timing", line, r["code"] in (0, 1))
        K = 10000
        for (mode, t), pts in sorted(unit.items()):
            units = {"full": binom(K, t), "fullfast": binom(K, t - 1), "progression": binom(K - 1, t - 2)}[mode]
            (k1, u1), (k2, u2) = pts[0], pts[-1]
            beta = math.log(u2 / u1) / math.log(k2 / k1) if k2 != k1 else 0.0
            flat = units * u2; fit = units * u2 * (K / k2) ** max(beta, 0.0)
            line = "extrapolated %-11s t=%d q=23 k=10000, 1 thread: %.3g s (%.3g days) at the k=%d unit cost; %.3g days with the fitted growth k^%.2f" % (
                mode, t, flat, flat / 86400, k2, fit / 86400, beta)
            print(line, flush=True); lines.append(line)
    finally:
        for f in fams.values():
            os.remove(f)
    return lines


def binom(a, b):
    return math.comb(a, b) if 0 <= b <= a else 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=20261101)
    ap.add_argument("--no-mutations", action="store_true")
    ap.add_argument("--no-timing", action="store_true")
    ap.add_argument("--no-medium", action="store_true")
    ap.add_argument("--diff", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    t_start = time.time()
    exe = build(SRC, os.path.join(WORK, "cphfcheck"))
    exe_noomp = build(SRC, os.path.join(WORK, "cphfcheck_noomp"), omp=False)
    orig = build(ORIG, os.path.join(WORK, "cphfcheck_orig"))
    S = Suite(exe, exe_noomp)
    rng = random.Random(a.seed)
    print("== legacy modes", flush=True); section_legacy(S, orig, rng)
    print("== differential", flush=True)
    dstats = section_diff(S, rng, a.diff if a.diff is not None else (120 if a.quick else 700))
    print("== planted faults", flush=True); cats = section_planted(S, rng, 4 if a.quick else 20)
    print("== certification negatives", flush=True); section_negatives(S, rng, 3 if a.quick else 12)
    print("== real families", flush=True); section_real(S, rng)
    if not a.no_medium:
        print("== medium", flush=True); section_medium(S, rng)
    msum = []
    if not a.no_mutations:
        print("== mutations", flush=True); msum = section_mutations(S, a.seed, a.quick)
    tlines = []
    if not a.no_timing:
        print("== timing", flush=True); tlines = section_timing(S, rng, a.quick)
    print("\n== summary")
    secs = []
    for sec, _, ok, _ in S.results:
        if sec not in secs:
            secs.append(sec)
    for sec in secs:
        rs = [r for r in S.results if r[0] == sec]
        print("%-10s %4d tests, %4d passed, %d failed" % (sec, len(rs), sum(r[2] for r in rs), sum(not r[2] for r in rs)))
    print("diff stats:", dstats)
    print("planted categories (shift, wild): ", {"%s/%s" % k: v for k, v in cats.items()})
    for m in msum:
        print("mutation:", m)
    for l in tlines:
        print(l)
    nfail = sum(not r[2] for r in S.results)
    print("TOTAL %d tests, %d failed, %.0fs" % (len(S.results), nfail, time.time() - t_start))
    for f in (exe, exe_noomp, orig):
        os.remove(f)
    shutil.rmtree(WORK, ignore_errors=True)
    print("ALL PASS" if nfail == 0 else "SOME TESTS FAILED")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
