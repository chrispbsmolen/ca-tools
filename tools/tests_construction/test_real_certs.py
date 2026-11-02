#!/usr/bin/env python3
"""Planted faults on the four real Power CZ certificates (q = 13, t = 4, e = 3).

The arrays are too large for a brute-force check here (C(1728, 4) = 3.7e11 4-sets), so these tests
check verdicts only: the four certificates pass and reproduce the stored arrays' canonical sha256;
each planted fault is rejected by the check it targets. Every single-entry change of each binary
ingredient (sha256 updated so only the quilting check can see it) is tried: the change is
rejected exactly when the independent quilting check below says the ingredient lost a pattern.
"""
import copy
import hashlib
import itertools
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # repository root
BUILD = os.environ.get("CZTEST_BUILD", __import__("tempfile").gettempdir())
sys.path.insert(0, os.path.join(ROOT, "tools"))
import construction_cert as cc  # noqa: E402

CERTS = os.path.join(ROOT, "table", "constructions", "powercz")
STORED = os.environ.get("POWERCZ_ARRAYS", os.path.join(
    ROOT, "table", "arrays"))
CT_TOOLS = os.path.join(ROOT, "tools")
NAMES = ["CA_216_4_1368_2", "CA_224_4_1476_2", "CA_233_4_1596_2", "CA_242_4_1728_2"]
COVERS = {"S22_13": (2, 2), "S03_13": (0, 3), "S14_13": (1, 4), "S13_12": (1, 3), "S14_12": (1, 4)}

errors = []
counts = {}


def expect(label, ok, want_ok, got, want_check=None):
    counts[label] = counts.get(label, 0) + 1
    if ok != want_ok or (want_check and want_check not in got):
        errors.append("%s: ok=%s failures=%s (wanted ok=%s, %s)" % (label, ok, sorted(got),
                                                                   want_ok, want_check))


def run(path):
    try:
        r = cc.run(path)
        return r["ok"], {f[0] for f in r["failures"]}, r
    except cc.CertError as ex:
        return False, {"malformed"}, None


def qa_ok(rows, lo, hi):
    w = len(rows[0])
    for cols in itertools.combinations(range(w), 4):
        seen = {tuple(r[c] for c in cols) for r in rows}
        for p in itertools.product((0, 1), repeat=4):
            if lo <= sum(p) <= hi and p not in seen:
                return False
    return True


def main():
    sys.path.insert(0, CT_TOOLS)
    import check_submission as cs
    work = tempfile.mkdtemp(prefix="realcert_", dir=BUILD)
    # 1. the four certificates pass and match the canonical hash of the stored arrays
    for n in NAMES:
        ok, got, r = run(os.path.join(CERTS, n + ".cert.json"))
        expect("real certificate valid", ok, True, got)
        _, _, sha = cs.canonical_of_file(os.path.join(STORED, n + ".txt"), 2)
        if r["sha256"] != sha:
            errors.append("%s: rebuilt sha %s, stored canonical %s" % (n, r["sha256"], sha))
        print("%s: valid=%s N=%d k=%d rebuilt %s stored-canonical %s %.2f s"
              % (n, ok, r["N"], r["k"], r["sha256"][:16], sha[:16], r["seconds"]))

    def variant(name, mutate):
        d = os.path.join(work, "v")
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(CERTS, d)
        p = os.path.join(d, name + ".cert.json")
        cert = json.load(open(p))
        mutate(cert, d)
        json.dump(cert, open(p, "w"))
        return run(p)

    base = NAMES[0]
    # 2. agreement: duplicate a point
    def dup(c, d):
        c["family"]["rows"][1]["point"] = c["family"]["rows"][0]["point"]
    ok, got, _ = variant(base, dup)
    expect("duplicate point", ok, False, got, "agreement")
    # 3. species: one S13 row replaced by S22 (weight 1, 3 now in 6 rows)
    def s22(c, d):
        c["family"]["rows"][4]["ingredient"] = "S22_12"
        c["ingredients"]["S22_12"] = {"file": "S13_12.txt",
                                      "sha256": c["ingredients"]["S13_12"]["sha256"],
                                      "covers": {"weights": [2, 2]}}
    ok, got, _ = variant(base, s22)
    expect("weight 1/3 in 6 rows", ok, False, got, "species")
    # 4. the S03 row declared as S13 only (weight 0 in no row)
    def no0(c, d):
        c["ingredients"]["S03_13"]["covers"] = {"weights": [1, 3]}
    ok, got, _ = variant(base, no0)
    expect("weight 0 in no row", ok, False, got, "species")
    # 5. over-claim: S13_12 declared to cover weight 0 too
    def over(c, d):
        c["ingredients"]["S13_12"]["covers"] = {"weights": [0, 3]}
    ok, got, _ = variant(base, over)
    expect("ingredient over-claims weight 0", ok, False, got, "quilting")
    # 6. N, k, sha, forbidden value, file hash
    for lab, fn, chk in [
            ("wrong N", lambda c, d: c["expected"].__setitem__("N", c["expected"]["N"] - 1), "N"),
            ("wrong k", lambda c, d: c["expected"].__setitem__("k", c["expected"]["k"] + 1), "k"),
            ("wrong sha", lambda c, d: c["expected"].__setitem__("array_sha256", "f" * 64), "sha256"),
            ("forbidden value changed", lambda c, d: c["family"]["rows"][3].__setitem__("forbidden", [2]), "k"),
            ("ingredient file hash", lambda c, d: c["ingredients"]["S22_13"].__setitem__("sha256", "a" * 64),
             "ingredient_hash")]:
        ok, got, _ = variant(base, fn)
        expect(lab, ok, False, got, chk)
    # 6b. duplicate JSON key (two definitions of one ingredient) is malformed
    d = os.path.join(work, "dup")
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(CERTS, d)
    p = os.path.join(d, base + ".cert.json")
    txt = open(p).read().replace('"ingredients": {', '"ingredients": {\n  "S22_13": {"file": "S13_12.txt", '
                                 '"sha256": "%s", "covers": {"weights": [2, 2]}},'
                                 % hashlib.sha256(open(os.path.join(d, "S13_12.txt"), "rb").read()).hexdigest(), 1)
    open(p, "w").write(txt)
    ok, got, _ = run(p)
    expect("duplicate JSON key", ok, False, got, "malformed")
    # 7. every single-entry flip of every ingredient (sha updated): rejected iff it breaks the QA
    flips = {}
    for ing, (lo, hi) in COVERS.items():
        src = os.path.join(CERTS, ing + ".txt")
        rows = [list(map(int, l.split())) for l in open(src) if l.strip()]
        cert_for = next(n for n in NAMES if ing in json.load(open(os.path.join(CERTS, n + ".cert.json")))["ingredients"])
        nrej = nbreak = 0
        for i in range(len(rows)):
            for j in range(len(rows[0])):
                r2 = copy.deepcopy(rows)
                r2[i][j] ^= 1
                breaks = not qa_ok(r2, lo, hi)
                text = "".join(" ".join(map(str, r)) + "\n" for r in r2)

                def m(c, d, text=text):
                    open(os.path.join(d, ing + ".txt"), "w").write(text)
                    c["ingredients"][ing]["sha256"] = hashlib.sha256(text.encode()).hexdigest()
                ok, got, _ = variant(cert_for, m)
                # the array changes, so the sha256 check always rejects; the quilting check must
                # fire exactly when the flip breaks the declared property
                nrej += "quilting" in got
                nbreak += breaks
                counts["ingredient flip"] = counts.get("ingredient flip", 0) + 1
                if ok or ("quilting" in got) != breaks or (got - {"quilting", "sha256"}):
                    errors.append("flip %s (%d,%d): ok=%s failures=%s breaks=%s"
                                  % (ing, i, j, ok, sorted(got), breaks))
        flips[ing] = (len(rows) * len(rows[0]), nbreak, nrej)
    for ing, (n, b, r) in flips.items():
        print("%s: %d single-entry flips, %d break the declared quilting property, %d rejected by the quilting check"
              % (ing, n, b, r))
    shutil.rmtree(work, ignore_errors=True)
    print("checks: " + "; ".join("%s %d" % kv for kv in counts.items()))
    if errors:
        print("ERRORS:")
        for e in errors:
            print("  " + e)
        return 1
    print("ALL REAL-CERTIFICATE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
