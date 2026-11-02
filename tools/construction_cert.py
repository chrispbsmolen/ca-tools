#!/usr/bin/env python3
"""construction_cert - check a construction certificate and rebuild the array it proves.

A construction certificate records the recipe of a covering array instead of the array: for
"powercz-1" (Colbourn and Zhou 2012, Theorem 2.2 with Lemma 2.3) a hash family with M rows and
k columns, one quilting array (ingredient) per row, and the species classes each ingredient is
claimed to cover. This program

  1. regenerates the hash family from its description (its own GF(q) arithmetic),
  2. checks every hypothesis the coverage proof uses, exactly and exhaustively:
       width       every row of the hash family has width w_i >= t
       ingredient  every ingredient file has the recorded sha256, is a rectangular array over
                   0..v-1 with exactly w_i columns for each row it is assigned to
       agreement   any two distinct columns of the hash family agree in at most e-1 rows
                   (checked as: every e-subset of rows maps the k columns injectively)
       quilting    every ingredient covers, on every t-set of its columns, every t-tuple whose
                   species (multiset of values) it is declared to cover
       species     every species S of size t over v symbols is declared in more than
                   (e-1) * tau(S) rows, tau(S) = number of pairs of unequal entries
  3. assembles the array (block i = ingredient i with its columns indexed by row i of the hash
     family), serializes it in the table's canonical text (tools/check_submission.py:
     canon_serialize) and hashes it as a stream,
  4. compares N, k and the sha256 with the certificate's expected values.

It exits 0 only if every check passes. The format and the proof are in
README_construction_cert.md. Standard library only.

Usage:
  construction_cert.py CERT.json [--write ARRAY.txt] [--quiet]
Exit status: 0 certificate valid, 1 a check failed, 2 malformed certificate or usage error.
"""
import hashlib
import itertools
import json
import os
import re
import sys
import time

FORMAT = "construction-cert-1"
CONSTRUCTIONS = ("powercz-1",)
MAX_FIELD = 4096            # largest q for which GF(q) tables are built
MAX_COLUMNS = 4000000       # largest q^e enumerated
HEX64 = re.compile(r"^[0-9a-f]{64}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_.+-]{1,100}$")
INT_RE = re.compile(r"^[0-9]+$")


class CertError(Exception):
    """the certificate is malformed (exit 2)"""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def need_int(obj, key, lo=None, hi=None, where=""):
    if key not in obj:
        raise CertError("%smissing key %r" % (where, key))
    x = obj[key]
    if not is_int(x):
        raise CertError("%s%r must be an integer, got %r" % (where, key, x))
    if lo is not None and x < lo:
        raise CertError("%s%r = %d is below %d" % (where, key, x, lo))
    if hi is not None and x > hi:
        raise CertError("%s%r = %d is above %d" % (where, key, x, hi))
    return x


def only_keys(obj, allowed, where):
    if not isinstance(obj, dict):
        raise CertError("%s must be a JSON object" % where)
    extra = sorted(set(obj) - set(allowed))
    if extra:
        raise CertError("%s: unknown key(s) %s" % (where, ", ".join(map(repr, extra))))


def is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def comb(n, r):
    if r < 0 or r > n:
        return 0
    out = 1
    for i in range(r):
        out = out * (n - i) // (i + 1)
    return out


def species_list(t, v):
    """all species of size t over v symbols, as count vectors (c_0, ..., c_{v-1}), sum t"""
    out = []

    def rec(prefix, left, slots):
        if slots == 1:
            out.append(tuple(prefix + [left]))
            return
        for c in range(left, -1, -1):
            rec(prefix + [c], left - c, slots - 1)
    rec([], t, v)
    return out


def tau(sp):
    t = sum(sp)
    return comb(t, 2) - sum(comb(c, 2) for c in sp)


def species_of(tup, v):
    c = [0] * v
    for x in tup:
        c[x] += 1
    return tuple(c)


def arrangements(sp, v):
    """every t-tuple over 0..v-1 whose species is sp"""
    t = sum(sp)
    return [tup for tup in itertools.product(range(v), repeat=t) if species_of(tup, v) == sp]


def fmt_species(sp, v):
    if v == 2:
        return "weight %d" % sp[1]
    return "{" + ",".join("%d^%d" % (s, c) for s, c in enumerate(sp) if c) + "}"


# ---------------------------------------------------------------------------
# GF(p^m): element i <-> polynomial sum_j d_j x^j with d_j the base-p digits of i
# (d_0 least significant), modulo the monic modulus a_0 + a_1 x + ... + a_m x^m.
# ---------------------------------------------------------------------------

class Field:
    def __init__(self, p, m, modulus):
        self.p, self.m, self.q = p, m, p ** m
        self.modulus = list(modulus)
        q = self.q
        digits = [self._digits(i) for i in range(q)]
        self.add = [[self._undigits([(a + b) % p for a, b in zip(digits[i], digits[j])])
                     for j in range(q)] for i in range(q)]
        self.mul = [[self._undigits(self._polymulmod(digits[i], digits[j]))
                     for j in range(q)] for i in range(q)]

    def _digits(self, i):
        d = []
        for _ in range(self.m):
            d.append(i % self.p)
            i //= self.p
        return d

    def _undigits(self, d):
        x = 0
        for c in reversed(d):
            x = x * self.p + c
        return x

    def _polymulmod(self, a, b):
        p, m = self.p, self.m
        prod = [0] * (2 * m - 1)
        for i, x in enumerate(a):
            if x:
                for j, y in enumerate(b):
                    prod[i + j] = (prod[i + j] + x * y) % p
        # reduce: x^m = -(a_0 + ... + a_{m-1} x^{m-1})  (modulus is monic)
        for deg in range(2 * m - 2, m - 1, -1):
            c = prod[deg]
            if c:
                prod[deg] = 0
                for j in range(m):
                    prod[deg - m + j] = (prod[deg - m + j] - c * self.modulus[j]) % p
        return prod[:m]


def parse_field(obj):
    only_keys(obj, ("q", "p", "m", "modulus"), "field")
    q = need_int(obj, "q", 2, MAX_FIELD, "field: ")
    p = need_int(obj, "p", 2, None, "field: ")
    m = need_int(obj, "m", 1, None, "field: ")
    if p ** m != q:
        raise CertError("field: q = %d is not p^m = %d^%d" % (q, p, m))
    if m == 1:
        if "modulus" in obj and obj["modulus"] not in (None, [0, 1]):
            raise CertError("field: a prime field takes no modulus (or [0, 1])")
        modulus = [0, 1]
    else:
        modulus = obj.get("modulus")
        if not isinstance(modulus, list) or len(modulus) != m + 1 or \
                not all(is_int(c) and 0 <= c < p for c in modulus):
            raise CertError("field: modulus must be a list of m+1 = %d coefficients in 0..%d, "
                            "constant term first" % (m + 1, p - 1))
        if modulus[m] != 1:
            raise CertError("field: modulus must be monic (last coefficient 1)")
    return p, m, q, modulus


# ---------------------------------------------------------------------------
# certificate parsing
# ---------------------------------------------------------------------------

def parse_covers(obj, t, v, where):
    only_keys(obj, ("weights", "species", "all"), where)
    if len(obj) != 1:
        raise CertError("%s: give exactly one of 'weights', 'species', 'all'" % where)
    allsp = species_list(t, v)
    if "all" in obj:
        if obj["all"] is not True:
            raise CertError("%s: 'all' must be true" % where)
        return set(allsp)
    if "weights" in obj:
        if v != 2:
            raise CertError("%s: 'weights' is only for v = 2; use 'species'" % where)
        w = obj["weights"]
        if not (isinstance(w, list) and len(w) == 2 and all(is_int(x) for x in w)
                and 0 <= w[0] <= w[1] <= t):
            raise CertError("%s: 'weights' must be [a, b] with 0 <= a <= b <= t" % where)
        return {(t - wt, wt) for wt in range(w[0], w[1] + 1)}
    sps = obj["species"]
    if not isinstance(sps, list):
        raise CertError("%s: 'species' must be a list of count vectors (it may be empty: an "
                        "ingredient that counts for no species)" % where)
    out = set()
    for sp in sps:
        if not (isinstance(sp, list) and len(sp) == v and all(is_int(c) and c >= 0 for c in sp)
                and sum(sp) == t):
            raise CertError("%s: species %r is not a list of %d counts summing to t = %d"
                            % (where, sp, v, t))
        if tuple(sp) in out:
            raise CertError("%s: species %r listed twice" % (where, sp))
        out.add(tuple(sp))
    return out


def parse_matrix_text(text, where):
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        toks = line.split()
        if not toks:
            continue
        row = []
        for tok in toks:
            if not INT_RE.match(tok):
                raise CertError("%s line %d: entry %r is not a nonnegative integer"
                                % (where, lineno, tok[:20]))
            row.append(int(tok))
        rows.append(row)
    return rows


def load_certificate(path):
    def no_duplicates(pairs):
        d = {}
        for key, val in pairs:
            if key in d:
                raise CertError("duplicate key %r in the certificate" % key)
            d[key] = val
        return d
    try:
        with open(path, "rb") as f:
            raw = f.read()
        cert = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (OSError, ValueError) as e:
        raise CertError("cannot read certificate %s: %s" % (path, e))
    only_keys(cert, ("format", "construction", "t", "v", "e", "field", "family", "ingredients",
                     "expected", "notes"), "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if cert.get("construction") not in CONSTRUCTIONS:
        raise CertError("construction must be one of %s" % ", ".join(CONSTRUCTIONS))
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and
                                 all(isinstance(s, str) for s in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 2, 32)
    v = need_int(cert, "v", 2, 64)
    e = need_int(cert, "e", 1, 64)
    c = {"t": t, "v": v, "e": e, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest()}

    # expected values
    exp = cert.get("expected")
    only_keys(exp, ("N", "k", "array_sha256"), "expected")
    c["exp_N"] = need_int(exp, "N", 1, None, "expected: ")
    c["exp_k"] = need_int(exp, "k", 1, None, "expected: ")
    sha = exp.get("array_sha256")
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("expected: array_sha256 must be 64 lowercase hex digits")
    c["exp_sha"] = sha

    # ingredients
    ings = cert.get("ingredients")
    if not isinstance(ings, dict) or not ings:
        raise CertError("ingredients must be a nonempty object name -> ingredient")
    c["ingredients"] = {}
    for name, ing in ings.items():
        where = "ingredient %r" % name
        if not NAME_RE.match(name):
            raise CertError("%s: bad name" % where)
        only_keys(ing, ("file", "sha256", "rows", "covers"), where)
        d = {"name": name, "covers": parse_covers(ing.get("covers"), t, v, where + " covers")}
        if "file" in ing:
            if "rows" in ing:
                raise CertError("%s: give 'file' or 'rows', not both" % where)
            fn = ing["file"]
            if not isinstance(fn, str) or not NAME_RE.match(fn) or fn.startswith("."):
                raise CertError("%s: file must be a plain file name beside the certificate"
                                % where)
            h = ing.get("sha256")
            if not isinstance(h, str) or not HEX64.match(h):
                raise CertError("%s: a file ingredient needs sha256 (64 lowercase hex)" % where)
            fp = os.path.join(c["dir"], fn)
            try:
                with open(fp, "rb") as f:
                    raw = f.read()
            except OSError as ex:
                raise CertError("%s: cannot read %s: %s" % (where, fp, ex))
            d["file"], d["sha_expected"] = fn, h
            d["sha_actual"] = hashlib.sha256(raw).hexdigest()
            try:
                text = raw.decode("ascii")
            except UnicodeDecodeError:
                raise CertError("%s: file is not ASCII text" % where)
            d["rows"] = parse_matrix_text(text, "%s (%s)" % (where, fn))
        elif "rows" in ing:
            if "sha256" in ing:
                raise CertError("%s: an inline ingredient takes no sha256" % where)
            rows = ing["rows"]
            if not isinstance(rows, list) or not all(isinstance(r, list) and
                                                     all(is_int(x) and x >= 0 for x in r)
                                                     for r in rows):
                raise CertError("%s: rows must be a list of lists of nonnegative integers"
                                % where)
            d["rows"] = [list(r) for r in rows]
        else:
            raise CertError("%s: give 'file' (with 'sha256') or 'rows'" % where)
        c["ingredients"][name] = d

    # hash family
    fam = cert.get("family")
    if not isinstance(fam, dict):
        raise CertError("family must be an object")
    ftype = fam.get("type")
    if ftype == "reed-solomon":
        only_keys(fam, ("type", "rows", "column_limit"), "family")
        if "field" not in cert:
            raise CertError("a reed-solomon family needs 'field'")
        c["field"] = parse_field(cert["field"])
        q = c["field"][2]
        if q ** e > MAX_COLUMNS:
            raise CertError("q^e = %d columns is above the limit %d" % (q ** e, MAX_COLUMNS))
        rows = fam.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CertError("family: rows must be a nonempty list")
        frows = []
        for i, r in enumerate(rows):
            where = "family row %d" % i
            only_keys(r, ("point", "forbidden", "ingredient"), where)
            pt = r.get("point")
            if pt == "inf":
                pt = q
            elif not (is_int(pt) and 0 <= pt < q):
                raise CertError("%s: point must be a field element 0..%d or \"inf\"" % (where, q - 1))
            fb = r.get("forbidden", [])
            if not (isinstance(fb, list) and all(is_int(x) and 0 <= x < q for x in fb)):
                raise CertError("%s: forbidden must be a list of field elements" % where)
            if len(set(fb)) != len(fb):
                raise CertError("%s: forbidden lists a value twice" % where)
            if len(fb) >= q:
                raise CertError("%s: every value is forbidden" % where)
            frows.append({"point": pt, "forbidden": sorted(fb), "ingredient": r.get("ingredient")})
        c["family"] = {"type": ftype, "rows": frows}
        if "column_limit" in fam:
            c["family"]["column_limit"] = need_int(fam, "column_limit", 1, None, "family: ")
    elif ftype == "explicit":
        only_keys(fam, ("type", "rows"), "family")
        if "field" in cert:
            raise CertError("an explicit family takes no 'field'")
        rows = fam.get("rows")
        if not isinstance(rows, list) or not rows:
            raise CertError("family: rows must be a nonempty list")
        frows = []
        k = None
        for i, r in enumerate(rows):
            where = "family row %d" % i
            only_keys(r, ("width", "values", "ingredient"), where)
            w = need_int(r, "width", 1, None, where + ": ")
            vals = r.get("values")
            if not (isinstance(vals, list) and all(is_int(x) and 0 <= x < w for x in vals)):
                raise CertError("%s: values must be a list of symbols 0..width-1" % where)
            if k is None:
                k = len(vals)
            elif len(vals) != k:
                raise CertError("%s: %d values where row 0 has %d" % (where, len(vals), k))
            frows.append({"width": w, "values": list(vals), "ingredient": r.get("ingredient")})
        c["family"] = {"type": ftype, "rows": frows}
    else:
        raise CertError("family type must be 'reed-solomon' or 'explicit'")
    for i, r in enumerate(c["family"]["rows"]):
        if r["ingredient"] not in c["ingredients"]:
            raise CertError("family row %d: ingredient %r is not defined" % (i, r["ingredient"]))
    unused = set(c["ingredients"]) - {r["ingredient"] for r in c["family"]["rows"]}
    if unused:
        raise CertError("ingredient(s) defined but not assigned to any row: %s"
                        % ", ".join(sorted(unused)))
    return c


# ---------------------------------------------------------------------------
# hash family generation
# ---------------------------------------------------------------------------

def build_family(c):
    """sets c['H'] (M lists of k symbols, row i over 0..w_i-1) and c['widths']"""
    fam = c["family"]
    if fam["type"] == "explicit":
        c["H"] = [r["values"] for r in fam["rows"]]
        c["widths"] = [r["width"] for r in fam["rows"]]
        return
    p, m, q, modulus = c["field"]
    F = Field(p, m, modulus)
    c["F"] = F
    e = c["e"]
    add, mul = F.add, F.mul
    # columns: coefficient tuples (c_0, ..., c_{e-1}) of the polynomial c_0 + c_1 x + ... in
    # lexicographic order (c_0 most significant), as itertools.product(range(q), repeat=e)
    raw = []
    for r in fam["rows"]:
        x = r["point"]
        vals = []
        for coeffs in itertools.product(range(q), repeat=e):
            if x == q:                      # the point at infinity: the coefficient of x^(e-1)
                vals.append(coeffs[e - 1])
                continue
            acc = 0
            for cj in reversed(coeffs):     # Horner
                acc = add[mul[acc][x]][cj]
            vals.append(acc)
        raw.append(vals)
    ncols = q ** e
    keep = [j for j in range(ncols)
            if all(raw[i][j] not in fam["rows"][i]["forbidden"] for i in range(len(raw)))]
    lim = fam.get("column_limit")
    if lim is not None:
        if lim > len(keep):         # reported by check_shape
            c["column_limit_short"] = (lim, len(keep))
        keep = keep[:lim]
    H, widths = [], []
    for i, r in enumerate(fam["rows"]):
        allowed = [s for s in range(q) if s not in r["forbidden"]]
        relabel = {s: n for n, s in enumerate(allowed)}
        H.append([relabel[raw[i][j]] for j in keep])
        widths.append(len(allowed))
    c["H"], c["widths"] = H, widths


# ---------------------------------------------------------------------------
# the checks: each takes the context and returns a list of failure messages
# ---------------------------------------------------------------------------

def check_field(c):
    """sanity of the field description (soundness does not depend on it: the agreement check
    below tests the generated family itself); p prime, no zero divisors, ring axioms"""
    if "F" not in c:
        return []
    F = c["F"]
    p, q = F.p, F.q
    out = []
    if not is_prime(p):
        return ["p = %d is not prime" % p]
    for a in range(1, q):
        row = F.mul[a]
        if 0 in row[1:] or len(set(row)) != q:
            return ["GF(%d) with modulus %r is not a field: %d has no inverse (the modulus is "
                    "reducible)" % (q, F.modulus, a)]
    add, mul = F.add, F.mul
    if q <= 64:
        for a in range(q):
            for b in range(q):
                if add[a][b] != add[b][a] or mul[a][b] != mul[b][a]:
                    return ["GF(%d): commutativity fails at %d, %d" % (q, a, b)]
                for d in range(q):
                    if mul[a][add[b][d]] != add[mul[a][b]][mul[a][d]]:
                        return ["GF(%d): distributivity fails at %d, %d, %d" % (q, a, b, d)]
                    if mul[mul[a][b]][d] != mul[a][mul[b][d]]:
                        return ["GF(%d): associativity fails at %d, %d, %d" % (q, a, b, d)]
    return out


def check_shape(c):
    """k >= t; every ingredient a nonempty rectangular array over 0..v-1 whose number of
    columns equals the width of every row it is assigned to"""
    out = []
    k = len(c["H"][0])
    if "column_limit_short" in c:
        out.append("family: column_limit %d exceeds the %d columns kept"
                   % c["column_limit_short"])
    if k < c["t"]:
        out.append("the hash family has k = %d columns, fewer than t = %d" % (k, c["t"]))
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        if not rows:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        bad = [i for i, r in enumerate(rows) if len(r) != w]
        if bad:
            out.append("ingredient %s is ragged (row %d has %d entries, row 0 has %d)"
                       % (name, bad[0], len(rows[bad[0]]), w))
            continue
        big = [(i, j) for i, r in enumerate(rows) for j, x in enumerate(r) if x >= c["v"]]
        if big:
            i, j = big[0]
            out.append("ingredient %s: entry %d at row %d column %d is not a symbol 0..%d"
                       % (name, rows[i][j], i, j, c["v"] - 1))
        for i, r in enumerate(c["family"]["rows"]):
            if r["ingredient"] == name and c["widths"][i] != w:
                out.append("ingredient %s has %d columns but family row %d has width %d"
                           % (name, w, i, c["widths"][i]))
    return out


def check_width(c):
    """every row of the hash family has width >= t (a quilting array on fewer than t columns
    covers nothing and its declared species would count vacuously)"""
    return ["family row %d has width %d < t = %d" % (i, w, c["t"])
            for i, w in enumerate(c["widths"]) if w < c["t"]]


def check_ingredient_hash(c):
    out = []
    for name, ing in c["ingredients"].items():
        if "file" in ing and ing["sha_actual"] != ing["sha_expected"]:
            out.append("ingredient %s: file %s has sha256 %s, the certificate records %s"
                       % (name, ing["file"], ing["sha_actual"], ing["sha_expected"]))
    return out


def agreement_by_subsets(H, e):
    """two distinct columns agree in >= e rows iff they agree on some e-subset of rows, iff
    that subset maps them to the same tuple; returns (column, column, rows) or None"""
    M, k = len(H), len(H[0])
    for sub in itertools.combinations(range(M), e):
        seen = {}
        rows = [H[i] for i in sub]
        for j in range(k):
            key = tuple(r[j] for r in rows)
            if key in seen:
                return seen[key], j, list(sub)
            seen[key] = j
    return None


def agreement_by_pairs(H, e):
    """direct count over all pairs of columns; returns (column, column, rows) or None"""
    M, k = len(H), len(H[0])
    cols = [tuple(H[i][j] for i in range(M)) for j in range(k)]
    for a in range(k):
        ca = cols[a]
        for b in range(a + 1, k):
            cb = cols[b]
            n = 0
            for i in range(M):
                if ca[i] == cb[i]:
                    n += 1
            if n >= e:
                return a, b, [i for i in range(M) if ca[i] == cb[i]]
    return None


def check_agreement(c):
    """any two distinct columns agree in at most e-1 rows (exact; the cheaper of two exact
    methods is used)"""
    H, e = c["H"], c["e"]
    M, k = len(H), len(H[0])
    if comb(M, e) * k * e <= k * k * M // 2:
        bad = agreement_by_subsets(H, e)
    else:
        bad = agreement_by_pairs(H, e)
    if bad:
        a, b, rows = bad
        return ["columns %d and %d agree in rows %s, at least e = %d rows; the bound is "
                "e-1 = %d" % (a, b, rows, e, e - 1)]
    return []


def check_quilting(c):
    """each ingredient covers every tuple of every declared species on every t-set of columns"""
    t, v = c["t"], c["v"]
    out = []
    arr_cache = {}
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        if not rows:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        if any(len(r) != w for r in rows):
            out.append("ingredient %s is ragged; its quilting property cannot hold" % name)
            continue
        need = []
        for sp in sorted(ing["covers"]):
            if sp not in arr_cache:
                arr_cache[sp] = arrangements(sp, v)
            need.append((sp, arr_cache[sp]))
        missing = 0
        first = None
        for cols in itertools.combinations(range(w), t):
            present = set(tuple(r[j] for j in cols) for r in rows)
            for sp, arrs in need:
                for tup in arrs:
                    if tup not in present:
                        missing += 1
                        if first is None:
                            first = (cols, tup, sp)
        if missing:
            cols, tup, sp = first
            out.append("ingredient %s does not cover its declared species: %d (t-set, tuple) "
                       "pairs missing, first columns %s tuple %s (%s)"
                       % (name, missing, list(cols), list(tup), fmt_species(sp, v)))
    return out


def check_species(c):
    """every species S is declared in more than (e-1) * tau(S) rows"""
    t, v, e = c["t"], c["v"], c["e"]
    out = []
    table = []
    decl = [c["ingredients"][r["ingredient"]]["covers"] for r in c["family"]["rows"]]
    for sp in species_list(t, v):
        n = sum(1 for d in decl if sp in d)
        need = (e - 1) * tau(sp) + 1
        table.append((sp, tau(sp), need, n))
        if n < need:
            out.append("%s (tau = %d) is declared in %d rows; Lemma 2.3 needs more than "
                       "(e-1)*tau = %d, i.e. at least %d" % (fmt_species(sp, v), tau(sp), n,
                                                             (e - 1) * tau(sp), need))
    c["species_table"] = table
    return out


# assembly-dependent checks (run after the array is built)

def check_symbols(c):
    """the table's parser keeps an array 0-based only if symbol 0 occurs"""
    if 0 not in c["symbols"]:
        return ["the assembled array never uses symbol 0, so the table's canonicalization "
                "(check_submission.parse_array) would not read it as 0-based"]
    return []


def check_N(c):
    if c["N"] != c["exp_N"]:
        return ["the array has N = %d rows, the certificate claims %d" % (c["N"], c["exp_N"])]
    return []


def check_k(c):
    if c["k"] != c["exp_k"]:
        return ["the array has k = %d columns, the certificate claims %d" % (c["k"], c["exp_k"])]
    return []


def check_sha(c):
    if c["sha256"] != c["exp_sha"]:
        return ["the rebuilt array has canonical sha256 %s, the certificate claims %s"
                % (c["sha256"], c["exp_sha"])]
    return []


# order matters only for reporting; every check runs (those after the assembly only if the
# array could be built)
CHECKS = [("field", check_field), ("shape", check_shape), ("width", check_width),
          ("ingredient_hash", check_ingredient_hash), ("agreement", check_agreement),
          ("quilting", check_quilting), ("species", check_species)]
POST_CHECKS = [("symbols", check_symbols), ("N", check_N), ("k", check_k), ("sha256", check_sha)]


# ---------------------------------------------------------------------------
# assembly in the table's canonical text
# ---------------------------------------------------------------------------

def assemble(c, write=None):
    """stack block i = ingredient(i)[:, H[i]] for i = 0..M-1; hash the canonical text
    (one run per line, single spaces, '\\n' after every line, symbols 0-based)"""
    h = hashlib.sha256()
    fout = open(write, "w", encoding="ascii", newline="\n") if write else None
    N = 0
    symbols = set()
    try:
        for i, r in enumerate(c["family"]["rows"]):
            Q = c["ingredients"][r["ingredient"]]["rows"]
            Hi = c["H"][i]
            used = sorted(set(Hi))
            for qrow in Q:
                strs = [str(x) for x in qrow]
                line = " ".join([strs[s] for s in Hi]) + "\n"
                symbols.update(qrow[s] for s in used)
                h.update(line.encode("ascii"))
                if fout:
                    fout.write(line)
                N += 1
    finally:
        if fout:
            fout.close()
    c["N"], c["k"], c["sha256"], c["symbols"] = N, len(c["H"][0]), h.hexdigest(), symbols


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

def run(path, write=None, log=None):
    """check the certificate at path; returns a dict with ok, failures [(check, message)],
    passed [check], N, k, sha256, species_table, seconds. Raises CertError when malformed."""
    t0 = time.time()
    say = log or (lambda s: None)
    c = load_certificate(path)
    build_family(c)
    say("certificate %s: %s, t = %d, v = %d, e = %d, M = %d rows, k = %d columns"
        % (path, c["family"]["type"], c["t"], c["v"], c["e"], len(c["H"]), len(c["H"][0])))
    failures, passed = [], []
    for name, fn in CHECKS:
        try:
            msgs = fn(c)
        except Exception as ex:          # a check that cannot complete is a failure
            msgs = ["the check could not complete: %r" % (ex,)]
        if msgs:
            failures += [(name, m) for m in msgs]
            for m in msgs:
                say("FAIL [%s] %s" % (name, m))
        else:
            passed.append(name)
            say("pass [%s]" % name)
    built = False
    try:
        assemble(c, write)
        built = True
    except Exception as ex:
        failures.append(("assembly", "the array cannot be assembled: %r" % (ex,)))
        say("FAIL [assembly] %r" % (ex,))
    if built:
        for name, fn in POST_CHECKS:
            try:
                msgs = fn(c)
            except Exception as ex:
                msgs = ["the check could not complete: %r" % (ex,)]
            if msgs:
                failures += [(name, m) for m in msgs]
                for m in msgs:
                    say("FAIL [%s] %s" % (name, m))
            else:
                passed.append(name)
                say("pass [%s]" % name)
    return {"ok": built and not failures, "failures": failures, "passed": passed,
            "cert_sha256": c["cert_sha256"],
            "N": c.get("N"), "k": c.get("k"), "sha256": c.get("sha256"), "t": c["t"],
            "v": c["v"], "species_table": c.get("species_table"),
            "seconds": time.time() - t0}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    write, quiet = None, False
    if "--write" in argv:
        i = argv.index("--write")
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        write = argv[i + 1]
        del argv[i:i + 2]
    if "--quiet" in argv:
        argv.remove("--quiet")
        quiet = True
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__)
        return 2
    log = None if quiet else print
    try:
        res = run(argv[0], write, log)
    except CertError as ex:
        print("MALFORMED: %s" % ex)
        return 2
    if not quiet and res["species_table"]:
        print("species table (species, tau, rows needed, rows declared):")
        for sp, ta, need, n in res["species_table"]:
            print("  %-14s tau %2d  need >= %2d  have %2d" % (fmt_species(sp, res["v"]), ta, need, n))
    print("certificate sha256 = %s" % res["cert_sha256"])
    if res["sha256"]:
        print("N = %s  k = %s  t = %d  v = %d  sha256 = %s"
              % (res["N"], res["k"], res["t"], res["v"], res["sha256"]))
    print("%s (%.2f s)" % ("CERTIFICATE VALID" if res["ok"] else
                           "CERTIFICATE REJECTED: %d failure(s) in %s"
                           % (len(res["failures"]),
                              ", ".join(sorted({f[0] for f in res["failures"]}))),
                           res["seconds"]))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
