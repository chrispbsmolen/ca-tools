#!/usr/bin/env python3
"""withdrawn_fingerprints.py - write table/withdrawn_fingerprints.csv.

The 137 array files withdrawn on 2026-10-27 (table/withdrawn_files.csv) are no
longer stored, but the submission check should still notice a submission that
is one of them with its rows, columns or symbols permuted. This script reads
each withdrawn file from the commit before the withdrawal (356d0fe^, where the
files are still in the repository history), computes the fingerprint of
tools/check_submission.py (fingerprint()), and writes one row per file:
file, t, v, k, N, source_detail, fingerprint. Only fingerprints are stored,
never the arrays. Run from the repository root, in a full clone:

    python3 tools/withdrawn_fingerprints.py
"""
import csv
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_submission as cs  # noqa: E402

BEFORE = "356d0fe^"
OUT = "table/withdrawn_fingerprints.csv"


def main():
    rows = list(csv.DictReader(open("table/withdrawn_files.csv", newline="", encoding="utf-8")))
    out = []
    for r in rows:
        data = subprocess.run(["git", "show", "%s:table/arrays/%s" % (BEFORE, r["file"])],
                              stdout=subprocess.PIPE, check=True).stdout
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            arr = cs.parse_array(path, int(r["v"]))[0]
        finally:
            os.unlink(path)
        fp = cs.fingerprint(arr)
        out.append(dict(file=r["file"], t=r["t"], v=r["v"], k=r["k"], N=r["N"],
                        source_detail=r["source_detail"], fingerprint=fp or ""))
        print(r["file"], fp or "too large")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "t", "v", "k", "N", "source_detail", "fingerprint"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print("wrote %s (%d rows, %d without a fingerprint)"
          % (OUT, len(out), sum(1 for o in out if not o["fingerprint"])))


if __name__ == "__main__":
    main()
