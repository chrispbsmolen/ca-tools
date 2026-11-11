#!/usr/bin/env python3
"""construction_cert - check a construction certificate and rebuild the array it proves.

A construction certificate records the recipe of a covering array instead of the array. Nine
constructions are known (tools/CONSTRUCTION_CERT.md states each theorem, its hypotheses and the
proof the checker follows):

  powercz-1  Colbourn and Zhou 2012, Theorem 2.2 with Lemma 2.3 (below)
  powercz-2  powercz-1 for v = 2 with a column relabelling per block, and the constant tuples (weights
             0 and t) proved by exact enumeration instead of being declared by a block (e = 2); the
             heavy parts run in the C helper tools/cz2help.c, compiled at run time with cc
  fuse-1     Colbourn, Keri, Rivas Soriano and Schlage-Puchta 2010, Lemma 3.1: a CA(N; t, k, v+1)
             gives a CA(N-2; t, k, v), t >= 2, by the two-row fusing of tools/cphf/fuse2.c
  derive-1   the derived array: the rows of a CA(N; t+1, k+1, v) with symbol s in column c,
             column c deleted, form a CA(N_s; t, k, v)
  product-1  the direct product of a CA(N1; 2, k1, v) and a CA(N2; 2, k2, v): a CA(N1+N2-d; 2,
             k1 k2, v), d the rows of the second part that repeat a row of the first (constant rows)
  sms51-1    Shokri, Moura and Stevens (arXiv:2510.13122v3), Theorem 5.1: three truncated Moebius
             planes of an ovoid of PG(3, q), q an odd prime power, give a CA(3q^4 - 2; 4, (q^2+1)/2, q);
             the anti-cocircularity (their Theorem 4.25) is checked exactly by enumerating circles
  sms65-1    the same authors, Theorem 6.2 with the ingredient size of Corollary 6.5: a
             CA(3q^4 + (q-2)N; 4, q^2+1, q) from a CA(N; 3, (q^2+1)/2, q), the ingredient built here
             from a pair of orthogoval planes and checked exactly, or an array ingredient
  sm-xplication-1
             Shokri and Moura (J. Combin. Des. 33 (2025) 156-171; thesis of K. Shokri, Chapter 5), the
             general theorem 5.2.6 with the redundant rows of the last block removed: x copies of the
             CA(2q^3 - 1; 3, q^2+q+1, q) of a primitive cubic and its inverse, shifted by a difference
             covering array, P blocks, and a last block; the 2-, q-, q^2- and (q^2-q+1)-plications
  product-ctj-1
             Colbourn and Torres-Jimenez 2013, Corollary 4.3: the direct product of a CA(N1; 2, k1, v)
             and a CA(N2; 2, k2, v) with a set S of rows of the first and a set T of rows of the
             second made constant with |S| + |T| <= v distinct symbols, those rows left out: a
             CA(N1 + N2 - |S| - |T|; 2, k1 k2, v); an ingredient may itself be such a product

An ingredient is given inline ("rows"), as a file beside the certificate ("file" and its "sha256"),
both checked exhaustively here, or by the array_sha256 of a counted VERIFIED row of the table
("table"; the array is read from table/arrays, its canonical hash checked, and its coverage
trusted as verified by the table). For "powercz-1" (Colbourn and Zhou 2012, Theorem 2.2 with
Lemma 2.3) the certificate is a hash family with M rows and k columns, one quilting array
(ingredient) per row, and the species classes each ingredient is claimed to cover. This program

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
tools/CONSTRUCTION_CERT.md. Standard library only (powercz-2 also compiles tools/cz2help.c with cc
when it is available, and otherwise does its exact work in Python up to a limit, failing above it).

Usage:
  construction_cert.py CERT.json [--write ARRAY.txt] [--quiet] [--table-dir DIR]
--table-dir (default: the table/ of this repository) is where "table" ingredients are found.
Exit status: 0 certificate valid, 1 a check failed, 2 malformed certificate or usage error.
"""
import csv
import gzip
import hashlib
import itertools
import json
import os
import re
import sys
import time

FORMAT = "construction-cert-1"
CONSTRUCTIONS = ("powercz-1", "powercz-2", "fuse-1", "derive-1", "product-1", "sms51-1", "sms65-1",
                 "sm-xplication-1", "product-ctj-1")
ARRAY_KINDS = ("fuse-1", "derive-1", "product-1")
SMS_KINDS = ("sms51-1", "sms65-1")
# the reference id (table/references.csv) of the theorem of each construction, for builds_on
# (derive-1 has none: deriving a strength t-1 array is folklore with no single source in
# references.csv, so the submitter's builds_on is kept as given and nothing is added)
REFERENCE = {"powercz-1": "power-cz2012", "powercz-2": "power-cz2012", "fuse-1": "fuse-ckrs2010",
             "derive-1": None, "product-1": "product-cmmssy2006", "sms51-1": "mobius-sms2025",
             "sms65-1": "mobius-sms2025", "sm-xplication-1": "lfsr-sm2025", "product-ctj-1": "pca-ct2013"}
REPO_TABLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "table")
# the exhaustive check of an inline or file ingredient here costs about C(k, t) * N entry reads in
# Python; above this an ingredient must be entered in the table first and named by its hash
INGREDIENT_WORK = 3 * 10 ** 8
# powercz-2: the C helper (compiled at run time; its source must have this sha256, so the tool hash
# of this file in a row's stamp also fixes the helper) and its work limit, in 64-bit word operations
HELPER_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cz2help.c")
HELPER_SHA256 = "17a22a3d3e604e8d862860f8656877c21f53d73294cb9451647561dae6137b56"
HELPER_WORK = 10 ** 11
HELPER_LIST = 10 ** 7       # the most bad t-sets of one block the helper lists for the enumeration
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


def load_certificate(path, table_dir=None):
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
    if isinstance(cert, dict) and cert.get("construction") in ARRAY_KINDS:
        return load_array_kind(cert, raw, path, table_dir)
    if isinstance(cert, dict) and cert.get("construction") in SMS_KINDS:
        return load_sms(cert, raw, path, table_dir)
    if isinstance(cert, dict) and cert.get("construction") == SMX_KIND:
        return load_smx(cert, raw, path, table_dir)
    if isinstance(cert, dict) and cert.get("construction") == CTJ_KIND:
        return load_ctj(cert, raw, path, table_dir)
    cz2 = isinstance(cert, dict) and cert.get("construction") == "powercz-2"
    only_keys(cert, ("format", "construction", "t", "v", "e", "field", "family", "ingredients",
                     "expected", "notes") + (("enumerate_weights",) if cz2 else ()), "certificate")
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
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "kind": cert["construction"]}
    if cz2:
        parse_powercz2(cert, c)

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
        only_keys(ing, ("file", "sha256", "rows", "covers", "table"), where)
        d = {"name": name, "covers": parse_covers(ing.get("covers"), t, v, where + " covers")}
        if "table" in ing:
            if "file" in ing or "rows" in ing or "sha256" in ing:
                raise CertError("%s: give 'table' alone (no 'file', 'rows' or 'sha256')" % where)
            d.update(resolve_table(ing["table"], table_dir, where))
            d["need_t"], d["need_v"] = t, v
        elif "file" in ing:
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
            only_keys(r, ("point", "forbidden", "ingredient") + (("relabel",) if cz2 else ()), where)
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
            if cz2:
                frows[-1]["relabel"] = parse_relabel(r, where)
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
            only_keys(r, ("width", "values", "ingredient") + (("relabel",) if cz2 else ()), where)
            w = need_int(r, "width", 1, None, where + ": ")
            vals = r.get("values")
            if not (isinstance(vals, list) and all(is_int(x) and 0 <= x < w for x in vals)):
                raise CertError("%s: values must be a list of symbols 0..width-1" % where)
            if k is None:
                k = len(vals)
            elif len(vals) != k:
                raise CertError("%s: %d values where row 0 has %d" % (where, len(vals), k))
            frows.append({"width": w, "values": list(vals), "ingredient": r.get("ingredient")})
            if cz2:
                frows[-1]["relabel"] = parse_relabel(r, where)
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
        if "table" in ing:
            continue        # a covering array of strength >= t of the table covers every species
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


# ---------------------------------------------------------------------------
# powercz-2: relabelled blocks and constant tuples by enumeration (tools/CONSTRUCTION_CERT.md,
# "Power CZ with relabelled blocks (powercz-2)")
# ---------------------------------------------------------------------------

def parse_powercz2(cert, c):
    """the keys of powercz-2 beyond those of powercz-1: v = 2, t <= 7, enumerate_weights"""
    t, v, e = c["t"], c["v"], c["e"]
    if v != 2:
        raise CertError("powercz-2 is for v = 2 (v = %d)" % v)
    if t > 7:
        raise CertError("powercz-2 is for t <= 7 (t = %d)" % t)
    ew = cert.get("enumerate_weights", [])
    if not (isinstance(ew, list) and all(is_int(x) for x in ew)):
        raise CertError("enumerate_weights must be a list of weights")
    if len(set(ew)) != len(ew):
        raise CertError("enumerate_weights lists a weight twice")
    if any(x not in (0, t) for x in ew):
        raise CertError("enumerate_weights may list only the weights 0 and t = %d (the species with tau = 0, "
                        "the constant tuples), not %s" % (t, [x for x in ew if x not in (0, t)]))
    if ew and e != 2:
        raise CertError("the enumeration of enumerate_weights is implemented for e = 2 only (two blocks "
                        "determine a column only when two columns agree in at most one row); e = %d" % e)
    c["enumerate_weights"] = sorted(ew)


def parse_relabel(r, where):
    """a family row's relabel: a list of ingredient columns (a permutation, checked by 'relabel'), or None"""
    if "relabel" not in r:
        return None
    pi = r["relabel"]
    if not (isinstance(pi, list) and all(is_int(x) for x in pi)):
        raise CertError("%s: relabel must be a list of integers (ingredient columns)" % where)
    return list(pi)


def apply_relabel(c):
    """H[i][col] := pi_i[H[i][col]]: the value of row i (0..w_i-1) selects ingredient column pi_i of that
    value. A relabel that is not a permutation of 0..w_i-1 is reported by check_relabel and not applied."""
    c["relabel_failures"] = []
    c["relabelled_rows"] = 0
    for i, r in enumerate(c["family"]["rows"]):
        pi = r.get("relabel")
        if pi is None:
            continue
        w = c["widths"][i]
        if sorted(pi) != list(range(w)):
            dup = sorted({x for x in pi if pi.count(x) > 1})[:3] if len(pi) <= 4096 else []
            out = [x for x in pi if not 0 <= x < w][:3]
            c["relabel_failures"].append(
                "family row %d: relabel is not a permutation of the %d ingredient columns 0..%d (%d entries%s%s)"
                % (i, w, w - 1, len(pi), ", repeated %s" % dup if dup else "",
                   ", outside the range %s" % out if out else ""))
            continue
        c["H"][i] = [pi[x] for x in c["H"][i]]
        c["relabelled_rows"] += 1


def check_relabel(c):
    """powercz-2: every relabel is a permutation of the columns of the row's ingredient (0..w_i-1)"""
    return list(c["relabel_failures"])


class Helper:
    """tools/cz2help.c, compiled once per process into a temporary folder with cc; None (with the
    reason) when there is no compiler, the build fails, or the source is not the recorded one"""
    path = None
    why = None
    tried = False
    disabled = bool(os.environ.get("CONSTRUCTION_CERT_NO_HELPER"))

    @classmethod
    def get(cls):
        if cls.disabled:
            cls.why = "the C helper is disabled"
            return None
        if cls.tried:
            return cls.path
        cls.tried = True
        import atexit
        import shutil
        import subprocess
        import tempfile
        try:
            with open(HELPER_SRC, "rb") as f:
                src = f.read()
        except OSError as ex:
            cls.why = "cannot read %s: %s" % (HELPER_SRC, ex)
            return None
        h = hashlib.sha256(src).hexdigest()
        if h != HELPER_SHA256:
            cls.why = "tools/cz2help.c has sha256 %s, construction_cert.py records %s" % (h, HELPER_SHA256)
            return None
        cc_exe = shutil.which("cc") or shutil.which("gcc")
        if not cc_exe:
            cls.why = "no C compiler (cc)"
            return None
        d = tempfile.mkdtemp(prefix="cz2help-")
        atexit.register(shutil.rmtree, d, True)
        exe = os.path.join(d, "cz2help")
        try:
            p = subprocess.run([cc_exe, "-O3", "-o", exe, HELPER_SRC], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, universal_newlines=True)
        except OSError as ex:
            cls.why = "cc failed: %s" % ex
            return None
        if p.returncode != 0 or not os.access(exe, os.X_OK):
            cls.why = "cc could not build tools/cz2help.c: %s" % p.stderr[:300]
            return None
        cls.path = exe
        return exe

    @classmethod
    def run(cls, args):
        import subprocess
        p = subprocess.run([cls.path] + [str(a) for a in args], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode != 0:
            raise RuntimeError("cz2help %s failed (exit %d): %s" % (args[0], p.returncode, p.stderr.strip()[:300]))
        return p.stdout


def cz2_tmpdir(c):
    """a temporary folder for the helper's input files, removed at the end of run()"""
    if "cz2_tmp" not in c:
        import tempfile
        c["cz2_tmp"] = tempfile.mkdtemp(prefix="cz2-")
    return c["cz2_tmp"]


def cz2_file(c, name):
    """the ingredient as a text file for the helper, written from the rows read (0/1, single spaces)"""
    files = c.setdefault("cz2_files", {})
    if name not in files:
        p = os.path.join(cz2_tmpdir(c), "ing%d.txt" % len(files))
        with open(p, "w", encoding="ascii", newline="\n") as f:
            for r in c["ingredients"][name]["rows"]:
                f.write(" ".join(map(str, r)) + "\n")
        files[name] = p
    return files[name]


def words(n):
    return (n + 63) // 64


def py_quilt_missing(rows, t, weights):
    """pure Python, exact: the number of (t-set, tuple) pairs with the tuple's weight in `weights` that no
    row shows, and the first such t-set with the first such weight (tuples in itertools.product order,
    as the helper)"""
    w = len(rows[0])
    tuples = [tp for tp in itertools.product((0, 1), repeat=t) if sum(tp) in weights]
    cols = [tuple(r[j] for r in rows) for j in range(w)]
    missing, first = 0, None
    for cs in itertools.combinations(range(w), t):
        present = set(zip(*[cols[j] for j in cs]))
        for tp in tuples:
            if tp not in present:
                missing += 1
                if first is None:
                    first = (list(cs), sum(tp))
    return missing, first


def zmasks(rows, z):
    """column j -> the rows equal to z, as a Python int bit set"""
    w = len(rows[0])
    out = [0] * w
    for i, r in enumerate(rows):
        b = 1 << i
        for j in range(w):
            if r[j] == z:
                out[j] |= b
    return out


def py_bad(rows, t, z, listing=False):
    """pure Python, exact: {s: number of s-sets of columns with no row constant z} for s = 1..t, stopping
    after the first s < t with a positive count; with listing, also the bad t-sets (lexicographic)"""
    zm = zmasks(rows, z)
    w = len(rows[0])
    counts, lst = {}, []
    for s in range(1, t + 1):
        n = 0
        for cs in itertools.combinations(range(w), s):
            x = -1
            for j in cs:
                x &= zm[j]
            if not x:
                n += 1
                if listing and s == t:
                    lst.append(cs)
        counts[s] = n
        if s < t and n:
            break
    return counts, lst


def py_enumerate(c, z, a, b, bad_a, bad_b):
    """pure Python, exact (e = 2): (candidates, survivors, first survivors), as the helper's enum"""
    t, H = c["t"], c["H"]
    M, k = len(H), len(H[0])
    pair = {}
    for col in range(k):
        key = (H[a][col], H[b][col])
        if key in pair:
            raise RuntimeError("columns %d and %d agree in rows %d and %d" % (pair[key], col, a, b))
        pair[key] = col
    others = [r for r in range(M) if r not in (a, b)]
    zm = {}
    for r in others:
        name = c["family"]["rows"][r]["ingredient"]
        if name not in zm:
            zm[name] = zmasks(c["ingredients"][name]["rows"], z)
    test = [(H[r], zm[c["family"]["rows"][r]["ingredient"]]) for r in others]
    perms = list(itertools.permutations(range(t)))
    cand, surv, shown = 0, 0, []
    for Xa in bad_a:
        for Xb in bad_b:
            for pm in perms:
                cols = []
                for j in range(t):
                    col = pair.get((Xa[j], Xb[pm[j]]))
                    if col is None:
                        break
                    cols.append(col)
                else:
                    cand += 1
                    alive = True
                    for Hr, zr in test:
                        x = -1
                        for col in cols:
                            x &= zr[Hr[col]]
                        if x:
                            alive = False
                            break
                    if alive:
                        surv += 1
                        if len(shown) < 5:
                            shown.append(sorted(cols))
    return cand, surv, shown


def cz2_note(c):
    return " (%s)" % Helper.why if Helper.get() is None and Helper.why else ""


def check_quilting2(c):
    """powercz-2: as check_quilting (every tuple of every declared weight on every t-set of columns of
    every ingredient), exact, by the C helper or, up to INGREDIENT_WORK, in Python"""
    t = c["t"]
    out = []
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue        # a covering array of strength >= t of the table covers every species
        rows = ing["rows"]
        if not rows or not rows[0]:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        if any(len(r) != w for r in rows) or any(x not in (0, 1) for r in rows for x in r):
            out.append("ingredient %s is ragged or not binary; its quilting property cannot hold" % name)
            continue
        wts = sorted(sp[1] for sp in ing["covers"])
        if not wts or w < t:
            continue        # nothing declared (or no t-set: the width check reports it)
        exe = Helper.get()
        if exe and comb(w, t) * (2 ** t) * words(len(rows)) <= HELPER_WORK:
            res = Helper.run(["quilt", cz2_file(c, name), t, sum(1 << x for x in wts)]).split()
            miss = int(res[2])
            first = (list(map(int, res[4:4 + t])), int(res[5 + t])) if miss else None
        elif comb(w, t) * len(rows) * t <= INGREDIENT_WORK:
            miss, first = py_quilt_missing(rows, t, set(wts))
        else:
            out.append("ingredient %s: the quilting check (C(%d, %d) column sets of %d rows) is above the limit of "
                       "this checker%s" % (name, w, t, len(rows), cz2_note(c)))
            continue
        if miss:
            out.append("ingredient %s does not cover its declared weights %s: %d (t-set, tuple) pairs missing, "
                       "first columns %s (weight %d)" % (name, wts, miss, first[0], first[1]))
    return out


def check_species2(c):
    """powercz-2: every species (weight) is declared in more than (e-1) tau rows (Lemma 2.3), or is a
    constant tuple listed in enumerate_weights (proved by check_enumeration)"""
    t, v, e = c["t"], c["v"], c["e"]
    out, table = [], []
    decl = [c["ingredients"][r["ingredient"]]["covers"] for r in c["family"]["rows"]]
    for sp in species_list(t, v):
        n = sum(1 for d in decl if sp in d)
        need = (e - 1) * tau(sp) + 1
        table.append((sp, tau(sp), need, n))
        if sp[1] in c["enumerate_weights"]:
            continue
        if n < need:
            out.append("%s (tau = %d) is declared in %d rows; Lemma 2.3 needs more than (e-1)*tau = %d, i.e. at "
                       "least %d%s" % (fmt_species(sp, v), tau(sp), n, (e - 1) * tau(sp), need,
                                       " (or list it in enumerate_weights)" if tau(sp) == 0 else ""))
    c["species_table"] = table
    return out


def check_enumeration(c):
    """powercz-2: every weight of enumerate_weights (the tuple z^t, z = 0 for weight 0 and 1 for weight
    t) is shown on every t-set of array columns, by exact enumeration (tools/CONSTRUCTION_CERT.md):
      1. no ingredient has an s-set of columns, s < t, with no row constant z ("bad"), so a t-set of
         array columns whose image in some block has fewer than t columns is covered there;
      2. the bad t-sets of two blocks a and b, every bijection between them, the array columns found
         by their pair of values in rows a and b (unique, e = 2), and the other blocks tested directly;
         a t-set left over (a survivor) misses z^t, and there must be none."""
    out = []
    c["enumeration"] = {}
    ew = c["enumerate_weights"]
    if not ew:
        return out
    t, H = c["t"], c["H"]
    M = len(H)
    rows_of = [r["ingredient"] for r in c["family"]["rows"]]
    if M < 2:
        return ["the enumeration needs at least two rows in the hash family"]
    for name in set(rows_of):
        rws = c["ingredients"][name]["rows"]
        if not rws or not rws[0] or any(len(r) != len(rws[0]) for r in rws) or \
                any(x not in (0, 1) for r in rws for x in r):
            return ["ingredient %s is ragged or not binary; nothing can be enumerated" % name]
    for wt in ew:
        z = 0 if wt == 0 else 1
        rep = c["enumeration"].setdefault(wt, {"z": z})
        # 1. bad sets of every ingredient
        counts, too_big = {}, False
        for name in sorted(set(rows_of)):
            rws = c["ingredients"][name]["rows"]
            w = len(rws[0])
            exe = Helper.get()
            if exe and comb(w, t) * words(len(rws)) * t <= HELPER_WORK:
                cn = {}
                for line in Helper.run(["bad", cz2_file(c, name), t, z]).splitlines():
                    f = line.split()
                    cn[int(f[1])] = int(f[2])
            elif comb(w, t) * len(rws) * t <= INGREDIENT_WORK:
                cn = py_bad(rws, t, z)[0]
            else:
                out.append("weight %d: listing the bad %d-sets of ingredient %s (C(%d, %d) sets) is above the limit "
                           "of this checker%s" % (wt, t, name, w, t, cz2_note(c)))
                too_big = True
                continue
            counts[name] = cn
            small = [s for s in range(1, t) if cn.get(s, 0) > 0]
            if small:
                out.append("weight %d: ingredient %s has %d %d-sets of columns with no row constant %d, so a t-set of "
                           "array columns whose image there has %d columns can miss the tuple; the enumeration needs "
                           "none below t" % (wt, name, cn[small[0]], small[0], z, small[0]))
        rep["bad"] = {name: [cn.get(s) for s in range(1, t + 1)] for name, cn in counts.items()}
        if too_big or len(counts) < len(set(rows_of)) or any(cn.get(s, 0) for cn in counts.values()
                                                             for s in range(1, t)):
            continue
        # 2. the two blocks with the fewest pairs of bad t-sets, and the enumeration
        nbad = [counts[n][t] for n in rows_of]
        a, b = min(itertools.combinations(range(M), 2), key=lambda p: (nbad[p[0]] * nbad[p[1]], p))
        rep["blocks"] = [a, b]
        work = nbad[a] * nbad[b] * math_factorial(t)
        rep["cases"] = work
        exe = Helper.get()
        maxw = max(words(len(c["ingredients"][n]["rows"])) for n in rows_of)
        if work == 0:
            # block a or b has no bad t-set (and none below t): it covers z^t on every t-set
            cand, surv, shown = 0, 0, []
            rep["method"] = "none needed"
        elif exe and work * max(1, M - 2) * maxw * t <= HELPER_WORK and max(nbad[a], nbad[b]) <= HELPER_LIST:
            hp = os.path.join(cz2_tmpdir(c), "H.txt")
            if not os.path.exists(hp):
                with open(hp, "w", encoding="ascii", newline="\n") as f:
                    for row in H:
                        f.write(" ".join(map(str, row)) + "\n")
            res = Helper.run(["enum", t, z, a, b, hp] + [cz2_file(c, n) for n in rows_of])
            shown = []
            for line in res.splitlines():
                f = line.split()
                if f[0] == "survivor":
                    shown.append(list(map(int, f[1:])))
                elif f[:2] == ["enum", "candidates"]:
                    cand = int(f[2])
                elif f[:2] == ["enum", "survivors"]:
                    surv = int(f[2])
            rep["method"] = "cz2help"
        elif work * max(1, M - 2) * t * t <= INGREDIENT_WORK:
            la = py_bad(c["ingredients"][rows_of[a]]["rows"], t, z, True)[1]
            lb = py_bad(c["ingredients"][rows_of[b]]["rows"], t, z, True)[1]
            cand, surv, shown = py_enumerate(c, z, a, b, la, lb)
            rep["method"] = "python"
        else:
            out.append("weight %d: the enumeration (%d x %d bad %d-sets x %d bijections) is above the limit of this "
                       "checker%s" % (wt, nbad[a], nbad[b], t, math_factorial(t), cz2_note(c)))
            continue
        rep["candidates"], rep["survivors"] = cand, surv
        if surv:
            out.append("weight %d: %d t-sets of array columns have no row constant %d (first %s)"
                       % (wt, surv, z, "; ".join(str(s) for s in shown[:3])))
    return out


def enumeration_text(c, rep):
    bad = ", ".join("%s %s" % (n, "/".join("-" if x is None else str(x) for x in v)) for n, v in sorted(rep.get("bad", {}).items()))
    s = "tuple %s^%d; bad s-sets (s = 1..%d) per ingredient: %s" % (rep["z"], c["t"], c["t"], bad or "not computed")
    if "survivors" in rep:
        s += "; blocks %d and %d, %d cases, %d give array columns, %d survivors (%s)" % (
            rep["blocks"][0], rep["blocks"][1], rep["cases"], rep["candidates"], rep["survivors"], rep["method"])
    return s


def math_factorial(n):
    out = 1
    for i in range(2, n + 1):
        out *= i
    return out


CHECKS2 = [("field", check_field), ("shape", check_shape), ("width", check_width),
           ("ingredient_hash", check_ingredient_hash), ("agreement", check_agreement),
           ("relabel", check_relabel), ("quilting", check_quilting2), ("species", check_species2),
           ("enumeration", check_enumeration)]


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


# ---------------------------------------------------------------------------
# ingredients from the table, and the constructions on arrays (fuse-1, derive-1, product-1)
# ---------------------------------------------------------------------------

def resolve_table(sha, table_dir, where):
    """An ingredient named by the array_sha256 of a counted VERIFIED row of the table (tier VERIFIED,
    not retracted; table/ca_table.py counted()). The array is read from table/arrays (plain or gzip)
    and its canonical text must hash to sha. Returns the rows and the row's t, v, k, N (the largest
    strength among the counted VERIFIED rows of that array)."""
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("%s: 'table' must be the 64 lower-case hex digits of an array_sha256" % where)
    td = table_dir or REPO_TABLE
    if REPO_TABLE not in sys.path:
        sys.path.insert(0, REPO_TABLE)
    from ca_table import counted
    try:
        with open(os.path.join(td, "ca_table.csv"), newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with open(os.path.join(td, "MANIFEST.csv"), newline="", encoding="utf-8") as f:
            man = list(csv.DictReader(f))
    except OSError as e:
        raise CertError("%s: cannot read the table in %s: %s" % (where, td, e))
    cand = [r for r in counted(rows) if r["tier"] == "VERIFIED" and r["array_sha256"] == sha]
    if not cand:
        raise CertError("%s: %s is not the array_sha256 of a counted VERIFIED row of the table"
                        % (where, sha[:16]))
    row = max(cand, key=lambda r: int(r["t"]))
    files = [m["file"] for m in man if m["sha256"] == sha]
    if not files:
        raise CertError("%s: the array %s is not stored in table/arrays" % (where, sha[:16]))
    path = os.path.join(td, "arrays", files[0])
    try:
        op = gzip.open if path.endswith(".gz") else open
        with op(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise CertError("%s: cannot read table/arrays/%s: %s" % (where, files[0], e))
    if hashlib.sha256(data).hexdigest() != sha:
        raise CertError("%s: table/arrays/%s does not hash to %s" % (where, files[0], sha[:16]))
    text = data.decode("ascii")
    if "NA" in text:
        raise CertError("%s: the array has don't-care entries, which an ingredient may not have" % where)
    mat = parse_matrix_text(text, "%s (table/arrays/%s)" % (where, files[0]))
    return {"rows": mat, "table": {"sha256": sha, "file": files[0], "t": int(row["t"]), "v": int(row["v"]),
                                   "k": int(row["k"]), "N": int(row["N"]), "stamp": row["verify_stamp"]}}


def parse_expected(cert, c):
    exp = cert.get("expected")
    only_keys(exp, ("N", "k", "array_sha256"), "expected")
    c["exp_N"] = need_int(exp, "N", 1, None, "expected: ")
    c["exp_k"] = need_int(exp, "k", 1, None, "expected: ")
    sha = exp.get("array_sha256")
    if not isinstance(sha, str) or not HEX64.match(sha):
        raise CertError("expected: array_sha256 must be 64 lowercase hex digits")
    c["exp_sha"] = sha


def parse_array_ingredient(obj, where, c, table_dir):
    """an array ingredient: {"rows": [[...]]}, {"file": name, "sha256": hex} or {"table": sha}"""
    only_keys(obj, ("file", "sha256", "rows", "table"), where)
    if sum(1 for x in ("file", "rows", "table") if x in obj) != 1:
        raise CertError("%s: give exactly one of 'rows', 'file' (with 'sha256') or 'table'" % where)
    d = {"name": where}
    if "table" in obj:
        if "sha256" in obj:
            raise CertError("%s: a table ingredient takes no sha256 (the table hash is its name)" % where)
        d.update(resolve_table(obj["table"], table_dir, where))
    elif "file" in obj:
        fn, h = obj["file"], obj.get("sha256")
        if not isinstance(fn, str) or not NAME_RE.match(fn) or fn.startswith("."):
            raise CertError("%s: file must be a plain file name beside the certificate" % where)
        if not isinstance(h, str) or not HEX64.match(h):
            raise CertError("%s: a file ingredient needs sha256 (64 lowercase hex)" % where)
        try:
            with open(os.path.join(c["dir"], fn), "rb") as f:
                raw = f.read()
        except OSError as ex:
            raise CertError("%s: cannot read %s: %s" % (where, fn, ex))
        d["file"], d["sha_expected"], d["sha_actual"] = fn, h, hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            raise CertError("%s: file is not ASCII text" % where)
        d["rows"] = parse_matrix_text(text, "%s (%s)" % (where, fn))
    else:
        if "sha256" in obj:
            raise CertError("%s: an inline ingredient takes no sha256" % where)
        rows = obj["rows"]
        if not isinstance(rows, list) or not all(isinstance(r, list) and all(is_int(x) and x >= 0 for x in r)
                                                 for r in rows):
            raise CertError("%s: rows must be a list of lists of nonnegative integers" % where)
        d["rows"] = [list(r) for r in rows]
    return d


ARRAY_KEYS = {"fuse-1": ("input", "rows"), "derive-1": ("input", "column", "symbol"),
              "product-1": ("first", "second", "constant_rows")}


def load_array_kind(cert, raw, path, table_dir):
    kind = cert["construction"]
    only_keys(cert, ("format", "construction", "t", "v", "expected", "notes") + ARRAY_KEYS[kind], "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and all(isinstance(x, str) for x in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 1, 32)
    v = need_int(cert, "v", 2, 64)
    c = {"kind": kind, "t": t, "v": v, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "ingredients": {}}
    parse_expected(cert, c)
    # each ingredient with the strength and the number of symbols the theorem needs of it
    roles = {"fuse-1": [("input", t, v + 1)], "derive-1": [("input", t + 1, v)],
             "product-1": [("first", 2, v), ("second", 2, v)]}[kind]
    for role, nt, nv in roles:
        if role not in cert:
            raise CertError("missing key %r" % role)
        d = parse_array_ingredient(cert[role], role, c, table_dir)
        d["need_t"], d["need_v"] = nt, nv
        c["ingredients"][role] = d
    if kind == "fuse-1":
        zr = cert.get("rows", [0, 1])
        if not (isinstance(zr, list) and len(zr) == 2 and all(is_int(x) and x >= 0 for x in zr)):
            raise CertError("rows must be [z, r], two row numbers (default [0, 1])")
        c["zr"] = list(zr)
    elif kind == "derive-1":
        c["column"] = need_int(cert, "column", 0)
        c["symbol"] = need_int(cert, "symbol", 0)
    else:
        cr = cert.get("constant_rows", [None, None])
        if not (isinstance(cr, list) and len(cr) == 2 and all(x is None or (is_int(x) and x >= 0) for x in cr)):
            raise CertError("constant_rows must be [a, b], each a row number or null")
        c["constant_rows"] = list(cr)
    return c


def ca_missing(rows, t, v, limit=None):
    """Exhaustive: None if rows (N x k over 0..v-1) cover every t-tuple on every t-set of columns,
    else (columns, a missing tuple). Raises ValueError when C(k, t) * N exceeds limit."""
    k = len(rows[0])
    if limit is not None and comb(k, t) * len(rows) * t > limit:
        raise ValueError("C(%d, %d) * %d is above the limit of this check" % (k, t, len(rows)))
    for r in rows:
        for j, x in enumerate(r):
            if not 0 <= x < v:            # a symbol outside 0..v-1 must not count towards a t-set
                return [j], [x]
    cols = [tuple(r[j] for r in rows) for j in range(k)]
    full = v ** t
    for cs in itertools.combinations(range(k), t):
        seen = set(zip(*[cols[j] for j in cs]))
        if len(seen) < full:
            for tup in itertools.product(range(v), repeat=t):
                if tup not in seen:
                    return list(cs), list(tup)
    return None


def check_array_shape(c):
    """every array ingredient is a nonempty rectangular array over the symbols 0..v_in-1 the theorem
    needs of it, with at least as many columns as the strength needed of it"""
    out = []
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        if not rows or not rows[0]:
            out.append("ingredient %s has no rows" % name)
            continue
        w = len(rows[0])
        bad = [i for i, r in enumerate(rows) if len(r) != w]
        if bad:
            out.append("ingredient %s is ragged (row %d has %d entries, row 0 has %d)"
                       % (name, bad[0], len(rows[bad[0]]), w))
            continue
        big = [(i, j) for i, r in enumerate(rows) for j, x in enumerate(r) if x >= ing["need_v"]]
        if big:
            i, j = big[0]
            out.append("ingredient %s: entry %d at row %d column %d is not a symbol 0..%d"
                       % (name, rows[i][j], i, j, ing["need_v"] - 1))
        if w < ing["need_t"]:
            out.append("ingredient %s has %d columns, fewer than the strength %d it needs"
                       % (name, w, ing["need_t"]))
    return out


def check_ingredient_ca(c):
    """every inline or file ingredient is a covering array of the strength and over the number of
    symbols the theorem needs, checked here exhaustively (every t-set, every tuple); a table
    ingredient is checked by ingredient_table instead"""
    out = []
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue
        rows = ing["rows"]
        if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows) or len(rows[0]) < ing["need_t"]:
            out.append("ingredient %s cannot be a covering array of strength %d (see shape)" % (name, ing["need_t"]))
            continue
        try:
            miss = ca_missing(rows, ing["need_t"], ing["need_v"], INGREDIENT_WORK)
        except ValueError as e:
            out.append("ingredient %s is too large to check here (%s); enter it in the table first and name "
                       "it by its array_sha256" % (name, e))
            continue
        if miss:
            out.append("ingredient %s is not a CA(%d; %d, %d, %d): columns %s miss the tuple %s"
                       % (name, len(rows), ing["need_t"], len(rows[0]), ing["need_v"], miss[0], miss[1]))
    return out


def check_table_ingredients(c):
    """every table ingredient is the array of a counted VERIFIED row (resolved when the certificate
    is read) whose strength is at least the strength needed, with the number of symbols needed and
    the number of rows and columns of the array read"""
    out = []
    for name, ing in c["ingredients"].items():
        tb = ing.get("table")
        if not tb:
            continue
        rows = ing["rows"]
        if tb["t"] < ing["need_t"]:
            out.append("ingredient %s: the table row has strength %d, the construction needs %d"
                       % (name, tb["t"], ing["need_t"]))
        if tb["v"] != ing["need_v"]:
            out.append("ingredient %s: the table row has v = %d, the construction needs %d"
                       % (name, tb["v"], ing["need_v"]))
        if (tb["N"], tb["k"]) != (len(rows), len(rows[0]) if rows else 0):
            out.append("ingredient %s: the table row is %d x %d, the stored array %d x %d"
                       % (name, tb["N"], tb["k"], len(rows), len(rows[0]) if rows else 0))
    return out


def check_fuse_strength(c):
    """fuse-1: t >= 2 (the proof covers a tuple with the help of a second column)"""
    return [] if c["t"] >= 2 else ["fuse-1 needs t >= 2 (t = %d)" % c["t"]]


def check_fuse_rows(c):
    """fuse-1: the rows z and r are two distinct rows of the input"""
    z, r = c["zr"]
    n = len(c["ingredients"]["input"]["rows"])
    if z == r or not (z < n and r < n):
        return ["rows [%d, %d] are not two distinct rows of the %d-row input" % (z, r, n)]
    return []


def check_derive_column(c):
    """derive-1: the column is a column of the input, and the input has at least t+1 columns"""
    rows = c["ingredients"]["input"]["rows"]
    k = len(rows[0]) if rows else 0
    out = []
    if not c["column"] < k:
        out.append("column %d is not a column of the %d-column input" % (c["column"], k))
    if k - 1 < c["t"]:
        out.append("the derived array would have %d columns, fewer than t = %d" % (k - 1, c["t"]))
    return out


def check_derive_symbol(c):
    """derive-1: the symbol is one of 0..v-1"""
    return [] if c["symbol"] < c["v"] else ["symbol %d is not one of 0..%d" % (c["symbol"], c["v"] - 1)]


def check_product_strength(c):
    """product-1: the direct product gives strength 2 only"""
    return [] if c["t"] == 2 else ["product-1 gives strength 2, the certificate says t = %d" % c["t"]]


def check_product_constant_rows(c):
    """product-1: each constant_rows entry is null or a row of its ingredient"""
    out = []
    for role, x in zip(("first", "second"), c["constant_rows"]):
        n = len(c["ingredients"][role]["rows"])
        if x is not None and x >= n:
            out.append("constant_rows: %d is not a row of the %d-row %s ingredient" % (x, n, role))
    return out


def rows_fuse(c):
    A = c["ingredients"]["input"]["rows"]
    z, r = c["zr"]
    top = c["v"]                       # the symbol removed: the largest of the input, v
    Z = A[z]

    def tau(x, j):                     # the transposition Z[j] <-> top in column j
        return top if x == Z[j] else Z[j] if x == top else x
    R = [tau(x, j) for j, x in enumerate(A[r])]
    for i, row in enumerate(A):
        if i in (z, r):
            continue
        out = []
        for j, x in enumerate(row):
            y = tau(x, j)
            if y == top:
                y = R[j] if R[j] != top else 0
            out.append(y)
        yield out


def rows_derive(c):
    col, s = c["column"], c["symbol"]
    for row in c["ingredients"]["input"]["rows"]:
        if row[col] == s:
            yield row[:col] + row[col + 1:]


def normalize(rows, r):
    """row r made all 0 by the transposition rows[r][j] <-> 0 in every column j (None: unchanged)"""
    if r is None:
        return rows
    Z = rows[r]
    return [[0 if x == Z[j] else Z[j] if x == 0 else x for j, x in enumerate(row)] for row in rows]


def rows_product(c):
    A = normalize(c["ingredients"]["first"]["rows"], c["constant_rows"][0])
    B = normalize(c["ingredients"]["second"]["rows"], c["constant_rows"][1])
    k1, k2 = len(A[0]), len(B[0])
    const_a = {row[0] for row in A if len(set(row)) == 1}
    for a in A:
        yield [a[i] for i in range(k1) for _ in range(k2)]
    for b in B:
        if len(set(b)) == 1 and b[0] in const_a:
            continue                   # the same row as a constant row of the first part
        yield [b[j] for _ in range(k1) for j in range(k2)]


ROWS_OF = {"fuse-1": rows_fuse, "derive-1": rows_derive, "product-1": rows_product}


def width_of(c):
    ing = c["ingredients"]
    if c["kind"] == "fuse-1":
        return len(ing["input"]["rows"][0])
    if c["kind"] == "derive-1":
        return len(ing["input"]["rows"][0]) - 1
    return len(ing["first"]["rows"][0]) * len(ing["second"]["rows"][0])


def assemble_array_kind(c, write=None):
    """the rows of the construction in order, in the table's canonical text, hashed as a stream"""
    h = hashlib.sha256()
    fout = open(write, "w", encoding="ascii", newline="\n") if write else None
    N, symbols = 0, set()
    try:
        for row in ROWS_OF[c["kind"]](c):
            line = " ".join(map(str, row)) + "\n"
            symbols.update(row)
            h.update(line.encode("ascii"))
            if fout:
                fout.write(line)
            N += 1
    finally:
        if fout:
            fout.close()
    c["N"], c["k"], c["sha256"], c["symbols"] = N, width_of(c), h.hexdigest(), symbols


def check_out_symbols(c):
    """every symbol of the rebuilt array is one of 0..v-1 (the theorem's alphabet)"""
    bad = sorted(x for x in c["symbols"] if not 0 <= x < c["v"])
    return ["the rebuilt array uses symbol %d, outside 0..%d" % (bad[0], c["v"] - 1)] if bad else []


KIND_CHECKS = {
    "fuse-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
               ("ingredient_ca", check_ingredient_ca), ("fuse_strength", check_fuse_strength),
               ("fuse_rows", check_fuse_rows)],
    "derive-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
                 ("ingredient_ca", check_ingredient_ca), ("derive_column", check_derive_column),
                 ("derive_symbol", check_derive_symbol)],
    "product-1": [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
                  ("ingredient_ca", check_ingredient_ca), ("product_strength", check_product_strength),
                  ("product_constant_rows", check_product_constant_rows)],
}
# run for every construction (powercz-1 included) that names an ingredient by its table hash
TABLE_CHECKS = [("ingredient_table", check_table_ingredients)]
KIND_POST_CHECKS = [("alphabet", check_out_symbols)]


# ---------------------------------------------------------------------------
# Shokri, Moura and Stevens (arXiv:2510.13122v3): sms51-1 (Theorem 5.1) and sms65-1 (Theorem 6.2
# with the ingredient of Corollary 6.5). tools/CONSTRUCTION_CERT.md states the theorems and the
# proofs these checks follow.
# ---------------------------------------------------------------------------

SMS_MAX_Q = 31              # largest q (the q^4 - 1 powers of alpha are listed here in Python)
SMS_KEYS = {"sms51-1": ("p",), "sms65-1": ("ingredient",)}


def popcount(x):
    return bin(x).count("1")


def sms_powers(F, f):
    """the coordinate vectors of x^0, x^1, ..., x^(q^m - 2) in F_q[x]/(f), f monic of degree m given
    constant term first (m + 1 labels), and the first e > 0 with x^e = 1 (None if none below q^m)"""
    q, m = F.q, len(f) - 1
    add, mul = F.add, F.mul
    neg = [add[a].index(0) for a in range(q)]
    nf = [neg[c] for c in f[:m]]                     # x^m = -(f_0 + ... + f_(m-1) x^(m-1))
    one = tuple([1] + [0] * (m - 1))
    cur = one
    out = []
    ret = None
    for e in range(q ** m - 1):
        out.append(cur)
        top = cur[m - 1]
        nxt = [0] + list(cur[:m - 1])
        if top:
            mr = mul[top]
            nxt = [add[nxt[i]][mr[nf[i]]] for i in range(m)]
        cur = tuple(nxt)
        if cur == one and ret is None:
            ret = e + 1
    return out, ret


def rot(mask, e, n, full):
    """{s : (s + e) mod n in D} from the mask of D (bit d set for d in D)"""
    e %= n
    return ((mask >> e) | (mask << (n - e))) & full if e else mask


def divisors(n):
    return [d for d in range(1, n) if n % d == 0]


def parse_poly(obj, deg, q, where):
    if not (isinstance(obj, list) and len(obj) == deg + 1 and all(is_int(x) and 0 <= x < q for x in obj)
            and obj[deg] == 1):
        raise CertError("%s must be a list of %d field elements 0..%d, constant term first, the last 1 (monic)"
                        % (where, deg + 1, q - 1))
    return list(obj)


def load_sms(cert, raw, path, table_dir):
    kind = cert["construction"]
    only_keys(cert, ("format", "construction", "t", "v", "field", "quartic", "multipliers", "expected", "notes")
              + SMS_KEYS[kind], "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and all(isinstance(x, str) for x in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 4, 4)
    v = need_int(cert, "v", 3, SMS_MAX_Q)
    if "field" not in cert:
        raise CertError("missing key 'field'")
    p, m, q, modulus = parse_field(cert["field"])
    if q != v or q % 2 == 0:
        raise CertError("%s: the field must be GF(v) with v odd (v = %d, q = %d)" % (kind, v, q))
    c = {"kind": kind, "t": t, "v": v, "q": q, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "ingredients": {}}
    c["F"] = Field(p, m, modulus)
    parse_expected(cert, c)
    c["quartic"] = parse_poly(cert.get("quartic"), 4, q, "quartic")
    n = (q ** 4 - 1) // (q - 1)
    c["n"], c["half"] = n, (q * q + 1) // 2
    mult = cert.get("multipliers", [1, 2, 4])
    if not (isinstance(mult, list) and len(mult) == 3 and all(is_int(x) and 1 <= x < n for x in mult)):
        raise CertError("multipliers must be three integers in 1..%d (default [1, 2, 4])" % (n - 1))
    if kind == "sms65-1" and (mult[1] % 2 or mult[2] % 2):
        raise CertError("sms65-1: the second and third multipliers must be even (the blocks A(H) | A(H))")
    c["mult"] = list(mult)
    half = c["half"]
    if kind == "sms51-1":
        pv = cert.get("p")
        if isinstance(pv, str) and len(pv) == half and set(pv) <= {"0", "1"}:
            c["p"] = [int(ch) for ch in pv]
        else:
            raise CertError("p must be a string of (q^2+1)/2 = %d characters 0 or 1" % half)
    else:
        ing = cert.get("ingredient")
        if isinstance(ing, dict) and "orthogoval" in ing:
            only_keys(ing, ("orthogoval",), "ingredient")
            og = ing["orthogoval"]
            only_keys(og, ("cubic", "points"), "ingredient.orthogoval")
            c["cubic"] = parse_poly(og.get("cubic"), 3, q, "ingredient.orthogoval.cubic")
            pts = og.get("points")
            if not (isinstance(pts, list) and len(pts) == half and all(is_int(x) and 0 <= x < q ** 3 - 1 for x in pts)):
                raise CertError("ingredient.orthogoval.points must be (q^2+1)/2 = %d exponents 0..%d"
                                % (half, q ** 3 - 2))
            c["points"] = list(pts)
            c["ingredients"]["R"] = {"recipe": "orthogoval", "name": "R"}
        elif isinstance(ing, dict):
            d = parse_array_ingredient(ing, "R", c, table_dir)
            d["need_t"], d["need_v"] = 3, q
            c["ingredients"]["R"] = d
        else:
            raise CertError("ingredient must be an object: {\"orthogoval\": ...} or an array ingredient")
    # the powers of alpha (the array is defined by them whatever the checks find)
    c["L4"], c["ret4"] = sms_powers(c["F"], c["quartic"])
    return c


def sms_geometry(c):
    """D0 = {e < n : first coordinate of alpha^e is 0} as a set and as a mask, cached"""
    if "D0" not in c:
        n = c["n"]
        D0 = [e for e in range(n) if c["L4"][e][0] == 0]
        mask = 0
        for e in D0:
            mask |= 1 << e
        c["D0"], c["D0set"], c["D0mask"], c["full"] = D0, set(D0), mask, (1 << n) - 1
    return c


def check_quartic(c):
    """alpha (the class of x modulo the quartic) has multiplicative order q^4 - 1, so the quartic is
    primitive and F_q[x]/(quartic) is the field F_(q^4)"""
    q = c["q"]
    if c["ret4"] != q ** 4 - 1:
        return ["x has order %s modulo the quartic %r, not q^4 - 1 = %d: the quartic is not primitive"
                % (c["ret4"] if c["ret4"] else "no finite", c["quartic"], q ** 4 - 1)]
    return []


def check_hyperplanes(c):
    """the n = (q^4-1)/(q-1) translates of D0 are distinct (D0 has no period), so they are the zero sets
    of n pairwise non-proportional functionals, that is of all the hyperplanes of PG(3, q)"""
    sms_geometry(c)
    n, mask, full = c["n"], c["D0mask"], c["full"]
    q = c["q"]
    out = []
    if len(c["D0"]) != q * q + q + 1:
        out.append("D0 has %d elements, a plane of PG(3, %d) has %d points" % (len(c["D0"]), q, q * q + q + 1))
    for d in divisors(n):
        if rot(mask, d, n, full) == mask:
            out.append("D0 has period %d, so its translates are not all distinct" % d)
            break
    return out


def sms_ready(c):
    """the hyperplane checks use Lemma 2, which needs (Q) and the size of D0; without them they do not run
    (and fail), so a certificate with a degenerate quartic cannot make them slow"""
    sms_geometry(c)
    q = c["q"]
    if c["ret4"] != q ** 4 - 1 or len(c["D0"]) != q * q + q + 1:
        return ["not checked: the quartic is not primitive or D0 is not a plane (see quartic, hyperplanes)"]
    return []


def sms_masks(c, mult, cols, xfun):
    """for each column c in cols: the mask of hyperplanes s with (mult (q+1) xfun(c) + s) mod n in D0"""
    sms_geometry(c)
    n, q, mask, full = c["n"], c["q"], c["D0mask"], c["full"]
    return {col: rot(mask, mult * (q + 1) * xfun(col), n, full) for col in cols}


def check_actm(c):
    """(ACTM) no 4-set of columns of the full ovoid, 0 <= col < q^2+1, with distinct x = col mod half, is
    dependent in all three labelings E_l(col) = l (q+1) col mod n (l the multipliers); by the shift
    col -> col+1 it suffices to test the 4-sets that contain column 0"""
    if sms_ready(c):
        return sms_ready(c)
    q, n, half = c["q"], c["n"], c["half"]
    l1, l2, l3 = c["mult"]
    K = q * q + 1
    D0set = c["D0set"]
    ident = lambda col: col
    M2 = sms_masks(c, l2, range(K), ident)
    M3 = sms_masks(c, l3, range(K), ident)
    E1 = [(l1 * (q + 1) * col) % n for col in range(K)]
    E2 = [(l2 * (q + 1) * col) % n for col in range(K)]
    E3 = [(l3 * (q + 1) * col) % n for col in range(K)]
    tested = 0
    for s1 in range(n):
        if (E1[0] + s1) % n not in D0set:
            continue
        Y = [col for col in range(1, K) if col % half != 0 and (E1[col] + s1) % n in D0set]
        for ib in range(len(Y)):
            b = Y[ib]
            for ic in range(ib + 1, len(Y)):
                cc_ = Y[ic]
                if cc_ % half == b % half:
                    continue
                P2 = M2[0] & M2[b] & M2[cc_]
                if not P2:
                    continue
                P3 = M3[0] & M3[b] & M3[cc_]
                if not P3:
                    continue
                single2 = P2 & (P2 - 1) == 0
                single3 = P3 & (P3 - 1) == 0
                s2 = P2.bit_length() - 1
                s3 = P3.bit_length() - 1
                for d in Y[ic + 1:]:
                    if d % half in (b % half, cc_ % half):
                        continue
                    tested += 1
                    in2 = ((E2[d] + s2) % n in D0set) if single2 else bool(M2[d] & P2)
                    if not in2:
                        continue
                    in3 = ((E3[d] + s3) % n in D0set) if single3 else bool(M3[d] & P3)
                    if in3:
                        c["actm_tested"] = tested
                        return ["columns %s of the full ovoid (distinct x) are dependent in all three labelings "
                                "(multipliers %s)" % ([0, b, cc_, d], c["mult"])]
    c["actm_tested"] = tested
    return []


def check_caps(c):
    """sms65-1, case 2: any 3 columns of H2 = G^(l2 (q+1)) and of H4 = G^(l3 (q+1)) on half columns are
    linearly independent (exactly one common hyperplane); by the shift x -> x+1 mod half (l even) it
    suffices to test the 3-sets that contain column 0"""
    if sms_ready(c):
        return sms_ready(c)
    q, half = c["q"], c["half"]
    out = []
    for l in c["mult"][1:]:
        M = sms_masks(c, l, range(half), lambda x: x)
        for b in range(1, half):
            P = M[0] & M[b]
            for cc_ in range(b + 1, half):
                if popcount(P & M[cc_]) != 1:
                    out.append("columns 0, %d, %d of G^(%d(q+1)) on %d columns are linearly dependent"
                               % (b, cc_, l, half))
                    return out
    return out


def check_pairs(c):
    """sms65-1, case 3: the 4 columns x, x + half, x', x' + half of G^(l1 (q+1)) on q^2+1 columns are
    linearly independent (no common hyperplane); by the shift it suffices to take x = 0"""
    if sms_ready(c):
        return sms_ready(c)
    q, half = c["q"], c["half"]
    K = q * q + 1
    M = sms_masks(c, c["mult"][0], range(K), lambda col: col)
    base = M[0] & M[half]
    for x in range(1, half):
        if base & M[x] & M[x + half]:
            return ["columns 0, %d, %d, %d of G^(%d(q+1)) are linearly dependent" % (half, x, x + half, c["mult"][0])]
    return []


def sms_ortho(c):
    """the orthogoval ingredient: powers of beta, D3, the scaled generator matrices (cached)"""
    if "L3" not in c:
        F, q = c["F"], c["q"]
        c["L3"], c["ret3"] = sms_powers(F, c["cubic"])
        n3 = q * q + q + 1
        D3 = [e for e in range(n3) if c["L3"][e][0] == 0]
        mask = 0
        for e in D3:
            mask |= 1 << e
        c["n3"], c["D3"], c["D3mask"], c["full3"] = n3, D3, mask, (1 << n3) - 1
    return c


def check_cubic(c):
    """the orthogoval ingredient: beta (x modulo the cubic) has multiplicative order q^3 - 1"""
    sms_ortho(c)
    q = c["q"]
    if c["ret3"] != q ** 3 - 1:
        return ["x has order %s modulo the cubic %r, not q^3 - 1 = %d: the cubic is not primitive"
                % (c["ret3"] if c["ret3"] else "no finite", c["cubic"], q ** 3 - 1)]
    return []


def check_lines(c):
    """the q^2+q+1 translates of D3 = {e : first coordinate of beta^e is 0} are distinct (all the lines)"""
    sms_ortho(c)
    n3, mask, full = c["n3"], c["D3mask"], c["full3"]
    q = c["q"]
    out = []
    if len(c["D3"]) != q + 1:
        out.append("D3 has %d elements, a line of PG(2, %d) has %d points" % (len(c["D3"]), q, q + 1))
    for d in divisors(n3):
        if rot(mask, d, n3, full) == mask:
            out.append("D3 has period %d" % d)
            break
    return out


def check_points(c):
    """every chosen column beta^j and beta^-j has a nonzero first coordinate (so it can be scaled to 1)"""
    sms_ortho(c)
    L3, n = c["L3"], c["q"] ** 3 - 1
    for i, j in enumerate(c["points"]):
        if L3[j][0] == 0 or L3[(-j) % n][0] == 0:
            return ["point %d (j = %d): beta^j or beta^-j has first coordinate 0" % (i, j)]
    return []


def check_orthogoval(c):
    """every 3 of the chosen columns are linearly independent in G1 (points beta^j) or in G2 (points
    beta^-j): the 3-sets dependent in G1 are those on a line, enumerated over the q^2+q+1 lines"""
    sms_ortho(c)
    q, n3, D3mask, full = c["q"], c["n3"], c["D3mask"], c["full3"]
    if c["ret3"] != q ** 3 - 1 or len(c["D3"]) != q + 1:
        return ["not checked: the cubic is not primitive or D3 is not a line (see cubic, lines)"]
    D3set = set(c["D3"])
    P1 = [j % n3 for j in c["points"]]
    M2 = [rot(D3mask, (-j) % n3, n3, full) for j in c["points"]]
    k = len(P1)
    for s in range(n3):
        Y = [i for i in range(k) if (P1[i] + s) % n3 in D3set]
        for a, b, d in itertools.combinations(Y, 3):
            if M2[a] & M2[b] & M2[d]:
                return ["columns %s of the ingredient are dependent in both planes" % ([a, b, d],)]
    return []


def check_r_shape(c):
    """an array ingredient R has exactly (q^2+1)/2 columns, over 0..q-1"""
    ing = c["ingredients"]["R"]
    out = check_array_shape(c)
    rows = ing["rows"]
    if rows and rows[0] and len(rows[0]) != c["half"]:
        out.append("ingredient R has %d columns, Theorem 6.2 needs (q^2+1)/2 = %d" % (len(rows[0]), c["half"]))
    return out


SMS_CHECKS_COMMON = [("field", check_field), ("quartic", check_quartic), ("hyperplanes", check_hyperplanes),
                     ("actm", check_actm)]
SMS_CHECKS = {
    "sms51-1": SMS_CHECKS_COMMON,
    "sms65-1": SMS_CHECKS_COMMON + [("caps", check_caps), ("pairs", check_pairs)],
}
SMS_ORTHO_CHECKS = [("cubic", check_cubic), ("lines", check_lines), ("points", check_points),
                    ("orthogoval", check_orthogoval)]
SMS_ARRAY_CHECKS = [("shape", check_r_shape), ("ingredient_hash", check_ingredient_hash),
                    ("ingredient_ca", check_ingredient_ca)]


def sms_checks(c):
    out = list(SMS_CHECKS[c["kind"]])
    if c["kind"] == "sms65-1":
        out += SMS_ORTHO_CHECKS if "recipe" in c["ingredients"]["R"] else SMS_ARRAY_CHECKS
    return out


# --- assembly: rows as bytes of field labels, F_q addition by carry-free integer addition ---

class SmsRows:
    """F_q-linear combinations of vectors as byte strings of labels. A label a is coded as the integer
    sum_j d_j B^j of its base-p digits d_j, B = 2p - 1, so the sum of two codes has no carry between
    digits and between bytes (two codes add to at most 2 (B^m - 1) / 2 < 256 when B^m < 256)."""

    def __init__(self, F):
        self.F = F
        p, m, q = F.p, F.m, F.q
        B = 2 * p - 1
        if B ** m > 256:
            raise ValueError("GF(%d) is too large for the byte coding" % q)
        self.code = [sum(((a // p ** j) % p) * B ** j for j in range(m)) for a in range(q)]
        dec = [0] * 256
        for s in range(256):
            ds = [(s // B ** j) % B for j in range(m)]
            if all(x <= 2 * (p - 1) for x in ds):
                dec[s] = sum((x % p) * p ** j for j, x in enumerate(ds))
        self.to_label = bytes(dec)                  # sum of two codes -> label
        self.to_code = bytes(self.code + [0] * (256 - q))
        self.shift = {e: bytes([F.add[a][e] for a in range(q)] + [0] * (256 - q)) for e in range(q)}

    def span_rows(self, G):
        """the q^m rows of A(G), G a list of m rows (lists of labels), in itertools.product order"""
        F, q = self.F, self.F.q
        m = len(G)
        k = len(G[0])
        mul = F.mul
        scaled = [[int.from_bytes(bytes(self.code[mul[a][g]] for g in row), "big") for a in range(q)] for row in G]
        tl, tc = self.to_label, self.to_code

        def comb2(X, Y):              # all x + y, x in X, y in Y (codes), as codes
            return [int.from_bytes((x + y).to_bytes(k, "big").translate(tl).translate(tc), "big") for x in X for y in Y]
        if m == 4:
            P, Q = comb2(scaled[0], scaled[1]), comb2(scaled[2], scaled[3])
        elif m == 3:
            P, Q = comb2(scaled[0], scaled[1]), scaled[2]
        else:
            raise ValueError("m must be 3 or 4")
        for x in P:
            for y in Q:
                yield (x + y).to_bytes(k, "big").translate(tl)


class TextHash:
    """the canonical text of rows given as bytes of labels (< 100): hashed, optionally written"""

    def __init__(self, k, write=None, chunk_rows=4096):
        self.k, self.h, self.N = k, hashlib.sha256(), 0
        self.buf, self.chunk = [], chunk_rows
        self.fout = open(write, "wb") if write else None
        self.tens = bytes([48 + a // 10 if a >= 10 else 255 for a in range(100)] + [255] * 156)
        self.ones = bytes([48 + a % 10 for a in range(100)] + [48] * 156)
        self.sep = {}
        self.has0, self.maxsym = False, 0

    def add(self, row):
        self.buf.append(row)
        if len(self.buf) >= self.chunk:
            self.flush()

    def flush(self):
        if not self.buf:
            return
        r = len(self.buf)
        b = b"".join(self.buf)
        self.buf = []
        if r not in self.sep:
            self.sep[r] = ((b" " * (self.k - 1)) + b"\n") * r
        self.maxsym = max(self.maxsym, max(b))
        self.has0 = self.has0 or 0 in b
        out = bytearray(3 * len(b))
        out[0::3] = b.translate(self.tens)
        out[1::3] = b.translate(self.ones)
        out[2::3] = self.sep[r]
        text = out.translate(None, b"\xff")
        self.h.update(text)
        if self.fout:
            self.fout.write(text)
        self.N += r

    def close(self):
        self.flush()
        if self.fout:
            self.fout.close()


def sms_vectors(c, mult, cols):
    """the columns L(alpha^(mult (q+1) col)) for col in cols, as 4 rows of labels"""
    L4, q = c["L4"], c["q"]
    nn = q ** 4 - 1
    vecs = [L4[(mult * (q + 1) * col) % nn] for col in cols]
    return [[v[i] for v in vecs] for i in range(4)]


def sms_ingredient_rows(c, S):
    """the rows of the ingredient R as bytes of labels"""
    ing = c["ingredients"]["R"]
    if "recipe" not in ing:
        for row in ing["rows"]:
            yield bytes(row)
        return
    sms_ortho(c)
    F, q, L3 = c["F"], c["q"], c["L3"]
    n = q ** 3 - 1
    inv = [None] + [F.mul[a].index(1) for a in range(1, q)]

    def scaled(j):
        v = L3[j]
        s = inv[v[0]]
        return [F.mul[s][x] for x in v]
    G1 = [scaled(j % n) for j in c["points"]]
    G2 = [scaled((-j) % n) for j in c["points"]]
    G1 = [[v[i] for v in G1] for i in range(3)]
    G2 = [[v[i] for v in G2] for i in range(3)]
    for row in S.span_rows(G1):
        yield row
    for idx, row in enumerate(S.span_rows(G2)):
        if idx % (q * q) == 0:          # u = (u0, 0, 0): the constant row u0, also a row of the first part
            continue
        yield row


def assemble_sms(c, write=None):
    F, q, half = c["F"], c["q"], c["half"]
    S = SmsRows(F)
    l1, l2, l3 = c["mult"]
    if c["kind"] == "sms51-1":
        cols = [i + c["p"][i] * half for i in range(half)]
        T = TextHash(half, write)
        try:
            for bi, l in enumerate((l1, l2, l3)):
                for idx, row in enumerate(S.span_rows(sms_vectors(c, l, cols))):
                    if bi and idx == 0:     # u = 0: the all-zero row, kept only in the first block
                        continue
                    T.add(row)
        finally:
            T.close()
        k = half
    else:
        K = q * q + 1
        T = TextHash(K, write)
        try:
            for row in S.span_rows(sms_vectors(c, l1, range(K))):
                T.add(row)
            for row in S.span_rows(sms_vectors(c, l2, range(half))):
                T.add(row + row)
            sh = S.shift[1]
            for row in S.span_rows(sms_vectors(c, l3, range(half))):
                T.add(row + row.translate(sh))
            R = list(sms_ingredient_rows(c, S))
            for r in range(1, q - 1):
                sh = S.shift[r + 1]
                for row in R:
                    T.add(row + row.translate(sh))
        finally:
            T.close()
        k = K
    c["N"], c["k"], c["sha256"] = T.N, k, T.h.hexdigest()
    c["symbols"] = ({0} if T.has0 else set()) | ({T.maxsym} if T.N else set())


# ---------------------------------------------------------------------------
# sm-xplication-1: the general theorem (Theorem 5.2.6) of the thesis of K. Shokri (doi:10.20381/ruor-31663),
# Chapter 5 = Shokri and Moura, J. Combin. Des. 33 (2025) 156-171, with the last ingredient given as the
# rows that remain after the redundant ones are removed (Theorems 5.2.7, 5.2.8, 5.2.11, 5.2.13 and
# Corollary 5.2.12). tools/CONSTRUCTION_CERT.md states the theorem and the proof these checks follow.
# ---------------------------------------------------------------------------

SMX_KIND = "sm-xplication-1"
SMX_MAX_Q = 32              # largest q (labels below 100 and the byte coding of SmsRows)
SMX_MAX_DCA = 10 ** 6       # entries of the difference covering array D
SMX_LAST_WORK = 3 * 10 ** 8  # C(x, 3) * |E| for the exhaustive check of the last block
SMX_P_WORK = 3 * 10 ** 8     # C(k, 2) * |P| for the exhaustive check of P


def parse_labels(obj, q, where, width=None):
    """a nonempty list of rows of equal length (= width if given) of labels 0..q-1"""
    if not (isinstance(obj, list) and obj and all(isinstance(r, list) and r for r in obj)):
        raise CertError("%s must be a nonempty list of nonempty rows" % where)
    w = len(obj[0]) if width is None else width
    for i, r in enumerate(obj):
        if len(r) != w or not all(is_int(x) and 0 <= x < q for x in r):
            raise CertError("%s: row %d must have %d labels 0..%d" % (where, i, w, q - 1))
    return [list(r) for r in obj]


def load_smx(cert, raw, path, table_dir):
    only_keys(cert, ("format", "construction", "t", "v", "field", "cubic", "points", "dca", "last", "expected",
                     "notes"), "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and all(isinstance(x, str) for x in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 3, 3)
    v = need_int(cert, "v", 2, SMX_MAX_Q)
    if "field" not in cert:
        raise CertError("missing key 'field'")
    p, m, q, modulus = parse_field(cert["field"])
    if q != v:
        raise CertError("%s: the field must be GF(v) (v = %d, q = %d)" % (SMX_KIND, v, q))
    c = {"kind": SMX_KIND, "t": t, "v": v, "q": q, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "ingredients": {}}
    c["F"] = Field(p, m, modulus)
    parse_expected(cert, c)
    c["cubic"] = parse_poly(cert.get("cubic"), 3, q, "cubic")
    pts = cert.get("points", list(range(q)))
    if not (isinstance(pts, list) and sorted(pts) == list(range(q)) and all(is_int(a) for a in pts)):
        raise CertError("points must list the q labels 0..%d once each (the evaluation points of P)" % (q - 1))
    c["points"] = list(pts)
    D = parse_labels(cert.get("dca"), q, "dca")
    if len(D) < 2:
        raise CertError("dca must have at least 2 rows (rows 0 and 1 go with A(G1) and A(G2))")
    x = len(D[0])
    if len(D) * x > SMX_MAX_DCA:
        raise CertError("dca has %d entries, above %d" % (len(D) * x, SMX_MAX_DCA))
    c["D"], c["x"] = D, x
    last = cert.get("last")
    if not isinstance(last, list):
        raise CertError("last must be a list of 3 x %d generator matrices (possibly empty)" % x)
    c["last"] = [parse_labels(H, q, "last[%d]" % i, x) for i, H in enumerate(last)]
    if any(len(H) != 3 for H in c["last"]):
        raise CertError("every matrix of last must have 3 rows")
    c["k0"] = q * q + q + 1
    c["ingredients"]["P"] = {"recipe": "Corollary 5.1.9", "name": "P"}
    if c["last"]:
        c["ingredients"]["C"] = {"recipe": "the rows of A(H) for %s of last" % (
            "the matrix H" if len(c["last"]) == 1 else "the %d matrices H" % len(c["last"])), "name": "C"}
    # the powers of alpha (the array is defined by them whatever the checks find)
    c["L3"], c["ret3"] = sms_powers(c["F"], c["cubic"])
    return c


def smx_columns(c):
    """the columns of G1 (L(alpha^j)) and G2 (L(alpha^-j)), 0 <= j < q^2+q+1, as tuples"""
    if "G1c" not in c:
        L, n, k0 = c["L3"], c["q"] ** 3 - 1, c["k0"]
        c["G1c"] = [tuple(L[j % n]) for j in range(k0)]
        c["G2c"] = [tuple(L[(-j) % n]) for j in range(k0)]
    return c["G1c"], c["G2c"]


def smx_normal(F, vec):
    """the projective point of a nonzero vector: scaled so that its first nonzero entry is 1"""
    for a in vec:
        if a:
            s = F.mul[a].index(1)
            return tuple(F.mul[s][b] for b in vec)
    return None


def check_smx_cubic(c):
    """alpha (the class of x modulo the cubic) has order q^3 - 1: the cubic is primitive (the hypothesis of
    Theorem 3.2.4); soundness does not rest on it, the points and cphf checks test G1 and G2 themselves"""
    q = c["q"]
    if c["ret3"] != q ** 3 - 1:
        return ["x has order %s modulo the cubic %r, not q^3 - 1 = %d: the cubic is not primitive"
                % (c["ret3"] if c["ret3"] else "no finite", c["cubic"], q ** 3 - 1)]
    return []


def check_smx_points(c):
    """(H1) any two columns of G1 are linearly independent, and so are any two of G2: then A(G1) and A(G2)
    are CA(q^3; 2, q^2+q+1, q), and every symbol occurs in each column"""
    F = c["F"]
    out = []
    for name, cols in zip(("G1", "G2"), smx_columns(c)):
        seen = {}
        for j, col in enumerate(cols):
            pt = smx_normal(F, col)
            if pt is None:
                out.append("column %d of %s is zero" % (j, name))
                break
            if pt in seen:
                out.append("columns %d and %d of %s are proportional" % (seen[pt], j, name))
                break
            seen[pt] = j
    return out


def check_smx_cphf(c):
    """(H2) no 3 columns are linearly dependent in both G1 and G2 (Theorem 3.2.4: the two rows form a
    CPHF(2; q^2+q+1, q, 3)). Three vectors of F_q^3 are dependent if and only if a nonzero functional h
    vanishes on all three; h runs over all q^2+q+1 normalized nonzero vectors, Z_g(h) is the set of
    columns of G_g where h vanishes, and the check is |Z_1(h1) & Z_2(h2)| <= 2 for all h1, h2."""
    F, q = c["F"], c["q"]
    add, mul = F.add, F.mul
    hs = [h for h in itertools.product(range(q), repeat=3) if smx_normal(F, h) == h]
    masks = []
    for cols in smx_columns(c):
        ms = []
        for h in hs:
            r0, r1, r2 = mul[h[0]], mul[h[1]], mul[h[2]]
            mk = 0
            for j, (g0, g1, g2) in enumerate(cols):
                if add[add[r0[g0]][r1[g1]]][r2[g2]] == 0:
                    mk |= 1 << j
            ms.append(mk)
        masks.append(ms)
    M2 = masks[1]
    for i1, m1 in enumerate(masks[0]):
        for i2, m2 in enumerate(M2):
            z = m1 & m2
            if z:
                z &= z - 1
                if z:
                    z &= z - 1
                    if z:
                        z = m1 & m2
                        trip = [j for j in range(c["k0"]) if z >> j & 1][:3]
                        return ["columns %s are dependent in G1 (functional %r) and in G2 (functional %r)"
                                % (trip, hs[i1], hs[i2])]
    return []


def smx_P(c):
    """P: Corollary 5.1.9, the first q^2+q+1 columns of the CA(2q^2 - q; 2, q^2 + 2q, q) of Theorem 5.1.8
    with the Bush OA(q^2; 2, q+1, q) (c0 + c1 X at the points, and c1) as both ingredients, as lists of
    rows (CONSTRUCTION_CERT.md)"""
    if "P" not in c:
        F, q, k0 = c["F"], c["q"], c["k0"]
        rho = [(c1, c0) for c1 in range(1, q) for c0 in range(q)]
        ev = [[F.add[c0][F.mul[c1][z]] for z in c["points"]] for c1, c0 in rho]
        rows = []
        for (c1, c0), e in zip(rho, ev):                    # first part: A1 tiled, C, A1
            rows.append(e * q + [c1] * q + e)
        for (c1, c0), e in zip(rho, ev):                    # second part: B1 columns repeated, B1, C
            rows.append([e[j] for j in range(q) for _ in range(q)] + e + [c1] * q)
        for a in range(q):                                  # constant rows over the first q^2 columns
            rows.append([a] * (q * q) + [0] * (2 * q))
        c["P"] = [r[:k0] for r in rows]
    return c["P"]


def check_smx_P(c):
    """(H3) P is a CA(N1; 2, q^2+q+1, q): every pair of columns covers all q^2 pairs (exhaustive)"""
    P, q, k0 = smx_P(c), c["q"], c["k0"]
    if comb(k0, 2) * len(P) > SMX_P_WORK:
        return ["P has %d rows and %d columns, above the work limit %d" % (len(P), k0, SMX_P_WORK)]
    cols = [[r[j] for r in P] for j in range(k0)]
    colq = [[q * a for a in col] for col in cols]
    import operator
    add = operator.add
    for a in range(k0):
        A = colq[a]
        for b in range(a + 1, k0):
            if len(set(map(add, A, cols[b]))) != q * q:
                got = set(map(add, A, cols[b]))
                miss = min(set(range(q * q)) - got)
                return ["P does not cover (%d, %d) on columns %d, %d" % (miss // q, miss % q, a, b)]
    return []


def check_smx_dca(c):
    """(H4) D is a DCA(m; 2, x, q): for any two columns l < l', the differences D[r][l'] - D[r][l] over the
    rows r take all q values"""
    F, q, D, x = c["F"], c["q"], c["D"], c["x"]
    neg = [F.add[a].index(0) for a in range(q)]
    for l in range(x):
        for l2 in range(l + 1, x):
            diffs = {F.add[r[l2]][neg[r[l]]] for r in D}
            if len(diffs) != q:
                miss = min(set(range(q)) - diffs)
                return ["D misses the difference %d on columns %d, %d" % (miss, l, l2)]
    return []


def smx_span(F, H):
    """A(H) for a 3-row matrix H: the rows u0 H[0] + u1 H[1] + u2 H[2], u in itertools.product order"""
    q = F.q
    add, mul = F.add, F.mul
    x = len(H[0])
    for u in itertools.product(range(q), repeat=3):
        m0, m1, m2 = mul[u[0]], mul[u[1]], mul[u[2]]
        yield tuple(add[add[m0[H[0][j]]][m1[H[1][j]]]][m2[H[2][j]]] for j in range(x))


def smx_last(c):
    """the D-part E_D = {D[r] + a : r, a} and the last block C': the rows of A(H) for H in last, in order,
    without the rows of E_D and without repeats"""
    if "C" not in c:
        F, q, D = c["F"], c["q"], c["D"]
        ED = {tuple(F.add[d][a] for d in r) for r in D for a in range(q)}
        seen, C = set(ED), []
        for H in c["last"]:
            for row in smx_span(F, H):
                if row not in seen:
                    seen.add(row)
                    C.append(row)
        c["ED"], c["C"] = ED, C
    return c["ED"], c["C"]


def check_smx_last(c):
    """(H5) E = E_D together with C' covers every 3-set of the x column blocks (exhaustive); E_D is covered
    in every column block triple by the first m row blocks of the array (CONSTRUCTION_CERT.md)"""
    q, x = c["q"], c["x"]
    if x < 3:
        return []
    ED, C = smx_last(c)
    E = list(ED) + C
    if comb(x, 3) * len(E) > SMX_LAST_WORK:
        return ["E has %d rows and %d columns, above the work limit %d" % (len(E), x, SMX_LAST_WORK)]
    import operator
    add = operator.add
    cols = [[r[j] for r in E] for j in range(x)]
    cq2 = [[q * q * a for a in col] for col in cols]
    cq = [[q * a for a in col] for col in cols]
    for a in range(x):
        for b in range(a + 1, x):
            ab = list(map(add, cq2[a], cq[b]))
            for d in range(b + 1, x):
                if len(set(map(add, ab, cols[d]))) != q ** 3:
                    got = set(map(add, ab, cols[d]))
                    miss = min(set(range(q ** 3)) - got)
                    return ["the last block with E_D does not cover (%d, %d, %d) on column blocks %d, %d, %d"
                            % (miss // (q * q), miss // q % q, miss % q, a, b, d)]
    return []


SMX_CHECKS = [("field", check_field), ("cubic", check_smx_cubic), ("points", check_smx_points),
              ("cphf", check_smx_cphf), ("P", check_smx_P), ("dca", check_smx_dca), ("last", check_smx_last)]


def assemble_smx(c, write=None):
    """row block 0: A(G1) + D[0], block 1: A(G2) + D[1], block r >= 2: P + D[r] (D[r][l] added in column
    block l), then the rows of C' with entry l repeated k0 times in column block l"""
    F, q, D, x, k0 = c["F"], c["q"], c["D"], c["x"], c["k0"]
    S = SmsRows(F)
    G1c, G2c = smx_columns(c)
    T = TextHash(x * k0, write)
    try:
        for r, cols in enumerate((G1c, G2c)):
            sh = [S.shift[d] for d in D[r]]
            G = [[v[i] for v in cols] for i in range(3)]
            for row in S.span_rows(G):
                T.add(b"".join([row.translate(s) for s in sh]))
        P = smx_P(c)
        for r in range(2, len(D)):
            sh = [S.shift[d] for d in D[r]]
            for prow in P:
                row = bytes(prow)
                T.add(b"".join([row.translate(s) for s in sh]))
        _, C = smx_last(c)
        for crow in C:
            T.add(b"".join([bytes([a]) * k0 for a in crow]))
    finally:
        T.close()
    c["N"], c["k"], c["sha256"] = T.N, x * k0, T.h.hexdigest()
    c["symbols"] = ({0} if T.has0 else set()) | ({T.maxsym} if T.N else set())


# order matters only for reporting; every check runs (those after the assembly only if the
# array could be built)
CHECKS = [("field", check_field), ("shape", check_shape), ("width", check_width),
          ("ingredient_hash", check_ingredient_hash), ("agreement", check_agreement),
          ("quilting", check_quilting), ("species", check_species)]
POST_CHECKS = [("symbols", check_symbols), ("N", check_N), ("k", check_k), ("sha256", check_sha)]


# ---------------------------------------------------------------------------
# the product of Colbourn and Torres-Jimenez 2013 (Corollary 4.3): product-ctj-1. tools/CONSTRUCTION_CERT.md
# states the theorem and the proof these checks follow.
# ---------------------------------------------------------------------------

CTJ_KIND = "product-ctj-1"
CTJ_MAX_DEPTH = 8             # nesting depth of products inside the certificate
CTJ_MAX_INNER = 5 * 10 ** 7   # entries of an inner product held in memory


def parse_ctj_constant(obj, where):
    """[[rows of S], [rows of T]]: two lists of row numbers (default [[], []])"""
    if obj is None:
        return [[], []]
    if not (isinstance(obj, list) and len(obj) == 2 and all(isinstance(x, list) for x in obj)
            and all(is_int(i) and i >= 0 for x in obj for i in x)):
        raise CertError("%s: constant must be [[rows of the first], [rows of the second]], lists of row "
                        "numbers" % where)
    return [list(obj[0]), list(obj[1])]


def parse_ctj_node(obj, where, c, table_dir, depth):
    """an ingredient of product-ctj-1: an array (rows, file or table, as for the other array
    constructions) or a product {"product": {"first", "second", "constant"}, "N", "k"}; either with
    an optional "columns": k' (the first k' columns are kept)"""
    if not isinstance(obj, dict):
        raise CertError("%s must be an object" % where)
    if depth > CTJ_MAX_DEPTH:
        raise CertError("%s: products nested deeper than %d" % (where, CTJ_MAX_DEPTH))
    if "product" in obj:
        only_keys(obj, ("product", "N", "k", "columns"), where)
        p = obj["product"]
        if not isinstance(p, dict):
            raise CertError("%s.product must be an object" % where)
        only_keys(p, ("first", "second", "constant"), where + ".product")
        node = {"where": where, "leaf": None, "N_decl": need_int(obj, "N", 1, None, where + ": "),
                "k_decl": need_int(obj, "k", 1, None, where + ": ")}
        for role in ("first", "second"):
            if role not in p:
                raise CertError("%s.product: missing key %r" % (where, role))
            node[role] = parse_ctj_node(p[role], where + "." + role, c, table_dir, depth + 1)
        node["constant"] = parse_ctj_constant(p.get("constant"), where + ".product")
    else:
        leaf = dict((k, x) for k, x in obj.items() if k != "columns")
        d = parse_array_ingredient(leaf, where, c, table_dir)
        d["need_t"], d["need_v"] = 2, c["v"]
        c["ingredients"][where] = d
        node = {"where": where, "leaf": d}
    node["columns"] = need_int(obj, "columns", 0, None, where + ": ") if "columns" in obj else None
    c["ctj_nodes"].append(node)
    return node


def load_ctj(cert, raw, path, table_dir):
    only_keys(cert, ("format", "construction", "t", "v", "first", "second", "constant", "expected", "notes"),
              "certificate")
    if cert.get("format") != FORMAT:
        raise CertError("format must be %r" % FORMAT)
    if "notes" in cert and not (isinstance(cert["notes"], str) or
                                (isinstance(cert["notes"], list) and all(isinstance(x, str) for x in cert["notes"]))):
        raise CertError("notes must be a string or a list of strings")
    t = need_int(cert, "t", 1, 32)
    v = need_int(cert, "v", 2, 64)
    c = {"kind": CTJ_KIND, "t": t, "v": v, "dir": os.path.dirname(os.path.abspath(path)),
         "cert_sha256": hashlib.sha256(raw).hexdigest(), "ingredients": {}, "ctj_nodes": []}
    parse_expected(cert, c)
    top = {"where": "top", "leaf": None, "N_decl": None, "k_decl": None, "columns": None}
    for role in ("first", "second"):
        if role not in cert:
            raise CertError("missing key %r" % role)
        top[role] = parse_ctj_node(cert[role], role, c, table_dir, 1)
    top["constant"] = parse_ctj_constant(cert.get("constant"), "certificate")
    c["ctj_nodes"].append(top)
    c["ctj_top"] = top
    return c


def ctj_relabel(M, S, base, v):
    """the symbol exchange of the theorem: in every column the entry of row S[r] becomes base + r, and the
    other symbols of 0..v-1 take the other values of 0..v-1, both in increasing order (rows of S that
    are not rows of M are skipped; symbols outside 0..v-1 are left as they are)"""
    if not S:
        return M
    S = [s for s in S if s < len(M)]
    k = len(M[0])
    maps = []
    for j in range(k):
        perm = {}
        for r, s in enumerate(S):
            perm.setdefault(M[s][j], base + r)
        tgt = set(perm.values())
        rest_src = [x for x in range(v) if x not in perm]
        rest_tgt = [y for y in range(v) if y not in tgt]
        for x, y in zip(rest_src, rest_tgt):
            perm[x] = y
        maps.append(perm)
    return [[maps[j].get(x, x) for j, x in enumerate(row)] for row in M]


def ctj_parts(c, node):
    """the two ingredients of a product node after the symbol exchange, and the rows kept"""
    A, B = ctj_array(c, node["first"]), ctj_array(c, node["second"])
    S, T = node["constant"]
    A2 = ctj_relabel(A, S, 0, c["v"])
    B2 = ctj_relabel(B, T, len(set(S)), c["v"])
    sS, sT = set(S), set(T)
    return ([r for x, r in enumerate(A2) if x not in sS], [r for y, r in enumerate(B2) if y not in sT],
            len(A[0]), len(B[0]))


def ctj_full(c, node):
    """a product node as built (before its columns option), held in memory"""
    if "_full" not in node:
        Ak, Bk, k1, k2 = ctj_parts(c, node)
        if (len(Ak) + len(Bk)) * k1 * k2 > CTJ_MAX_INNER:
            raise ValueError("%s: an inner product of %d entries is above %d" %
                             (node["where"], (len(Ak) + len(Bk)) * k1 * k2, CTJ_MAX_INNER))
        rows = [[a[i] for i in range(k1) for _ in range(k2)] for a in Ak]
        rows += [b * k1 for b in Bk]
        node["_full"] = rows
    return node["_full"]


def ctj_array(c, node):
    """the array an ingredient node stands for: the leaf or the inner product, then its first
    `columns` columns"""
    if "_arr" not in node:
        M = node["leaf"]["rows"] if node["leaf"] is not None else ctj_full(c, node)
        if node["columns"] is not None:
            M = [r[:node["columns"]] for r in M]
        node["_arr"] = M
    return node["_arr"]


def ctj_products(c):
    return [n for n in c["ctj_nodes"] if n["leaf"] is None]


def check_ctj_strength(c):
    """product-ctj-1: the theorem gives strength 2 only"""
    return [] if c["t"] == 2 else ["product-ctj-1 gives strength 2, the certificate says t = %d" % c["t"]]


def check_ctj_columns(c):
    """product-ctj-1: every columns option keeps at least 2 and at most all the columns of its array"""
    out = []
    for n in c["ctj_nodes"]:
        if n["columns"] is None:
            continue
        M = n["leaf"]["rows"] if n["leaf"] is not None else ctj_full(c, n)
        k = len(M[0]) if M else 0
        if not 2 <= n["columns"] <= k:
            out.append("%s: columns %d is not between 2 and the %d columns of the array" % (n["where"], n["columns"], k))
    return out


def check_ctj_rows(c):
    """product-ctj-1: every row named in constant is a row of its ingredient, named once"""
    out = []
    for n in ctj_products(c):
        for role, L in zip(("first", "second"), n["constant"]):
            N = len(ctj_array(c, n[role]))
            bad = [x for x in L if x >= N]
            if bad:
                out.append("%s: constant row %d is not a row of the %d-row %s ingredient" % (n["where"], bad[0], N, role))
            if len(set(L)) != len(L):
                out.append("%s: a constant row of the %s ingredient is named twice" % (n["where"], role))
    return out


def check_ctj_constant(c):
    """product-ctj-1: every two rows of S differ in every column, and every two rows of T"""
    out = []
    for n in ctj_products(c):
        for role, L in zip(("first", "second"), n["constant"]):
            M = ctj_array(c, n[role])
            L = [x for x in L if x < len(M)]
            for a, b in itertools.combinations(L, 2):
                same = [j for j, (x, y) in enumerate(zip(M[a], M[b])) if x == y]
                if same:
                    out.append("%s: rows %d and %d of the %s ingredient agree in column %d, so they cannot both "
                               "be made constant with distinct symbols" % (n["where"], a, b, role, same[0]))
    return out


def check_ctj_budget(c):
    """product-ctj-1: |S| + |T| <= v (the constant rows take distinct symbols)"""
    out = []
    for n in ctj_products(c):
        s = len(set(n["constant"][0])) + len(set(n["constant"][1]))
        if s > c["v"]:
            out.append("%s: %d constant rows, more than v = %d" % (n["where"], s, c["v"]))
    return out


def check_ctj_nested(c):
    """product-ctj-1: every inner product has the N and k its specification declares"""
    out = []
    for n in ctj_products(c):
        if n["N_decl"] is None:
            continue
        M = ctj_full(c, n)
        if (len(M), len(M[0]) if M else 0) != (n["N_decl"], n["k_decl"]):
            out.append("%s: the inner product is %d x %d, its specification says N = %d, k = %d"
                       % (n["where"], len(M), len(M[0]) if M else 0, n["N_decl"], n["k_decl"]))
    return out


CTJ_CHECKS = [("shape", check_array_shape), ("ingredient_hash", check_ingredient_hash),
              ("ingredient_ca", check_ingredient_ca), ("ctj_strength", check_ctj_strength),
              ("ctj_columns", check_ctj_columns), ("ctj_rows", check_ctj_rows),
              ("ctj_constant", check_ctj_constant), ("ctj_budget", check_ctj_budget),
              ("ctj_nested", check_ctj_nested)]


def assemble_ctj(c, write=None):
    """the top product row by row in the table's canonical text, hashed as a stream: the kept rows of the
    first ingredient with entry i repeated k2 times in column block i, then the kept rows of the second
    ingredient repeated k1 times (column (i, j) at i k2 + j)"""
    Ak, Bk, k1, k2 = ctj_parts(c, c["ctj_top"])
    h = hashlib.sha256()
    fout = open(write, "w", encoding="ascii", newline="\n") if write else None
    N, symbols = 0, set()
    try:
        for a in Ak:
            symbols.update(a)
            line = " ".join([" ".join([str(x)] * k2) for x in a]) + "\n"
            h.update(line.encode("ascii"))
            if fout:
                fout.write(line)
            N += 1
        for b in Bk:
            symbols.update(b)
            s = " ".join(map(str, b))
            line = " ".join([s] * k1) + "\n"
            h.update(line.encode("ascii"))
            if fout:
                fout.write(line)
            N += 1
    finally:
        if fout:
            fout.close()
    c["N"], c["k"], c["sha256"], c["symbols"] = N, k1 * k2, h.hexdigest(), symbols


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

def run(path, write=None, log=None, table_dir=None):
    """check the certificate at path; returns a dict with ok, failures [(check, message)],
    passed [check], N, k, sha256, species_table, construction, ingredients, seconds. Raises
    CertError when malformed. table_dir: where "table" ingredients are found (default: the table/
    of this repository)."""
    t0 = time.time()
    say = log or (lambda s: None)
    c = load_certificate(path, table_dir)
    kind = c["kind"]
    if kind in ARRAY_KINDS:
        checks, post, build = KIND_CHECKS[kind], POST_CHECKS + KIND_POST_CHECKS, assemble_array_kind
        say("certificate %s: %s, t = %d, v = %d, ingredients %s"
            % (path, kind, c["t"], c["v"], ", ".join("%s %d x %d" % (n, len(i["rows"]), len(i["rows"][0]) if i["rows"] else 0)
                                                    for n, i in c["ingredients"].items())))
    elif kind in SMS_KINDS:
        checks, post, build = sms_checks(c), POST_CHECKS + KIND_POST_CHECKS, assemble_sms
        R = c["ingredients"].get("R")
        say("certificate %s: %s, t = 4, q = %d, multipliers %s, %s" % (
            path, kind, c["q"], c["mult"], "p = %s" % "".join(map(str, c["p"])) if kind == "sms51-1" else
            "ingredient R %s" % ("built from orthogoval planes (cubic %r)" % (c["cubic"],) if "recipe" in R else
                                 "%d x %d" % (len(R["rows"]), len(R["rows"][0]) if R["rows"] else 0))))
    elif kind == SMX_KIND:
        checks, post, build = SMX_CHECKS, POST_CHECKS + KIND_POST_CHECKS, assemble_smx
        say("certificate %s: %s, t = 3, q = %d, cubic %r, D %d x %d, last block from %d generator matrices"
            % (path, kind, c["q"], c["cubic"], len(c["D"]), c["x"], len(c["last"])))
    elif kind == CTJ_KIND:
        checks, post, build = CTJ_CHECKS, POST_CHECKS + KIND_POST_CHECKS, assemble_ctj
        say("certificate %s: %s, t = %d, v = %d, %d product(s), leaf ingredients %s"
            % (path, kind, c["t"], c["v"], len(ctj_products(c)),
               ", ".join("%s %d x %d" % (n, len(i["rows"]), len(i["rows"][0]) if i["rows"] else 0)
                         for n, i in c["ingredients"].items())))
    elif kind == "powercz-2":
        build_family(c)
        apply_relabel(c)
        checks, post, build = CHECKS2, POST_CHECKS, assemble
        say("certificate %s: powercz-2, %s, t = %d, v = %d, e = %d, M = %d rows (%d relabelled), k = %d columns, "
            "enumerate_weights %s" % (path, c["family"]["type"], c["t"], c["v"], c["e"], len(c["H"]),
                                      c["relabelled_rows"], len(c["H"][0]), c["enumerate_weights"]))
    else:
        build_family(c)
        checks, post, build = CHECKS, POST_CHECKS, assemble
        say("certificate %s: %s, t = %d, v = %d, e = %d, M = %d rows, k = %d columns"
            % (path, c["family"]["type"], c["t"], c["v"], c["e"], len(c["H"]), len(c["H"][0])))
    if any("table" in i for i in c["ingredients"].values()):
        checks = checks + TABLE_CHECKS
    failures, passed = [], []
    try:
        for name, fn in checks:
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
            if name == "enumeration":
                for wt, rep in sorted(c.get("enumeration", {}).items()):
                    say("  weight %d: %s" % (wt, enumeration_text(c, rep)))
    finally:
        if "cz2_tmp" in c:
            import shutil
            shutil.rmtree(c["cz2_tmp"], ignore_errors=True)
    built = False
    try:
        build(c, write)
        built = True
    except Exception as ex:
        failures.append(("assembly", "the array cannot be assembled: %r" % (ex,)))
        say("FAIL [assembly] %r" % (ex,))
    if built:
        for name, fn in post:
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
    ings = []
    for name, i in c["ingredients"].items():
        if "recipe" in i:
            ings.append(dict(name=name, source="recipe", recipe=i["recipe"]))
        elif "table" in i:
            ings.append(dict(name=name, source="table", sha256=i["table"]["sha256"], file=i["table"]["file"]))
        elif "file" in i:
            ings.append(dict(name=name, source="file", sha256=i["sha_actual"], file=i["file"]))
        else:
            ings.append(dict(name=name, source="inline"))
    return {"ok": built and not failures, "failures": failures, "passed": passed,
            "cert_sha256": c["cert_sha256"], "construction": kind, "ingredients": ings,
            "N": c.get("N"), "k": c.get("k"), "sha256": c.get("sha256"), "t": c["t"],
            "v": c["v"], "species_table": c.get("species_table"),
            "seconds": time.time() - t0, **({"enumerate_weights": c["enumerate_weights"],
                                             "enumeration": c.get("enumeration", {})}
                                            if kind == "powercz-2" else {})}


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
    table_dir = None
    if "--table-dir" in argv:
        i = argv.index("--table-dir")
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        table_dir = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__)
        return 2
    log = None if quiet else print
    try:
        res = run(argv[0], write, log, table_dir)
    except CertError as ex:
        print("MALFORMED: %s" % ex)
        return 2
    if not quiet and res["species_table"]:
        print("species table (species, tau, rows needed, rows declared):")
        for sp, ta, need, n in res["species_table"]:
            print("  %-14s tau %2d  need >= %2d  have %2d%s" % (fmt_species(sp, res["v"]), ta, need, n,
                                                               "  (enumerated)" if sp[1] in
                                                               res.get("enumerate_weights", ()) else ""))
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
