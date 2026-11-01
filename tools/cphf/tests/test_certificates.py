#!/usr/bin/env python3
"""End-to-end tests of tools/check_certificates.py and tools/cphf_cert.py (standard library only).

Usage: python3 tools/cphf/tests/test_certificates.py

Works on a temporary copy of table/ (without arrays/), never on the repository's own table. Tests:
  identity     family_sha256 of the stored families equals CERTIFICATES.csv, and cphfcheck canon
               writes the same bytes as the Python serialization
  local        the unsharded exact check, --apply, and the consistency checks of the result
  duplicate    the same family again is rejected, and so is a family named twice
  sharded      plan, run (3 shards + array hash), results, apply-result: VERIFIED
  forged       a missing, repeated or relabelled shard never gives VERIFIED (the claim is screened);
               a tampered result folder is refused at entry
  failing      a family that is not a CPHF fails in the shards, in the screen and in the light check
  screened     over the budget: SCREENED, then an exact check on another machine adds VERIFIED;
               the same family screened again is refused
  hashless     above the entry threshold (lowered in-process) the row has no array_sha256, is
               identified by family_sha256 and passes the consistency checks, which reject it
               under the real threshold
  fill         family_sha256 filled once in the existing certificate rows: allowed from empty to the
               listing's value, refused for another value, on another row, or once set (needs git)
  light        the pull request check through check_submission.py
Prints PASS/FAIL per test; exit status 0 only if everything passed.
"""
import contextlib
import csv
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(REPO, "tools")
sys.path.insert(0, TOOLS)
import cphf_cert as cc  # noqa: E402
import check_certificates as ck  # noqa: E402
import check_submission as cs  # noqa: E402
import consistency  # noqa: E402

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": " + " ".join(str(detail).split())[-400:]),
          flush=True)


def quiet(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = fn(*args)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
            buf.write(str(e))
    return code, buf.getvalue()


def cert(args):
    return quiet(ck.main, args)


def write_claims(sub, claims):
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "certificates.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(ck.HEADER)
        for c in claims:
            w.writerow([c.get(x, "") for x in ck.HEADER])


def claim(t, v, k, N, fname, mode=""):
    return dict(t=t, v=v, k=k, N=N, file=fname, mode=mode, source_detail="test", construction="test CPHF",
                builds_on="cphf-smc2006", credit="Test Person", notes="")


def stored_family(name):
    return [l.split() for l in open(os.path.join(REPO, "table", "certificates", name))
            if l.strip() and not l.startswith("#")]


def consistency_problems(root):
    """the table-level consistency checks on the copy (arrays/ is not part of the copy)"""
    cwd = os.getcwd(); os.chdir(root)
    try:
        consistency.problems.clear()
        raw, rows, man = consistency.load()
        consistency.check_structure(raw, rows, man)
        consistency.check_certificates(rows)
        consistency.check_retracted(rows)
        return list(consistency.problems)
    finally:
        os.chdir(cwd)


def table_rows(root):
    return list(csv.DictReader(open(os.path.join(root, "table", "ca_table.csv"), newline="", encoding="utf-8")))


def fresh(tmp):
    root = os.path.join(tmp, "repo%d" % random.randrange(10 ** 9))
    os.makedirs(os.path.join(root, "table"))
    for name in os.listdir(os.path.join(REPO, "table")):
        src = os.path.join(REPO, "table", name)
        if name == "arrays":
            continue
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(root, "table", name))
        else:
            shutil.copy(src, os.path.join(root, "table", name))
    os.makedirs(os.path.join(root, "submissions"))
    return root


def make_subs(root):
    """test-rev: CPHF_11_121_3_5 with its columns reversed (a CPHF, progression rows, cyclic);
    test-aff: the affine CPHF(1; 5, 5, 2); test-bad: a random family that is not a CPHF"""
    sub = os.path.join(root, "submissions", "test-rev")
    os.makedirs(sub)
    with open(os.path.join(sub, "rev.txt"), "w") as f:
        f.write("# reversed\n" + "".join(" ".join(r[::-1]) + "\n" for r in stored_family("CPHF_11_121_3_5.txt")))
    write_claims(sub, [claim(5, 3, 121, 2663, "rev.txt")])
    sub2 = os.path.join(root, "submissions", "test-aff")
    os.makedirs(sub2)
    with open(os.path.join(sub2, "aff.txt"), "w") as f:
        f.write(" ".join(str(5 + x) for x in range(5)) + "\n")
    write_claims(sub2, [claim(2, 5, 5, 25, "aff.txt", "auto affine")])
    sub3 = os.path.join(root, "submissions", "test-bad")
    os.makedirs(sub3)
    rng = random.Random(7)
    with open(os.path.join(sub3, "bad.txt"), "w") as f:
        for _ in range(3):
            f.write(" ".join(str(rng.randrange(1, 27)) for _ in range(60)) + "\n")
    write_claims(sub3, [claim(3, 3, 60, 3 * 26 + 1, "bad.txt")])
    return sub, sub2, sub3


def sharded(root, sub, extra=(), drop=None, tamper=None):
    """plan, every task, results; returns (code, result folder)"""
    tdir = os.path.join(root, "table")
    plan = os.path.join(root, "plan-%s.json" % os.path.basename(sub))
    code, out = cert([sub, "--table-dir", tdir, "--plan", plan, "--threads", "2"] + list(extra))
    doc = json.load(open(plan))
    tasks = os.path.join(root, "tasks-%s" % os.path.basename(sub))
    for tk in doc["tasks"]:
        if drop and tk in drop:
            continue
        cert([sub, "--table-dir", tdir, "--run", plan, "--task", tk, "--out", os.path.join(tasks, tk), "--threads", "2"])
    if tamper:
        tamper(tasks)
    res = os.path.join(root, "result-%s" % os.path.basename(sub))
    code, out = cert([sub, "--table-dir", tdir, "--results", plan, "--tasks", tasks, "--out", res, "--threads", "2"]
                     + list(extra))
    return code, res, doc


def fill_tests(tmp):
    """consistency.check_append_only: family_sha256 may go from empty to the value of the row's
    CERTIFICATES.csv listing, once; any other change of it is refused. The base is a git commit of a
    copy of the table in which the certificate rows have an empty family_sha256."""
    if shutil.which("git") is None:
        record("family_sha256 fill: git available", False, "git not found")
        return
    root = fresh(tmp)
    path = os.path.join(root, "table", "ca_table.csv")
    raw = open(path, "rb").read()
    lines = raw.split(b"\r\n")
    filled = [i for i, l in enumerate(lines) if re.search(rb",[0-9a-f]{64}$", l) and i > 0]
    if len(filled) < 2:
        record("family_sha256 fill: certificate rows filled in this table", False, "%d rows" % len(filled))
        return
    blank = list(lines)
    for i in filled:
        blank[i] = blank[i][:-64]
    git = lambda *a: subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), cwd=root,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def problems_vs(base):
        cwd = os.getcwd(); os.chdir(root)
        try:
            consistency.problems.clear()
            consistency.check_append_only(base)
            return list(consistency.problems)
        finally:
            os.chdir(cwd)
    git("init", "-q")
    open(path, "wb").write(b"\r\n".join(blank))
    git("add", "table/ca_table.csv"); git("commit", "-q", "-m", "blank")
    open(path, "wb").write(raw)
    pr = problems_vs("HEAD")
    record("family_sha256 fill: empty to the listing's value is allowed", not pr, "; ".join(pr[:2]))
    bad = list(lines)
    bad[filled[0]] = bad[filled[0]][:-1] + (b"0" if bad[filled[0]][-1:] != b"0" else b"1")
    open(path, "wb").write(b"\r\n".join(bad))
    pr = problems_vs("HEAD")
    record("family_sha256 fill: a value not the listing's is refused", any("family_sha256 changed" in p for p in pr),
           "; ".join(pr[:2]))
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))
    plain = next(i for i, r in enumerate(rows, 1) if r["tier"] == "VERIFIED" and not r["family_sha256"]
                 and not r["verify_stamp"].startswith(consistency.CERT_STAMPS))
    other = list(lines)
    other[plain] = other[plain] + lines[filled[0]][-64:]
    open(path, "wb").write(b"\r\n".join(other))
    pr = problems_vs("HEAD")
    record("family_sha256 fill: refused on a row not checked through a certificate",
           any("family_sha256 changed" in p for p in pr), "; ".join(pr[:2]))
    open(path, "wb").write(raw)
    git("add", "table/ca_table.csv"); git("commit", "-q", "-m", "filled")
    open(path, "wb").write(b"\r\n".join(bad))
    pr = problems_vs("HEAD")
    record("family_sha256 fill: never changed once set", any("family_sha256 changed" in p for p in pr), "; ".join(pr[:2]))
    open(path, "wb").write(b"\r\n".join(blank))
    pr = problems_vs("HEAD")
    record("family_sha256 fill: never emptied once set", any("family_sha256 changed" in p for p in pr), "; ".join(pr[:2]))
    shutil.rmtree(root, ignore_errors=True)


def main():
    tmp = tempfile.mkdtemp(prefix="certtest-")
    try:
        run_all(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [n for n, ok in RESULTS if not ok]
    print("%d tests, %d failed%s" % (len(RESULTS), len(bad), (": " + ", ".join(bad)) if bad else ""))
    return 1 if bad else 0


def run_all(tmp):
    exe = ck.build(tmp)
    ck.build = lambda _tmp: exe            # one build for every call below
    ck.SCREEN_SAMPLES = 20000              # a smaller screen; its rules are the same
    # identity of the stored families
    certs = list(csv.DictReader(open(os.path.join(REPO, "table", "certificates", "CERTIFICATES.csv"))))
    ok, why = True, ""
    for c in certs:
        m = re.match(r"CPHF\((\d+); (\d+), (\d+), (\d+)\)", c["family"]); n, k, q, t = map(int, m.groups())
        path = os.path.join(REPO, "table", "certificates", c["file"])
        fs = cc.family_identity(path, q, t)[0]
        subprocess.run([exe, path, str(t), str(q), "canon", os.path.join(tmp, "c.txt")], check=True,
                       stdout=subprocess.DEVNULL)
        if fs != c["family_sha256"] or ck.file_sha(os.path.join(tmp, "c.txt")) != fs:
            ok, why = False, c["file"]
    record("identity stored families (Python and cphfcheck canon)", ok, why)

    # local exact check and entry
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, out = cert([sub, "--table-dir", tdir, "--threads", "2", "--apply"])
    rows = table_rows(root)
    r = rows[-1]
    record("local exact + apply", code == 0 and r["tier"] == "VERIFIED" and r["family_sha256"]
           and "(CPHF certificate, exact)" in r["verify_stamp"] and len(r["array_sha256"]) == 64, out[-300:])
    pr = consistency_problems(root)
    record("local: consistency", not pr, "; ".join(pr[:3]))
    code, out = cert([sub, "--table-dir", tdir, "--threads", "2"])
    record("duplicate family rejected", code == 1 and "duplicate" in out, out[-200:])
    dup = os.path.join(root, "submissions", "test-dup")
    shutil.copytree(sub2, dup)
    shutil.copy(os.path.join(dup, "aff.txt"), os.path.join(dup, "aff2.txt"))
    write_claims(dup, [claim(2, 5, 5, 25, "aff.txt", "affine"), claim(2, 5, 5, 25, "aff2.txt", "")])
    code, out = cert([dup, "--table-dir", tdir, "--threads", "2"])
    record("family named twice in one submission rejected", code == 1 and "named twice" in out, out[-200:])
    code, out = cert([sub2, "--table-dir", tdir, "--threads", "2"])
    record("affine claim, mode 'auto affine'", code == 0 and "PASS aff.txt" in out, out[-200:])
    write_claims(sub2, [claim(2, 5, 5, 25, "aff.txt", "")])
    code, out = cert([sub2, "--table-dir", tdir, "--threads", "2"])
    record("affine decided by N when the mode is empty", code == 0, out[-200:])
    write_claims(sub2, [claim(2, 5, 5, 21, "aff.txt", "")])
    code, out = cert([sub2, "--table-dir", tdir, "--threads", "2"])
    record("wrong N rejected", code == 1 and "gives" in out, out[-200:])
    write_claims(sub2, [claim(2, 5, 5, 25, "aff.txt", "cyclic 1 affine")])
    code, out = cert([sub2, "--table-dir", tdir, "--threads", "2"])
    record("explicit mode cyclic s still works", code == 0, out[-200:])
    write_claims(sub2, [claim(2, 5, 5, 25, "aff.txt", "progression affine")])
    code, out = cert([sub2, "--table-dir", tdir, "--threads", "2"])
    record("explicit mode progression still works", code == 0, out[-200:])
    root2 = fresh(tmp)
    subf = make_subs(root2)[0]
    write_claims(subf, [claim(5, 3, 121, 2663, "rev.txt", "fastprog")])
    code, out = cert([subf, "--table-dir", os.path.join(root2, "table"), "--threads", "2"])
    record("explicit mode fastprog", code == 0 and "PASS rev.txt: fastprog," in out, out[-200:])

    # sharded on main
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"])
    rj = json.load(open(os.path.join(res, "result.json")))
    record("sharded plan uses several shards", doc["claims"][0]["shards"] >= 2, str(doc["claims"][0]["shards"]))
    record("auto plans fastprog for a family of progression rows", doc["claims"][0]["method"] == "fastprog",
           doc["claims"][0]["method"])
    record("sharded results: VERIFIED", code == 0 and rj["claims"][0]["tier"] == "VERIFIED", rj["claims"][0]["check"])
    code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--out", os.path.join(root, "o")])
    record("apply-result without --apply changes nothing", code == 0 and len(table_rows(root)) == len(table_rows(fresh(tmp))))
    code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
    rows = table_rows(root)
    record("apply-result --apply", code == 0 and rows[-1]["tier"] == "VERIFIED" and "shards" in
           open(os.path.join(tdir, "certificates", "CERTIFICATES.csv")).read().splitlines()[-1], out[-200:])
    pr = consistency_problems(root)
    record("sharded: consistency", not pr, "; ".join(pr[:3]))
    code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
    record("the same result twice is refused (duplicate)", code == 1 and len(table_rows(root)) == len(rows), out[-200:])

    # forged and missing shards never give VERIFIED
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"], drop={"c0-s1"})
    rj = json.load(open(os.path.join(res, "result.json")))
    record("missing shard: screened, not verified", code == 0 and rj["claims"][0]["tier"] == "SCREENED"
           and "missing" in rj["claims"][0]["check"], rj["claims"][0]["check"][-160:])

    def relabel(tasks):          # shard 0's output passed off as shard 1 (shard 1 dropped)
        src = os.path.join(tasks, "c0-s0", "c0-s0.txt")
        txt = open(src).read().replace("SHARD i=0 ", "SHARD i=1 ").replace("# task: c0-s0", "# task: c0-s1")
        os.makedirs(os.path.join(tasks, "c0-s1"), exist_ok=True)
        open(os.path.join(tasks, "c0-s1", "c0-s1.txt"), "w").write(txt)
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"], drop={"c0-s1"}, tamper=relabel)
    rj = json.load(open(os.path.join(res, "result.json")))
    record("relabelled shard: detected, screened", rj["claims"][0]["tier"] == "SCREENED"
           and ("add up" in rj["claims"][0]["check"] or "is in shards" in rj["claims"][0]["check"]),
           rj["claims"][0]["check"][-160:])

    def duplicate(tasks):
        shutil.copytree(os.path.join(tasks, "c0-s0"), os.path.join(tasks, "c0-s0-copy"))
        os.rename(os.path.join(tasks, "c0-s0-copy", "c0-s0.txt"), os.path.join(tasks, "c0-s0-copy", "c0-s0x.txt"))
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"], tamper=duplicate)
    rj = json.load(open(os.path.join(res, "result.json")))
    record("repeated shard: detected, screened", rj["claims"][0]["tier"] == "SCREENED"
           and "twice" in rj["claims"][0]["check"], rj["claims"][0]["check"][-160:])
    # a good result whose shard outputs are tampered with afterwards is refused at entry
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"])
    os.remove(os.path.join(res, "tasks", "c0-s1.txt"))
    before = len(table_rows(root))
    code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
    record("tampered result refused at entry", code == 1 and len(table_rows(root)) == before, out[-200:])

    # a family that is not a CPHF
    code, res, doc = sharded(root, sub3, extra=["--shard-hours", "1e-7"])
    rep = open(os.path.join(res, "report.md")).read()
    record("not a CPHF: shards find it, nothing passes", code == 1 and "not a CPHF" in rep, rep[-200:])
    code, res, doc = sharded(root, sub3, extra=["--shard-hours", "1e-12", "--max-shards", "1"])
    rep = open(os.path.join(res, "report.md")).read()
    record("not a CPHF: the screen finds it", code == 1 and "not a CPHF" in rep, rep[-200:])
    code, out = cert([sub3, "--table-dir", tdir, "--threads", "2"])
    record("not a CPHF: local exact check fails", code == 1 and "not a CPHF" in out, out[-200:])

    # over the budget: SCREENED, later VERIFIED by an exact check elsewhere
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-12", "--max-shards", "2"])
    rj = json.load(open(os.path.join(res, "result.json")))
    record("over budget: plan screens", not doc["claims"][0]["exact"] and doc["tasks"] == ["c0-hash"], str(doc["tasks"]))
    code, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
    rows = table_rows(root)
    record("over budget: SCREENED row", code == 0 and rows[-1]["tier"] == "SCREENED"
           and "screened" in rows[-1]["verify_stamp"] and "SCREENED, not exhaustively verified" in rows[-1]["notes"],
           rows[-1]["verify_stamp"])
    pr = consistency_problems(root)
    record("screened: consistency", not pr, "; ".join(pr[:3]))
    code, res2, doc = sharded(root, sub, extra=["--shard-hours", "1e-12", "--max-shards", "2"])
    record("screened again: refused", code == 1, "")
    code, out = cert([sub, "--table-dir", tdir, "--threads", "2", "--apply"])
    rows = table_rows(root)
    record("exact check later: VERIFIED row added", code == 0 and rows[-1]["tier"] == "VERIFIED"
           and rows[-2]["tier"] == "SCREENED" and rows[-1]["family_sha256"] == rows[-2]["family_sha256"]
           and "entered earlier as SCREENED" in rows[-1]["notes"], out[-200:])
    pr = consistency_problems(root)
    record("screened then verified: consistency", not pr, "; ".join(pr[:3]))
    code, out = cert([sub, "--table-dir", tdir, "--threads", "2"])
    record("after VERIFIED the family is a duplicate", code == 1 and "duplicate" in out, out[-160:])

    # above the array hash threshold (lowered in-process)
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    saved = cc.ARRAY_HASH_MAX_ENTRIES
    cc.ARRAY_HASH_MAX_ENTRIES = 1000
    try:
        code, res, doc = sharded(root, sub, extra=["--shard-hours", "1e-7"])
        code2, out = cert([sub, "--table-dir", tdir, "--apply-result", res, "--apply", "--out", os.path.join(root, "o")])
        rows = table_rows(root)
        r = rows[-1]
        record("hashless: no hash task, row without array_sha256", "c0-hash" not in doc["tasks"] and code2 == 0
               and r["array_sha256"] == "" and len(r["family_sha256"]) == 64
               and r["verify_stamp"].endswith("(CPHF certificate, exact; array not hashed)"), r["verify_stamp"])
        pr = consistency_problems(root)
        record("hashless: consistency with the lowered threshold", not pr, "; ".join(pr[:3]))
        sys.path.insert(0, os.path.join(REPO, "table"))
        import ca_table
        record("hashless: identity() is the family", ca_table.identity(r) == ("family", r["family_sha256"]))
        # a RETRACTED row for it is matched by family_sha256
        ret = dict(r); ret.update(tier="RETRACTED", notes="test: retracted")
        with open(os.path.join(tdir, "ca_table.csv"), "a", newline="", encoding="utf-8") as f:
            csv.writer(f, lineterminator="\r\n").writerow([ret[h] for h in cs.TABLE_HEADER])
        rows = table_rows(root)
        pr = consistency_problems(root)
        record("hashless: RETRACTED row keyed on family_sha256", not pr and
               not any(x["tier"] == "VERIFIED" and x["family_sha256"] == r["family_sha256"] for x in ca_table.counted(rows)),
               "; ".join(pr[:3]))
    finally:
        cc.ARRAY_HASH_MAX_ENTRIES = saved
    pr = consistency_problems(root)
    record("hashless: rejected under the real threshold", any("without a sha256" in p for p in pr)
           and any("only" in p and "entries" in p for p in pr), "; ".join(pr[:2]))

    # family_sha256 filled once in the existing certificate rows (append-only exception)
    fill_tests(tmp)

    # the light check of a pull request (through check_submission.py)
    root = fresh(tmp); tdir = os.path.join(root, "table")
    sub, sub2, sub3 = make_subs(root)
    cav = os.path.join(tmp, "ca_verify")
    if not os.path.exists(cav):
        subprocess.run(["cc", "-O2", "-pthread", "-o", cav, os.path.join(REPO, "ca_verify.c")], check=True)
    out = os.path.join(root, "light")
    code, text = quiet(cs.main, [sub, "--table-dir", tdir, "--ca-verify", cav, "--out", out, "--threads", "2"])
    rep = open(os.path.join(out, "report.md")).read()
    record("light check passes and states the plan", code == 0 and "on merge: exact check" in rep
           and "Result: PASS" in rep and "estimates:" in rep, rep[-300:])
    out3 = os.path.join(root, "light3")
    code, text = quiet(cs.main, [sub3, "--table-dir", tdir, "--ca-verify", cav, "--out", out3, "--threads", "2"])
    rep = open(os.path.join(out3, "report.md")).read()
    record("light check of a non-CPHF fails in the screen", code == 1 and "not a CPHF" in rep, rep[-300:])
    write_claims(sub2, [claim(2, 5, 5, 25, "aff.txt", "sideways")])
    code, text = quiet(cs.main, [sub2, "--table-dir", tdir, "--ca-verify", cav, "--out", os.path.join(root, "l2"), "--threads", "2"])
    record("light check: bad mode fails", code == 1, "")


if __name__ == "__main__":
    sys.exit(main())
