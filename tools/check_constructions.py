#!/usr/bin/env python3
"""check_constructions - construction certificates as a submission route.

A submission is a directory submissions/<slug>/ holding constructions.csv

    t,v,k,N,file,source_detail,construction,builds_on,credit,notes

(the fields of claims.csv; file names a certificate, a JSON file of the format construction-cert-1
in the same directory, tools/CONSTRUCTION_CERT.md) and the certificates and ingredient files it
names. For every claim this script runs tools/construction_cert.py, which checks every hypothesis
of the construction's theorem exactly and rebuilds the array in the table's canonical text, and
then checks the claim against the table: t, v, k, N as the certificate gives them, the array's
canonical sha256 not yet in the table, builds_on, and the comparison with the best known size. A
rebuilt array that ca_verify can check in a short time is checked by it as well (a cross-check of
the certificate checker; a disagreement fails the claim).

Identity and storage: a row is identified by the array_sha256 of the rebuilt array, as every array
row. The certificate is always stored, in table/constructions/<slug>/ with its ingredient files,
and listed in table/constructions/CONSTRUCTIONS.csv; it is the recipe that rebuilds the array. The
rebuilt array is also stored in table/arrays (the rules of submitted arrays: gzip above 1 MiB of
text) when its text is at most 50 MiB; above that only the certificate is kept, and the row's
notes say so. family_sha256 stays empty.

Usage:
  check_constructions.py SUB --light [--out DIR]    the pull request check (a report)
  check_constructions.py SUB [--apply] [--pr N]     the check on main; --apply enters the rows
Exit status: 0 every claim passed, 1 otherwise, 2 usage error. Standard library only.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_submission as cs  # noqa: E402
import builds_on as bo  # noqa: E402
import construction_cert as ccert  # noqa: E402

HEADER = ["t", "v", "k", "N", "file", "source_detail", "construction", "builds_on", "credit", "notes"]
LIST_HEADER = ["file", "t", "v", "k", "N", "construction", "sha256", "array_sha256", "check", "stored"]
MAX_ENTRIES = 10 ** 9            # N * k rebuilt here in Python (about a minute per 10^8 entries)
MAX_CERT_BYTES = 1024 * 1024     # one certificate file
CROSS_CHECK_SECONDS = 120        # ca_verify also checks the rebuilt array when predicted below this
STORE_MAX_BYTES = cs.MAX_FILE_BYTES   # a rebuilt array up to this size as text is stored in table/arrays


class ConError(Exception):
    pass


def tool_hash():
    return hashlib.sha256(open(os.path.join(HERE, "construction_cert.py"), "rb").read()).hexdigest()[:12]


def read_claims(sub):
    path = os.path.join(sub, "constructions.csv")
    if os.path.islink(path) or not os.path.isfile(path):
        raise ConError("constructions.csv is missing or not a regular file")
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        hdr = [h.strip() for h in next(rd, [])]
        if hdr != HEADER:
            raise ConError("constructions.csv header must be exactly %s (found %s)" % (",".join(HEADER), ",".join(hdr)))
        out = []
        for n, rec in enumerate(rd, 2):
            if not any(x.strip() for x in rec):
                continue
            if len(rec) != len(HEADER):
                raise ConError("constructions.csv line %d has %d fields, expected %d" % (n, len(rec), len(HEADER)))
            out.append(dict(raw=dict(zip(HEADER, rec)), line=n))
    if not out:
        raise ConError("constructions.csv has no claims")
    return out


def int_of(raw, name, lo):
    x = (raw.get(name) or "").strip()
    if not re.fullmatch(r"[0-9]+", x) or int(x) < lo:
        raise ConError("constructions.csv field %s=%r is not a whole number of at least %d" % (name, x, lo))
    return int(x)


def check_claim(cl, ctx, tmp):
    raw = cl["raw"]
    cl.update(passed=False, reasons=[], notes_out=[], lines=[])
    try:
        for fld in ("file", "source_detail", "construction", "credit"):
            if not (raw.get(fld) or "").strip():
                raise ConError("constructions.csv field %s is empty" % fld)
        for fld in HEADER:
            if any(ch in (raw.get(fld) or "") for ch in "\r\n"):
                raise ConError("constructions.csv field %s contains a line break" % fld)
        t, v, k, N = (int_of(raw, x, 1) for x in ("t", "v", "k", "N"))
        cl.update(t=t, v=v, k=k, N=N)
        fname = raw["file"].strip()
        if not cs.SAFE_NAME.match(fname) or not fname.endswith(".json"):
            raise ConError("file %r is not a plain .json file name in the submission directory" % fname)
        path = os.path.join(ctx["sub"], fname)
        if os.path.islink(path) or not os.path.isfile(path):
            raise ConError("certificate %s is missing (or is not a regular file)" % fname)
        if os.path.getsize(path) > MAX_CERT_BYTES:
            raise ConError("certificate %s is above %d bytes" % (fname, MAX_CERT_BYTES))
        if fname in ctx["seen_file"]:
            raise ConError("certificate %s is named twice" % fname)
        ctx["seen_file"].add(fname)
        if N * k > MAX_ENTRIES:
            raise ConError("N k = %d entries is above the %d this route rebuilds; ask the maintainer" % (N * k, MAX_ENTRIES))
        text_bytes = N * k * (len(str(v - 1)) + 1)
        out_path = os.path.join(tmp, "rebuilt-%d.txt" % cl["line"]) if text_bytes <= STORE_MAX_BYTES else None
        t0 = time.monotonic()
        try:
            res = ccert.run(path, out_path, table_dir=ctx["table_dir"])
        except ccert.CertError as e:
            raise ConError("the certificate is malformed: %s" % e)
        cl["seconds"] = time.monotonic() - t0
        kind = res["construction"]
        cl["kind"], cl["res"] = kind, res
        if not res["ok"]:
            raise ConError("the certificate is rejected by tools/construction_cert.py: %s" % "; ".join(
                "[%s] %s" % f for f in res["failures"][:6]))
        if (res["t"], res["v"], res["k"], res["N"]) != (t, v, k, N):
            raise ConError("the certificate gives CA(%s; %s, %s, %s), the claim says CA(%d; %d, %d, %d)"
                           % (res["N"], res["t"], res["k"], res["v"], N, t, k, v))
        sha = res["sha256"]
        cl["sha256"] = sha
        cl["lines"].append("certificate valid (%s, %s): every hypothesis checked, the array rebuilt in %.2f s"
                           % (kind, ", ".join(res["passed"]), cl["seconds"]))
        cl["lines"].append("array sha256 (canonical form): `%s`" % sha)
        for ing in res["ingredients"]:
            cl["lines"].append("ingredient %s: %s" % (ing["name"], ingredient_text(ing)))
        # builds_on: as given, checked, with the reference of the construction's theorem
        given = raw.get("builds_on") or ""
        ref = ccert.REFERENCE[kind]
        if not given.strip():
            raise ConError("builds_on is empty; it lists the ids of table/references.csv the array rests on%s"
                           % (" (%s at least)" % ref if ref else ""))
        if ref and ref not in given.split(";"):
            given = ccert.REFERENCE[kind] + ";" + given
            cl["notes_out"].append("builds_on: %s added (the theorem of %s)" % (ccert.REFERENCE[kind], kind))
        norm, errs, warns, links = bo.check(given, raw["construction"], ctx["refs"])
        if errs:
            raise ConError("builds_on: " + "; ".join(errs))
        cl["builds_on"] = norm
        cl["notes_out"] += ["builds_on: " + w for w in warns]
        if links:
            cl["notes_out"].append("builds_on names a new method (%s); the maintainer confirms it before the merge"
                                   % ", ".join(links))
        # identity and duplicates
        if sha in ctx["manifest_sha"]:
            raise ConError("duplicate: this array is already in the table as table/arrays/%s" % ctx["manifest_sha"][sha])
        if sha in ctx["table_sha"]:
            raise ConError("duplicate: this array is already recorded in ca_table.csv")
        if sha in ctx["seen_sha"]:
            raise ConError("duplicate: the same array as %s in this submission" % ctx["seen_sha"][sha])
        ctx["seen_sha"][sha] = fname
        prev, prow = cs.best_known(ctx["rows"], t, v, k)
        cl["previous_best"], cl["previous_row"] = prev, prow
        cl["comparison"] = ("exceeds_table" if prev is None or N < prev else "equals_best" if N == prev else "above_table")
        cl["lines"].append("table: %s; %s" % (cl["comparison"], cs.previous_text(cl)))
        # storage
        cl["stored"] = out_path is not None and os.path.getsize(out_path) <= STORE_MAX_BYTES
        cl["array_path"] = out_path if cl["stored"] else None
        if cl["stored"]:
            cl["lines"].append("on entry the array is stored in table/arrays (%d bytes as text%s)"
                               % (os.path.getsize(out_path), ", gzip" if os.path.getsize(out_path) > cs.GZIP_ABOVE else ""))
        else:
            cl["lines"].append("the array has %d entries, above 50 MiB as text: only the certificate is stored, and it "
                               "rebuilds the array" % (N * k))
        # cross-check: ca_verify on the rebuilt array when it is quick
        pred = cs.predict_verify_seconds(N, t, v, k, ctx["threads"])
        if cl["stored"] and ctx["ca_verify"] and pred <= CROSS_CHECK_SECONDS and k >= t:
            r = cs.run_ca_verify(ctx["ca_verify"], out_path, t, v, ctx["threads"], 4 * CROSS_CHECK_SECONDS)
            if r["outcome"] != "verified":
                raise ConError("the certificate checker and ca_verify disagree (ca_verify: %s); this is a bug, "
                               "report it" % (r["summary"] or r["outcome"]))
            cl["cross_check"] = True
            cl["lines"].append("cross-check: ca_verify verifies the rebuilt array too (%s)" % cs.fmt_secs(r["seconds"]))
        else:
            cl["cross_check"] = False
            cl["lines"].append("cross-check by ca_verify not run (predicted %s, or no ca_verify)" % cs.fmt_secs(pred))
        if cl["stored"]:
            cl["constant_rows"] = cs.run_constant_rows(ctx["constant_rows"], out_path, v, ctx["cr_budget"])
        else:
            cl["constant_rows"] = None
        cl["passed"] = True
    except (ConError, OSError, ValueError) as e:
        cl["reasons"].append(str(e))
    return cl


def ingredient_text(ing):
    if ing["source"] == "table":
        return "the VERIFIED table row of array_sha256 %s (table/arrays/%s), trusted as verified" % (ing["sha256"], ing["file"])
    if ing["source"] == "file":
        return "file %s (sha256 %s), checked here" % (ing["file"], ing["sha256"][:16])
    return "inline, checked here"


def notes_of(cl, ctx, stored_name):
    raw = cl["raw"]
    cmp_txt = {"exceeds_table": "exceeds table: ", "equals_best": "equals table: ",
               "above_table": "above table best, not an improvement: "}[cl["comparison"]] + cs.previous_text(cl)
    ings = "; ".join("%s %s" % (i["name"], "table row %s" % i["sha256"][:16] if i["source"] == "table" else
                                 "file %s" % i["file"] if i["source"] == "file" else "inline")
                     for i in cl["res"]["ingredients"])
    parts = ["credit: " + raw["credit"].strip(), cmp_txt,
             "construction certificate table/constructions/%s/%s (%s), ingredients: %s" % (
                 ctx["slug"], raw["file"].strip(), cl["kind"], ings)]
    if stored_name:
        parts.append("array stored as table/arrays/%s" % stored_name)
    else:
        parts.append("array of %d entries not stored (above 50 MiB as text), rebuilt from the certificate"
                     % (cl["N"] * cl["k"]))
    if cl.get("cross_check"):
        parts.append("also verified by ca_verify")
    parts.append("from submissions/%s/constructions.csv" % ctx["slug"])
    if (raw.get("notes") or "").strip():
        parts.append(raw["notes"].strip())
    return "; ".join(parts)


def report(ctx, claims, ok, problems):
    L = ["## Construction certificates: `%s`" % ctx["slug"], ""]
    L.append("**Result: %s.** %d of %d claims passed." % ("PASS" if ok else "FAIL",
                                                          sum(1 for c in claims if c.get("passed")), len(claims)))
    L.append("")
    L.append("Checked with `tools/construction_cert.py` (tool %s), which checks every hypothesis of the "
             "construction exactly and rebuilds the array (tools/CONSTRUCTION_CERT.md). A pull request run is a "
             "report; the rows are entered on main, where the check runs again with the tools of main." % ctx["tool"])
    L.append("")
    for p in problems:
        L.append("- **%s**" % cs.md_cell(p))
    for i, c in enumerate(claims, 1):
        L.append("**%d. %s** (%s)" % (i, cs.md_cell(c["raw"].get("file", "")), "PASS" if c.get("passed") else "FAIL"))
        L.append("")
        if (c["raw"].get("construction") or "").strip():
            L.append("- construction: %s" % cs.md_cell(c["raw"]["construction"].strip()))
        if c.get("builds_on"):
            L.append("- builds on: %s" % cs.md_cell(c["builds_on"]))
        for line in c.get("lines", []):
            L.append("- " + cs.md_cell(line))
        for r in c.get("reasons", []):
            L.append("- **%s**" % cs.md_cell(r))
        for n in c.get("notes_out", []):
            L.append("- note: %s" % cs.md_cell(n))
        if c.get("canonical_name"):
            L.append("- recorded as `table/arrays/%s`" % c["canonical_name"])
        L.append("")
    return "\n".join(L) + "\n"


def apply(claims, ctx):
    td = ctx["table_dir"]
    cdir = os.path.join(td, "constructions", ctx["slug"])
    if os.path.exists(cdir):
        raise ConError("table/constructions/%s exists already" % ctx["slug"])
    taken = dict(ctx["taken"])
    trows, mrows, lrows, files = [], [], [], []
    for cl in claims:
        name = None
        if cl["stored"]:
            canon = open(cl["array_path"], encoding="ascii").read()
            cl["canon_text"] = canon
            name = cs.canonical_name(cl, taken)
            taken[name] = cl["sha256"]
            cl["canonical_name"] = name
            files.append((name, canon))
        stamp = "construction_cert %s %s %s (%s, exact)" % (ctx["tool"], ctx["date"], cs.machine_tag(), cl["kind"])
        trows.append([cl["t"], cl["v"], cl["k"], cl["N"], "VERIFIED", cs.SOURCE_ID, cl["raw"]["source_detail"].strip(),
                      ctx["snapshot_id"], cl["sha256"], stamp, ctx["date"], notes_of(cl, ctx, name), "", "",
                      cl["raw"]["construction"].strip(), cl["builds_on"], ""])
        if name:
            mstatus = {"exceeds_table": "exceeds_snapshot", "equals_best": "equals_best",
                       "above_table": "above_best"}[cl["comparison"]]
            mrows.append([name, cl["t"], cl["v"], cl["k"], cl["N"], mstatus, cl["sha256"], cs.SOURCE_ID,
                          cl["raw"]["source_detail"].strip(), stamp,
                          cl["constant_rows"] if cl.get("constant_rows") is not None else ""])
        lrows.append(["%s/%s" % (ctx["slug"], cl["raw"]["file"].strip()), cl["t"], cl["v"], cl["k"], cl["N"], cl["kind"],
                      cl["res"]["cert_sha256"], cl["sha256"],
                      "%s: %s" % (stamp.split(" (")[0], ", ".join(cl["res"]["passed"])), name or ""])
    for name, _ in files:
        if os.path.exists(os.path.join(td, "arrays", name)):
            raise ConError("refusing to overwrite table/arrays/%s" % name)
    # the certificates and their file ingredients
    os.makedirs(cdir)
    for cl in claims:
        fn = cl["raw"]["file"].strip()
        shutil.copyfile(os.path.join(ctx["sub"], fn), os.path.join(cdir, fn))
        for ing in cl["res"]["ingredients"]:
            if ing["source"] == "file":
                shutil.copyfile(os.path.join(ctx["sub"], ing["file"]), os.path.join(cdir, ing["file"]))
    os.makedirs(os.path.join(td, "arrays"), exist_ok=True)
    for name, text in files:
        cs.write_array(os.path.join(td, "arrays", name), text)
    tpath = os.path.join(td, "ca_table.csv")
    eol = "\r\n" if b"\r\n" in open(tpath, "rb").read(4096) else "\n"
    cs.append_text(tpath, cs.table_csv_text(trows), eol)
    if mrows:
        cs.append_text(os.path.join(td, "MANIFEST.csv"), cs.manifest_csv_text(mrows), "\n")
    lpath = os.path.join(td, "constructions", "CONSTRUCTIONS.csv")
    if not os.path.exists(lpath):
        with open(lpath, "w", encoding="utf-8", newline="") as f:
            f.write(",".join('"%s"' % h for h in LIST_HEADER) + "\n")
    cs.append_text(lpath, cs.manifest_csv_text(lrows), "\n")
    return len(trows), len(files)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("submission")
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--ca-verify", default=os.path.join(REPO, "ca_verify"))
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--light", action="store_true", help="the pull request check (never writes to the table)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--pr", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--constant-rows-minutes", type=float, default=10.0)
    a = ap.parse_args(argv)
    sub = os.path.abspath(a.submission.rstrip("/"))
    slug = os.path.basename(sub)
    if not cs.SAFE_NAME.match(slug):
        raise SystemExit("bad submission directory name %r" % slug)
    rows, manifest = cs.load_table(a.table_dir)
    cav = a.ca_verify if os.path.isfile(a.ca_verify) and os.access(a.ca_verify, os.X_OK) else None
    taken = {m["file"]: m["sha256"] for m in manifest}
    if os.path.isdir(os.path.join(a.table_dir, "arrays")):
        for n in os.listdir(os.path.join(a.table_dir, "arrays")):
            taken.setdefault(n, None)
    ctx = dict(sub=sub, slug=slug, table_dir=a.table_dir, rows=rows, refs=bo.load(a.table_dir),
               manifest_sha={m["sha256"]: m["file"] for m in manifest},
               table_sha={r["array_sha256"] for r in rows if r.get("array_sha256")},
               seen_sha={}, seen_file=set(), threads=max(1, min(64, a.threads)), ca_verify=cav,
               constant_rows=cs.constant_rows_binary(), cr_budget=a.constant_rows_minutes * 60.0,
               date=a.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
               snapshot_id=("pr-%s" % a.pr) if a.pr and a.pr != "main" else slug, tool=tool_hash(), taken=taken)
    problems, claims = [], []
    sizes = [os.path.getsize(os.path.join(sub, n)) for n in os.listdir(sub) if os.path.isfile(os.path.join(sub, n))] \
        if os.path.isdir(sub) else []
    if sum(sizes) > cs.MAX_SUBMISSION_BYTES or any(x > cs.MAX_FILE_BYTES for x in sizes):
        problems.append("the submission's files are above the size limits (50 MiB per file, 200 MiB in all)")
    others = [n for n in ("claims.csv", "certificates.csv", "external.csv", "upgrade.csv") if os.path.exists(os.path.join(sub, n))]
    if "upgrade.csv" in others:
        problems.append("constructions.csv and upgrade.csv cannot share a folder")
    try:
        claims = read_claims(sub)
    except ConError as e:
        problems.append(str(e))
    with tempfile.TemporaryDirectory(prefix="cacon-") as tmp:
        for cl in claims:
            check_claim(cl, ctx, tmp)
        ok = bool(claims) and not problems and all(c["passed"] for c in claims)
        applied = None
        if ok and a.apply and not a.light:
            try:
                applied = apply(claims, ctx)
            except (ConError, OSError) as e:
                problems.append(str(e))
                ok = False
        text = report(ctx, claims, ok, problems)
        if applied:
            text += ("\nApplied: %d rows appended to `table/ca_table.csv`, %d arrays added to `table/arrays/`, the "
                     "certificates stored in `table/constructions/%s/`.\n" % (applied[0], applied[1], slug))
        elif a.apply and not a.light:
            text += "\nNot applied: the submission did not pass.\n"
    out = a.out or "check-%s" % slug
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(dict(slug=slug, passed=ok, applied=bool(applied), problems=problems,
                       claims=[dict(file=c["raw"].get("file"), passed=c.get("passed"), sha256=c.get("sha256"),
                                    reasons=c.get("reasons")) for c in claims]), f, indent=1)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
