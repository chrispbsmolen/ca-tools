#!/usr/bin/env python3
"""Tests of mode fastprog of cphfcheck.c (standard library only).

Usage: python3 tools/cphf/tests/test_fastprog.py [--n N] [--planted P] [--seed S] [--quick]
                                                 [--no-mutations] [--mutation-n N] [--quiet]

  diff       random families (the generators of test_progression.py: progression rows of every kind
             of that suite, generic, shared A, monomial and conjugated monomial A with many WILD
             columns, affine, -I, I, eigenvector and invariant-subspace starts; other and dead rows;
             all-progression and near-CPHF families), t = 3..6, q up to 13: fastprog with 1 to 3
             threads and progression of the same build must give the exit code, the count, the first
             uncovered set and the 'checked' total of mode full of the first published build
             (tests/cphfcheck_a5ad0b7.c.ref), the full sorted list of uncovered sets (up to LISTCAP)
             of mode full of the unmodified source with CPHFCHECK_LIST, a consistent completeness line, and the row classification of the independent Python
             classifier. Built twice: -O3 -march=native (the AVX2 key pass where the machine has it)
             and -DNO_AVX2 (scalar key pass).
  shards     in about a third of the diff cases (every case with --shards-all): fastprog as m shards
             ("shard i m", m = 1, 2, 3, 5 or more than the outer loop has indices), combined by
             tools/cphf_cert.py combine(): count, first set and list equal to the unsharded fastprog
             run and to mode full; a missing, repeated or relabelled shard is refused
  planted    a set failing in every progression row is made dependent in every other row; fastprog
             (unsharded and sharded) must report it
  mutations  each mutant patches one step of the fastprog code (scalar build) and must make at least
             one test of a reduced diff + planted run fail; "wildcard-row-kept" is an equivalent
             mutant kept as a control (expected to pass, reported, not counted as a failure)
Prints FAIL lines (every line without --quiet) and a summary; exit status 0 only if all passed.
"""
import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import test_progression as T  # noqa: E402  (fields, generators, classifier, run, build)
import cphf_cert as cc  # noqa: E402

SRC = os.path.join(HERE, "..", "cphfcheck.c")
ORIG = os.path.join(HERE, "cphfcheck_a5ad0b7.c.ref")
LISTCAP = 40000
WORK = None

MUTANTS = [
    ("wild-disabled", "WILD columns treated as an ordinary class in the key pass (scalar path)",
     "        key[i] = wl ? -1 : kk;", "        key[i] = kk; (void)wl;"),
    ("no-probe", "WILD columns never matched with non-WILD columns",
     "            if ((v >> 16) != st) continue;\n            fjoin_chain", "            if (1) continue;\n            fjoin_chain"),
    ("no-wild-wild", "pairs of two WILD columns skipped",
     "        for (int w2 = w + 1; w2 < nw; w2++) fpair_rest(X, 0, c0 + iw, c0 + wlist[w2]);", "        (void)wlist;"),
    ("chain-first-only", "only the most recent column with the same key is paired",
     "    for (int l = prev; l >= 0; l = nxt[l]) {", "    for (int l = prev; l >= 0; l = -1) {"),
    ("probe-one-class-short", "a WILD column probes q of the q+1 compatible classes",
     "if (d < j && (mk >> d & 1)) { lo[d] = 0; hi[d] = q; }", "if (d < j && (mk >> d & 1)) { lo[d] = 0; hi[d] = q - 1; }"),
    ("range-off-by-one", "column p+1 never a candidate",
     "    int m = k - 1 - p, c0 = p + 1, nw = 0;", "    int m = k - 2 - p, c0 = p + 2, nw = 0;"),
    ("line-self", "LINE[P][P] a class instead of WILD",
     "        for (int Q = 0; Q < NPTS; Q++) {\n            if (Q == P) continue;",
     "        for (int Q = 0; Q < NPTS; Q++) {\n            if (Q == P) { LN(P)[Q] = 0; continue; }"),
    ("survivors-unchecked", "pairs passing the joined rows reported without the remaining rows",
     "    int last = j >= F->nlive;                 /* no live row after the j rows */", "    int last = 1;"),
    ("no-normalization", "point index of a vector not projective (scalar multiples distinct)",
     "        PTIDX[code] = (uint16_t)idx_of_norm[w];", "        PTIDX[code] = (uint16_t)(code % NPTS);"),
    ("prime-rank-ignored", "a prefix P' of rank < t-3 in a row is not treated as a wildcard row",
     "        if (rk < npp) { X->wildrows += k - 1 - last; continue; }", "        (void)rk;"),
    ("wildcard-row-kept", "CONTROL (equivalent mutant): a p with P dependent in a row keeps the row with its all-WILD table row",
     "        if (pr[p] == ZEROP) { X->wildrows++; continue; }", "        if (0) { X->wildrows++; continue; }"),
    ("progression-check-truncated", "u_c = A u_(c-1) checked only up to c = k-2",
     "    for (int c = 1; c <= k - 1; c++) {\n        uint8_t img[MAXT];", "    for (int c = 1; c <= k - 2; c++) {\n        uint8_t img[MAXT];"),
    ("shift-last-skipped", "the last shift of a representative skipped",
     "    for (int a = 0; a <= k - 1 - D[t - 1]; a++) {", "    for (int a = 0; a < k - 1 - D[t - 1]; a++) {"),
    ("shard-owned-ignored", "a fastprog shard (t >= 5) does every outer index, not only its own",
     "                if (!owned(p1)) continue;\n                Ctx *X = &ctxs[ctx_tid()];\n                int pp[MAXT];",
     "                Ctx *X = &ctxs[ctx_tid()];\n                int pp[MAXT];"),
    ("shard-t4-misdealt", "a fastprog shard (t = 4) does index 1 when it owns index 2, instead of when it owns 1",
     "                if (!owned(p)) continue;", "                if (!owned(p == 1 ? 2 : p)) continue;"),
]
CONTROLS = {"wildcard-row-kept"}


def build(src, out, extra):
    cmd = ["gcc", "-O3", "-fopenmp"] + list(extra) + ["-x", "c", "-o", out, src]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return out if p.returncode == 0 else None


def run(exe, fam, t, q, args, listing=False):
    return T.run(exe, fam, t, q, args, listing=listing, timeout=1200)


def shard_text(exe, fam, t, q, th, i, m):
    env = {k_: v for k_, v in os.environ.items() if k_ not in ("CPHFCHECK_LIST", "CPHFCHECK_LISTCAP")}
    env["CPHFCHECK_LISTCAP"] = str(LISTCAP + 1)
    p = subprocess.run([exe, fam, str(t), str(q), "fastprog", str(th), "shard", str(i), str(m)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env, timeout=1200)
    meta = "# family_sha256: f\n# tool: x\n# method: fastprog\n# t: %d\n# q: %d\n" % (t, q)
    return meta + p.stdout + "# exit: %d\n" % p.returncode


def k_for(rng, t):
    if t == 3:
        return rng.randint(4, 70)
    if t == 4:
        return rng.randint(5, 60)
    if t == 5:
        return rng.randint(6, 36) if rng.random() < 0.8 else rng.randint(36, 60)
    return rng.randint(7, 24) if rng.random() < 0.8 else rng.randint(24, 34)


def make_rows(rng, t, q, k):
    F = T.field(q)
    style = rng.random()
    if style < 0.25:                              # near-CPHF: spanning kinds only
        npg = rng.randint(3, 5); no = rng.randint(0, 2)
        shared = T.rand_inv(F, rng, t)
        rows = [T.prog_row(F, rng, t, k, rng.choice(["generic", "shared", "conjmonomial", "affine"]), shared) for _ in range(npg)]
        rows += [T.other_row(F, rng, t, k, rng.choice(["random", "affine"])) for _ in range(no)]
    elif style < 0.4:                             # WILD heavy: small order A (monomial), plus generic
        npg = rng.randint(1, 3); no = rng.randint(0, 2)
        rows = [T.prog_row(F, rng, t, k, rng.choice(["monomial", "conjmonomial", "negI", "generic"])) for _ in range(npg)]
        rows += [T.other_row(F, rng, t, k, rng.choice(T.O_KINDS)) for _ in range(no)]
    elif style < 0.5:                             # all progression rows (fully cyclic style families)
        rows = [T.prog_row(F, rng, t, k, "generic") for _ in range(rng.randint(1, 6))]
    else:
        rows = T.gen_family(rng, t, q, k, rng.randint(0, 4), rng.randint(0, 3))
    rng.shuffle(rows)
    return rows


class Suite:
    def __init__(self, exes, ref, orig, quiet):
        self.exes, self.ref, self.orig, self.quiet = exes, ref, orig, quiet
        self.res = []
        self.nid = 0

    def record(self, sec, name, ok, detail=""):
        self.res.append((sec, ok))
        if not ok or not self.quiet:
            print("%s %s %s %s" % ("PASS" if ok else "FAIL", sec, name, detail), flush=True)

    def tmp(self):
        self.nid += 1
        return os.path.join(WORK, "f_%d.txt" % self.nid)

    def compare(self, rows, t, q, rng, must_contain=None, shards=False):
        """(ok, detail) of the unsharded comparison, and the shard results as a list of (name, ok, detail)"""
        fam = self.tmp(); T.write_family(rows, q, fam); F = T.field(q)
        sh = []
        try:
            ref = run(self.orig, fam, t, q, ["full", 1])
            if ref["code"] not in (0, 1) or ref["count"] is None:
                return (False, "full failed %s" % ref["err"][:200]), sh
            th = rng.choice([1, 2, 3])
            exe = rng.choice(self.exes)
            want_list = ref["count"] <= LISTCAP
            new = run(exe, fam, t, q, ["fastprog", th], listing=want_list)
            old = run(exe, fam, t, q, ["progression", th])
            for name, r in (("fastprog", new), ("progression", old)):
                if r["code"] != ref["code"] or r["count"] != ref["count"] or r["first"] != ref["first"]:
                    return (False, "%s: exit %s count %s first %s vs full exit %s count %s first %s | %s" % (
                        name, r["code"], r["count"], r["first"], ref["code"], ref["count"], ref["first"],
                        (r["out"] + r["err"])[-400:])), sh
                if "INTERNAL" in r["out"] or "completeness" not in r["out"]:
                    return (False, "%s: internal failure or no completeness line" % name), sh
                m = re.search(r"= (\d+) \(expected (\d+)\)", r["out"])
                if not m or m.group(1) != m.group(2) or r.get("checked") != ref.get("checked"):
                    return (False, "%s: completeness mismatch" % name), sh
            for i, row in enumerate(rows):
                if new["rows"].get(i) != T.classify_py(F, row, t):
                    return (False, "row %d classified %s, python %s" % (i, new["rows"].get(i), T.classify_py(F, row, t))), sh
            L = None
            if want_list:
                L = run(self.ref, fam, t, q, ["full", 1], listing=True)["list"]
                if len(L) != ref["count"]:
                    return (False, "reference listing inconsistent"), sh
                if new["list"] != L:
                    miss = sorted(set(L) - set(new["list"]))[:3]; extra = sorted(set(new["list"]) - set(L))[:3]
                    return (False, "fastprog list differs: missing %s extra %s" % (miss, extra)), sh
                if must_contain is not None and tuple(must_contain) not in set(L):
                    return (False, "planted set not reported"), sh
            elif must_contain is not None:
                return (False, "too many uncovered to confirm the planted set"), sh
            if shards:
                lo, hi, _ = cc.outer_domain("fastprog", len(rows[0]), t)
                for m in sorted({1, rng.choice([2, 3, 5]), (hi - lo) + rng.randint(1, 2)}):
                    ex = rng.choice(self.exes)
                    texts = [shard_text(ex, fam, t, q, rng.choice([1, 2]), i, m) for i in range(m)]
                    nm = "m=%d" % m
                    try:
                        res = cc.combine(texts, "fastprog", len(rows[0]), t)
                    except cc.CertError as e:
                        sh.append((nm, False, "combine refused a complete set: %s" % e)); continue
                    ok = (res["uncovered"] == ref["count"] == new["count"] and res["first"] == ref["first"] == new["first"])
                    if ok and L is not None and res["listed_all"]:
                        ok = res["sets"] == L
                    if ok and must_contain is not None:
                        ok = tuple(must_contain) in set(res["sets"])
                    sh.append((nm, ok, "uncovered %d vs %d, first %s vs %s" % (res["uncovered"], ref["count"], res["first"], ref["first"])))
                    if m >= 2:
                        for what, tx in (("missing", texts[:-1]), ("repeated", texts + [texts[0]]),
                                         ("relabelled", [texts[0], texts[0].replace("SHARD i=0 ", "SHARD i=1 ")] + texts[2:])):
                            try:
                                cc.combine(tx, "fastprog", len(rows[0]), t)
                                sh.append((nm + " " + what, False, "accepted"))
                            except cc.CertError:
                                sh.append((nm + " " + what, True, "refused"))
            return (True, "uncovered %d th=%d" % (ref["count"], th)), sh
        finally:
            os.remove(fam)


def section_diff(S, rng, n, shards_all):
    for i in range(n):
        t = rng.choice([3, 4, 4, 5, 5, 5, 6, 6])
        q = rng.choice([3, 4, 5, 7, 8, 9, 11, 13])
        if t >= 5 and q >= 9 and rng.random() < 0.6:
            q = rng.choice([3, 4, 5, 7])
        k = k_for(rng, t)
        rows = make_rows(rng, t, q, k)
        name = "#%d t=%d q=%d k=%d n=%d" % (i, t, q, k, len(rows))
        (ok, d), sh = S.compare(rows, t, q, rng, shards=shards_all or rng.random() < 0.35)
        S.record("diff", name, ok, d)
        for nm, ok2, d2 in sh:
            S.record("shards", name + " " + nm, ok2, d2)


def section_planted(S, rng, n):
    done = tries = 0
    while done < n and tries < 60 * n:
        tries += 1
        t = rng.choice([3, 4, 4, 5, 5, 6]); q = rng.choice([3, 4, 5, 7, 8, 9])
        if t >= 5:
            q = rng.choice([3, 4, 5, 7])
        k = {3: rng.randint(12, 50), 4: rng.randint(10, 36), 5: rng.randint(10, 24), 6: rng.randint(9, 16)}[t]
        F = T.field(q)
        prow = [T.prog_row(F, rng, t, k, rng.choice(["generic", "shared", "monomial", "conjmonomial", "affine"]), T.rand_inv(F, rng, t))
                for _ in range(rng.randint(1, 4))]
        prow = [r for r in prow if T.classify_py(F, r, t) == "progression"]
        if not prow:
            continue
        fam = S.tmp(); T.write_family(prow, q, fam)
        try:
            ref = run(S.orig, fam, t, q, ["full", 1])
            if not ref["count"] or ref["count"] > 30000:
                continue
            pool = run(S.ref, fam, t, q, ["full", 1], listing=True)["list"]
        finally:
            os.remove(fam)
        X = rng.choice(pool)
        orows = [T.other_row(F, rng, t, k, rng.choice(["random", "affine", "few"])) for _ in range(rng.randint(1, 3))]
        for row in orows:
            j = rng.randrange(t); others = [row[c] for i, c in enumerate(X) if i != j]
            row[X[j]] = F.combo([rng.randrange(q) for _ in others], others, t)
        name = "t=%d q=%d k=%d set=%s" % (t, q, k, X)
        (ok, d), sh = S.compare(prow + orows, t, q, rng, must_contain=X, shards=rng.random() < 0.5)
        S.record("planted", name, ok, d)
        for nm, ok2, d2 in sh:
            S.record("shards", name + " " + nm, ok2, d2)
        done += 1


def section_mutations(S, ref, orig, seed, n, planted):
    src = open(SRC).read()
    for name, desc, old, new in MUTANTS:
        cnt = src.count(old)
        if cnt != 1:
            S.record("mutation", name, False, "patch target found %d times" % cnt)
            continue
        msrc = os.path.join(WORK, "mut.c")
        open(msrc, "w").write(src.replace(old, new, 1))
        mexe = build(msrc, os.path.join(WORK, "mut"), ["-DNO_AVX2"])
        if not mexe:
            S.record("mutation", name, False, "build failed"); continue
        M = Suite([mexe], ref, orig, True)
        M.record = lambda sec, nm, ok, d="", M=M: M.res.append((sec, ok))
        M.nid = 100000
        rng = random.Random(seed)
        section_diff(M, rng, n, name.startswith("shard"))
        section_planted(M, rng, planted)
        fails = sum(1 for _, ok in M.res if not ok)
        if name in CONTROLS:
            S.record("control", name, fails == 0, "%s: %d of %d tests fail (equivalent mutant, 0 expected)" % (desc, fails, len(M.res)))
        else:
            S.record("mutation", name, fails > 0, "%s: caught by %d of %d tests" % (desc, fails, len(M.res)))
        os.remove(msrc); os.remove(mexe)


def main():
    global WORK
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--planted", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--quick", action="store_true", help="--n 80 --planted 20 --mutation-n 40")
    ap.add_argument("--shards-all", action="store_true")
    ap.add_argument("--no-mutations", action="store_true")
    ap.add_argument("--mutation-n", type=int, default=80)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if a.quick:
        a.n, a.planted, a.mutation_n = 80, 20, 40
    WORK = tempfile.mkdtemp(prefix="cphffast-")
    try:
        exes = [build(SRC, os.path.join(WORK, "native"), ["-march=native"]),
                build(SRC, os.path.join(WORK, "scalar"), ["-DNO_AVX2"])]
        ref = build(SRC, os.path.join(WORK, "ref"), [])          # mode full with CPHFCHECK_LIST, never mutated
        orig = build(ORIG, os.path.join(WORK, "orig"), [])
        if not all(exes) or not ref or not orig:
            raise SystemExit("build failed")
        rng = random.Random(a.seed)
        S = Suite(exes, ref, orig, a.quiet)
        section_diff(S, rng, a.n, a.shards_all)
        section_planted(S, rng, a.planted)
        if not a.no_mutations:
            section_mutations(S, ref, orig, a.seed + 4, a.mutation_n, 10)
        secs = {}
        for s, ok in S.res:
            secs.setdefault(s, [0, 0]); secs[s][0] += 1; secs[s][1] += not ok
        for s, (n, f) in secs.items():
            print("%-9s %5d tests, %d failed" % (s, n, f))
        bad = sum(1 for _, ok in S.res if not ok)
        print("SUMMARY: %d tests, %d failed" % (len(S.res), bad))
        return 1 if bad else 0
    finally:
        shutil.rmtree(WORK, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
