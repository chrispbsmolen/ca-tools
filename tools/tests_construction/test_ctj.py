#!/usr/bin/env python3
"""Tests of the construction product-ctj-1 of tools/construction_cert.py (Colbourn and Torres-Jimenez
2013, Corollary 4.3: the direct product with constant rows of both ingredients left out).

Random small instances, valid ones and ones with planted faults, are written as certificates. Their
leaf ingredients are inline, in files, or in a small table of their own; one side is sometimes itself
a product (a nested specification), and an ingredient sometimes keeps only its first columns. This
file rebuilds each array with its own code (written from the theorem, not from the checker),
evaluates every hypothesis by its definition (its own coverage count for every leaf), and checks
every rebuilt array with ca_verify (exact), itself compared with a Python brute force.

Assertions per case, as in test_kinds.py:
  A1 the checker accepts exactly when the independent evaluation finds every hypothesis true
  A2 a planted fault that takes effect is reported by the check it targets
  A3 every accepted certificate gives a covering array (ca_verify) whose canonical sha256 is the
     independently computed one, and the file the checker writes has that sha256
  A4 (the theorem) every case whose hypotheses hold gives a covering array
  A5 for the faults ctj_constant and ctj_budget the array built anyway is counted, and how many of
     them fail to cover is printed (the theorem's hypotheses are needed, not decoration)
Then mutation testing: each check of the kind is disabled in turn, and two boundary mutants are
applied (ctj_budget allowing |S| + |T| = v + 1, ctj_constant comparing all columns but the last);
a mutant is killed when A1 or A2 fails on some case. symbols and alphabet are implied for this kind by
shape and ctj_budget (a leaf over 0..v-1 relabelled within 0..v-1), so their mutants are run and
reported but not required to die; the run shows they accept no non-covering array.

Usage: test_ctj.py [--cases N] [--seed S]   (exit 1 on any violation or surviving mutant)
"""
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
sys.path.insert(0, HERE)
import construction_cert as cc  # noqa: E402
from test_kinds import MiniTable, canon, covers, sha  # noqa: E402

FAULTS = ["ctj_constant", "ctj_budget", "ctj_rows", "ctj_nested", "ctj_columns", "ingredient_ca", "shape",
          "ingredient_hash", "ingredient_table", "ctj_strength", "N", "k", "sha256"]
CHECK_NAMES = [n for n, _ in cc.CTJ_CHECKS] + [n for n, _ in cc.TABLE_CHECKS] + \
    [n for n, _ in cc.POST_CHECKS + cc.KIND_POST_CHECKS]
IMPLIED = {"symbols", "alphabet"}


# ---------------------------------------------------------------------------------------------
# independent definitions

def make_ing(rng, k, v):
    """a random CA(N; 2, k, v) holding v rows that differ pairwise in every column (row r reads
    pi_j(r) in column j), padded with random rows until every pair is covered, rows shuffled; returns
    the rows and the indices of those v rows"""
    pis = [rng.sample(range(v), v) for _ in range(k)]
    rows = [[pis[j][r] for j in range(k)] for r in range(v)]
    rows += [[rng.randrange(v) for _ in range(k)] for _ in range(rng.randint(0, 3))]
    for a, b in itertools.combinations(range(k), 2):
        for x in range(v):
            for y in range(v):
                if not any(r[a] == x and r[b] == y for r in rows):
                    r = [rng.randrange(v) for _ in range(k)]
                    r[a], r[b] = x, y
                    rows.append(r)
    order = list(range(len(rows)))
    rng.shuffle(order)
    out = [rows[i] for i in order]
    special = sorted(order.index(r) for r in range(v))
    return out, special


def exchange(M, S, first_symbol, v):
    """per column: row S[r] gets symbol first_symbol + r; the remaining symbols, in increasing order,
    take the remaining values of 0..v-1 in increasing order"""
    out = [list(r) for r in M]
    for j in range(len(M[0])):
        src = [M[s][j] for s in S]
        dst = list(range(first_symbol, first_symbol + len(S)))
        others_src = sorted(set(range(v)) - set(src))
        others_dst = sorted(set(range(v)) - set(dst))
        table = dict(zip(src, dst))
        table.update(zip(others_src, others_dst))
        for i in range(len(M)):
            out[i][j] = table[M[i][j]]
    return out


def product_ind(A, B, S, T, v):
    A2, B2 = exchange(A, S, 0, v), exchange(B, T, len(S), v)
    k1, k2 = len(A[0]), len(B[0])
    rows = []
    for x in range(len(A)):
        if x not in S:
            rows.append([A2[x][col // k2] for col in range(k1 * k2)])
    for y in range(len(B)):
        if y not in T:
            rows.append([B2[y][col % k2] for col in range(k1 * k2)])
    return rows


class Node:
    """a leaf (rows, how it is given) or a product of two nodes, with an optional columns option"""

    def __init__(self, rows=None, special=None, first=None, second=None, S=(), T=()):
        self.rows, self.special = rows, special
        self.first, self.second, self.S, self.T = first, second, list(S), list(T)
        self.columns = None
        self.how = "rows"
        self.N_decl = self.k_decl = None
        self.bad_symbol = False
        self.table_t = 2

    def full(self, v):
        if self.rows is not None:
            return self.rows
        return product_ind(self.first.array(v), self.second.array(v), self.S, self.T, v)

    def array(self, v):
        M = self.full(v)
        return [r[:self.columns] for r in M] if self.columns is not None else M


def nodes_of(n):
    yield n
    if n.rows is None:
        yield from nodes_of(n.first)
        yield from nodes_of(n.second)


def build_case(rng):
    v = rng.randint(2, 4)

    def leaf():
        k = rng.randint(2, 4)
        rows, special = make_ing(rng, k, v)
        n = Node(rows=rows, special=special)
        n.how = rng.choice(["rows", "file", "table"])
        return n

    def pick(n):
        """some rows of n that differ pairwise in every column (of the array as used)"""
        M = n.array(v)
        cand = n.special if n.rows is not None and n.columns is None else None
        if cand is None:
            cand = []
            for i in rng.sample(range(len(M)), len(M)):
                if all(all(a != b for a, b in zip(M[i], M[j])) for j in cand):
                    cand.append(i)
        return list(cand)

    def product(depth):
        a = product(depth + 1) if depth < 2 and rng.random() < 0.3 else leaf()
        b = product(depth + 1) if depth < 2 and rng.random() < 0.3 else leaf()
        for x in (a, b):
            if rng.random() < 0.25:
                k = len(x.full(v)[0])
                if k > 2:
                    x.columns = rng.randint(2, k - 1)
        ca, cb = pick(a), pick(b)
        ns = rng.randint(0, min(len(ca), v))
        nt = rng.randint(0, min(len(cb), v - ns))
        p = Node(first=a, second=b, S=rng.sample(ca, ns), T=rng.sample(cb, nt))
        return p

    top = product(0)
    for n in nodes_of(top):
        if n.rows is None and n is not top:
            M = n.full(v)
            n.N_decl, n.k_decl = len(M), len(M[0])
    case = {"v": v, "t": 2, "top": top, "fault": None, "exp_delta": (0, 0), "bad_sha": False,
            "file_corrupt": None}
    return case


def plant(rng, c, fault):
    v, top = c["v"], c["top"]
    prods = [n for n in nodes_of(top) if n.rows is None]
    leaves = [n for n in nodes_of(top) if n.rows is not None]
    c["fault"] = fault
    if fault == "ctj_constant":
        # half the time: a new row that agrees with a named constant row in the last column only
        cands = [(p, side) for p in prods for side in ("first", "second")
                 if getattr(p, side).rows is not None and getattr(p, side).columns is None
                 and (p.S if side == "first" else p.T) and len(p.S) + len(p.T) < v]
        if cands and rng.random() < 0.5:
            p, side = rng.choice(cands)
            n = getattr(p, side)
            L = p.S if side == "first" else p.T
            s = n.rows[L[0]]
            r = [(x + rng.randint(1, v - 1)) % v for x in s[:-1]] + [s[-1]]
            n.rows = n.rows + [r]
            L.append(len(n.rows) - 1)         # one row more and one more left out: sizes above unchanged
            return
        for _ in range(50):
            p = rng.choice(prods)
            side = rng.choice(["first", "second"])
            M = getattr(p, side).array(v)
            L = p.S if side == "first" else p.T
            pairs = [(i, j) for i in range(len(M)) for j in range(len(M)) if i != j and i not in L and
                     any(a == b for a, b in zip(M[i], M[j])) and j in L]
            if pairs and len(p.S) + len(p.T) < v:
                i, j = rng.choice(pairs)
                L.append(i)
                return
            if len(M) >= 2 and not L and v >= 2:
                agree = [(i, j) for i, j in itertools.combinations(range(len(M)), 2)
                         if any(a == b for a, b in zip(M[i], M[j]))]
                if agree and len(p.S) + len(p.T) + 2 <= v:
                    L.extend(rng.choice(agree))
                    return
        c["fault"] = None
    elif fault == "ctj_budget":
        p = rng.choice(prods)
        a = p.first.special if p.first.rows is not None and p.first.columns is None else None
        b = p.second.special if p.second.rows is not None and p.second.columns is None else None
        if a and b:
            ns = rng.randint(1, v)
            p.S, p.T = list(a[:ns]), list(b[:v + 1 - ns])
        else:
            c["fault"] = None
    elif fault == "ctj_rows":
        p = rng.choice(prods)
        side = rng.choice(["first", "second"])
        M = getattr(p, side).array(v)
        L = p.S if side == "first" else p.T
        if L and rng.random() < 0.5:
            L.append(L[0])
        else:
            L.append(len(M) + rng.randint(0, 2))
    elif fault == "ctj_nested":
        inner = [n for n in prods if n is not top]
        if inner:
            n = rng.choice(inner)
            if rng.random() < 0.5:
                n.N_decl += rng.choice([-1, 1])
            else:
                n.k_decl += 1
        else:
            c["fault"] = None
    elif fault == "ctj_columns":
        n = rng.choice([x for x in nodes_of(top) if x is not top])
        k = len(n.full(v)[0])
        n.columns = rng.choice([1, k + 1])
    elif fault == "ingredient_ca":
        n = rng.choice(leaves)
        n.how = rng.choice(["rows", "file"])
        # delete a row that alone shows some pair, unless it is a named constant row
        M = n.rows
        named = set()
        for p in prods:
            if p.first is n:
                named |= set(p.S)
            if p.second is n:
                named |= set(p.T)
        k = len(M[0])
        for i in rng.sample(range(len(M)), len(M)):
            if i in named or (n.special and i in n.special):
                continue
            rest = M[:i] + M[i + 1:]
            if cc.ca_missing(rest, 2, v):
                n.rows = rest
                n.special = [s - (s > i) for s in n.special] if n.special else n.special
                for p in prods:
                    if p.first is n:
                        p.S = [s - (s > i) for s in p.S]
                    if p.second is n:
                        p.T = [s - (s > i) for s in p.T]
                return
        c["fault"] = None
    elif fault == "shape":
        n = rng.choice(leaves)
        i, j = rng.randrange(len(n.rows)), rng.randrange(len(n.rows[0]))
        n.rows = [list(r) for r in n.rows]
        n.rows[i][j] = v
        n.bad_symbol = True
    elif fault == "ingredient_hash":
        n = rng.choice(leaves)
        n.how = "file"
        c["file_corrupt"] = n
    elif fault == "ingredient_table":
        n = rng.choice(leaves)
        n.how = "table"
        n.table_t = 1
    elif fault == "ctj_strength":
        c["t"] = 3
    elif fault == "N":
        c["exp_delta"] = (rng.choice([-1, 1]), 0)
    elif fault == "k":
        c["exp_delta"] = (0, 1)
    elif fault == "sha256":
        c["bad_sha"] = True


def evaluate(c):
    """the failing hypotheses by their definitions, and the array the recipe gives (None if it cannot
    be built)"""
    v, top = c["v"], c["top"]
    fails = set()
    for n in nodes_of(top):
        if n.rows is not None:
            if any(x >= v for r in n.rows for x in r):
                fails.add("shape")
            elif not covers(n.rows, 2, v):
                fails.add("ingredient_ca" if n.how != "table" else "ingredient_table")
            if n.how == "table" and n.table_t < 2:
                fails.add("ingredient_table")
            if c["file_corrupt"] is n:
                fails.add("ingredient_hash")
    if c["t"] != 2:
        fails.add("ctj_strength")
    built_ok = True
    for n in nodes_of(top):
        if n.columns is not None:
            try:
                k = len(n.full(v)[0])
            except Exception:
                built_ok = False
                continue
            if not 2 <= n.columns <= k:
                fails.add("ctj_columns")
    for p in [n for n in nodes_of(top) if n.rows is None]:
        try:
            A, B = p.first.array(v), p.second.array(v)
        except Exception:
            built_ok = False
            continue
        for M, L in ((A, p.S), (B, p.T)):
            if any(x >= len(M) for x in L) or len(set(L)) != len(L):
                fails.add("ctj_rows")
            Lv = [x for x in L if x < len(M)]
            if any(any(a == b for a, b in zip(M[i], M[j])) for i, j in itertools.combinations(Lv, 2)):
                fails.add("ctj_constant")
        if len(set(p.S)) + len(set(p.T)) > v:
            fails.add("ctj_budget")
        if p is not top:
            try:
                F = p.full(v)
                if (len(F), len(F[0])) != (p.N_decl, p.k_decl):
                    fails.add("ctj_nested")
            except Exception:
                built_ok = False
    out = None
    if built_ok and not fails & {"ctj_rows", "ctj_constant", "ctj_budget", "shape", "ctj_columns"}:
        try:
            out = top.array(v)
        except Exception:
            out = None
    if out is not None:
        N, k = len(out), len(out[0])
        if c["exp_delta"] != (0, 0):
            fails.add("N" if c["exp_delta"][0] else "k")
        if c["bad_sha"]:
            fails.add("sha256")
        c["exp"] = (N + c["exp_delta"][0], k + c["exp_delta"][1],
                    "0" * 64 if c["bad_sha"] else sha(canon(out)))
    else:
        c["exp"] = None
    return fails, out


def write_case(c, folder, table, idx):
    d = os.path.join(folder, "case%04d" % idx)
    os.makedirs(d)
    v = c["v"]
    counter = [0]

    def spec(n):
        if n.rows is None:
            s = {"product": {"first": spec(n.first), "second": spec(n.second), "constant": [n.S, n.T]},
                 "N": n.N_decl, "k": n.k_decl}
        elif n.how == "rows":
            s = {"rows": n.rows}
        elif n.how == "file":
            counter[0] += 1
            fn = "leaf%d.txt" % counter[0]
            text = canon(n.rows)
            with open(os.path.join(d, fn), "w") as f:
                f.write(text)
            h = sha(text)
            if c["file_corrupt"] is n:
                h = sha(text + "0 \n")
            s = {"file": fn, "sha256": h}
        else:
            text = canon(n.rows)
            h = sha(text)
            if h not in table.seen:
                table.add(h, text, n.table_t, v, len(n.rows[0]), len(n.rows))
                table.seen.add(h)
            s = {"table": h}
        if n.columns is not None:
            s["columns"] = n.columns
        return s

    top = c["top"]
    exp = c["exp"] or (1, 1, "0" * 64)
    cert = {"format": "construction-cert-1", "construction": "product-ctj-1", "t": c["t"], "v": v,
            "first": spec(top.first), "second": spec(top.second), "constant": [top.S, top.T],
            "expected": {"N": max(1, exp[0]), "k": max(1, exp[1]), "array_sha256": exp[2]}}
    path = os.path.join(d, "cert.json")
    with open(path, "w") as f:
        json.dump(cert, f)
    return path


# ---------------------------------------------------------------------------------------------
# mutation testing

def disabled(c):
    return []


def _budget_weak(c):                 # |S| + |T| <= v + 1
    return [n["where"] for n in cc.ctj_products(c)
            if len(set(n["constant"][0])) + len(set(n["constant"][1])) > c["v"] + 1]


def _constant_weak(c):               # the last column of an ingredient is not compared
    out = []
    for n in cc.ctj_products(c):
        for role, L in zip(("first", "second"), n["constant"]):
            M = cc.ctj_array(c, n[role])
            L = [x for x in L if x < len(M)]
            for a, b in itertools.combinations(L, 2):
                if any(x == y for x, y in zip(M[a][:-1], M[b][:-1])):
                    out.append(n["where"])
    return out


def install(name, fn):
    saved = (list(cc.CTJ_CHECKS), list(cc.POST_CHECKS), list(cc.KIND_POST_CHECKS), list(cc.TABLE_CHECKS))
    for lst in (cc.CTJ_CHECKS, cc.POST_CHECKS, cc.KIND_POST_CHECKS, cc.TABLE_CHECKS):
        lst[:] = [(n, fn if n == name else f) for n, f in lst]
    return saved


def restore(saved):
    cc.CTJ_CHECKS[:], cc.POST_CHECKS[:], cc.KIND_POST_CHECKS[:], cc.TABLE_CHECKS[:] = saved


def run_checker(path, table_dir, write=None):
    try:
        r = cc.run(path, write, table_dir=table_dir)
        return r["ok"], {f[0] for f in r["failures"]}, r["sha256"]
    except cc.CertError as e:
        return False, {"malformed: %s" % e}, None


def main():
    args = sys.argv[1:]
    ncases = int(args[args.index("--cases") + 1]) if "--cases" in args else 300
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20261110
    rng = random.Random(seed)
    t0 = time.time()
    work = tempfile.mkdtemp(prefix="cactj-")
    cav = os.path.join(work, "ca_verify")
    subprocess.check_call(["cc", "-O2", "-pthread", "-o", cav, os.path.join(ROOT, "ca_verify.c")])
    table = MiniTable(os.path.join(work, "table"))
    table.seen = set()
    cases = []
    for idx in range(ncases):
        c = build_case(rng)
        if idx % 3:
            fault = FAULTS[idx % len(FAULTS)] if idx % 2 else rng.choice(FAULTS)
            for _ in range(100):
                plant(rng, c, fault)
                if c["fault"]:
                    break
                c = build_case(rng)
        fails, out = evaluate(c)
        path = write_case(c, work, table, idx)
        cases.append((c, path, fails, out))
    table.flush()
    # a fault in the rows of the recipe (no array by the independent code): the certificate's expected
    # values are set to what the checker builds anyway, so that the planted fault is the only failure
    # and a mutant without its check accepts that array
    for c, path, fails, out in cases:
        if c["exp"] is None and c["fault"] in ("ctj_constant", "ctj_budget", "ctj_rows", "ctj_columns"):
            try:
                r = cc.run(path, table_dir=table.dir)
            except cc.CertError:
                continue
            if r["sha256"]:
                cert = json.load(open(path))
                cert["expected"] = {"N": r["N"], "k": r["k"], "array_sha256": r["sha256"]}
                json.dump(cert, open(path, "w"))
    errors, stats = [], {}
    brute = [0, 0]
    theorem = [0, 0]
    a5 = {"ctj_constant": [0, 0], "ctj_budget": [0, 0]}
    nested = sum(1 for c, _, _, _ in cases if any(n.rows is None for n in nodes_of(c["top"].first))
                 or any(n.rows is None for n in nodes_of(c["top"].second)))
    for c, path, fails, out in cases:
        key = c["fault"] or "valid"
        st = stats.setdefault(key, [0, 0, 0, 0])
        st[0] += 1
        wpath = path + ".out"
        ok, got, csha = run_checker(path, table.dir, wpath)
        cover = None
        if out is not None and out and all(0 <= x < c["v"] for r in out for x in r):
            with open(wpath + ".ind", "w") as f:
                f.write(canon(out))
            cover = subprocess.run([cav, wpath + ".ind", "2", str(c["v"]), "1"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL).returncode == 0
            if len(out) * cc.comb(len(out[0]), 2) <= 40000:
                brute[0] += 1
                if covers(out, 2, c["v"]) != cover:
                    brute[1] += 1
                    errors.append("ca_verify and brute force disagree on %s" % path)
        else:
            cover = False
        if c["fault"] in a5 and fails == {c["fault"]} and os.path.isfile(wpath):
            # the array the checker builds anyway from the faulty recipe
            bad = [list(map(int, ln.split())) for ln in open(wpath)]
            if bad:
                a5[c["fault"]][0] += 1
                a5[c["fault"]][1] += not (all(0 <= x < c["v"] for r in bad for x in r) and covers(bad, 2, c["v"]))
        if ok:
            st[1] += 1
        if cover:
            st[2] += 1
        if c["fault"] and c["fault"] in fails:
            st[3] += 1
        if ok != (not fails):
            errors.append("A1 %s %s: checker ok=%s %s, independent %s" % (path, key, ok, sorted(got), sorted(fails)))
        if c["fault"] and c["fault"] in fails and c["fault"] not in got:
            errors.append("A2 %s %s: planted fault not reported (%s)" % (path, key, sorted(got)))
        if ok:
            wsha = hashlib.sha256(open(wpath, "rb").read()).hexdigest()
            if not cover or csha != sha(canon(out)) or wsha != csha:
                errors.append("A3 %s %s: accepted, covering=%s" % (path, key, cover))
        if not fails:
            theorem[0] += 1
            if not cover:
                theorem[1] += 1
                errors.append("A4 %s %s: hypotheses hold but the array is not covering" % (path, key))
    print("seed %d, %d certificates (%d with a nested product), %.1f s" % (seed, len(cases), nested, time.time() - t0))
    print("%-18s %6s %8s %8s %10s" % ("case", "certs", "accepted", "covering", "fault real"))
    for label, st in sorted(stats.items()):
        print("%-18s %6d %8d %8d %10d" % (label, st[0], st[1], st[2], st[3]))
    print("theorem: %d certificates satisfy every hypothesis; %d of their arrays not covering" % tuple(theorem))
    print("ca_verify vs brute force: %d arrays, %d disagreements" % tuple(brute))
    for f, (n, bad) in sorted(a5.items()):
        print("A5 %s: %d arrays built anyway, %d of them not a covering array over v symbols" % (f, n, bad))

    mutants = [("disable:" + n, n, disabled) for n in CHECK_NAMES] + [
        ("ctj_budget: |S| + |T| <= v + 1", "ctj_budget", _budget_weak),
        ("ctj_constant: last column not compared", "ctj_constant", _constant_weak)]
    survivors = 0
    print("mutation testing (%d mutants):" % len(mutants))
    for mname, name, fn in mutants:
        saved = install(name, fn)
        killed = unsound = 0
        try:
            for c, path, fails, out in cases:
                ok, got, csha = run_checker(path, table.dir, path + ".mut")
                if (ok != (not fails)) or (c["fault"] and c["fault"] in fails and c["fault"] not in got):
                    killed += 1
                if ok and fails:
                    rows = [list(map(int, ln.split())) for ln in open(path + ".mut")]
                    if not (rows and all(0 <= x < c["v"] for r in rows for x in r) and covers(rows, 2, c["v"])):
                        unsound += 1
        finally:
            restore(saved)
        must = name not in IMPLIED or mname != "disable:" + name
        survivors += must and killed == 0
        print("  %-42s %-8s by %4d cases; accepts a non-covering array: %d%s"
              % (mname, "KILLED" if killed else "SURVIVED", killed, unsound,
                 "" if must else " (implied by shape and ctj_budget for this kind)"))
        if not must and unsound:
            errors.append("%s accepts a non-covering array" % mname)
    print("mutants surviving: %d" % survivors)
    if survivors:
        errors.append("%d mutant(s) survived" % survivors)
    shutil.rmtree(work, ignore_errors=True)
    print("total %.0f s" % (time.time() - t0))
    if errors:
        print("FAILURES (%d):" % len(errors))
        for e in errors[:40]:
            print("  " + e)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
