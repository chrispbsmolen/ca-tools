#!/usr/bin/env python3
"""Tests of the constructions fuse-1, derive-1 and product-1 of tools/construction_cert.py, and of
ingredients named by their table hash (for these and for powercz-1).

Random small instances (valid ones and ones with planted faults) are written as certificates, with
their ingredients inline, in files, or in a small table of their own (table/ca_table.csv,
MANIFEST.csv and arrays/ in a temporary folder). Independently of the checker, this file rebuilds
each array (its own code, written differently), evaluates every hypothesis by its definition (its
own exhaustive coverage count for every ingredient), and checks every rebuilt array with ca_verify
(exact, every t-set), itself compared with a Python brute force on the small arrays.

Assertions per case:
  A1 the checker accepts exactly when the independent evaluation finds every hypothesis true
  A2 a planted fault that takes effect is reported by the check it targets
  A3 every accepted certificate gives a covering array (ca_verify) whose canonical sha256 is the
     independently computed one, and the file the checker writes has that sha256
  A4 (the theorems) every case whose hypotheses hold gives a covering array
Then mutation testing: each check is disabled in turn (and three boundary mutants are applied);
a mutant is killed when A1 or A2 fails on some case. The run lists, for each mutant, the cases it
gets wrong and how many non-covering arrays it accepts.

Usage: test_kinds.py [--cases N] [--seed S]   (exit 1 on any violation or surviving mutant)
"""
import csv
import hashlib
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import construction_cert as cc  # noqa: E402

TABLE_HEADER = ["t", "v", "k", "N", "tier", "source_id", "source_detail", "snapshot_id", "array_sha256",
                "verify_stamp", "entered", "notes", "lb", "lb_evidence", "construction", "builds_on",
                "family_sha256"]
MANIFEST_HEADER = ["file", "t", "v", "k", "N", "status", "sha256", "source_id", "source_detail",
                   "verify_stamp", "constant_rows"]


# ---------------------------------------------------------------------------------------------
# independent definitions

def covers(rows, t, v):
    """every t-set of columns shows all v^t tuples (counted per t-set with a dictionary)"""
    if not rows or not rows[0] or len(rows[0]) < t:
        return False
    k = len(rows[0])
    for cols in itertools.combinations(range(k), t):
        seen = {}
        for r in rows:
            seen[tuple(r[j] for j in cols)] = 1
        if len(seen) != v ** t or any(not all(0 <= x < v for x in key) for key in seen):
            return False
    return True


def canon(rows):
    return "".join(" ".join(str(x) for x in r) + "\n" for r in rows)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def make_ca(rng, t, k, v, extra=0):
    """a random covering array: random rows, then for each missing tuple a random row patched to show
    it, then `extra` random rows, shuffled"""
    rows = [[rng.randrange(v) for _ in range(k)] for _ in range(rng.randint(1, v ** t))]
    for cols in itertools.combinations(range(k), t):
        have = {tuple(r[j] for j in cols) for r in rows}
        for tup in itertools.product(range(v), repeat=t):
            if tup not in have:
                r = [rng.randrange(v) for _ in range(k)]
                for j, x in zip(cols, tup):
                    r[j] = x
                rows.append(r)
                have = {tuple(rr[j] for j in cols) for rr in rows}
    rows += [[rng.randrange(v) for _ in range(k)] for _ in range(extra)]
    rng.shuffle(rows)
    return rows


def fuse_ind(A, v, z, r):
    """fuse-1 by its definition: relabel each column so that row z reads v everywhere, keep row r,
    drop rows z and r, write each remaining v as the entry of row r in that column (0 when row r has
    v there)"""
    perm = []
    for j in range(len(A[0])):
        p = list(range(v + 1))
        p[A[z][j]], p[v] = v, A[z][j]
        perm.append(p)
    B = [[perm[j][x] for j, x in enumerate(row)] for row in A]
    keep = B[r]
    out = []
    for i in range(len(B)):
        if i == z or i == r:
            continue
        out.append([keep[j] if (x == v and keep[j] != v) else (0 if x == v else x) for j, x in enumerate(B[i])])
    return out


def derive_ind(A, col, s):
    return [[x for j, x in enumerate(row) if j != col] for row in A if row[col] == s]


def product_ind(A, B, ca, cb):
    def norm(M, r):
        if r is None:
            return [list(x) for x in M]
        out = []
        for row in M:
            nr = []
            for j, x in enumerate(row):
                y = M[r][j]
                nr.append(0 if x == y else (y if x == 0 else x))
            out.append(nr)
        return out
    A2, B2 = norm(A, ca), norm(B, cb)
    k1, k2 = len(A2[0]), len(B2[0])
    top = [[a[c // k2] for c in range(k1 * k2)] for a in A2]
    bot = [[b[c % k2] for c in range(k1 * k2)] for b in B2]
    tops = {tuple(x) for x in top}
    return top + [x for x in bot if not (tuple(x) in tops and len(set(x)) == 1)]


# ---------------------------------------------------------------------------------------------
# cases

class Case:
    def __init__(self, kind, t, v):
        self.kind, self.t, self.v = kind, t, v
        self.ings = {}           # role -> dict(rows, source, need_t, need_v, table_t, table_v)
        self.params = {}
        self.fault = None        # the check the planted fault targets
        self.override = {}       # expected N, k, sha256 overridden


def build_case(rng, kind):
    if kind == "fuse-1":
        t = rng.choice([2, 2, 3])
        v = rng.choice([2, 3]) if t == 3 else rng.choice([2, 3, 4])
        k = rng.randint(t, t + 4)
        c = Case(kind, t, v)
        A = make_ca(rng, t, k, v + 1, rng.randint(0, 3))
        c.ings["input"] = dict(rows=A, need_t=t, need_v=v + 1)
        z, r = rng.sample(range(len(A)), 2)
        c.params["rows"] = [z, r]
    elif kind == "derive-1":
        t = rng.choice([1, 2, 2, 3])
        v = rng.choice([2, 3]) if t < 3 else 2
        k = rng.randint(t + 1, t + 4)
        c = Case(kind, t, v)
        A = make_ca(rng, t + 1, k, v, rng.randint(0, 3))
        c.ings["input"] = dict(rows=A, need_t=t + 1, need_v=v)
        c.params["column"] = rng.randrange(k)
        c.params["symbol"] = rng.randrange(v)
    else:
        v = rng.choice([2, 3, 4])
        c = Case(kind, 2, v)
        for role in ("first", "second"):
            c.ings[role] = dict(rows=make_ca(rng, 2, rng.randint(2, 5), v, rng.randint(0, 2)), need_t=2, need_v=v)
        c.params["constant_rows"] = [rng.choice([None, rng.randrange(len(c.ings["first"]["rows"]))]),
                                     rng.choice([None, rng.randrange(len(c.ings["second"]["rows"]))])]
    for role, d in c.ings.items():
        d["source"] = rng.choice(["inline", "file", "table"])
        d["table_t"], d["table_v"] = d["need_t"] + rng.choice([0, 0, 1]), d["need_v"]
    return c


FAULTS = {
    "fuse-1": ["ingredient_ca", "shape", "ingredient_hash", "ingredient_table", "fuse_strength", "fuse_rows",
               "N", "k", "sha256"],
    "derive-1": ["ingredient_ca", "shape", "ingredient_hash", "ingredient_table", "derive_column",
                 "derive_symbol", "N", "k", "sha256", "symbols"],
    "product-1": ["ingredient_ca", "shape", "ingredient_hash", "ingredient_table", "product_strength",
                  "product_constant_rows", "N", "k", "sha256", "symbols", "alphabet"],
}


def plant(rng, c, fault):
    c.fault = fault
    role = rng.choice(sorted(c.ings))
    d = c.ings[role]
    A = d["rows"]
    if fault == "ingredient_ca":
        # drop every row that shows some chosen tuple on some chosen t-set
        cols = sorted(rng.sample(range(len(A[0])), d["need_t"]))
        tup = tuple(A[0][j] for j in cols)
        d["rows"] = [r for r in A if tuple(r[j] for j in cols) != tup] or [[(x + 1) % d["need_v"] for x in A[0]]]
        if d["source"] == "table":
            d["source"] = "inline"
    elif fault == "shape":
        if rng.random() < 0.5:
            i = rng.randrange(len(A))
            A[i] = A[i][:-1]
        else:
            A[rng.randrange(len(A))][rng.randrange(len(A[0]))] = d["need_v"]
        if d["source"] == "table":
            d["source"] = "inline"
    elif fault == "ingredient_hash":
        d["source"] = "file"
        d["tamper"] = True
    elif fault == "ingredient_table":
        d["source"] = "table"
        if rng.random() < 0.5:
            # a row of lower strength, and an array of only that strength
            d["table_t"] = d["need_t"] - 1
            if d["table_t"] >= 1:
                d["rows"] = make_ca(rng, d["table_t"], len(A[0]), d["need_v"], 0)
                if c.kind == "fuse-1":
                    c.params["rows"] = rng.sample(range(len(d["rows"])), 2) if len(d["rows"]) > 1 else [0, 1]
                if c.kind == "product-1":
                    c.params["constant_rows"] = [None, None]
        else:
            d["table_v"] = d["need_v"] + 1
    elif fault == "fuse_strength":
        # t = 1, with an input of strength 1 only (so the two rows removed can be needed)
        c.t = 1
        k = len(A[0])
        for dd in c.ings.values():
            dd["rows"] = make_ca(rng, 1, k, c.v + 1, rng.randint(0, 1))
            dd["need_t"] = 1
            dd["table_t"] = 1
        c.params["rows"] = rng.sample(range(len(c.ings["input"]["rows"])), 2)
    elif fault == "fuse_rows":
        z = c.params["rows"][0]
        c.params["rows"] = [z, z] if rng.random() < 0.5 else [z, len(A) + rng.randrange(3)]
    elif fault == "derive_column":
        c.params["column"] = len(A[0]) + rng.randrange(3)
    elif fault == "derive_symbol":
        c.params["symbol"] = c.v + rng.randrange(2)
    elif fault == "product_strength":
        c.t = 3
    elif fault == "product_constant_rows":
        c.params["constant_rows"][0] = len(c.ings["first"]["rows"]) + rng.randrange(3)
    elif fault in ("N", "k", "sha256"):
        c.override[fault] = True
    elif fault == "symbols":
        # no symbol 0 anywhere in the ingredients (so none in the array); they are not covering then
        for dd in c.ings.values():
            dd["rows"] = [[x if x else 1 for x in r] for r in dd["rows"]]
        c.params.pop("constant_rows", None)
        if c.kind == "product-1":
            c.params["constant_rows"] = [None, None]
        if c.kind == "derive-1":
            c.params["symbol"] = max(1, c.params["symbol"]) if c.v > 1 else 1
    elif fault == "alphabet":
        # a symbol v in the second ingredient (also a shape failure): the array uses it
        B = c.ings["second"]["rows"]
        B[rng.randrange(len(B))][rng.randrange(len(B[0]))] = c.v
        c.ings["second"]["source"] = "inline"


# ---------------------------------------------------------------------------------------------
# writing a case, and its independent evaluation

def write_case(c, folder, table, idx):
    """the certificate (and file ingredients, and table rows); returns its path"""
    cert = {"format": "construction-cert-1", "construction": c.kind, "t": c.t, "v": c.v}
    for role, d in c.ings.items():
        if d["source"] == "inline":
            cert[role] = {"rows": d["rows"]}
        elif d["source"] == "file":
            fn = "c%d_%s.txt" % (idx, role)
            text = canon(d["rows"])
            with open(os.path.join(folder, fn), "w") as f:
                f.write(text + ("0\n" if d.get("tamper") else ""))
            cert[role] = {"file": fn, "sha256": sha(text)}
        else:
            text = canon(d["rows"])
            h = sha(text)
            table.add(h, text, d["table_t"], d["table_v"], len(d["rows"][0]), len(d["rows"]))
            cert[role] = {"table": h}
    cert.update(c.params)
    out = rebuild(c)
    N, k, h = (max(1, len(out)), max(1, width(c)), sha(canon(out))) if out is not None else (1, 1, "0" * 64)
    if c.override.get("N"):
        N += 1
    if c.override.get("k"):
        k += 1
    if c.override.get("sha256"):
        h = "f" * 64
    cert["expected"] = {"N": N, "k": k, "array_sha256": h}
    path = os.path.join(folder, "c%d.json" % idx)
    with open(path, "w") as f:
        json.dump(cert, f)
    return path


def width(c):
    if c.kind == "fuse-1":
        return len(c.ings["input"]["rows"][0])
    if c.kind == "derive-1":
        return len(c.ings["input"]["rows"][0]) - 1
    return len(c.ings["first"]["rows"][0]) * len(c.ings["second"]["rows"][0])


def rebuild(c):
    try:
        if c.kind == "fuse-1":
            return fuse_ind(c.ings["input"]["rows"], c.v, *c.params["rows"])
        if c.kind == "derive-1":
            return derive_ind(c.ings["input"]["rows"], c.params["column"], c.params["symbol"])
        return product_ind(c.ings["first"]["rows"], c.ings["second"]["rows"], *c.params["constant_rows"])
    except (IndexError, ValueError):
        return None


def evaluate(c):
    """the set of hypotheses (named as the checker's checks) that fail, by definition"""
    fails = set()
    for role, d in c.ings.items():
        A = d["rows"]
        w = len(A[0]) if A and A[0] else 0
        rect = bool(A) and w > 0 and all(len(r) == w for r in A)
        if not rect or any(x >= d["need_v"] for r in A for x in r) or w < d["need_t"]:
            fails.add("shape")
        if d.get("tamper"):
            fails.add("ingredient_hash")
        if d["source"] == "table":
            if d["table_t"] < d["need_t"] or d["table_v"] != d["need_v"]:
                fails.add("ingredient_table")
        elif not (rect and covers(A, d["need_t"], d["need_v"])):
            fails.add("ingredient_ca")
    n = {role: len(d["rows"]) for role, d in c.ings.items()}
    if c.kind == "fuse-1":
        if c.t < 2:
            fails.add("fuse_strength")
        z, r = c.params["rows"]
        if z == r or z >= n["input"] or r >= n["input"]:
            fails.add("fuse_rows")
    elif c.kind == "derive-1":
        k = len(c.ings["input"]["rows"][0])
        if c.params["column"] >= k or k - 1 < c.t:
            fails.add("derive_column")
        if c.params["symbol"] >= c.v:
            fails.add("derive_symbol")
    else:
        if c.t != 2:
            fails.add("product_strength")
        for role, x in zip(("first", "second"), c.params["constant_rows"]):
            if x is not None and x >= n[role]:
                fails.add("product_constant_rows")
    out = rebuild(c)
    if out is None:
        fails.add("assembly")
        return fails, None
    if not any(0 in r for r in out):
        fails.add("symbols")
    if any(not 0 <= x < c.v for r in out for x in r):
        fails.add("alphabet")
    for key in ("N", "k", "sha256"):
        if c.override.get(key):
            fails.add(key)
    return fails, out


class MiniTable:
    def __init__(self, folder):
        self.dir = folder
        os.makedirs(os.path.join(folder, "arrays"))
        self.rows, self.man = [], []

    def add(self, h, text, t, v, k, N):
        name = "CA_%s.txt" % h[:16]
        with open(os.path.join(self.dir, "arrays", name), "w") as f:
            f.write(text)
        self.rows.append([t, v, k, N, "VERIFIED", "S7", "test", "test", h, "ca_verify test", "2026-11-02", "credit: test",
                          "", "", "test", "", ""])
        self.man.append([name, t, v, k, N, "equals_best", h, "S7", "test", "ca_verify test", ""])

    def flush(self):
        with open(os.path.join(self.dir, "ca_table.csv"), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(TABLE_HEADER)
            w.writerows(self.rows)
        with open(os.path.join(self.dir, "MANIFEST.csv"), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(MANIFEST_HEADER)
            w.writerows(self.man)


# ---------------------------------------------------------------------------------------------
# mutation testing

def disabled(c):
    return []


def _fuse_strength_weak(c):          # t >= 1 instead of t >= 2
    return [] if c["t"] >= 1 else ["t"]


def _table_strength_weak(c):         # only v and dimensions checked, not the strength
    out = []
    for name, ing in c["ingredients"].items():
        tb = ing.get("table")
        if tb and (tb["v"] != ing["need_v"] or (tb["N"], tb["k"]) != (len(ing["rows"]), len(ing["rows"][0]))):
            out.append(name)
    return out


def _ingredient_ca_one_lower(c):     # coverage checked at strength need_t - 1
    out = []
    for name, ing in c["ingredients"].items():
        if "table" in ing:
            continue
        rows = ing["rows"]
        if not rows or any(len(r) != len(rows[0]) for r in rows):
            out.append(name)
            continue
        tt = max(1, ing["need_t"] - 1)
        if len(rows[0]) < tt or cc.ca_missing(rows, tt, ing["need_v"]):
            out.append(name)
    return out


def all_check_names():
    names = set()
    for lst in cc.KIND_CHECKS.values():
        names |= {n for n, _ in lst}
    names |= {n for n, _ in cc.POST_CHECKS + cc.KIND_POST_CHECKS + cc.TABLE_CHECKS}
    return sorted(names)


def install(name, fn):
    saved = (dict((k, list(v)) for k, v in cc.KIND_CHECKS.items()), list(cc.POST_CHECKS),
             list(cc.KIND_POST_CHECKS), list(cc.TABLE_CHECKS))
    for k in cc.KIND_CHECKS:
        cc.KIND_CHECKS[k][:] = [(n, fn if n == name else f) for n, f in cc.KIND_CHECKS[k]]
    for lst in (cc.POST_CHECKS, cc.KIND_POST_CHECKS, cc.TABLE_CHECKS):
        lst[:] = [(n, fn if n == name else f) for n, f in lst]
    return saved


def restore(saved):
    kc, post, kpost, tab = saved
    for k in cc.KIND_CHECKS:
        cc.KIND_CHECKS[k][:] = kc[k]
    cc.POST_CHECKS[:] = post
    cc.KIND_POST_CHECKS[:] = kpost
    cc.TABLE_CHECKS[:] = tab


def run_checker(path, table_dir, write=None):
    try:
        r = cc.run(path, write, table_dir=table_dir)
        return r["ok"], {f[0] for f in r["failures"]}, r["sha256"]
    except cc.CertError as e:
        return False, {"malformed: %s" % e}, None


# ---------------------------------------------------------------------------------------------

def powercz_table_cases(work, cav):
    """powercz-1 with an ingredient named by its table hash: one row of width k (explicit family, e
    = 1) whose ingredient is a CA(t, k, v) of the table; the array is that ingredient. The table
    row's strength below t is refused by ingredient_table, and quilting is not asked of it."""
    errs = []
    rng = random.Random(5)
    for i in range(12):
        t, v = rng.choice([(2, 2), (2, 3), (3, 2)])
        k = rng.randint(t, t + 3)
        A = make_ca(rng, t, k, v)
        for bad in (False, True):
            d = os.path.join(work, "pcz%d%s" % (i, "b" if bad else ""))
            os.makedirs(d)
            tb = MiniTable(os.path.join(d, "table"))
            h = sha(canon(A))
            tb.add(h, canon(A), t - 1 if bad else t, v, k, len(A))
            tb.flush()
            cert = {"format": "construction-cert-1", "construction": "powercz-1", "t": t, "v": v, "e": 1,
                    "family": {"type": "explicit", "rows": [{"width": k, "values": list(range(k)), "ingredient": "T"}]},
                    "ingredients": {"T": {"table": h, "covers": {"all": True}}},
                    "expected": {"N": len(A), "k": k, "array_sha256": h}}
            p = os.path.join(d, "c.json")
            json.dump(cert, open(p, "w"))
            ok, got, csha = run_checker(p, tb.dir)
            if ok == bad or (bad and "ingredient_table" not in got) or (not bad and csha != h):
                errs.append("powercz table ingredient case %d bad=%s: ok=%s %s" % (i, bad, ok, sorted(got)))
    return errs, 24


def main():
    args = sys.argv[1:]
    ncases = int(args[args.index("--cases") + 1]) if "--cases" in args else 150
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20261102
    rng = random.Random(seed)
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="cakinds-")
    cav = os.path.join(work, "ca_verify")
    subprocess.check_call(["cc", "-O2", "-pthread", "-o", cav, os.path.join(ROOT, "ca_verify.c")])
    table = MiniTable(os.path.join(work, "table"))
    cases = []
    idx = 0
    for kind in cc.ARRAY_KINDS:
        for n in range(ncases):
            c = build_case(rng, kind)
            if n % 3 == 0:
                pass                                   # valid
            else:
                plant(rng, c, rng.choice(FAULTS[kind]))
            path = write_case(c, work, table, idx)
            idx += 1
            fails, out = evaluate(c)
            cases.append((c, path, fails, out))
    table.flush()
    errors = []
    stats = {}
    brute = [0, 0]
    accepted_noncover = 0
    theorem = [0, 0]
    for c, path, fails, out in cases:
        key = (c.kind, c.fault or "valid")
        st = stats.setdefault(key, [0, 0, 0, 0])
        st[0] += 1
        wpath = path + ".out"
        ok, got, csha = run_checker(path, table.dir, wpath)
        cover = None
        if out is not None and out and all(len(r) == len(out[0]) for r in out) and len(out[0]) >= c.t \
                and all(0 <= x < c.v for r in out for x in r):
            with open(wpath + ".ind", "w") as f:
                f.write(canon(out))
            cover = subprocess.run([cav, wpath + ".ind", str(c.t), str(c.v), "1"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL).returncode == 0
            if len(out) * cc.comb(len(out[0]), c.t) <= 20000:
                brute[0] += 1
                if covers(out, c.t, c.v) != cover:
                    brute[1] += 1
                    errors.append("ca_verify and brute force disagree on %s" % path)
        else:
            cover = False
        if ok:
            st[1] += 1
        if cover:
            st[2] += 1
        if c.fault and c.fault in fails:
            st[3] += 1
        if ok != (not fails):
            errors.append("A1 %s %s: checker ok=%s %s, independent %s" % (path, key, ok, sorted(got), sorted(fails)))
        if c.fault and c.fault in fails and c.fault not in got:
            errors.append("A2 %s %s: planted fault not reported (%s)" % (path, key, sorted(got)))
        if ok:
            wsha = hashlib.sha256(open(wpath, "rb").read()).hexdigest()
            if not cover or csha != sha(canon(out)) or wsha != csha:
                accepted_noncover += 1
                errors.append("A3 %s %s: accepted, covering=%s" % (path, key, cover))
        if not fails:
            theorem[0] += 1
            if not cover:
                theorem[1] += 1
                errors.append("A4 %s %s: hypotheses hold but the array is not covering" % (path, key))
    print("seed %d, %d certificates (%d per construction), %.1f s" % (seed, len(cases), ncases, time.time() - t0))
    print("%-10s %-22s %6s %8s %8s %8s" % ("kind", "case", "certs", "accepted", "covering", "fault real"))
    for (kind, label), st in sorted(stats.items()):
        print("%-10s %-22s %6d %8d %8d %8d" % (kind, label, st[0], st[1], st[2], st[3]))
    print("theorem: %d certificates satisfy every hypothesis; %d of their arrays not covering" % tuple(theorem))
    print("ca_verify vs brute force: %d arrays, %d disagreements" % tuple(brute))
    perr, pn = powercz_table_cases(work, cav)
    errors += perr
    print("powercz-1 with a table ingredient: %d certificates, %d errors" % (pn, len(perr)))

    # mutation testing
    mutants = [("disable:" + n, n, disabled) for n in all_check_names()] + [
        ("fuse_strength: t >= 1", "fuse_strength", _fuse_strength_weak),
        ("ingredient_table: strength not compared", "ingredient_table", _table_strength_weak),
        ("ingredient_ca: strength one lower", "ingredient_ca", _ingredient_ca_one_lower)]
    survivors = 0
    print("mutation testing (%d mutants):" % len(mutants))
    for mname, name, fn in mutants:
        saved = install(name, fn)
        killed = unsound = 0
        try:
            for c, path, fails, out in cases:
                ok, got, csha = run_checker(path, table.dir)
                if (ok != (not fails)) or (c.fault and c.fault in fails and c.fault not in got):
                    killed += 1
                if ok and fails & {"ingredient_ca", "shape", "ingredient_table", "fuse_strength", "fuse_rows",
                                   "derive_column", "derive_symbol", "product_strength", "product_constant_rows"}:
                    if out is None or not (out and covers(out, c.t, c.v)):
                        unsound += 1
        finally:
            restore(saved)
        survivors += killed == 0
        print("  %-44s %-8s by %4d cases; accepts a non-covering array: %d"
              % (mname, "KILLED" if killed else "SURVIVED", killed, unsound))
    print("mutants surviving: %d" % survivors)
    if survivors:
        errors.append("%d mutant(s) survived" % survivors)
    shutil.rmtree(work, ignore_errors=True)
    print("total %.0f s" % (time.time() - t0))
    if errors:
        print("ERRORS (%d):" % len(errors))
        for e in errors[:40]:
            print("  " + e)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
