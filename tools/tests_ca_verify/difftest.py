#!/usr/bin/env python3
"""Differential test: ca_verify2 against the original ca_verify (and a tiny
independent Python reference) on thousands of random small arrays.

Usage: difftest.py ORIG NEW [count] [seed] [--quiet]

For each case we generate an array (random, covering, or near-covering with
exactly one missing tuple at a random position), write it in a random
accepted syntax (0- or 1-based symbols, space/tab/comma separators, optional
don't-care tokens), and run both programs with several thread counts. The
complete stdout and the exit code must be identical. Sharded runs of NEW
must partition the column sets: gap and column-set counts add up to the
unsharded ones and the verdict agrees. The Python reference checks the
verdict, the number of column sets with gaps and the number of missing
tuples independently.
"""
import itertools
import os
import random
import subprocess
import sys
import tempfile

WILD = -1


def coverage(rows, t, v):
    """Return (gaps, missing_tuples, first_missing) over all t-sets, with the
    same conventions as ca_verify: a row with a don't-care in the projection
    contributes nothing."""
    k = len(rows[0])
    gaps = 0
    missing = 0
    first = []
    for cols in itertools.combinations(range(k), t):
        seen = set()
        for r in rows:
            tup = tuple(r[c] for c in cols)
            if WILD in tup:
                continue
            seen.add(tup)
        miss = v ** t - len(seen)
        if miss:
            gaps += 1
            missing += miss
            if len(first) < 10:
                for tup in itertools.product(range(v), repeat=t):
                    if tup not in seen:
                        first.append((cols, tup))
                        break
    return gaps, missing, first


def greedy_cover(rows, t, v, k, rng, avoid=None):
    """Add rows until every tuple is covered except 'avoid' = (cols, tuple)."""
    all_tuples = list(itertools.product(range(v), repeat=t))
    for _ in range(1000):
        missing = []
        for cols in itertools.combinations(range(k), t):
            seen = {tuple(r[c] for c in cols) for r in rows}
            for tup in all_tuples:
                if tup not in seen and (avoid is None or (cols, tup) != avoid):
                    missing.append((cols, tup))
        if not missing:
            return rows
        rng.shuffle(missing)
        for cols, tup in missing:
            if any(tuple(r[c] for c in cols) == tup for r in rows):
                continue
            while True:
                row = [rng.randrange(v) for _ in range(k)]
                for c, s in zip(cols, tup):
                    row[c] = s
                if avoid is None:
                    break
                acols, atup = avoid
                if tuple(row[c] for c in acols) != atup:
                    break
            rows.append(row)
    raise RuntimeError("greedy fill did not converge")


def make_case(rng):
    t = rng.choice([1, 2, 2, 3, 3, 3, 4, 4, 5])
    v = rng.choice([2, 2, 2, 3, 3, 4, 5, 6])
    if v ** t > 700:
        v = 2
    k = rng.randint(t, min(t + 6, 10))
    kind = rng.choice(["random", "random", "covering", "covering", "near", "near", "near"])
    if kind == "random":
        n = rng.randint(1, 3 * v ** t)
        rows = [[rng.randrange(v) for _ in range(k)] for _ in range(n)]
    elif kind == "covering":
        n = rng.randint(0, v ** t)
        rows = [[rng.randrange(v) for _ in range(k)] for _ in range(n)]
        rows = greedy_cover(rows, t, v, k, rng)
    else:
        cols = tuple(sorted(rng.sample(range(k), t)))
        tup = tuple(rng.randrange(v) for _ in range(t))
        avoid = (cols, tup)
        rows = []
        for _ in range(rng.randint(0, v ** t)):
            while True:
                row = [rng.randrange(v) for _ in range(k)]
                if tuple(row[c] for c in cols) != tup:
                    break
            rows.append(row)
        rows = greedy_cover(rows, t, v, k, rng, avoid)
    # don't-cares: in some cases, a few entries
    wild = rng.random() < 0.3 and len(rows) > 0
    if wild:
        for _ in range(rng.randint(1, max(1, len(rows) * k // 10))):
            rows[rng.randrange(len(rows))][rng.randrange(k)] = WILD
    return t, v, k, rows, kind, wild


def write_array(path, rows, v, rng):
    # 1-based symbols are auto-shifted only when they span exactly 1..v, so
    # write them 1-based only if the array contains both 0 and v-1
    vals = {x for r in rows for x in r if x != WILD}
    shift = 1 if (rng.random() < 0.3 and 0 in vals and (v - 1) in vals) else 0
    sep = rng.choice([" ", " ", ",", "\t", ", "])
    wild_tokens = ["-", "*", "x", "NA"]
    lines = []
    for r in rows:
        toks = []
        for x in r:
            if x == WILD:
                toks.append(rng.choice(wild_tokens))
            else:
                toks.append(str(x + shift))
        lines.append(sep.join(toks))
    if rng.random() < 0.2:
        lines.insert(rng.randrange(len(lines) + 1), "")   # blank line is skipped
    with open(path, "w") as f:
        f.write("\n".join(lines) + ("\n" if rng.random() < 0.8 else ""))


def run(exe, args, env=None):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    p = subprocess.run([exe] + [str(a) for a in args], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True, timeout=600,
                       env=full_env)
    return p.returncode, p.stdout, p.stderr


def random_env(rng):
    """Test hooks of ca_verify2: force a representation (value planes or
    one-hot lanes), a class-building method and the portable kernel, so that
    every code path is compared against the original, not only the one the
    heuristics pick for small arrays."""
    if rng.random() < 0.4:
        return {}
    env = {}
    r = rng.random()
    if r < 0.4:
        env["CA_VERIFY2_REP"] = "planes"
    elif r < 0.8:
        env["CA_VERIFY2_REP"] = "onehot"
    if rng.random() < 0.5:
        env["CA_VERIFY2_CLASSES"] = rng.choice(["bitset", "sort"])
    if rng.random() < 0.3:
        env["CA_VERIFY2_KERNEL"] = "base"
    if rng.random() < 0.4:
        env["CA_VERIFY2_ROWS"] = rng.choice(["bits", "list"])
    return env


def sperner_ca2(rng, n, k):
    """CA(n; 2, k, 2): k distinct, pairwise non-complementary n/2-subsets of
    the rows as columns (Katona / Kleitman-Spencer). Exact strength 2."""
    cols = set()
    half = n // 2
    while len(cols) < k:
        sub = tuple(sorted(rng.sample(range(n), half)))
        comp = tuple(i for i in range(n) if i not in sub)
        if sub in cols or comp in cols:
            continue
        cols.add(sub)
    cols = list(cols)
    rng.shuffle(cols)
    rows = [[0] * k for _ in range(n)]
    for j, sub in enumerate(cols):
        for i in sub:
            rows[i][j] = 1
    return rows


def make_medium_case(rng):
    """Wider arrays (k up to about 1100) with few rows, to exercise the
    multi-chunk column passes; the original still runs in about a second."""
    kind = rng.choice(["sperner", "sperner_wild", "random2", "random3", "randomv"])
    if kind.startswith("sperner"):
        t, v = 2, 2
        n = rng.choice([14, 16])
        k = rng.randint(200, 1100)
        rows = sperner_ca2(rng, n, k)
        if kind == "sperner_wild":
            for _ in range(rng.randint(1, 3)):
                rows[rng.randrange(n)][rng.randrange(k)] = WILD
        return t, v, k, rows, kind, kind == "sperner_wild"
    if kind == "random2":
        t, v, k, n = 2, 2, rng.randint(200, 1100), rng.randint(3, 12)
    elif kind == "random3":
        t, v, k, n = 3, 2, rng.randint(200, 330), rng.randint(3, 25)
    else:
        t, v, k, n = 2, rng.choice([3, 5, 9, 20, 40]), rng.randint(60, 400), rng.randint(3, 40)
    rows = [[rng.randrange(v) for _ in range(k)] for _ in range(n)]
    wild = rng.random() < 0.3
    if wild:
        for _ in range(rng.randint(1, 5)):
            rows[rng.randrange(n)][rng.randrange(k)] = WILD
    return t, v, k, rows, kind, wild


def parse_counts(out, rc):
    line = out.splitlines()[0] if out else ""
    if rc == 0:
        import re
        m = re.search(r"all (\d+) column sets", line)
        return 0, int(m.group(1)), 0
    if rc == 1:
        import re
        m = re.search(r"(\d+) of (\d+) column sets have gaps \((\d+) missing", line)
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    orig, new = args[0], args[1]
    count = int(args[2]) if len(args) > 2 else 2000
    seed = int(args[3]) if len(args) > 3 else 1
    rng = random.Random(seed)
    tmpdir = tempfile.mkdtemp(prefix="difftest_", dir=os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(tmpdir, "arr.txt")
    fails = 0
    stats = {"random": 0, "covering": 0, "near": 0, "wild": 0, "verified": 0, "gaps": 0,
             "shard_checks": 0, "thread_runs": 0}
    for i in range(count):
        if rng.random() < 0.08:
            t, v, k, rows, kind, wild = make_medium_case(rng)
            stats["medium"] = stats.get("medium", 0) + 1
        else:
            t, v, k, rows, kind, wild = make_case(rng)
            stats[kind] += 1
        stats["wild"] += wild
        write_array(path, rows, v, rng)
        ncomb = 1
        for j in range(t):
            ncomb = ncomb * (k - j) // (j + 1)
        if rows and ncomb * len(rows) <= 400000:
            ref_gaps, ref_missing, _ = coverage(rows, t, v)
        elif not rows:
            ref_gaps = ncomb
            ref_missing = ref_gaps * v ** t
        else:
            ref_gaps = ref_missing = None   # too large for the Python reference
        threads = sorted(set([1, rng.choice([2, 3, 4, 5, 7, 11])]))
        for nt in threads:
            stats["thread_runs"] += 1
            env = random_env(rng)
            rc1, out1, err1 = run(orig, [path, t, v, nt])
            rc2, out2, err2 = run(new, [path, t, v, nt], env)
            err2 = "env=%r\n%s" % (env, err2)
            ok = rc1 == rc2 and out1 == out2
            if ok and rc1 in (0, 1):
                g, c, m = parse_counts(out1, rc1)
                if ref_gaps is not None and (g != ref_gaps or m != ref_missing):
                    ok = False
                    err2 += "\nREFERENCE disagrees: gaps %d missing %d" % (ref_gaps, ref_missing)
            if ok and rc1 in (0, 1):
                stats["verified" if rc1 == 0 else "gaps"] += 1
            if not ok:
                fails += 1
                keep = os.path.join(tmpdir, "fail_%d_t%d_v%d_nt%d.txt" % (i, t, v, nt))
                os.rename(path, keep)
                print("MISMATCH case %d kind=%s t=%d v=%d k=%d N=%d nt=%d wild=%s -> %s"
                      % (i, kind, t, v, k, len(rows), nt, wild, keep))
                print("  orig rc=%d\n%s\n  new rc=%d\n%s\n  new stderr: %s" % (rc1, out1, rc2, out2, err2))
                break
        if fails and not os.path.exists(path):
            continue
        # sharding: counts must add up and verdict agree
        if rng.random() < 0.5 and k > t:
            nsh = rng.choice([2, 3, 4])
            tg = tc = tm = 0
            rcs = []
            for s in range(nsh):
                rc, out, err = run(new, [path, t, v, rng.choice([1, 2, 3]), "%d/%d" % (s, nsh)],
                                   random_env(rng))
                if rc not in (0, 1):
                    fails += 1
                    print("SHARD ERROR case %d shard %d/%d rc=%d: %s" % (i, s, nsh, rc, err))
                    break
                g, c, m = parse_counts(out, rc)
                tg += g; tc += c; tm += m
                rcs.append(rc)
                tag = "(shard %d/%d)" % (s, nsh)
                if tag not in out.splitlines()[0]:
                    fails += 1
                    print("SHARD TAG missing case %d: %s" % (i, out))
            else:
                rc1, out1, _ = run(orig, [path, t, v, 1])
                g1, c1, m1 = parse_counts(out1, rc1)
                verdict = 1 if any(r == 1 for r in rcs) else 0
                if (tg, tc, tm, verdict) != (g1, c1, m1, rc1):
                    fails += 1
                    print("SHARD SUM mismatch case %d: shards (%d,%d,%d,%d) vs (%d,%d,%d,%d)"
                          % (i, tg, tc, tm, verdict, g1, c1, m1, rc1))
                else:
                    stats["shard_checks"] += 1
        if not quiet and (i + 1) % 200 == 0:
            print("  %d cases done, %d failures" % (i + 1, fails), flush=True)
    print("difftest: %d cases, %d failures; %s" % (count, fails, stats))
    if not fails:
        try:
            os.remove(path)
            os.rmdir(tmpdir)
        except OSError:
            pass
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
