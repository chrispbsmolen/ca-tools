#!/usr/bin/env python3
"""End-to-end tests of upgrade requests (tools/check_upgrades.py) on a temporary copy of the table.

The copy holds table/ (without the stored arrays: MANIFEST.csv starts empty) in a git repository
of its own, so tools/consistency.py --check --pr --base can compare it with its first commit.
SCREENED entries are made there by the real routes: a claims.csv submission and an external.csv
deposit, both forced to the screen, and a certificates.csv family planned over the budget. Then
upgrade requests are checked, planned, run in shards (in process, as the workflow matrix runs
them), combined and entered, and the table is checked by tools/consistency.py.

Assertions: the VERIFIED rows are exactly the SCREENED rows' claims with the original credit,
construction and builds_on, the mark and the stamp; MANIFEST and EXTERNAL statuses follow; the
family gets its exact listing; consistency passes; and a request that names a VERIFIED, unknown,
retracted or non-covering entry, a request over the budget, missing or tampered shards, and a
request entered twice are all refused or leave the table as it was. Also unit tests of
tools/ca_shard_merge.py.

Usage: test_upgrades.py [--keep DIR]   (prints PASS/FAIL lines and a summary; exit 1 on a failure)
"""
import csv
import glob
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import check_submission as cs  # noqa: E402
import check_certificates as ck  # noqa: E402
import check_upgrades as cu  # noqa: E402
import external_array as ea  # noqa: E402
import ca_shard_merge as sm  # noqa: E402

RESULTS = {"pass": 0, "fail": 0}


def check(cond, what):
    RESULTS["pass" if cond else "fail"] += 1
    print("%s  %s" % ("PASS" if cond else "FAIL", what), flush=True)
    return cond


def quiet(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try:
            rc = fn(*args)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 2
    return rc, buf.getvalue()


def table_rows(T):
    return list(csv.DictReader(open(os.path.join(T, "table", "ca_table.csv"), newline="", encoding="utf-8")))


def file_bytes(path):
    return open(path, "rb").read()


# ---------------------------------------------------------------------------------------------

def make_repo(T):
    os.makedirs(os.path.join(T, "table", "arrays"))
    src = os.path.join(REPO, "table")
    for name in os.listdir(src):
        p = os.path.join(src, name)
        if name == "arrays":
            continue
        if os.path.isdir(p):
            shutil.copytree(p, os.path.join(T, "table", name))
        elif not name.endswith(".md"):
            shutil.copyfile(p, os.path.join(T, "table", name))
    with open(os.path.join(T, "table", "MANIFEST.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(",".join('"%s"' % h for h in cs.MANIFEST_HEADER) + "\n")
    os.makedirs(os.path.join(T, "submissions"))
    g = ["git", "-C", T, "-c", "user.name=x", "-c", "user.email=x@x", "-c", "gc.auto=0"]
    subprocess.run(g[:3] + ["init", "-q"], check=True)
    subprocess.run(g + ["add", "table"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "base"], check=True)
    # untracked, so consistency.py does not check its links (the copy has no tools/ or docs/)
    shutil.copyfile(os.path.join(src, "README.md"), os.path.join(T, "table", "README.md"))
    return subprocess.run(g + ["rev-parse", "HEAD"], stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()


def consistency(T, base):
    p = subprocess.run([sys.executable, os.path.join(REPO, "tools", "consistency.py"), "--check", "--pr",
                        "--base", base], cwd=T, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True)
    probs = [l for l in p.stdout.splitlines() if l.startswith("PROBLEM")]
    return p.returncode, probs, p.stdout


def ca_verify_ok(cav, rows, t, v, tmp):
    path = os.path.join(tmp, "cv.txt")
    with open(path, "w") as f:
        f.write(cs.canon_serialize(rows))
    return subprocess.run([cav, path, str(t), str(v), "2"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def random_ca(rng, cav, N, t, k, v, tmp):
    while True:
        rows = [[rng.randrange(v) for _ in range(k)] for _ in range(N)]
        if ca_verify_ok(cav, rows, t, v, tmp):
            return rows


def write_rows(path, rows):
    with open(path, "w") as f:
        f.write(cs.canon_serialize(rows))


def claims_line(t, v, k, N, fname, credit, construction="random search test", builds_on="new https://example.org/x"):
    return "%d,%d,%d,%d,%s,test recipe %s,%s,%s,%s,\n" % (t, v, k, N, fname, fname, construction, builds_on, credit)


# ---------------------------------------------------------------------------------------------

def run(keep=None):
    tmp_root = keep or tempfile.mkdtemp(prefix="caup-test-")
    T = os.path.join(tmp_root, "repo")
    W = os.path.join(tmp_root, "work")
    os.makedirs(W, exist_ok=True)
    base = make_repo(T)
    TD = os.path.join(T, "table")
    cav = os.path.join(W, "ca_verify")
    subprocess.run(["cc", "-O3", "-pthread", "-o", cav, os.path.join(REPO, "ca_verify.c")], check=True)
    rng = random.Random(20261102)

    # --- unit tests of the shard merge -------------------------------------------------------
    A = random_ca(rng, cav, 30, 2, 40, 2, W)
    write_rows(os.path.join(W, "a.txt"), A)

    def shard_out(n, i, path=os.path.join(W, "a.txt"), t=2, v=2):
        args = [cav, path, str(t), str(v), "2"] + (["%d/%d" % (i, n)] if n > 1 else [])
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True).stdout
    for n in (1, 2, 3, 7):
        outs = [shard_out(n, i) for i in range(n)]
        r = sm.merge(outs, 2, 40, 30, 2)
        check(r["verified"] and r["combos"] == 780 and r["shards"] == n, "merge: %d shards verify, 780 sets" % n)
    outs = [shard_out(3, i) for i in range(3)]
    for name, bad in (("missing shard", outs[:2]), ("repeated shard", [outs[0], outs[0], outs[1], outs[2]]),
                      ("mixed shard counts", [outs[0], outs[1], shard_out(2, 1)]),
                      ("count edited", [outs[0], outs[1], outs[2].replace("all 260 ", "all 261 ", 1)
                                        if "all 260 " in outs[2] else outs[2].replace(" - all ", " - all 1", 1)]),
                      ("other N", None), ("empty output", [outs[0], outs[1], ""])):
        if name == "other N":
            try:
                sm.merge(outs, 2, 40, 31, 2)
                ok = False
            except sm.MergeError:
                ok = True
            check(ok, "merge refuses: %s" % name)
            continue
        try:
            sm.merge(bad, 2, 40, 30, 2)
            ok = False
        except sm.MergeError:
            ok = True
        check(ok, "merge refuses: %s" % name)
    Bad = [row[:] for row in A]
    for row in Bad:
        row[0] = 0
        row[1] = 0
    write_rows(os.path.join(W, "bad.txt"), Bad)
    r = sm.merge([shard_out(3, i, os.path.join(W, "bad.txt")) for i in range(3)], 2, 40, 30, 2)
    check(not r["verified"] and r["gaps"] >= 1, "merge: gaps found in a shard make the merged verdict NOT COVERING")

    # --- SCREENED entries made by the real routes -----------------------------------------------
    old_ff = cs.FULL_FRACTION
    cs.FULL_FRACTION = -1.0                      # every array with more than 30 columns is screened
    S1 = os.path.join(T, "submissions", "scr-array")
    os.makedirs(S1)
    arr1 = random_ca(rng, cav, 30, 2, 40, 2, W)
    write_rows(os.path.join(S1, "A1.txt"), arr1)
    arr2 = random_ca(rng, cav, 120, 2, 45, 3, W)
    write_rows(os.path.join(S1, "A2.txt"), arr2)
    with open(os.path.join(S1, "claims.csv"), "w") as f:
        f.write(",".join(cs.CLAIMS_HEADER) + "\n")
        f.write(claims_line(2, 2, 40, 30, "A1.txt", "Alice Original"))
        f.write(claims_line(2, 3, 45, 120, "A2.txt", "Bob Original", "simulated annealing test", "sa-ccl2003"))
    rc, out = quiet(cs.main, [S1, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out",
                              os.path.join(W, "o-s1"), "--apply", "--date", "2026-11-01"])
    check(rc == 0, "claims.csv submission screened and applied (rc %s)" % rc)
    # an external deposit, screened
    deposit = {}
    real_download = ea.download

    def fake_download(loc, workdir, local_root=None):
        base, _, member = loc.partition("::")
        raw = os.path.join(workdir, "download")
        shutil.copyfile(deposit[base], raw)
        return raw
    ea.download = fake_download
    arr3 = random_ca(rng, cav, 35, 2, 42, 2, W)
    p3 = os.path.join(W, "deposit3.txt")
    with open(p3, "w") as f:                          # 1-based in the deposit, canonical form is 0-based
        f.write("".join(" ".join(str(x + 1) for x in r) + "\n" for r in arr3))
    sha3 = cs.sha256_text(cs.canon_serialize(arr3))
    loc3 = "https://zenodo.org/records/1/files/deposit3.txt"
    deposit[loc3] = p3
    S2 = os.path.join(T, "submissions", "scr-external")
    os.makedirs(S2)
    with open(os.path.join(S2, "external.csv"), "w") as f:
        f.write(",".join(ea.EXT_CLAIMS_HEADER) + "\n")
        f.write("2,2,42,35,%s,%s,test deposit,random search,new https://example.org/y,Carol Original,\n" % (loc3, sha3))
    rc, out = quiet(ea.main, [S2, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--apply"])
    check(rc == 0, "external.csv deposit screened and applied (rc %s)" % rc)
    cs.FULL_FRACTION = old_ff
    # a CPHF family planned over the budget, so screened
    S3 = os.path.join(T, "submissions", "scr-family")
    os.makedirs(S3)
    with tempfile.TemporaryDirectory(prefix="cafam-") as tmpb:
        exe = ck.build(tmpb)
        while True:
            fam = [[rng.randrange(27) for _ in range(12)] for _ in range(8)]
            fp = os.path.join(S3, "F.txt")
            with open(fp, "w") as f:
                f.write("".join(" ".join(map(str, r)) + "\n" for r in fam))
            if ck.run(exe, [fp, 3, 3, "full", 2])[0] == 0:
                break
    with open(os.path.join(S3, "certificates.csv"), "w") as f:
        f.write(",".join(ck.HEADER_NO_MODE) + "\n")
        f.write("3,3,12,%d,F.txt,test family,Sherwood covering perfect hash family,cphf-smc2006,Dana Original,\n"
                % (8 * 26 + 1))
    plan = os.path.join(W, "fam-plan.json")
    rc1, _ = quiet(ck.main, [S3, "--table-dir", TD, "--plan", plan, "--max-shards", "0", "--threads", "2"])
    for task in json.load(open(plan))["tasks"]:          # the array hash
        quiet(ck.main, [S3, "--table-dir", TD, "--run", plan, "--task", task, "--out", os.path.join(W, "fam-tasks")])
    rc2, _ = quiet(ck.main, [S3, "--table-dir", TD, "--results", plan, "--tasks", os.path.join(W, "fam-tasks"),
                             "--out", os.path.join(W, "fam-res"), "--max-shards", "0", "--threads", "2",
                             "--date", "2026-11-01"])
    rc3, _ = quiet(ck.main, [S3, "--table-dir", TD, "--apply-result", os.path.join(W, "fam-res"), "--apply",
                             "--out", os.path.join(W, "fam-app"), "--date", "2026-11-01"])
    check((rc1, rc2, rc3) == (0, 0, 0), "certificates.csv family over the budget: screened and applied %s" % ((rc1, rc2, rc3),))
    rows0 = table_rows(T)
    scr = [r for r in rows0 if r["tier"] == "SCREENED" and r["entered"] >= "2026-11-01"
           and "test" in r["source_detail"]]
    check(len(scr) == 4, "four SCREENED rows made (%d)" % len(scr))
    fam_row = [r for r in scr if r["family_sha256"]][0]
    sha1 = cs.sha256_text(cs.canon_serialize(arr1))
    sha2 = cs.sha256_text(cs.canon_serialize(arr2))
    rc, probs, txt = consistency(T, base)
    check(rc == 0, "consistency passes with the SCREENED rows (%s)" % (probs[:3] or (txt[-300:] if rc else "")))

    # --- the request ---------------------------------------------------------------------------
    U = os.path.join(T, "submissions", "up-1")
    os.makedirs(U)
    with open(os.path.join(U, "upgrade.csv"), "w") as f:
        f.write("kind,sha256,credit,notes\n")
        f.write("array,%s,Erin Requester,\n" % sha1)
        f.write("array,%s,Erin Requester,please\n" % sha2)
        f.write("array,%s,Erin Requester,\n" % sha3)
        f.write("family,%s,Erin Requester,\n" % fam_row["family_sha256"])
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--light", "--out", os.path.join(W, "up-light"), "--threads", "2"])
    check(rc == 0 and out.count("on merge: exact check") == 4, "light check passes and plans 4 exact checks")
    rc, out = quiet(cs.main, [U, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "up-pr")])
    rep = open(os.path.join(W, "up-pr", "report.md")).read()
    check(rc == 0 and "## Upgrade request: `up-1`" in rep and "**Result: PASS.**" in rep,
          "the pull request check (check_submission.py) runs the light check of upgrade.csv")
    before = file_bytes(os.path.join(TD, "ca_table.csv"))
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--threads", "2"])
    check(rc == 0 and out.count(": verified: ") == 4 and "Every entry passed" in out
          and file_bytes(os.path.join(TD, "ca_table.csv")) == before,
          "the local exact check (unsharded, no --apply) passes all 4 and changes nothing")
    plan = os.path.join(W, "up-plan.json")
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--plan", plan, "--threads", "2"])
    doc = json.load(open(plan))
    check(rc == 0 and doc["failed"] is None and len(doc["entries"]) == 4, "plan made")
    # shard the checks: 3 shards for the first array, 2 for the family (the plan is data; the merge
    # must still prove that every t-set was checked once)
    doc["entries"][0]["shards"] = 3
    if doc["entries"][3]["method"] in ("full", "fullfast", "cyclic 1"):
        doc["entries"][3]["shards"] = 2
    doc["tasks"] = cu.tasks_of(doc["entries"])
    json.dump(doc, open(plan, "w"))
    tasks = os.path.join(W, "up-tasks")
    for task in doc["tasks"]:
        rc, _ = quiet(cu.main, [U, "--table-dir", TD, "--run", plan, "--task", task, "--out", tasks, "--threads", "2"])
        check(rc == 0, "task %s ran" % task)
    res = os.path.join(W, "up-res")
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--results", plan, "--tasks", tasks, "--out", res,
                              "--date", "2026-11-02"])
    rj = json.load(open(os.path.join(res, "result.json")))
    check(rc == 0 and [e["outcome"] for e in rj["entries"]] == ["verified"] * 4, "results: 4 verified (%s)"
          % [e["outcome"] for e in rj["entries"]])
    # tampered result folders are refused before anything is entered
    for name, edit in (("a shard output count edited", "count"), ("a shard output removed", "remove"),
                       ("a shard of another array", "sha")):
        bad = os.path.join(W, "up-res-bad")
        shutil.rmtree(bad, ignore_errors=True)
        shutil.copytree(res, bad)
        f0 = sorted(glob.glob(os.path.join(bad, "tasks", "u0-s*.txt")))[1]
        txt0 = open(f0).read()
        if edit == "count":
            import re
            txt0 = re.sub(r"all (\d+) column sets", lambda m: "all %d column sets" % (int(m.group(1)) + 1), txt0)
            open(f0, "w").write(txt0)
        elif edit == "remove":
            os.remove(f0)
        else:
            open(f0, "w").write(txt0.replace(sha1, sha2))
        before = file_bytes(os.path.join(TD, "ca_table.csv"))
        rc, out = quiet(cu.main, [U, "--table-dir", TD, "--apply-result", bad, "--apply", "--out", os.path.join(W, "x")])
        check(rc == 1 and file_bytes(os.path.join(TD, "ca_table.csv")) == before,
              "refused at entry, table unchanged: %s" % name)
    man_before = file_bytes(os.path.join(TD, "MANIFEST.csv"))
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--apply-result", res, "--apply", "--out", os.path.join(W, "up-app"),
                              "--date", "2026-11-02"])
    check(rc == 0, "apply-result enters the rows (rc %s)" % rc)
    rows1 = table_rows(T)
    new = rows1[len(rows0):]
    check(len(new) == 4 and all(r["tier"] == "VERIFIED" for r in new), "4 VERIFIED rows appended")
    for r in new:
        s = [x for x in scr if (x["array_sha256"], x["family_sha256"]) == (r["array_sha256"], r["family_sha256"])]
        same = s and all(s[0][c] == r[c] for c in ("t", "v", "k", "N", "source_id", "source_detail", "snapshot_id",
                                                   "construction", "builds_on", "array_sha256", "family_sha256"))
        check(bool(same), "row %s,%s,%s,%s keeps the claim, construction and builds_on of its SCREENED row"
              % (r["t"], r["v"], r["k"], r["N"]))
        orig = cu.original_credit(s[0]["notes"]) if s else None
        check(r["notes"].startswith("credit: %s; " % orig) and
              ("exact check of the SCREENED row of %s, requested in submissions/up-1 by Erin Requester" % s[0]["entered"])
              in r["notes"], "row notes: original credit %s and the request mark" % orig)
        if r["family_sha256"]:
            check(r["verify_stamp"].startswith("cphfcheck ") and r["verify_stamp"].endswith("(CPHF certificate, exact)"),
                  "family stamp %s" % r["verify_stamp"])
        else:
            check(r["verify_stamp"].startswith("ca_verify ") and " 2026-11-02 " in r["verify_stamp"],
                  "array stamp %s" % r["verify_stamp"])
    check(new[0]["verify_stamp"].endswith("(exact, 3 shards)"), "the sharded array says so in its stamp")
    check("please" in new[1]["notes"], "the request's notes are kept")
    man = list(csv.DictReader(open(os.path.join(TD, "MANIFEST.csv"), newline="")))
    check(all(m["status"] != "screened" for m in man if m["sha256"] in (sha1, sha2)), "MANIFEST status follows")
    check(len(file_bytes(os.path.join(TD, "MANIFEST.csv"))) > 0 and man_before != file_bytes(os.path.join(TD, "MANIFEST.csv")),
          "MANIFEST rewritten")
    ext = list(csv.DictReader(open(os.path.join(TD, "EXTERNAL.csv"), newline="")))
    check([e["status"] for e in ext if e["sha256"] == sha3] == ["verified"], "EXTERNAL status follows")
    certs = list(csv.DictReader(open(os.path.join(TD, "certificates", "CERTIFICATES.csv"), newline="")))
    lst = [c for c in certs if c["family_sha256"] == fam_row["family_sha256"]]
    check(len(lst) == 2 and sum("screened" in c["check"] for c in lst) == 1, "family listed again, exact")
    rc, probs, txt = consistency(T, base)
    check(rc == 0, "consistency passes after the upgrade (%s)" % probs[:3])
    subprocess.run(["git", "-C", T, "-c", "user.name=x", "-c", "user.email=x@x", "-c", "gc.auto=0",
                    "commit", "-qam", "up-1"], check=True)

    # --- refusals --------------------------------------------------------------------------------
    before = file_bytes(os.path.join(TD, "ca_table.csv"))
    rc, out = quiet(cu.main, [U, "--table-dir", TD, "--apply-result", res, "--apply", "--out", os.path.join(W, "x")])
    check(rc == 1 and "already has a VERIFIED row" in out and file_bytes(os.path.join(TD, "ca_table.csv")) == before,
          "the same request entered twice is refused")
    ex_sha = [r for r in rows0 if r["tier"] == "VERIFIED" and r["array_sha256"]][0]["array_sha256"]
    cases = [("an entry with a VERIFIED row", "array,%s,X Y," % ex_sha, "already has a VERIFIED row"),
             ("an unknown sha256", "array,%s,X Y," % ("ab" * 32), "no row of the table"),
             ("kind array for a family row", "array,%s,X Y," % fam_row["array_sha256"], "already has a VERIFIED row"),
             ("a bad kind", "table,%s,X Y," % sha1, "is not 'array' or 'family'"),
             ("an empty credit", "array,%s,," % sha1, "credit is empty"),
             ("upper-case hex", "array,%s,X Y," % sha1.upper(), "lower-case hex")]
    for i, (name, line, why) in enumerate(cases):
        d = os.path.join(T, "submissions", "neg-%d" % i)
        os.makedirs(d)
        with open(os.path.join(d, "upgrade.csv"), "w") as f:
            f.write("kind,sha256,credit,notes\n" + line + "\n")
        rc, out = quiet(cu.main, [d, "--table-dir", TD, "--light", "--out", os.path.join(W, "n%d" % i)])
        check(rc == 1 and why in out, "light check refuses %s" % name)
    d = os.path.join(T, "submissions", "neg-mixed")
    os.makedirs(d)
    open(os.path.join(d, "upgrade.csv"), "w").write("kind,sha256,credit,notes\narray,%s,X Y,\n" % sha1)
    open(os.path.join(d, "claims.csv"), "w").write(",".join(cs.CLAIMS_HEADER) + "\n")
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--light", "--out", os.path.join(W, "nm")])
    check(rc == 1 and "must be alone" in out, "upgrade.csv beside claims.csv is refused")
    rc, out = quiet(cs.main, [d, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "nm-pr")])
    check(rc == 1 and "must be alone" in open(os.path.join(W, "nm-pr", "report.md")).read(),
          "the pull request check fails upgrade.csv beside claims.csv")

    # a SCREENED row whose array is not covering (made by hand, as a faulty screen could leave it),
    # a retracted SCREENED row, and a request over the budget
    cs.FULL_FRACTION = -1.0
    S4 = os.path.join(T, "submissions", "scr-more")
    os.makedirs(S4)
    arr5 = random_ca(rng, cav, 32, 2, 41, 2, W)
    arr6 = random_ca(rng, cav, 33, 2, 43, 2, W)
    write_rows(os.path.join(S4, "A5.txt"), arr5)
    write_rows(os.path.join(S4, "A6.txt"), arr6)
    with open(os.path.join(S4, "claims.csv"), "w") as f:
        f.write(",".join(cs.CLAIMS_HEADER) + "\n")
        f.write(claims_line(2, 2, 41, 32, "A5.txt", "Fay Original"))
        f.write(claims_line(2, 2, 43, 33, "A6.txt", "Gus Original"))
    rc, _ = quiet(cs.main, [S4, "--table-dir", TD, "--ca-verify", cav, "--threads", "2", "--out", os.path.join(W, "o-s4"),
                            "--apply", "--date", "2026-11-01"])
    cs.FULL_FRACTION = old_ff
    sha5 = cs.sha256_text(cs.canon_serialize(arr5))
    sha6 = cs.sha256_text(cs.canon_serialize(arr6))
    # the stored file of A5 is replaced by a non-covering array with the same name, and the row and
    # MANIFEST rewritten to its hash: a SCREENED row whose array is not covering
    bad5 = [r[:] for r in arr5]
    for r in bad5:
        r[1] = r[0]
    bsha = cs.sha256_text(cs.canon_serialize(bad5))
    m5 = [m for m in csv.DictReader(open(os.path.join(TD, "MANIFEST.csv"), newline="")) if m["sha256"] == sha5][0]
    write_rows(os.path.join(TD, "arrays", m5["file"]), bad5)
    for name in ("ca_table.csv", "MANIFEST.csv"):
        p = os.path.join(TD, name)
        data = file_bytes(p).replace(sha5.encode(), bsha.encode())
        open(p, "wb").write(data)
    # A6 retracted
    r6 = [r for r in table_rows(T) if r["array_sha256"] == sha6][0]
    cs.append_text(os.path.join(TD, "ca_table.csv"), cs.table_csv_text([[r6[c] if c != "tier" else "RETRACTED" for c in cs.TABLE_HEADER[:11]]
                                                                         + ["test retraction", "", "", r6["construction"], r6["builds_on"], ""]]), "\r\n")
    rc, probs, _ = consistency(T, base)
    check(rc == 0, "consistency passes with the planted rows (%s)" % probs[:3])
    rows2 = table_rows(T)
    d = os.path.join(T, "submissions", "neg-retracted")
    os.makedirs(d)
    open(os.path.join(d, "upgrade.csv"), "w").write("kind,sha256,credit,notes\narray,%s,X Y,\n" % sha6)
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--light", "--out", os.path.join(W, "nr")])
    check(rc == 1 and "retracted" in out, "light check refuses a retracted SCREENED row")
    d = os.path.join(T, "submissions", "up-bad")
    os.makedirs(d)
    open(os.path.join(d, "upgrade.csv"), "w").write("kind,sha256,credit,notes\narray,%s,X Y,\n" % bsha)
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--light", "--out", os.path.join(W, "nb")])
    check(rc == 0, "light check passes the non-covering SCREENED row (it cannot know)")
    plan = os.path.join(W, "bad-plan.json")
    quiet(cu.main, [d, "--table-dir", TD, "--plan", plan])
    doc = json.load(open(plan))
    doc["entries"][0]["shards"] = 2
    doc["tasks"] = cu.tasks_of(doc["entries"])
    json.dump(doc, open(plan, "w"))
    tb = os.path.join(W, "bad-tasks")
    for task in doc["tasks"]:
        quiet(cu.main, [d, "--table-dir", TD, "--run", plan, "--task", task, "--out", tb, "--threads", "2"])
    rb = os.path.join(W, "bad-res")
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--results", plan, "--tasks", tb, "--out", rb])
    check(rc == 1 and json.load(open(os.path.join(rb, "result.json")))["entries"][0]["outcome"] == "failed",
          "results: the non-covering array fails the exact check")
    before = file_bytes(os.path.join(TD, "ca_table.csv"))
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--apply-result", rb, "--apply", "--out", os.path.join(W, "x")])
    check(rc == 1 and file_bytes(os.path.join(TD, "ca_table.csv")) == before, "nothing entered for it")
    # over the budget, and shards that did not finish: nothing entered, exit 3
    d = os.path.join(T, "submissions", "up-budget")
    os.makedirs(d)
    open(os.path.join(d, "upgrade.csv"), "w").write("kind,sha256,credit,notes\narray,%s,X Y,\n" % bsha)
    plan = os.path.join(W, "bud-plan.json")
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--plan", plan, "--max-shards", "0"])
    doc = json.load(open(plan))
    check(doc["tasks"] == [] and not doc["entries"][0]["exact"], "over the budget: no task planned")
    rbud = os.path.join(W, "bud-res")
    quiet(cu.main, [d, "--table-dir", TD, "--results", plan, "--tasks", os.path.join(W, "none"), "--out", rbud])
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--apply-result", rbud, "--apply", "--out", os.path.join(W, "x")])
    check(rc == 3 and "stays SCREENED" in out and file_bytes(os.path.join(TD, "ca_table.csv")) == before,
          "over the budget: nothing entered, the report says the entry stays SCREENED")
    plan = os.path.join(W, "inc-plan.json")
    quiet(cu.main, [d, "--table-dir", TD, "--plan", plan])
    rinc = os.path.join(W, "inc-res")
    quiet(cu.main, [d, "--table-dir", TD, "--results", plan, "--tasks", os.path.join(W, "none"), "--out", rinc])
    rc, out = quiet(cu.main, [d, "--table-dir", TD, "--apply-result", rinc, "--apply", "--out", os.path.join(W, "x")])
    check(rc == 3 and file_bytes(os.path.join(TD, "ca_table.csv")) == before, "shards that did not finish: nothing entered")
    rc, probs, _ = consistency(T, base)
    check(rc == 0, "consistency passes at the end (%s)" % probs[:3])
    # an edit of the upgrade row is caught by consistency (two VERIFIED rows of the same array)
    p = os.path.join(TD, "ca_table.csv")
    good = file_bytes(p)
    last = [l for l in good.split(b"\r\n") if b"requested in submissions/up-1" in l][0]
    open(p, "wb").write(good + last.replace(b"2026-11-02,", b"2026-11-03,", 1) + b"\r\n")
    rc, probs, _ = consistency(T, base)
    check(rc == 1 and any("upgrade row" in x for x in probs), "consistency catches a second upgrade row")
    open(p, "wb").write(good)
    ea.download = real_download
    print("\n%d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    if not keep:
        shutil.rmtree(tmp_root, ignore_errors=True)
    return 1 if RESULTS["fail"] else 0


if __name__ == "__main__":
    keep = None
    if "--keep" in sys.argv:
        keep = sys.argv[sys.argv.index("--keep") + 1]
    sys.exit(run(keep))
