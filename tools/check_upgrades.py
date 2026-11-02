#!/usr/bin/env python3
"""check_upgrades - check SCREENED entries of the table exactly, on request, and enter VERIFIED rows.

A request is a directory submissions/<slug>/ holding upgrade.csv and nothing else:

    kind,sha256,credit,notes

kind is "array" or "family". sha256 is the array_sha256 of a SCREENED array row (an array stored
in table/arrays or kept in a deposit listed in table/EXTERNAL.csv) or the family_sha256 of a
SCREENED covering perfect hash family (stored in table/certificates). credit names who asks for
the check; the row keeps the credit, construction and builds_on of the SCREENED row. Anyone may
ask.

For every entry this script checks that the row exists, is SCREENED, is not retracted and has no
VERIFIED row yet, and that its array or family can be retrieved, then plans the exact check: for
an array, ca_verify (every t-set, sharded with SHARD/NSHARDS, combined by tools/ca_shard_merge.py,
which proves that the shards checked every one of the C(k,t) column sets exactly once); for a
family, the exact methods of tools/cphf/cphfcheck.c in shards (tools/check_certificates.py,
tools/cphf_cert.py). The time budget is that of certificates: the estimate doubled, at most
MAX_SHARDS shards of SHARD_HOURS hours on RUNNER_THREADS threads per entry, and one pool of the
same core-hours and MAX_TASKS jobs for the whole request, taken in the order of upgrade.csv. An
entry over the budget stays SCREENED and the report says so. Nothing is ever sampled here: an
entry is either checked exactly or left as it is.

Usage (each form prints a report; nothing in table/ changes without --apply):

  check_upgrades.py SUB --light [--out DIR]
        the pull request check: every entry resolved, the estimate and the plan (no exact check)
  check_upgrades.py SUB --plan PLAN.json
        on main: the plan and the tasks of the workflow matrix ("u<i>-s<j>")
  check_upgrades.py SUB --run PLAN.json --task ID --out DIR [--threads N]
        one shard of one entry
  check_upgrades.py SUB --results PLAN.json --tasks DIR --out DIR
        combine the shards and write result.json and report.md
  check_upgrades.py SUB --apply-result DIR [--apply]
        check a result folder again against the current table and enter the VERIFIED rows;
        table-page.yml does this on main, one request at a time
  check_upgrades.py SUB [--threads N] [--apply]
        the exact check on this machine, unsharded (also for a maintainer's own run)

Exit status: 0 passed (and with --apply at least one row entered), 1 a check failed (an entry is
not SCREENED, cannot be retrieved, or was shown not to be covering), 3 passed but nothing to enter
(every entry over the budget or not completed), 2 usage error. Standard library only.
"""
import argparse
import csv
import datetime
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_submission as cs  # noqa: E402
import check_certificates as ck  # noqa: E402
import cphf_cert as cc  # noqa: E402
import ca_shard_merge as sm  # noqa: E402
import external_array as ea  # noqa: E402
from cphf_cert import CertError  # noqa: E402

HEADER = ["kind", "sha256", "credit", "notes"]
KINDS = ("array", "family")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CA_VERIFY_SRC = os.path.join(REPO, "ca_verify.c")
# the note that marks an upgrade row; table-page.yml and certificate-check.yml look for
# "requested in submissions/<slug> by" to know that a request is entered
MARK = "exact check of the SCREENED row of %s, requested in submissions/%s by %s"
OTHER_ROUTES = ("claims.csv", "certificates.csv", "external.csv", "constructions.csv")


class UpError(Exception):
    """fails one entry; the message goes into the report"""


def ca_verify_tool():
    return hashlib.sha256(open(CA_VERIFY_SRC, "rb").read()).hexdigest()[:12]


def build_ca_verify(tmp):
    exe = os.path.join(tmp, "ca_verify")
    p = subprocess.run(["cc", "-O3", "-pthread", "-o", exe, CA_VERIFY_SRC], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        raise SystemExit("could not build ca_verify: %s" % p.stderr[:300])
    return exe


# ---------------------------------------------------------------------------------------------
# reading the request and the table

def read_request(sub):
    slug = os.path.basename(sub.rstrip("/"))
    path = os.path.join(sub, "upgrade.csv")
    others = [n for n in OTHER_ROUTES if os.path.exists(os.path.join(sub, n))]
    if others:
        raise UpError("upgrade.csv must be alone in its folder (found also %s); put the request "
                      "in a folder of its own" % ", ".join(others))
    if os.path.islink(path) or not os.path.isfile(path):
        raise UpError("submissions/%s/upgrade.csv is missing or not a regular file" % slug)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        hdr = [h.strip() for h in next(rd, [])]
        if hdr != HEADER:
            raise UpError("upgrade.csv header must be exactly %s (found %s)" % (",".join(HEADER), ",".join(hdr)))
        out = []
        for n, rec in enumerate(rd, 2):
            if not any(x.strip() for x in rec):
                continue
            if len(rec) != len(HEADER):
                raise UpError("upgrade.csv line %d has %d fields, expected %d" % (n, len(rec), len(HEADER)))
            out.append(dict(zip(HEADER, rec), line=n))
    if not out:
        raise UpError("upgrade.csv names no entry")
    return out


def load_ctx(table_dir):
    rows, manifest = cs.load_table(table_dir)
    ext_path = os.path.join(table_dir, "EXTERNAL.csv")
    ext = list(csv.DictReader(open(ext_path, newline="", encoding="utf-8"))) if os.path.exists(ext_path) else []
    certs = ck.load_certs(table_dir)
    gone = {r_key(r) for r in rows if r["tier"] == "RETRACTED"}
    return dict(table_dir=table_dir, rows=rows, manifest=manifest, external=ext, certs=certs, retracted=gone,
                refs=cs.load_references(table_dir))


def r_key(r):
    return (r["t"], r["v"], r["k"], r["N"], r["array_sha256"], r.get("family_sha256") or "")


def original_credit(notes):
    m = re.search(r"(?:^|; )credit: ([^;]+)", notes or "")
    return m.group(1).strip() if m else None


def resolve(e, ctx, seen):
    """The SCREENED row an entry names and where its array or family is. Raises UpError."""
    kind = (e.get("kind") or "").strip()
    sha = (e.get("sha256") or "").strip()
    for fld in HEADER:
        if any(ch in (e.get(fld) or "") for ch in "\r\n"):
            raise UpError("field %s contains a line break" % fld)
    if kind not in KINDS:
        raise UpError("kind %r is not 'array' or 'family'" % kind)
    if not HEX64.match(sha):
        raise UpError("sha256 %r is not 64 lower-case hex digits" % sha[:70])
    if not (e.get("credit") or "").strip():
        raise UpError("credit is empty: name who asks for the check (a real name, Rule 5)")
    if (kind, sha) in seen:
        raise UpError("the same %s is named twice in upgrade.csv" % kind)
    seen.add((kind, sha))
    col = "array_sha256" if kind == "array" else "family_sha256"
    named = [r for r in ctx["rows"] if (r.get(col) or "") == sha]
    if not named:
        raise UpError("no row of the table has %s %s" % (col, sha))
    if any(r["tier"] == "VERIFIED" for r in named):
        raise UpError("this %s already has a VERIFIED row; nothing to upgrade" % kind)
    scr = [r for r in named if r["tier"] == "SCREENED"]
    if not scr:
        raise UpError("the rows with %s %s are %s, not SCREENED" % (col, sha[:12], ", ".join(sorted({r["tier"] for r in named}))))
    if len(scr) > 1:
        raise UpError("%d SCREENED rows have %s %s; the request is ambiguous, ask the maintainer" % (len(scr), col, sha[:12]))
    r = scr[0]
    if r_key(r) in ctx["retracted"]:
        raise UpError("the SCREENED row is retracted (a RETRACTED row names it); it is not checked again")
    credit = original_credit(r["notes"])
    if not credit:
        raise UpError("the SCREENED row's notes do not name its credit; ask the maintainer")
    t, v, k, N = int(r["t"]), int(r["v"]), int(r["k"]), int(r["N"])
    out = dict(kind=kind, sha=sha, row=r, t=t, v=v, k=k, N=N, credit=credit, asked_by=e["credit"].strip(),
               notes=(e.get("notes") or "").strip())
    if kind == "array":
        if r.get("family_sha256"):
            raise UpError("this SCREENED row is given by a covering perfect hash family; name its "
                          "family_sha256 %s with kind family" % r["family_sha256"])
        if v > cs.CA_VERIFY_MAX_V or v ** t > (1 << 40) or v ** (t - 1) > cs.CA_VERIFY_MAX_VT1 or t < 2:
            raise UpError("t = %d, v = %d is outside the range of ca_verify" % (t, v))
        man = [m for m in ctx["manifest"] if m["sha256"] == sha]
        ext = [x for x in ctx["external"] if x["sha256"] == sha]
        if man:
            m = man[0]
            path = os.path.join(ctx["table_dir"], "arrays", m["file"])
            if (m["t"], m["v"], m["k"], m["N"]) != (r["t"], r["v"], r["k"], r["N"]):
                raise UpError("table/arrays/%s is listed with other parameters than the row" % m["file"])
            if not os.path.isfile(path):
                raise UpError("table/arrays/%s is listed in MANIFEST.csv but missing" % m["file"])
            out["source"] = dict(file=m["file"])
            out["where"] = "table/arrays/%s" % m["file"]
        elif ext:
            x = ext[0]
            try:
                ea.check_location(x["location"])
            except ea.ExtError as err:
                raise UpError("the deposit of this array cannot be fetched: %s" % err)
            if (x["t"], x["v"], x["k"], x["N"]) != (r["t"], r["v"], r["k"], r["N"]):
                raise UpError("table/EXTERNAL.csv lists this array with other parameters than the row")
            out["source"] = dict(location=x["location"])
            out["where"] = "deposit %s (table/EXTERNAL.csv)" % x["location"]
        else:
            raise UpError("the array is neither stored in table/arrays nor listed in table/EXTERNAL.csv, "
                          "so it cannot be retrieved here")
    else:
        lst = [c for c in ctx["certs"] if c.get("family_sha256") == sha]
        if not lst:
            raise UpError("the family is not listed in table/certificates/CERTIFICATES.csv")
        c = lst[0]
        if any("fused" in x["family"] or "+fuse" in (x.get("expansion") or "") for x in lst):
            raise UpError("the family is listed for a fused array; such rows are checked by the maintainer")
        path = os.path.join(ctx["table_dir"], "certificates", c["file"])
        if not os.path.isfile(path):
            raise UpError("table/certificates/%s is listed but missing" % c["file"])
        out["source"] = dict(family_file=c["file"])
        out["where"] = "table/certificates/%s" % c["file"]
        out["listing"] = c
    return out


# ---------------------------------------------------------------------------------------------
# the plan of an exact check

def array_plan(N, t, v, k, wild, a):
    """ca_verify in m shards on a.runner_threads threads each: the smallest m whose largest shard
    (its share of the t-sets, by ca_shard_merge.shard_sets) fits in a.shard_hours with the cost
    model of check_submission.py (which includes its safety factor 2, the doubling)."""
    terms = cs.verify_cost_terms(N, t, v, k, wild)
    read = cs.COST_SAFETY * (cs.COST_STARTUP + 1e-9 * terms["read"] * cs.COST_NS["read"])
    work = cs.COST_SAFETY * 1e-9 * sum(terms[n] * cs.COST_NS[n] for n in cs.COST_NS if n != "read")
    total = math.comb(k, t)
    cap = a.shard_hours * 3600.0
    for m in range(1, min(a.max_shards, k - t + 1) + 1):
        worst = max(sm.shard_sets(t, k, i, m) for i in range(m)) / float(total)
        wall = read + work * worst / a.runner_threads
        if wall <= cap:
            return dict(method="ca_verify", shards=m, exact=True, shard_hours=wall / 3600.0,
                        core_hours=(m * read + work) / 3600.0)
    return dict(method="ca_verify", shards=0, exact=False, shard_hours=None, core_hours=(read + work) / 3600.0)


def array_has_wildcards(e, ctx):
    """True when the stored array has a don't-care entry; for a deposit (not downloaded on a pull
    request or for the plan) the more expensive of the two estimates is used."""
    src = e["source"]
    if "file" not in src:
        return None
    path = os.path.join(ctx["table_dir"], "arrays", src["file"])
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            if b"NA" in b:
                return True
    return False


def plan_entry(e, ctx, exe, tmp, a, pool):
    if e["kind"] == "array":
        wild = array_has_wildcards(e, ctx)
        if wild is None:
            p0, p1 = array_plan(e["N"], e["t"], e["v"], e["k"], False, a), array_plan(e["N"], e["t"], e["v"], e["k"], True, a)
            p = p1 if (not p1["exact"] or (p0["exact"] and p1["core_hours"] >= p0["core_hours"])) else p0
        else:
            p = array_plan(e["N"], e["t"], e["v"], e["k"], wild, a)
        p = pool.take(p, False)
        return dict(p, estimate_text="ca_verify on %d threads: about %.3g core-hours with the safety factor"
                    % (a.runner_threads, p["core_hours"]))
    # a family: the claim as check_certificates.py reads it, from the SCREENED row and its listing
    r = e["row"]
    raw = dict(t=r["t"], v=r["v"], k=r["k"], N=r["N"], file=e["source"]["family_file"], mode="",
               source_detail=r["source_detail"], construction=r["construction"],
               builds_on=r["builds_on"] or "cphf-smc2006", credit=e["credit"], notes="")
    cctx = ck.load_context(ctx["table_dir"])
    c = ck.prepare(raw, os.path.join(ctx["table_dir"], "certificates"), exe, cctx, tmp)
    if not c.get("upgrade"):
        raise UpError("check_certificates does not see this family as SCREENED")
    if c["fam_sha"] != e["sha"]:
        raise UpError("the stored family file does not have the family_sha256 of the row")
    e["prepared"] = c
    est = ck.estimate(c, exe, a.threads)
    p = pool.take(cc.plan_claim(est, c["k"], c["t"], **ck.budget_args(a)), False)
    ests = ", ".join("%s %.3g core-seconds" % (x["method"], x["core_seconds"]) for x in est["methods"].values())
    return dict(p, estimate_text="cphfcheck estimates: %s" % ests, file_sha256=c["file_sha"],
                affine=c["affine"], n=c["n"])


def plan_text(e, p, a):
    if p["exact"]:
        return ("exact check with %s in %d shard%s on GitHub, about %.2g hours each (%.3g core-hours with "
                "the safety factor); a VERIFIED row is added if it passes" % (
                    p["method"], p["shards"], "" if p["shards"] == 1 else "s", p["shard_hours"], p["core_hours"]))
    return ("exact check with %s, about %.3g core-hours with the safety factor: over the budget of this request "
            "(%d shards of %g hours on %d threads per entry, %g core-hours and %d jobs for the whole request); "
            "the entry stays SCREENED" % (p["method"], p["core_hours"], a.max_shards, a.shard_hours,
                                         a.runner_threads, a.max_shards * a.shard_hours * a.runner_threads,
                                         ck.MAX_TASKS))


def describe(e):
    r = e["row"]
    return ["%s %s: the SCREENED row CA(%s; %s, %s, %s) entered %s, credit %s, construction %s" % (
                e["kind"], e["sha"], r["N"], r["t"], r["k"], r["v"], r["entered"], e["credit"],
                r["construction"][:200]),
            "retrieved from %s" % e["where"],
            "requested by %s" % e["asked_by"]]


# ---------------------------------------------------------------------------------------------
# the forms of the command

def report(slug, title, items, ok, extra=()):
    L = ["## Upgrade request: `%s`" % slug, "", title, "", "**Result: %s.**" % ("PASS" if ok else "FAIL"), ""]
    for i, c in enumerate(items, 1):
        L.append("**%d. %s %s** (%s)" % (i, cs.md_cell(c.get("kind", "")), cs.md_cell((c.get("sha") or "")[:16]),
                                         c.get("verdict", "PASS" if c.get("passed") else "FAIL")))
        L.append("")
        for line in c.get("lines", []):
            L.append("- " + cs.md_cell(line))
        for r in c.get("reasons", []):
            L.append("- **%s**" % cs.md_cell(r))
        L.append("")
    L += list(extra)
    return "\n".join(L) + "\n"


def write_out(out, text, summary):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, default=str)
        f.write("\n")
    print(text)


def entries_or_fail(sub, slug, a):
    try:
        return read_request(sub), None
    except UpError as err:
        return None, str(err)


def form_light(sub, slug, a):
    entries, failed = entries_or_fail(sub, slug, a)
    out = a.out or "check-%s" % slug
    items, ok = [], failed is None
    if failed:
        items.append(dict(kind="(request)", passed=False, reasons=[failed]))
    else:
        ctx = load_ctx(a.table_dir)
        pool, seen = ck.Pool(a), set()
        with tempfile.TemporaryDirectory(prefix="caup-") as tmp:
            exe = None
            for raw in entries:
                c = dict(kind=raw.get("kind", ""), sha=raw.get("sha256", ""), lines=[], reasons=[])
                try:
                    e = resolve(raw, ctx, seen)
                    c["lines"] += describe(e)
                    if e["kind"] == "array" and "file" in e["source"]:
                        got = stored_sha(os.path.join(a.table_dir, "arrays", e["source"]["file"]))
                        if got != e["sha"]:
                            raise UpError("table/arrays/%s does not hash to %s" % (e["source"]["file"], e["sha"]))
                        c["lines"].append("the stored file hashes to the row's array_sha256")
                    if e["kind"] == "family" and exe is None:
                        exe = ck.build(tmp)
                    p = plan_entry(e, ctx, exe, tmp, a, pool)
                    c["lines"].append(p["estimate_text"])
                    c["lines"].append("on merge: " + plan_text(e, p, a))
                    c["passed"] = True
                except (UpError, CertError, ValueError, OSError) as err:
                    ok = False
                    c["passed"] = False
                    c["reasons"].append(str(err))
                items.append(c)
    title = ("The exact check is not run on the pull request (a run on a pull request uses the pull request's "
             "own copy of the tools, so it is only a report). After the merge the certificate workflow on main "
             "runs it in shards with the tools of main, and the table workflow enters a VERIFIED row beside each "
             "SCREENED row that passes (tools/check_upgrades.py, submissions/README.md).")
    text = report(slug, title, items, ok)
    write_out(out, text, dict(slug=slug, passed=ok, upgrade=True,
                              entries=[dict(kind=c.get("kind"), sha256=c.get("sha"), passed=c.get("passed"),
                                            reasons=c.get("reasons")) for c in items]))
    return 0 if ok else 1


def stored_sha(path):
    h = hashlib.sha256()
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tasks_of(plan):
    out = []
    for p in plan:
        if p["exact"]:
            out += ["u%d-s%d" % (p["index"], j) for j in range(p["shards"])]
    return out


def form_plan(sub, slug, a):
    entries, failed = entries_or_fail(sub, slug, a)
    plan = []
    if not failed:
        ctx = load_ctx(a.table_dir)
        pool, seen = ck.Pool(a), set()
        try:
            with tempfile.TemporaryDirectory(prefix="caup-") as tmp:
                exe = None
                for i, raw in enumerate(entries):
                    e = resolve(raw, ctx, seen)
                    if e["kind"] == "family" and exe is None:
                        exe = ck.build(tmp)
                    p = plan_entry(e, ctx, exe, tmp, a, pool)
                    plan.append(dict(index=i, kind=e["kind"], sha256=e["sha"], t=e["t"], v=e["v"], k=e["k"],
                                     N=e["N"], source=e["source"], method=p["method"], shards=p["shards"],
                                     exact=p["exact"], core_hours=p["core_hours"], shard_hours=p["shard_hours"],
                                     file_sha256=p.get("file_sha256"), affine=p.get("affine"),
                                     text=plan_text(e, p, a)))
        except (UpError, CertError, ValueError, OSError) as err:
            plan, failed = [], str(err)
    doc = dict(slug=slug, kind="upgrade", failed=failed,
               budget=dict(runner_threads=a.runner_threads, max_shards=a.max_shards, shard_hours=a.shard_hours,
                           safety=a.safety),
               entries=plan, tasks=tasks_of(plan))
    with open(a.plan, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    for p in plan:
        print("%s %s: %s" % (p["kind"], p["sha256"][:12], p["text"]))
    if failed:
        print("plan failed: %s" % failed)
    print("tasks: %s" % (" ".join(doc["tasks"]) or "none"))
    return 0


def load_plan(path, slug):
    doc = json.load(open(path, encoding="utf-8"))
    if doc.get("slug") != slug or doc.get("kind") != "upgrade":
        raise SystemExit("the plan is not the upgrade plan of %s" % slug)
    return doc


def canonical_array(p, table_dir, tmp, local_root=None):
    """The canonical text of an entry's array as a file, and its sha256 computed here."""
    src = p["source"]
    if "file" in src:
        path = os.path.join(table_dir, "arrays", src["file"])
        if not path.endswith(".gz"):
            return path, stored_sha(path)
        out = os.path.join(tmp, "canon.txt")
        h = hashlib.sha256()
        with gzip.open(path, "rb") as f, open(out, "wb") as g:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
                g.write(b)
        return out, h.hexdigest()
    raw = ea.download(src["location"], tmp, local_root)
    out = os.path.join(tmp, "canon.txt")
    n, k, sha, _ = ea.canonicalize_stream(raw, p["v"], out)
    os.remove(raw)
    if (n, k) != (p["N"], p["k"]):
        raise UpError("the deposit holds a %d x %d array, the row says %d x %d" % (n, k, p["N"], p["k"]))
    return out, sha


def run_task(sub, slug, doc, task, outdir, threads, table_dir, tmp, local_root=None):
    m = re.fullmatch(r"u(\d+)-s(\d+)", task or "")
    if not m or task not in doc["tasks"]:
        raise SystemExit("task %r is not in the plan" % task)
    p = doc["entries"][int(m.group(1))]
    j = int(m.group(2))
    os.makedirs(outdir, exist_ok=True)
    meta = ["# task: %s" % task, "# kind: %s" % p["kind"], "# t: %d" % p["t"]]
    if p["kind"] == "array":
        exe = build_ca_verify(tmp)
        meta += ["# tool: %s" % ca_verify_tool(), "# q: %d" % p["v"]]
        try:
            path, sha = canonical_array(p, table_dir, tmp, local_root)
            meta.append("# array_sha256: %s" % sha)
            if sha != p["sha256"]:
                raise UpError("the array retrieved has sha256 %s, the row says %s" % (sha, p["sha256"]))
            args = [exe, path, str(p["t"]), str(p["v"]), str(threads)] + (
                ["%d/%d" % (j, p["shards"])] if p["shards"] > 1 else [])
            meta.append("# command: ca_verify FILE %s" % " ".join(args[2:]))
            r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            code, body = r.returncode, r.stdout
            body += "".join("# stderr: %s\n" % l for l in r.stderr.strip().splitlines()[:20])
        except (UpError, ea.ExtError, OSError, ValueError, UnicodeDecodeError) as err:
            code, body = 2, "# error: %s\n" % err
    else:
        exe = ck.build(tmp)
        fam = os.path.join(table_dir, "certificates", p["source"]["family_file"])
        if ck.file_sha(fam) != p["file_sha256"]:
            raise SystemExit("the family file changed since the plan was made")
        meta += ["# family_sha256: %s" % p["sha256"], "# tool: %s" % ck.tool_hash(), "# method: %s" % p["method"],
                 "# q: %d" % p["v"]]
        args = [fam, p["t"], p["v"]] + ck.mode_args(p["method"], threads) + ["shard", j, p["shards"]]
        meta.append("# command: cphfcheck %s" % " ".join(str(x) for x in args[1:]))
        code, out, err = ck.run(exe, args)
        body = out + ("" if out.endswith("\n") or not out else "\n")
        body += "".join("# stderr: %s\n" % l for l in err.strip().splitlines()[:20])
    path = os.path.join(outdir, "%s.txt" % task)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(meta) + "\n" + body + "# exit: %d\n" % code)
    print("%s: exit %d, written to %s" % (task, code, path))
    return code


def form_run(sub, slug, a):
    doc = load_plan(a.run, slug)
    with tempfile.TemporaryDirectory(prefix="caup-") as tmp:
        code = run_task(sub, slug, doc, a.task, a.out, a.threads, a.table_dir, tmp, a.local_root)
    return 0 if code in (0, 1) else code


def read_tasks(folder, index):
    out = []
    if folder and os.path.isdir(folder):
        for root, _, files in os.walk(folder):
            for fn in sorted(files):
                if re.fullmatch(r"u%d-s\d+\.txt" % index, fn):
                    out.append((fn, open(os.path.join(root, fn), encoding="utf-8").read()))
    return out


def meta_of(text):
    return dict(re.findall(r"^# ([a-z0-9_]+): (.*)$", text, re.M))


def decide(p, texts):
    """Decide one planned entry from its shard outputs. Returns (outcome, how) with outcome
    "verified", "over_budget", "incomplete" (the entry stays SCREENED) or "failed" (shown not to
    be a covering array, or a family shown not to be a CPHF)."""
    if not p["exact"]:
        return "over_budget", "over the budget of this request; the entry stays SCREENED"
    if not texts:
        return "incomplete", "no shard output (the jobs did not finish); the entry stays SCREENED"
    metas = [meta_of(x) for x in texts]
    if p["kind"] == "array":
        for x in metas:
            if x.get("array_sha256") != p["sha256"]:
                return "incomplete", ("a shard did not check the array of the row (%s); the entry stays SCREENED"
                                      % (x.get("error") or x.get("array_sha256", "no hash")))
        if len({x.get("tool") for x in metas}) != 1:
            return "incomplete", "the shards ran different versions of ca_verify; the entry stays SCREENED"
        try:
            r = sm.merge(texts, p["t"], p["k"], p["N"], p["v"])
        except sm.MergeError as err:
            return "incomplete", "the shards do not prove a verdict (%s); the entry stays SCREENED" % err
        if r["shards"] != p["shards"]:
            return "incomplete", "%d shards ran, the plan has %d; the entry stays SCREENED" % (r["shards"], p["shards"])
        if not r["verified"]:
            return "failed", ("NOT A COVERING ARRAY at strength %d: %d of %d column sets have gaps; first %s"
                              % (p["t"], r["gaps"], r["combos"], (r["examples"] or ["(none listed)"])[0]))
        return "verified", ("ca_verify %s, every one of the %d column sets checked, in %d shard%s merged by "
                            "tools/ca_shard_merge.py" % (metas[0]["tool"], r["combos"], r["shards"],
                                                         "" if r["shards"] == 1 else "s"))
    try:
        res = cc.combine(texts, p["method"], p["k"], p["t"])
        if any(x.get("family_sha256") != p["sha256"] for x in metas):
            raise CertError("a shard ran on another family")
    except CertError as err:
        return "incomplete", "the shards do not prove a verdict (%s); the entry stays SCREENED" % err
    if res["uncovered"]:
        return "failed", "not a CPHF: %d uncovered t-sets, the smallest (%s)" % (
            res["uncovered"], ",".join(map(str, res["first"])))
    return "verified", ("cphfcheck %s, method %s in %d shard%s: %d units checked, uncovered 0" % (
        metas[0]["tool"], p["method"], res["m"], "" if res["m"] == 1 else "s", res["units"]))


def form_results(sub, slug, a):
    doc = load_plan(a.results, slug)
    outdir = a.out or "result-%s" % slug
    os.makedirs(os.path.join(outdir, "tasks"), exist_ok=True)
    items, ok, res = [], doc["failed"] is None, []
    if doc["failed"]:
        items.append(dict(kind="(request)", passed=False, reasons=[doc["failed"]]))
    for p in doc["entries"]:
        texts = read_tasks(a.tasks, p["index"])
        for fn, txt in texts:
            with open(os.path.join(outdir, "tasks", fn), "w", encoding="utf-8") as f:
                f.write(txt)
        outcome, how = decide(p, [x for _, x in texts])
        if outcome == "failed":
            ok = False
        items.append(dict(kind=p["kind"], sha=p["sha256"], passed=outcome != "failed",
                          verdict={"verified": "VERIFIED", "failed": "FAIL"}.get(outcome, "stays SCREENED"),
                          lines=["plan: " + p["text"], "%s: %s" % (outcome, how)]))
        res.append(dict(index=p["index"], kind=p["kind"], sha256=p["sha256"], outcome=outcome, how=how))
    commit = cs.git_short_sha()
    text = report(slug, "Checked on main by the certificate workflow at %s." % commit, items, ok)
    result = dict(slug=slug, kind="upgrade", passed=ok, date=a.date or today(), machine=cs.machine_tag(),
                  commit=commit, plan=doc, entries=res)
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    with open(os.path.join(outdir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0 if ok else 1


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------------------------
# entering the rows

def comparison_text(ctx, e):
    prev, prow = cs.best_known(ctx["rows"], e["t"], e["v"], e["k"])
    if prev is None:
        return "exceeds_table", "exceeds table: no previous entry for these parameters"
    src = "%s %s" % (prow["tier"], prow["source_id"])
    if prow.get("snapshot_id"):
        src += " " + prow["snapshot_id"]
    pt = "previous best %d (row k=%s, %s)" % (prev, prow["k"], src)
    if e["N"] < prev:
        return "exceeds_table", "exceeds table: " + pt
    if e["N"] == prev:
        return "equals_best", "equals table: " + pt
    return "above_table", "above table best, not an improvement: " + pt


def stamp_of(e, commit, date, machine, how, shards):
    if e["kind"] == "array":
        return "ca_verify %s %s %s%s" % (commit, date, machine, " (exact, %d shards)" % shards if shards > 1 else "")
    tool = re.match(r"cphfcheck ([0-9a-f]+)", how).group(1)
    hashed = bool(e["row"]["array_sha256"])
    return "cphfcheck %s %s %s (CPHF certificate, exact%s)" % (tool, date, machine, "" if hashed else "; array not hashed")


def enter(entries, ctx, slug, date):
    """Append the VERIFIED rows (and the listing of a family, the MANIFEST or EXTERNAL status of an
    array) for the entries that passed. entries: resolved entries with stamp, how."""
    table_dir = ctx["table_dir"]
    trows, crows = [], []
    man_update, ext_update = {}, {}
    for e in entries:
        r = e["row"]
        status, cmp_txt = comparison_text(ctx, e)
        notes = ["credit: " + e["credit"], MARK % (r["entered"], slug, e["asked_by"]),
                 "checked exactly: " + e["how"], cmp_txt]
        if e["notes"]:
            notes.append(e["notes"])
        trows.append([r["t"], r["v"], r["k"], r["N"], "VERIFIED", r["source_id"], r["source_detail"],
                      r["snapshot_id"], r["array_sha256"], e["stamp"], date, "; ".join(notes), "", "",
                      r["construction"], r["builds_on"], r.get("family_sha256") or ""])
        if e["kind"] == "family":
            c = e["listing"]
            crows.append([c["file"], r["t"], r["v"], r["k"], r["N"], c["family"], c["sha256"], c["array_sha256"],
                          "%s: %s" % (e["stamp"].split(" (")[0], e["how"]), c["family_sha256"], c["expansion"]])
        elif "file" in e["source"]:
            man_update[e["sha"]] = ({"exceeds_table": "exceeds_snapshot", "equals_best": "equals_best",
                                     "above_table": "above_best"}[status], e["stamp"])
        else:
            ext_update[e["sha"]] = e["stamp"]
    tpath = os.path.join(table_dir, "ca_table.csv")
    eol = "\r\n" if b"\r\n" in open(tpath, "rb").read(4096) else "\n"
    cs.append_text(tpath, cs.table_csv_text(trows), eol)
    if crows:
        cs.append_text(os.path.join(table_dir, "certificates", "CERTIFICATES.csv"), cs.manifest_csv_text(crows), "\n")
    if man_update:
        rewrite_manifest(os.path.join(table_dir, "MANIFEST.csv"), man_update)
    if ext_update:
        rewrite_external(os.path.join(table_dir, "EXTERNAL.csv"), ext_update)
    return len(trows)


def rewrite_manifest(path, upd):
    """status and verify_stamp of the MANIFEST rows of upgraded arrays (screened -> the comparison
    at upgrade), the rest of the file byte for byte"""
    lines = open(path, encoding="utf-8", newline="").read().split("\n")
    out = []
    for line in lines:
        if line and not line.startswith('"file"'):
            rec = next(csv.reader([line]))
            if len(rec) == len(cs.MANIFEST_HEADER) and rec[6] in upd and rec[5] == "screened":
                st, stamp = upd[rec[6]]
                rec[5], rec[9] = st, stamp
                cells = [rec[0], int(rec[1]), int(rec[2]), int(rec[3]), int(rec[4])] + rec[5:10] + [
                    int(rec[10]) if rec[10].isdigit() else ""]
                line = cs.manifest_csv_text([cells]).rstrip("\n")
        out.append(line)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(out))


def rewrite_external(path, upd):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    for rec in rows[1:]:
        if rec and rec[0] in upd and rec[7] == "screened":
            rec[7], rec[9] = "verified", upd[rec[0]]
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


def form_apply_result(sub, slug, a):
    rdir = a.apply_result
    res = json.load(open(os.path.join(rdir, "result.json"), encoding="utf-8"))
    if res.get("slug") != slug or res.get("kind") != "upgrade":
        raise SystemExit("the result is not the upgrade result of %s" % slug)
    entries, failed = entries_or_fail(sub, slug, a)
    items, ok, todo = [], bool(res.get("passed")) and failed is None, []
    if failed:
        items.append(dict(kind="(request)", passed=False, reasons=[failed]))
    if not res.get("passed"):
        items.append(dict(kind="(result)", passed=False,
                          reasons=["the certificate workflow did not pass this request; see its report"]))
    ctx = load_ctx(a.table_dir)
    plan = {p["index"]: p for p in res["plan"]["entries"]}
    done = {x["index"]: x for x in res.get("entries", [])}
    seen = set()
    for i, raw in enumerate(entries or []):
        if not ok:
            break
        c = dict(kind=raw.get("kind", ""), sha=raw.get("sha256", ""), lines=[], reasons=[])
        try:
            e = resolve(raw, ctx, seen)
            p, x = plan.get(i), done.get(i)
            if p is None or x is None or p["sha256"] != e["sha"] or p["kind"] != e["kind"]:
                raise UpError("the result does not match upgrade.csv as it is now")
            c["lines"] += describe(e)
            # decide again from the shard outputs kept with the result, with the tools of this commit
            outcome, how = decide(p, [t for _, t in read_tasks(os.path.join(rdir, "tasks"), i)])
            if outcome != x["outcome"]:
                raise UpError("the shard outputs say %s, the result says %s" % (outcome, x["outcome"]))
            if outcome == "failed":
                raise UpError(how)
            c["lines"].append("%s: %s" % (outcome, how))
            if outcome == "verified":
                e["how"] = how
                e["stamp"] = stamp_of(e, res["commit"], res["date"], res["machine"], how, p["shards"])
                todo.append(e)
                c["verdict"] = "VERIFIED"
            else:
                c["verdict"] = "stays SCREENED"
            c["passed"] = True
        except (UpError, CertError, ValueError, OSError) as err:
            ok = False
            c["passed"] = False
            c["reasons"].append(str(err))
        items.append(c)
    text = report(slug, "Checked again on main against the table at this moment.", items, ok)
    n = 0
    if ok and todo and a.apply:
        n = enter(todo, ctx, slug, a.date or today())
        text += "\nApplied: %d VERIFIED rows appended to `table/ca_table.csv`.\n" % n
    elif ok and not todo:
        text += "\nNothing to enter: every entry stays SCREENED (see above).\n"
    elif a.apply and not ok:
        text += "\nNot applied: the request did not pass.\n"
    write_out(a.out or "apply-%s" % slug, text, dict(slug=slug, passed=ok, applied=n))
    if not ok:
        return 1
    return 0 if todo else 3


def form_local(sub, slug, a):
    """the exact check on this machine, unsharded, then (with --apply) the rows"""
    entries, failed = entries_or_fail(sub, slug, a)
    if failed:
        print("FAIL: %s" % failed)
        return 1
    ctx = load_ctx(a.table_dir)
    ok, todo, seen = True, [], set()
    with tempfile.TemporaryDirectory(prefix="caup-") as tmp:
        for i, raw in enumerate(entries):
            try:
                e = resolve(raw, ctx, seen)
                p = dict(index=i, kind=e["kind"], sha256=e["sha"], t=e["t"], v=e["v"], k=e["k"], N=e["N"],
                         source=e["source"], shards=1, exact=True)
                if e["kind"] == "family":
                    exe = ck.build(tmp)
                    pe = plan_entry(e, ctx, exe, tmp, a, ck.Pool(a))
                    p.update(method=pe["method"], file_sha256=pe["file_sha256"])
                else:
                    p["method"] = "ca_verify"
                doc = dict(tasks=["u%d-s0" % i], entries=[None] * i + [p])
                td = os.path.join(tmp, "tasks")
                run_task(sub, slug, doc, "u%d-s0" % i, td, a.threads, a.table_dir, tmp, a.local_root)
                outcome, how = decide(p, [t for _, t in read_tasks(td, i)])
                shutil.rmtree(td)
                print("%s %s: %s: %s" % (e["kind"], e["sha"][:12], outcome, how))
                if outcome == "failed":
                    ok = False
                elif outcome == "verified":
                    e["how"] = how
                    e["stamp"] = stamp_of(e, cs.git_short_sha(), a.date or today(), cs.machine_tag(), how, 1)
                    todo.append(e)
            except (UpError, CertError, ValueError, OSError) as err:
                ok = False
                print("FAIL %s: %s" % (raw.get("sha256", "")[:12], err))
    if not ok:
        print("Not every entry passed; nothing applied.")
        return 1
    if not todo:
        return 3
    if a.apply:
        print("Applied %d VERIFIED rows." % enter(todo, ctx, slug, a.date or today()))
    else:
        print("Every entry passed. Run again with --apply to enter them.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("submission")
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--plan", metavar="PLAN_JSON")
    ap.add_argument("--run", metavar="PLAN_JSON")
    ap.add_argument("--task", default=None)
    ap.add_argument("--results", metavar="PLAN_JSON")
    ap.add_argument("--tasks", default=None)
    ap.add_argument("--apply-result", metavar="DIR")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--runner-threads", type=int, default=cc.RUNNER_THREADS)
    ap.add_argument("--max-shards", type=int, default=cc.MAX_SHARDS)
    ap.add_argument("--shard-hours", type=float, default=cc.SHARD_HOURS)
    ap.add_argument("--safety", type=float, default=cc.SAFETY)
    ap.add_argument("--date", default=None)
    ap.add_argument("--local-root", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    sub = a.submission.rstrip("/")
    slug = os.path.basename(sub)
    if not cs.SAFE_NAME.match(slug):
        raise SystemExit("bad submission directory name %r" % slug)
    if a.light:
        return form_light(sub, slug, a)
    if a.plan:
        return form_plan(sub, slug, a)
    if a.run:
        return form_run(sub, slug, a)
    if a.results:
        return form_results(sub, slug, a)
    if a.apply_result:
        return form_apply_result(sub, slug, a)
    return form_local(sub, slug, a)


if __name__ == "__main__":
    sys.exit(main())
