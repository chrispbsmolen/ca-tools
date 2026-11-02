#!/usr/bin/env python3
"""Combine the outputs of sharded ca_verify runs (version 2, SHARD/NSHARDS) into one verdict.

Usage: ca_shard_merge.py t k OUT0 OUT1 ... OUTn-1

Each OUTi is the stdout of `ca_verify FILE t v threads i/n` (lines starting with
'#' are ignored, so a file may carry comment lines before or after the output).
A single unsharded output (`ca_verify FILE t v threads`) is accepted as n = 1.
The shards partition the C(k,t) column sets: shard i checks the sets whose
smallest column a is congruent to i mod n, and there are C(k-1-a, t-1) sets
with smallest column a. The merge checks that every shard 0..n-1 is present
exactly once, that each shard's column-set count is exactly the number of sets
of its residue class, that these add up to C(k,t), that every shard reports the
same t, k (and N and v when it is VERIFIED), and prints the combined summary in
ca_verify's format. So the shards together checked every one of the C(k,t)
column sets exactly once. Exit 0 if all shards verified, 1 if any shard found
gaps, 2 if the shard set is incomplete or inconsistent (then nothing has been
proven). tools/check_upgrades.py imports merge().
"""
import math
import re
import sys

SUM_RE = re.compile(r"^(VERIFIED|NOT A COVERING ARRAY)(?: \(shard (\d+)/(\d+)\))?: (.*)$")
VER_RE = re.compile(r"^CA\(N=(\d+); t=(\d+), k=(\d+), v=(\d+)\) - all (\d+) column sets fully cover all (\d+) tuples$")
GAP_RE = re.compile(r"^(\d+) of (\d+) column sets have gaps \((\d+) missing tuples total\)$")


class MergeError(Exception):
    """the shard outputs do not prove anything (incomplete or inconsistent)"""


def shard_sets(t, k, i, n):
    """the number of t-sets of k columns whose smallest column is congruent to i mod n, as
    ca_verify counts them (for t = 1 the single work unit of shard 0 holds all k sets)"""
    if t == 1:
        return k if i == 0 else 0
    return sum(math.comb(k - 1 - a, t - 1) for a in range(i, k - t + 1, n))


def merge(texts, t, k, N=None, v=None):
    """Combine shard outputs (a list of texts, any order). Returns dict(verified, shards, combos,
    gaps, missing, examples). Raises MergeError when they do not prove a verdict."""
    if not texts:
        raise MergeError("no shard outputs")
    seen = {}
    nsh = None
    combos = gaps = missing = 0
    examples = []
    for pos, text in enumerate(texts):
        lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            raise MergeError("output %d is empty (the shard did not finish)" % pos)
        m = SUM_RE.match(lines[0])
        if not m:
            raise MergeError("output %d is not a ca_verify summary: %s" % (pos, lines[0][:120]))
        verdict, rest = m.group(1), m.group(4)
        if m.group(2) is None:
            i, n = 0, 1
        else:
            i, n = int(m.group(2)), int(m.group(3))
            if n < 2:
                raise MergeError("output %d names shard %d/%d" % (pos, i, n))
        if nsh is None:
            nsh = n
        if n != nsh:
            raise MergeError("the outputs disagree on the number of shards (%d and %d)" % (nsh, n))
        if not 0 <= i < n:
            raise MergeError("shard %d/%d is out of range" % (i, n))
        if i in seen:
            raise MergeError("shard %d appears twice" % i)
        seen[i] = True
        want = shard_sets(t, k, i, n)
        if verdict == "VERIFIED":
            mm = VER_RE.match(rest)
            if not mm:
                raise MergeError("shard %d: cannot read %s" % (i, rest[:120]))
            if int(mm.group(2)) != t or int(mm.group(3)) != k:
                raise MergeError("shard %d checked t=%s, k=%s, not t=%d, k=%d" % (i, mm.group(2), mm.group(3), t, k))
            if N is not None and int(mm.group(1)) != N:
                raise MergeError("shard %d checked N=%s, not %d" % (i, mm.group(1), N))
            if v is not None and int(mm.group(4)) != v:
                raise MergeError("shard %d checked v=%s, not %d" % (i, mm.group(4), v))
            if v is not None and int(mm.group(6)) != v ** t:
                raise MergeError("shard %d counts %s tuples, not v^t = %d" % (i, mm.group(6), v ** t))
            got = int(mm.group(5))
        else:
            mm = GAP_RE.match(rest)
            if not mm:
                raise MergeError("shard %d: cannot read %s" % (i, rest[:120]))
            gaps += int(mm.group(1))
            missing += int(mm.group(3))
            got = int(mm.group(2))
            examples += [l.strip() for l in lines[1:] if l.strip().startswith("missing:")]
        if got != want:
            raise MergeError("shard %d/%d checked %d column sets; its residue class has %d" % (i, n, got, want))
        combos += got
    if len(seen) != nsh:
        miss = sorted(set(range(nsh)) - set(seen))
        raise MergeError("incomplete: %d of %d shards present (missing %s)"
                         % (len(seen), nsh, ", ".join(map(str, miss[:20]))))
    expect = math.comb(k, t)
    if combos != expect:          # cannot happen when every class count matched; kept as a guard
        raise MergeError("column set counts add up to %d, expected C(%d,%d) = %d" % (combos, k, t, expect))
    return dict(verified=gaps == 0, shards=nsh, combos=combos, gaps=gaps, missing=missing,
                examples=examples)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    t, k = int(sys.argv[1]), int(sys.argv[2])
    texts = []
    for path in sys.argv[3:]:
        with open(path) as f:
            texts.append(f.read())
    try:
        r = merge(texts, t, k)
    except MergeError as e:
        print(str(e))
        sys.exit(2)
    if r["verified"]:
        print("VERIFIED (merged %d shards): all %d column sets of t=%d, k=%d fully covered" % (r["shards"], r["combos"], t, k))
        sys.exit(0)
    print("NOT A COVERING ARRAY (merged %d shards): %d of %d column sets have gaps (%d missing tuples total)"
          % (r["shards"], r["gaps"], r["combos"], r["missing"]))
    for l in r["examples"][:10]:
        print("  " + l)
    sys.exit(1)


if __name__ == "__main__":
    main()
