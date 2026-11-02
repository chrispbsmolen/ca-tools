#!/usr/bin/env python3
"""End-to-end tests of construction certificates as a submission route (tools/check_constructions.py)
on a temporary copy of the table (the copy of tools/tests_upgrade/test_upgrades.py: table/ without the
stored arrays, MANIFEST.csv empty, in a git repository of its own).

Arrays are entered first by a claims.csv submission (so that a certificate can name them by their
table hash). Then a constructions.csv submission with a fuse-1 certificate (input from the table),
a derive-1 certificate (input in a file) and a product-1 certificate (inline inputs) is checked as
on a pull request (tools/check_submission.py), entered as on main (--apply), and the table is
checked by tools/consistency.py. The rebuilt arrays are checked by ca_verify. Then: the same
certificates again, the real Power CZ certificate of an array already in the table, a wrong N, a
claim that differs from the certificate, an ingredient named by the hash of a SCREENED row, an empty
builds_on, and the not-stored path (an array above the storage limit, kept only as its
certificate), and tampering with a stored certificate, which consistency.py reports.

Usage: test_route.py [--keep DIR]   (exit 1 on a failure)
"""
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "tools", "tests_upgrade"))
import check_submission as cs  # noqa: E402
import check_constructions as ccn  # noqa: E402
import construction_cert as ccert  # noqa: E402
import test_upgrades as tu  # noqa: E402

check, quiet, consistency, table_rows, file_bytes = tu.check, tu.quiet, tu.consistency, tu.table_rows, tu.file_bytes


def cert(kind, body, N=1, k=1, sha="0" * 64):
    d = {"format": "construction-cert-1", "construction": kind}
    d.update(body)
    d["expected"] = {"N": N, "k": k, "array_sha256": sha}
    return d


def finish(path, d, table_dir):
    """write the certificate with the expected values the checker computes"""
    json.dump(d, open(path, "w"))
    r = ccert.run(path, table_dir=table_dir)
    d["expected"] = {"N": r["N"], "k": r["k"], "array_sha256": r["sha256"]}
    json.dump(d, open(path, "w"), indent=1)
    return ccert.run(path, table_dir=table_dir)


def con_line(t, v, k, N, fn, credit, construction, builds_on):
    return "%d,%d,%d,%d,%s,test recipe %s,\"%s\",%s,%s,\n" % (t, v, k, N, fn, fn, construction, builds_on, credit)


def run(keep=None):
    root = keep or tempfile.mkdtemp(prefix="cacon-test-")
    T, W = os.path.join(root, "repo"), os.path.join(root, "work")
    os.makedirs(W, exist_ok=True)
    base = tu.make_repo(T)
    TD = os.path.join(T, "table")
    cav = os.path.join(W, "ca_verify")
    subprocess.run(["cc", "-O3", "-pthread", "-o", cav, os.path.join(REPO, "ca_verify.c")], check=True)
    rng = random.Random(7)
    # arrays in the table: OA(16; 2, 5, 4) over GF(4) (VERIFIED), and a SCREENED array
    mul = [[0, 0, 0, 0], [0, 1, 2, 3], [0, 2, 3, 1], [0, 3, 1, 2]]
    oa16 = [[a, b] + [a ^ mul[m][b] for m in (1, 2, 3)] for a in range(4) for b in range(4)]
    S0 = os.path.join(T, "submissions", "seed")
    os.makedirs(S0)
    tu.write_rows(os.path.join(S0, "OA16.txt"), oa16)
    scr = tu.random_ca(rng, cav, 30, 2, 40, 2, W)
    tu.write_rows(os.path.join(S0, "S.txt"), scr)
    with open(os.path.join(S0, "claims.csv"), "w") as f:
        f.write(",".join(cs.CLAIMS_HEADER) + "\n")
        f.write(tu.claims_line(2, 4, 5, 16, "OA16.txt", "Ann Seed", "orthogonal array over GF(4)", "oa-bush1952"))
        f.write(tu.claims_line(2, 2, 40, 30, "S.txt", "Ann Seed"))
    old_ff = cs.FULL_FRACTION
    rc, _ = quiet(cs.main, [S0, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "o0"),
                            "--apply", "--date", "2026-11-01"])
    check(rc == 0, "seed arrays entered")
    # the second as SCREENED: enter it again through another seed folder with the screen forced
    rows = table_rows(T)
    sha_oa = cs.sha256_text(cs.canon_serialize(oa16))
    sha_s = cs.sha256_text(cs.canon_serialize(scr))
    scr2 = tu.random_ca(rng, cav, 31, 2, 41, 2, W)
    S0b = os.path.join(T, "submissions", "seed-screened")
    os.makedirs(S0b)
    tu.write_rows(os.path.join(S0b, "S2.txt"), scr2)
    open(os.path.join(S0b, "claims.csv"), "w").write(",".join(cs.CLAIMS_HEADER) + "\n" +
                                                     tu.claims_line(2, 2, 41, 31, "S2.txt", "Ann Seed"))
    cs.FULL_FRACTION = -1.0
    rc, _ = quiet(cs.main, [S0b, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "o0b"),
                            "--apply", "--date", "2026-11-01"])
    cs.FULL_FRACTION = old_ff
    sha_s2 = cs.sha256_text(cs.canon_serialize(scr2))
    check(rc == 0 and [r["tier"] for r in table_rows(T) if r["array_sha256"] == sha_s2] == ["SCREENED"],
          "a SCREENED array entered")

    # --- the submission --------------------------------------------------------------------------
    S = os.path.join(T, "submissions", "con-1")
    os.makedirs(S)
    r_fuse = finish(os.path.join(S, "fuse.json"), cert("fuse-1", {"t": 2, "v": 3, "input": {"table": sha_oa}}), TD)
    ca3 = None
    while ca3 is None:
        x = tu.random_ca(rng, cav, 24, 3, 6, 2, W)
        ca3 = x
    txt = cs.canon_serialize(ca3)
    open(os.path.join(S, "ca3.txt"), "w").write(txt)
    r_der = finish(os.path.join(S, "derive.json"), cert("derive-1", {"t": 2, "v": 2, "input": {
        "file": "ca3.txt", "sha256": cs.sha256_text(txt)}, "column": 2, "symbol": 1}), TD)
    oa9 = [[a, b, (a + b) % 3, (a + 2 * b) % 3] for a in range(3) for b in range(3)]
    r_pro = finish(os.path.join(S, "product.json"), cert("product-1", {"t": 2, "v": 3, "first": {"rows": oa9},
                                                                       "second": {"rows": oa9}, "constant_rows": [0, 0]}), TD)
    check(all(r["ok"] for r in (r_fuse, r_der, r_pro)), "three certificates valid (%s)" % [(r["N"], r["k"]) for r in (r_fuse, r_der, r_pro)])
    with open(os.path.join(S, "constructions.csv"), "w") as f:
        f.write(",".join(ccn.HEADER) + "\n")
        f.write(con_line(2, 3, 5, r_fuse["N"], "fuse.json", "Ben Builder", "CKRS fusing of OA(16; 2, 5, 4)", "fuse-ckrs2010"))
        f.write(con_line(2, 2, 5, r_der["N"], "derive.json", "Ben Builder", "derived array of a CA(24; 3, 6, 2)", "oa-bush1952"))
        f.write(con_line(2, 3, 16, r_pro["N"], "product.json", "Ben Builder", "direct product of OA(9; 2, 4, 3) with itself",
                         "product-cmmssy2006;pca-ct2013"))
    rc, out = quiet(cs.main, [S, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "pr")])
    rep = open(os.path.join(W, "pr", "report.md")).read()
    check(rc == 0 and "## Construction certificates: `con-1`" in rep and "**Result: PASS.** 3 of 3" in rep,
          "pull request check (check_submission.py) passes the three certificates")
    check("builds_on: fuse-ckrs2010 added" not in rep, "derive-1 adds nothing to builds_on (no single source)")
    rows0 = table_rows(T)
    rc, out = quiet(ccn.main, [S, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--pr", "12",
                               "--out", os.path.join(W, "main"), "--apply", "--date", "2026-11-02"])
    check(rc == 0, "entered on main (rc %s)" % rc)
    new = table_rows(T)[len(rows0):]
    check(len(new) == 3 and all(r["tier"] == "VERIFIED" and r["verify_stamp"].startswith("construction_cert ")
                                and r["verify_stamp"].endswith("(%s, exact)" % k) for r, k in
                                zip(new, ("fuse-1", "derive-1", "product-1"))), "three VERIFIED rows with construction_cert stamps")
    check(all(r["snapshot_id"] == "pr-12" and r["notes"].startswith("credit: Ben Builder; ") and
              "from submissions/con-1/constructions.csv" in r["notes"] and r["family_sha256"] == "" for r in new),
          "rows: snapshot pr-12, credit, the route mark, no family_sha256")
    check([r["array_sha256"] for r in new] == [r_fuse["sha256"], r_der["sha256"], r_pro["sha256"]],
          "identity: the rebuilt arrays' canonical sha256")
    check(new[1]["builds_on"] == "oa-bush1952" and new[2]["builds_on"] == "product-cmmssy2006;pca-ct2013", "builds_on kept")
    man = {m["sha256"]: m for m in csv.DictReader(open(os.path.join(TD, "MANIFEST.csv"), newline=""))}
    for r, t, v in zip(new, (2, 2, 2), (3, 2, 3)):
        m = man.get(r["array_sha256"])
        ok = m is not None and subprocess.run([cav, os.path.join(TD, "arrays", m["file"]), str(t), str(v), "2"],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        check(ok and cs.canonical_of_file(os.path.join(TD, "arrays", m["file"]), v)[2] == r["array_sha256"],
              "stored array %s verifies with ca_verify and hashes to the row" % (m or {}).get("file"))
    lst = list(csv.DictReader(open(os.path.join(TD, "constructions", "CONSTRUCTIONS.csv"), newline="")))
    check(len(lst) == 3 and all(os.path.isfile(os.path.join(TD, "constructions", c["file"])) for c in lst)
          and os.path.isfile(os.path.join(TD, "constructions", "con-1", "ca3.txt")), "certificates and file ingredients stored and listed")
    rc, probs, txt = consistency(T, base)
    check(rc == 0, "consistency passes (%s)" % (probs[:3] or (txt[-300:] if rc else "")))
    cpath = os.path.join(TD, "constructions", "con-1", "derive.json")
    cdata = file_bytes(cpath)
    open(cpath, "wb").write(cdata.replace(b'"symbol": 1', b'"symbol": 0'))
    rc, probs, _ = consistency(T, base)
    check(rc == 1 and any("CONSTRUCTIONS.csv" in x and "sha256" in x for x in probs), "consistency: a tampered certificate is caught")
    open(cpath, "wb").write(cdata)
    lp = os.path.join(TD, "constructions", "CONSTRUCTIONS.csv")
    ldata = file_bytes(lp)
    open(lp, "wb").write(b"\n".join(ldata.split(b"\n")[:-2]) + b"\n")
    rc, probs, _ = consistency(T, base)
    check(rc == 1 and any("no listing" in x for x in probs), "consistency: a construction row without a listing is caught")
    open(lp, "wb").write(ldata)
    subprocess.run(["git", "-C", T, "-c", "user.name=x", "-c", "user.email=x@x", "-c", "gc.auto=0", "add", "-A", "table/arrays",
                    "table/constructions", "table/ca_table.csv", "table/MANIFEST.csv"], check=True)
    subprocess.run(["git", "-C", T, "-c", "user.name=x", "-c", "user.email=x@x", "-c", "gc.auto=0", "commit", "-qm", "con-1"], check=True)

    # --- refusals --------------------------------------------------------------------------------
    def neg(name, files, line, why):
        d = os.path.join(T, "submissions", name)
        os.makedirs(d)
        for fn, content in files.items():
            open(os.path.join(d, fn), "w").write(content)
        open(os.path.join(d, "constructions.csv"), "w").write(",".join(ccn.HEADER) + "\n" + line)
        before = file_bytes(os.path.join(TD, "ca_table.csv"))
        rc, out = quiet(ccn.main, [d, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out",
                                   os.path.join(W, name), "--apply"])
        rep = open(os.path.join(W, name, "report.md")).read()
        check(rc == 1 and why in rep and file_bytes(os.path.join(TD, "ca_table.csv")) == before,
              "refused, table unchanged: %s" % name)
    fj = open(os.path.join(S, "fuse.json")).read()
    neg("dup-again", {"fuse.json": fj}, con_line(2, 3, 5, r_fuse["N"], "fuse.json", "C D", "fusing", "fuse-ckrs2010"),
        "duplicate")
    pcz = os.path.join(REPO, "table", "constructions", "powercz")
    files = {fn: open(os.path.join(pcz, fn)).read() for fn in os.listdir(pcz)}
    real_sha = [r for r in table_rows(T) if r["t"] == "4" and r["k"] == "1368" and r["N"] == "216" and r["tier"] == "VERIFIED"]
    neg("dup-powercz", files, con_line(4, 2, 1368, 216, "CA_216_4_1368_2.cert.json", "C D", "Power CZ", "power-cz2012"),
        "duplicate" if real_sha else "PASS")
    bad = json.loads(fj)
    bad["expected"]["N"] += 1
    neg("wrong-N", {"fuse.json": json.dumps(bad)}, con_line(2, 3, 5, r_fuse["N"] + 1, "fuse.json", "C D", "fusing",
                                                             "fuse-ckrs2010"), "rejected by tools/construction_cert.py")
    neg("claim-differs", {"fuse.json": fj}, con_line(2, 3, 6, r_fuse["N"], "fuse.json", "C D", "fusing", "fuse-ckrs2010"),
        "the claim says")
    scert = json.dumps(cert("derive-1", {"t": 1, "v": 2, "input": {"table": sha_s2}, "column": 0, "symbol": 0}, 10, 40))
    neg("screened-input", {"s.json": scert}, con_line(1, 2, 40, 10, "s.json", "C D", "derived", "fuse-ckrs2010"),
        "is not the array_sha256 of a counted VERIFIED row")
    d2 = cert("derive-1", {"t": 1, "v": 2, "input": {"table": sha_s}, "column": 0, "symbol": 1})
    tmpd = os.path.join(W, "d2")
    os.makedirs(tmpd)
    r2 = finish(os.path.join(tmpd, "d2.json"), d2, TD)
    neg("empty-builds-on", {"d2.json": json.dumps(d2)}, con_line(1, 2, 39, r2["N"], "d2.json", "C D", "derived", ""),
        "builds_on is empty")
    # not stored: the storage limit lowered, so only the certificate is kept
    d = os.path.join(T, "submissions", "con-big")
    os.makedirs(d)
    shutil.copyfile(os.path.join(tmpd, "d2.json"), os.path.join(d, "d2.json"))
    open(os.path.join(d, "constructions.csv"), "w").write(",".join(ccn.HEADER) + "\n" +
                                                          con_line(1, 2, 39, r2["N"], "d2.json", "Eve Big", "derived array", "fuse-ckrs2010"))
    old = ccn.STORE_MAX_BYTES
    ccn.STORE_MAX_BYTES = 100
    nman = len(list(csv.DictReader(open(os.path.join(TD, "MANIFEST.csv"), newline=""))))
    rc, out = quiet(ccn.main, [d, "--table-dir", TD, "--ca-verify", cav, "--out", os.path.join(W, "big"), "--apply"])
    ccn.STORE_MAX_BYTES = old
    last = table_rows(T)[-1]
    check(rc == 0 and last["array_sha256"] == r2["sha256"] and "not stored" in last["notes"]
          and len(list(csv.DictReader(open(os.path.join(TD, "MANIFEST.csv"), newline="")))) == nman,
          "an array above the storage limit is entered with its certificate only")
    rc, probs, txt = consistency(T, base)
    check(rc == 0, "consistency passes with the unstored array (%s)" % (probs[:3] or (txt[-300:] if rc else "")))
    print("\n%d passed, %d failed" % (tu.RESULTS["pass"], tu.RESULTS["fail"]))
    if not keep:
        shutil.rmtree(root, ignore_errors=True)
    return 1 if tu.RESULTS["fail"] else 0


if __name__ == "__main__":
    keep = sys.argv[sys.argv.index("--keep") + 1] if "--keep" in sys.argv else None
    sys.exit(run(keep))
