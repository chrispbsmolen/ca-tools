#!/usr/bin/env python3
"""Tests of the shards, the estimate and mode auto of cphfcheck.c, and of the combiner in
tools/cphf_cert.py (standard library only).

Usage: python3 tools/cphf/tests/test_shards.py [--cases N] [--seed S]

  shards     random families (the generators of test_progression.py: progression rows of many kinds,
             other rows, dead rows; and cyclic families with one and two column orbits), modes full,
             fullfast, progression, fastprog and cyclic s, m shards for m from 1 to more than the outer loop has
             indices, 1 or 2 threads, OpenMP and plain builds: the combined count, the smallest
             uncovered t-set and the full list equal those of the unsharded run (full with
             CPHFCHECK_LIST is the reference list)
  detect     for every sharded case: a missing shard, a repeated shard, a shard relabelled as another,
             shards of a different m and a truncated shard output are all refused by combine()
  deal       the deal of cphf_cert.deal() (the planner's replica) gives the shard weights cphfcheck prints
  auto       mode auto reaches the verdict of mode full, with the method of smallest estimate
  canon      cphfcheck canon equals the Python serialization cphf1 and its hash
  expand     the buffered expand writes the same bytes as the first published version
             (tests/cphfcheck_a5ad0b7.c.ref), plain and affine
Prints PASS/FAIL per test and a summary; exit status 0 only if everything passed.
"""
import argparse
import hashlib
import os
import random
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import test_progression as tp  # noqa: E402  (fields, generators, build)
import cphf_cert as cc  # noqa: E402

SRC = os.path.join(HERE, "..", "cphfcheck.c")
ORIG = os.path.join(HERE, "cphfcheck_a5ad0b7.c.ref")
LISTCAP = 20000
RES = []
WORK = None


def record(sec, name, ok, detail=""):
    RES.append((sec, name, ok))
    if not ok or os.environ.get("VERBOSE"):
        print("%s %s %s %s" % ("PASS" if ok else "FAIL", sec, name, detail), flush=True)


def runx(exe, args, listing=False):
    env = dict(os.environ)
    env.pop("CPHFCHECK_LIST", None)
    env.pop("CPHFCHECK_LISTCAP", None)
    if listing:
        env["CPHFCHECK_LIST"] = "1"
    p = subprocess.run([exe] + [str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, env=env)
    return p.returncode, p.stdout, p.stderr


def shard_text(exe, fam, t, q, method, threads, i, m):
    margs = ["cyclic", method.split()[1]] if method.startswith("cyclic") else [method]
    code, out, err = runx(exe, [fam, t, q] + margs + [threads, "shard", i, m])
    meta = "# family_sha256: f\n# tool: x\n# method: %s\n# t: %d\n# q: %d\n" % (method, t, q)
    return meta + out + "# exit: %d\n" % code


def cyclic_family(F, rng, t, k, s, nrows):
    """rows with the symmetry col -> col + s: column c = s j + i holds A^j x_i, A the companion matrix of
    x^t - a, so A^(k/s) = a^(k/(s t)) I when t divides k/s"""
    rows = []
    while len(rows) < nrows:
        a = rng.randrange(1, F.q)
        A = [[0] * t for _ in range(t)]
        for i in range(t - 1):
            A[i + 1][i] = 1
        A[0][t - 1] = a
        xs = [tp.rand_vec(F, rng, t) for _ in range(s)]
        row = [None] * k
        cur = list(xs)
        for j in range(k // s):
            for i in range(s):
                row[s * j + i] = cur[i]
            cur = [F.matvec(A, x) for x in cur]
        # cphfcheck certifies a symmetry only in rows whose columns 0..k-s-1 span GF(q)^t
        if F.rank(row[:k - s]) == t:
            rows.append(row)
    return rows


def unsharded_ref(exe, fam, t, q):
    code, out, _ = runx(exe, [fam, t, q, "full", 1], listing=True)
    L = sorted(tuple(int(x) for x in l.split()[1:]) for l in out.splitlines() if l.startswith("U "))
    m = re.search(r"uncovered (\d+)", out)
    return code, int(m.group(1)), L


def check_case(exes, rng, rows, t, q, k, label, cyclic_s=0):
    fam = os.path.join(WORK, "f.txt")
    tp.write_family(rows, q, fam)
    exe = exes[0]
    code, count, L = unsharded_ref(exe, fam, t, q)
    methods = ["full", "fullfast", "progression", "fastprog"] + (["cyclic %d" % cyclic_s] if cyclic_s else [])
    for method in methods:
        lo, hi, d = cc.outer_domain(method, k, t)
        width = hi - lo
        for m in sorted({1, 2, rng.randint(2, 6), width + rng.randint(1, 3)}):
            ex = rng.choice(exes)
            th = rng.choice([1, 2])
            texts = [shard_text(ex, fam, t, q, method, th, i, m) for i in range(m)]
            name = "%s %s m=%d" % (label, method, m)
            try:
                res = cc.combine(texts, method, k, t)
            except cc.CertError as e:
                record("shards", name, False, "combine refused a complete set: %s" % e)
                continue
            if method.startswith("cyclic"):
                # cyclic counts representatives (smallest column < s): compare with the list restricted to them
                want = [x for x in L if x[0] < cyclic_s]
            elif method in ("progression", "fastprog"):
                want = L                        # progression and fastprog list every uncovered t-set (all shifts)
            else:
                want = L
            ok = res["uncovered"] == len(want) and (res["first"] == (want[0] if want else None))
            if ok and len(want) <= LISTCAP and res["listed_all"]:
                ok = res["sets"] == want
            record("shards", name, ok, "uncovered %d vs %d, first %s vs %s" % (
                res["uncovered"], len(want), res["first"], want[0] if want else None))
            # the same shards, damaged
            if m >= 2:
                bad = {
                    "missing": texts[:-1],
                    "repeated": texts + [texts[0]],
                    "relabelled": [texts[0], texts[0].replace("SHARD i=0 ", "SHARD i=1 ")] + texts[2:],
                    "other m": texts[:-1] + [shard_text(ex, fam, t, q, method, th, m - 1, m + 1)],
                    "truncated": texts[:-1] + [re.sub(r"SHARD i=.*\n", "", texts[-1])],
                }
                for what, tx in bad.items():
                    try:
                        cc.combine(tx, method, k, t)
                        record("detect", "%s %s" % (name, what), False, "accepted")
                    except cc.CertError:
                        record("detect", "%s %s" % (name, what), True)
            # the planner's deal equals the shard weights cphfcheck prints
            if m >= 2 and d is not None:
                load = cc.deal(method, k, t, m)
                printed = [int(re.search(r"weight (\d+) of", x).group(1)) for x in texts]
                record("deal", name, printed == load, "%s vs %s" % (printed, load))
    # auto: the verdict of full, by the method of smallest estimate
    code_a, out_a, _ = runx(exe, [fam, t, q, "auto", 2])
    est = cc.parse_estimate(out_a)
    chosen = re.search(r"auto: method (.*)", out_a).group(1)
    best = min(est["methods"].values(), key=lambda e: e["core_seconds"])["core_seconds"]
    ok = code_a == code and chosen == est["cheapest"]["method"] and \
        abs(est["methods"][chosen.split()[0]]["core_seconds"] - best) <= 1e-12 * max(1, best)
    record("auto", label, ok, "exit %d vs full %d, chose %s" % (code_a, code, chosen))
    if cyclic_s:
        record("auto", label + " symmetry found", est["symmetry"] and cyclic_s % est["symmetry"] == 0,
               "found %s" % est["symmetry"])
    # canon
    can = os.path.join(WORK, "c.txt")
    runx(exe, [fam, t, q, "canon", can])
    py = cc.canonical_family(cc.read_family(fam, q, t), q, t)
    record("canon", label, open(can, "rb").read() == py and cc.family_identity(fam, q, t)[0] == hashlib.sha256(py).hexdigest())


def main():
    global WORK
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=160)
    ap.add_argument("--seed", type=int, default=20261102)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    WORK = tempfile.mkdtemp(prefix="cphfshard-")
    exes = [tp.build(SRC, os.path.join(WORK, "omp")), tp.build(SRC, os.path.join(WORK, "plain"), omp=False)]
    orig = tp.build(ORIG, os.path.join(WORK, "orig"))
    for i in range(a.cases):
        if i % 4 == 3:                                # cyclic families, one or two orbits
            t = rng.choice([2, 3, 3, 4, 4, 5])
            q = rng.choice([3, 4, 5, 7, 8, 9])
            if t >= 5:
                q = rng.choice([3, 4])
            s = rng.choice([1, 2])
            k = s * t * rng.randint(2, {2: 10, 3: 8, 4: 5, 5: 3}[t])
            F = tp.field(q)
            rows = cyclic_family(F, rng, t, k, s, rng.randint(1, 4))
            if rng.random() < 0.3:                    # a dead or a random row breaks the symmetry or not
                rows.append(tp.other_row(F, rng, t, k, "random"))
                s0 = 0
            else:
                s0 = s
            check_case(exes, rng, rows, t, q, k, "#%d cyclic t=%d q=%d k=%d s=%d" % (i, t, q, k, s), s0)
        else:
            t = rng.choice([2, 3, 3, 4, 4, 5, 5, 6])
            q = rng.choice([3, 4, 5, 7, 8, 9])
            if t >= 5 and q >= 7:
                q = rng.choice([3, 4, 5])
            k = {2: rng.randint(3, 30), 3: rng.randint(4, 40), 4: rng.randint(5, 30), 5: rng.randint(6, 22),
                 6: rng.randint(7, 14)}[t]
            rows = tp.gen_family(rng, t, q, k, rng.randint(0, 4), rng.randint(0, 3))
            check_case(exes, rng, rows, t, q, k, "#%d t=%d q=%d k=%d n=%d" % (i, t, q, k, len(rows)))
    # expand: buffered output equals the first published version
    for i in range(12):
        t = rng.choice([2, 3, 4, 5]); q = rng.choice([2, 3, 4, 5, 7, 8, 9, 16, 25, 27, 32])
        if q ** t > 40000:
            q = 3
        k = rng.randint(t, 40)
        affine = rng.random() < 0.5
        F = tp.field(q)
        rows = [[tuple(([1] if affine else [rng.randrange(q)]) + [rng.randrange(q) for _ in range(t - 1)])
                 for _ in range(k)] for _ in range(rng.randint(1, 4))]
        fam = os.path.join(WORK, "e.txt"); tp.write_family(rows, q, fam)
        outs = []
        for exe in (exes[0], exes[1], orig):
            path = os.path.join(WORK, "x%d.txt" % len(outs))
            code, out, err = runx(exe, [fam, t, q, "expand", path] + (["affine"] if affine else []))
            outs.append((code, out, err, open(path, "rb").read()))
        record("expand", "t=%d q=%d k=%d affine=%s" % (t, q, k, affine), outs[0] == outs[2] and outs[1] == outs[2])
    bad = [r for r in RES if not r[2]]
    secs = {}
    for s, _, ok in RES:
        secs.setdefault(s, [0, 0]); secs[s][0] += 1; secs[s][1] += not ok
    for s, (n, f) in secs.items():
        print("%-8s %5d tests, %d failed" % (s, n, f))
    print("%d tests, %d failed" % (len(RES), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        if WORK:
            import shutil
            shutil.rmtree(WORK, ignore_errors=True)
    sys.exit(code)
