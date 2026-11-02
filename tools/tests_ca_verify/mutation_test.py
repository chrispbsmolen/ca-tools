#!/usr/bin/env python3
"""Mutation test for ca_verify2.c.

Each mutant breaks one step of the algorithm (a single textual edit of the
source). The mutant is compiled and run on a corpus of arrays whose expected
output comes from the original ca_verify; the mutant must disagree with the
expected output on at least one array (be "killed"). The unmutated source
must agree everywhere.

Usage: mutation_test.py ORIG_EXE SOURCE.c [seed]
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import difftest  # noqa: E402
WILD = difftest.WILD

# (name, old text, new text, env for the run, what it breaks)
MUTANTS = [
    ("bin_value0_missing",
     "v4u u0 = (a0 | ~o0) & ldv(dm + ci * CH);                            \\",
     "v4u u0 = (~o0) & ldv(dm + ci * CH);                                 \\",
     {}, "binary kernel ignores a missing value 0 in the last chunk"),
    ("dm_includes_c",
     "if (wi == w0 && ((c + 1) & 63)) m &= ~0ULL << ((c + 1) & 63);",
     "if (wi == w0 && ((c + 1) & 63)) m &= ~0ULL << (c & 63);",
     {}, "candidate mask includes column c itself"),
    ("prefix_bound",
     "for (int cn = c + 1; cn <= K - 1 - (T - 1 - j); cn++) {",
     "for (int cn = c + 1; cn <= K - 2 - (T - 1 - j); cn++) {",
     {}, "enumeration skips the last prefix column"),
    ("empty_class_count",
     "w->missing += (long long)V * __builtin_popcountll(unc);",
     "w->missing += __builtin_popcountll(unc);",
     {}, "empty class counts one missing tuple instead of v"),
    ("rank_off_by_one",
     "unsigned long long rank = rank_ok ? part - (unsigned long long)(K - 1 - d) : 0;",
     "unsigned long long rank = rank_ok ? part - (unsigned long long)(K - 2 - d) : 0;",
     {}, "lexicographic rank off by one (thread assignment of examples)"),
    ("shard_partition",
     "int a = shard_i + i * shard_n;",
     "int a = i * shard_n;",
     {}, "all shards check the same column sets"),
    ("wildcard_as_zero",
     "if (*p == '-' && !isdigit((unsigned char)p[1])) { val = WILDCARD; p++; }",
     "if (*p == '-' && !isdigit((unsigned char)p[1])) { val = 0; p++; }",
     {}, "a '-' don't-care is read as symbol 0"),
    ("planes_cov_or",
     "            cov &= o;                                                           \\",
     "            cov |= o;                                                           \\",
     {"CA_VERIFY2_REP": "planes"}, "value-plane kernel never reports a gap"),
    ("onehot_never_bad",
     "VT_ bad = (a0 ^ full) & m0;                                             \\",
     "VT_ bad = (a0 ^ full) & m0 & (full ^ full);                             \\",
     {"CA_VERIFY2_REP": "onehot"}, "one-hot kernel never reports a gap in the last units"),
    ("sort_wrong_rows",
     "for (int i = 0; i < m; i++) rows[off[tmpu[i]]++] = tmp[i];",
     "for (int i = 0; i < m; i++) rows[off[tmpu[i]]++] = tmp[i] / 2;",
     {"CA_VERIFY2_CLASSES": "sort"}, "counting sort places wrong rows in classes"),
    ("slow_path_count",
     "w->missing += __builtin_popcountll(mu);",
     "w->missing += __builtin_popcountll(mu) > 0;",
     {}, "missing tuples counted at most once per word"),
    ("example_order",
     "while (j >= 0 && w->pd[j] > d) {",
     "while (0 && j >= 0 && w->pd[j] > d) {",
     {}, "examples of one prefix not sorted by column"),
    ("chunk4_data",
     "x3 = ldv(p + 3 * cs); \\",
     "x3 = ldv(p + 2 * cs); \\",
     {}, "four-chunk pass accumulates the third chunk's data for the fourth"),
    ("column_bitset_rows",
     "X[((size_t)c * V + s) * W + (r >> 6)] |= 1ULL << (r & 63);",
     "X[((size_t)c * V + s) * W + (r >> 6)] |= 1ULL << ((r + 1) & 63);",
     {}, "per-(column,value) row bitsets shifted by one row"),
    ("first_tuple_value",
     "if (umiss) { while (u < V && !((umiss[u] >> b) & 1)) u++; }",
     "if (umiss) { while (u < V - 1 && !((umiss[u] >> b) & 1)) u++; u = (u + 1) % V; }",
     {}, "reported first missing tuple has the wrong last value"),
    ("onehot_lane_mask",
     [("uint8_t val = (d > c && d < K) ? 0xff : 0;",
       "uint8_t val = (d >= c && d < K) ? 0xff : 0;"),
      ("if (d <= c || d >= K) continue;",
       "if (d < c || d >= K) continue;")],
     None,
     {"CA_VERIFY2_REP": "onehot"}, "one-hot candidate columns include column c (both guards)"),
    ("extract_rows_count",
     "m += n < 8 ? n : 8;",
     "m += n < 8 ? n : 7;",
     {"CA_VERIFY2_ROWS": "list"}, "row list extraction drops a row from words with 8 or more rows"),
    ("sperner_chunk2",
     "if (hor(u0 | u1)) { BIN_REPORT(ci, a0, o0); BIN_REPORT(ci + 1, a1, o1); } \\",
     "if (hor(u0 | u1)) { BIN_REPORT(ci, a0, o0); } \\",
     {}, "two-chunk pass drops gaps of its second chunk"),
]


def build(src, exe):
    p = subprocess.run(["cc", "-O2", "-pthread", "-o", exe, src], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    return p.returncode == 0, p.stderr


def make_corpus(rng, tmpdir):
    """Arrays with their t, v and the runs (threads / shards) to perform."""
    corpus = []
    fixed = [  # (t, v, k, N): wide arrays hitting every chunk pass and the last chunk
        (2, 2, 900, 8), (2, 2, 1100, 10), (2, 2, 1000, 6), (3, 2, 330, 20),
        (2, 20, 300, 30), (2, 5, 400, 12), (2, 40, 200, 20), (2, 3, 1000, 9),
    ]
    for i in range(70 + len(fixed)):
        if i < 60:
            t, v, k, rows, kind, wild = difftest.make_case(rng)
        elif i < 70:
            t, v, k, rows, kind, wild = difftest.make_medium_case(rng)
        else:
            t, v, k, n = fixed[i - 70]
            if (t, v) == (2, 2) and i % 2 == 0:
                rows = difftest.sperner_ca2(rng, 14, k)
                rows = rows[:n] if n >= 14 else rows
            else:
                rows = [[rng.randrange(v) for _ in range(k)] for _ in range(n)]
            if i % 3 == 0:
                for _ in range(3):
                    rows[rng.randrange(len(rows))][rng.randrange(k)] = WILD
        path = os.path.join(tmpdir, "c%02d.txt" % i)
        difftest.write_array(path, rows, v, rng)
        corpus.append((path, t, v))
    return corpus


def expected_outputs(orig, corpus):
    exp = {}
    for path, t, v in corpus:
        for nt in (1, 3):
            exp[(path, nt)] = difftest.run(orig, [path, t, v, nt])[:2]
    return exp


def check(exe, corpus, exp, env):
    """Return the first disagreement with the expected outputs, or None."""
    for path, t, v in corpus:
        for nt in (1, 3):
            rc, out, err = difftest.run(exe, [path, t, v, nt], env)
            if (rc, out) != exp[(path, nt)]:
                return "%s threads=%d: rc %d vs %d\n%s\nvs\n%s" % (
                    os.path.basename(path), nt, rc, exp[(path, nt)][0], out, exp[(path, nt)][1])
        # shards must add up to the one-thread run
        rc1, out1 = exp[(path, 1)]
        g1, c1, m1 = difftest.parse_counts(out1, rc1)
        tg = tc = tm = 0
        for s in range(3):
            rc, out, err = difftest.run(exe, [path, t, v, 2, "%d/3" % s], env)
            if rc not in (0, 1):
                return "%s shard %d/3: rc %d %s" % (os.path.basename(path), s, rc, err)
            g, c, m = difftest.parse_counts(out, rc)
            tg += g; tc += c; tm += m
        if (tg, tc, tm) != (g1, c1, m1):
            return "%s shards sum (%d,%d,%d) vs (%d,%d,%d)" % (
                os.path.basename(path), tg, tc, tm, g1, c1, m1)
    return None


def main():
    orig, src = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rng = random.Random(seed)
    tmpdir = tempfile.mkdtemp(prefix="mutation_", dir=os.path.dirname(os.path.abspath(__file__)))
    corpus = make_corpus(rng, tmpdir)
    exp = expected_outputs(orig, corpus)
    text = open(src).read()
    exe = os.path.join(tmpdir, "mutant")
    ok, err = build(src, exe)
    if not ok:
        print("cannot build unmutated source:\n" + err)
        sys.exit(2)
    bad = check(exe, corpus, exp, {})
    if bad:
        print("UNMUTATED SOURCE DISAGREES with the original:\n" + bad)
        sys.exit(1)
    for envv in ({"CA_VERIFY2_REP": "planes"}, {"CA_VERIFY2_REP": "onehot"},
                 {"CA_VERIFY2_CLASSES": "sort"}, {"CA_VERIFY2_KERNEL": "base"},
                 {"CA_VERIFY2_ROWS": "list"}, {"CA_VERIFY2_ROWS": "bits"}):
        bad = check(exe, corpus, exp, envv)
        if bad:
            print("UNMUTATED SOURCE DISAGREES with env %r:\n%s" % (envv, bad))
            sys.exit(1)
    print("unmutated source agrees with the original on all %d arrays (all forced paths)" % len(corpus))
    survivors = []
    for name, old, new, env, what in MUTANTS:
        edits = old if isinstance(old, list) else [(old, new)]
        mtext = text
        bad_pattern = False
        for o, n in edits:
            if mtext.count(o) != 1:
                print("MUTANT %-22s pattern occurs %d times, expected 1" % (name, mtext.count(o)))
                bad_pattern = True
            mtext = mtext.replace(o, n)
        if bad_pattern:
            survivors.append(name)
            continue
        msrc = os.path.join(tmpdir, "mut_%s.c" % name)
        open(msrc, "w").write(mtext)
        ok, err = build(msrc, exe)
        if not ok:
            print("MUTANT %-22s does not compile (counts as killed only if intended): %s" % (name, err[:200]))
            survivors.append(name)
            continue
        bad = check(exe, corpus, exp, env)
        if bad:
            print("killed   %-22s (%s)" % (name, what))
        else:
            print("SURVIVED %-22s (%s)" % (name, what))
            survivors.append(name)
    print("mutation test: %d mutants, %d survived" % (len(MUTANTS), len(survivors)))
    if not survivors:
        shutil.rmtree(tmpdir, ignore_errors=True)
    sys.exit(1 if survivors else 0)


if __name__ == "__main__":
    main()
