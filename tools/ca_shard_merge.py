#!/usr/bin/env python3
"""Combine the outputs of sharded ca_verify runs (version 2, SHARD/NSHARDS) into one verdict.

Usage: ca_shard_merge.py t k OUT0 OUT1 ... OUTn-1

Each OUTi is the stdout of `ca_verify FILE t v threads i/n`. The shards
partition the C(k,t) column sets (shard i checks the sets whose smallest
column is congruent to i mod n), so the merge is a sum: it checks that every
shard 0..n-1 is present exactly once, that the column-set counts add up to
C(k,t), and prints the combined summary in ca_verify's format. Exit 0 if all
shards verified, 1 if any shard found gaps, 2 if the shard set is incomplete
or inconsistent (then nothing has been proven).
"""
import math
import re
import sys

SUM_RE = re.compile(r"^(VERIFIED|NOT A COVERING ARRAY) \(shard (\d+)/(\d+)\): (.*)$")
VER_RE = re.compile(r"CA\(N=(\d+); t=(\d+), k=(\d+), v=(\d+)\) - all (\d+) column sets fully cover all (\d+) tuples")
GAP_RE = re.compile(r"(\d+) of (\d+) column sets have gaps \((\d+) missing tuples total\)")


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    t, k = int(sys.argv[1]), int(sys.argv[2])
    seen = {}
    nsh = None
    combos = gaps = missing = 0
    examples = []
    for path in sys.argv[3:]:
        lines = open(path).read().splitlines()
        if not lines:
            print("%s: empty output" % path); sys.exit(2)
        m = SUM_RE.match(lines[0])
        if not m:
            print("%s: not a shard summary: %s" % (path, lines[0])); sys.exit(2)
        verdict, i, n, rest = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        if nsh is None:
            nsh = n
        if n != nsh or i in seen or not 0 <= i < n:
            print("%s: inconsistent or duplicate shard %d/%d" % (path, i, n)); sys.exit(2)
        seen[i] = path
        if verdict == "VERIFIED":
            mm = VER_RE.search(rest)
            if not mm or int(mm.group(2)) != t or int(mm.group(3)) != k:
                print("%s: parameters do not match t=%d k=%d" % (path, t, k)); sys.exit(2)
            combos += int(mm.group(5))
        else:
            mm = GAP_RE.search(rest)
            if not mm:
                print("%s: cannot parse %s" % (path, rest)); sys.exit(2)
            gaps += int(mm.group(1)); combos += int(mm.group(2)); missing += int(mm.group(3))
            examples += [l for l in lines[1:] if l.strip().startswith("missing:")]
    if nsh is None or len(seen) != nsh:
        print("incomplete: %d of %s shards present" % (len(seen), nsh)); sys.exit(2)
    expect = math.comb(k, t)
    if combos != expect:
        print("column set counts add up to %d, expected C(%d,%d) = %d" % (combos, k, t, expect))
        sys.exit(2)
    if gaps == 0:
        print("VERIFIED (merged %d shards): all %d column sets of t=%d, k=%d fully covered" % (nsh, combos, t, k))
        sys.exit(0)
    print("NOT A COVERING ARRAY (merged %d shards): %d of %d column sets have gaps (%d missing tuples total)"
          % (nsh, gaps, combos, missing))
    for l in examples[:10]:
        print(l)
    sys.exit(1)


if __name__ == "__main__":
    main()
