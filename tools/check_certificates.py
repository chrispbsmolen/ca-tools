#!/usr/bin/env python3
"""check_certificates - check covering perfect hash family certificates and enter their arrays.

A certificate submission is a directory submissions/<slug>/ holding certificates.csv

    t,v,k,N,file,mode,source_detail,construction,builds_on,credit,notes

(the mode column may be left out, or left empty, or say "auto"; builds_on as in
submissions/README.md; files without that column are still read, and get cphf-smc2006 plus
the ids their construction text matches) and the family files it names (the format of
tools/cphf/cphfcheck.c: n lines of k integers, each a vector of GF(v)^t in base v).

mode says which exact method checks the family. "auto" (the default) lets cphfcheck choose the
cheapest exact method from the data (a certified cyclic symmetry, progression rows, projection
hashing or every t-set; tools/cphf/README.md). The explicit modes are still accepted: "full"
(every t-set of columns), "fullfast" (the same answer, by projection hashing), "progression" (rows
that are affine progressions are certified and the check reduced by translation), "fastprog" (the
result of progression by a faster exact method; needs progression rows), "cyclic s" (the
symmetry col -> col + s is certified first, then every t-set with smallest column < s). Any of
these may end in " affine" (every vector has first coordinate 1; the array then has
n (v^t - v) + v runs instead of n (v^t - 1) + 1). Without " affine", N decides: N must be the
size one of the two rules gives.

Every family is identified by family_sha256 (tools/cphf_cert.py) and a family already in the
table is rejected, except that a family entered as SCREENED may be entered again with an exact
check (it then gets a VERIFIED row). The array is expanded and hashed as a stream (never written
to disk) when it has at most 10^12 entries; above that the row is identified by family_sha256
alone and its stamp says "array not hashed".

Usage (each form prints a report; nothing in table/ changes without --apply):

  check_certificates.py SUB [--threads N] [--apply] [--builds-on VALUE]
        the exact check on this machine, unsharded, then (with --apply) the VERIFIED rows; this is
        also how a SCREENED family is checked exactly later, on any machine
  check_certificates.py SUB --light [--out DIR]
        the pull request check: format, identity, duplicates, size, the estimate and the plan, and a
        small deterministic screen (no exact check)
  check_certificates.py SUB --plan PLAN.json [--max-shards M --shard-hours H --runner-threads T]
        on main: choose the method and the number of shards of every claim within the time budget,
        or mark it for a screen; lists the tasks of the workflow matrix
  check_certificates.py SUB --run PLAN.json --task ID --out DIR [--threads N]
        one task of the plan: shard j of claim i ("c<i>-s<j>") or the array hash of claim i ("c<i>-hash")
  check_certificates.py SUB --results PLAN.json --tasks DIR --out DIR
        combine the shards (exact counts checked), screen the claims over the budget or whose shards
        did not all finish, and write result.json, report.md and the task outputs to the out folder
  check_certificates.py SUB --apply-result DIR [--apply]
        check a result folder again against the current table (identity, duplicates, the shard
        counts, the comparison) and with --apply enter the rows: VERIFIED for an exact check,
        SCREENED for a screen; table-page.yml does this on main, one submission at a time
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import check_submission as cs  # noqa: E402
import builds_on as bo  # noqa: E402
import cphf_cert as cc  # noqa: E402
from cphf_cert import CertError  # noqa: E402

HEADER = ["t", "v", "k", "N", "file", "mode", "source_detail", "construction", "builds_on", "credit",
          "notes"]
# the mode column may be left out (the same as "auto")
HEADER_NO_MODE = [h for h in HEADER if h != "mode"]
# the header before builds_on (2026-11), still read; such claims get
# builds_on = cphf-smc2006 plus the ids their construction text matches
PREV_HEADER = ["t", "v", "k", "N", "file", "mode", "source_detail", "construction", "credit", "notes"]
CERT_HEADER = ["file", "t", "v", "k", "N", "family", "sha256", "array_sha256", "check", "family_sha256",
               "expansion"]
SRC = os.path.join(HERE, "cphf", "cphfcheck.c")
MODE_RE = re.compile(r"^(auto|full|fullfast|progression|fastprog|cyclic (\d+))?( ?affine)?$")
# the screen of a family over the budget (the conventions of check_submission.py: random column
# windows seeded from the hash, each checked exactly), and a sample of single t-sets
SCREEN_WINDOWS, SCREEN_WIDTH, SCREEN_SAMPLES = 20, 30, 10 ** 6
LIGHT_WINDOWS, LIGHT_SAMPLES = 5, 10 ** 5


def build(tmp):
    exe = os.path.join(tmp, "cphfcheck")
    # -march=native first: the AVX2 key pass of mode fastprog where the machine has it (same results,
    # 10 to 15 percent faster); each job builds its own binary, so shards never share one
    for cmd in (["cc", "-O3", "-march=native", "-fopenmp", "-o", exe, SRC, "-lm"],
                ["cc", "-O3", "-fopenmp", "-o", exe, SRC, "-lm"],
                ["cc", "-O3", "-o", exe, SRC, "-lm"]):          # without OpenMP: one thread
        if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return exe
    raise SystemExit("could not build %s" % SRC)


def tool_hash():
    return hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:12]


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def machine_tag():
    return cs.machine_tag()


def run(exe, args, timeout=None):
    p = subprocess.run([exe] + [str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def stream_hash(exe, fam, t, v, affine, tmp):
    """expand into a FIFO and hash it as it is written; returns (rows, sha256)"""
    fifo = os.path.join(tmp, "ca.fifo")
    if os.path.exists(fifo):
        os.remove(fifo)
    os.mkfifo(fifo)
    res = {}

    def reader():
        h = hashlib.sha256(); rows = 0
        with open(fifo, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b); rows += b.count(b"\n")
        res["sha"], res["rows"] = h.hexdigest(), rows
    th = threading.Thread(target=reader); th.start()
    p = subprocess.run([exe, fam, str(t), str(v), "expand", fifo] + (["affine"] if affine else []),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    th.join()
    if p.returncode != 0:
        raise CertError("expand failed: %s" % (p.stderr.strip() or p.stdout.strip()))
    return res["rows"], res["sha"]


def claim_builds_on(raw, refs):
    """builds_on for a certificate claim: as given (checked), or, for the
    header without the field, the CPHF origin plus the ids the construction
    text matches. Every array here is a CPHF expansion, so cphf-smc2006 is
    always included."""
    if "builds_on" in raw:
        given = raw["builds_on"]
        if "cphf-smc2006" not in given.split(";"):
            given = "cphf-smc2006;" + given if given.strip() else given
        norm, errs, warns, links = bo.check(given, raw["construction"], refs)
        if errs:
            raise CertError("builds_on: " + "; ".join(errs))
    else:
        norm, warns = "", []
    ids = [x for x in norm.split(";") if x]
    if "cphf-smc2006" not in ids:
        ids.insert(0, "cphf-smc2006")
    if "builds_on" not in raw:
        ids += [x for x in bo.suggest(raw["construction"], refs) if x not in ids]
    return ";".join(ids), warns


# ---------------------------------------------------------------------------------------------
# the table and the certificates already listed

def load_certs(table_dir):
    path = os.path.join(table_dir, "certificates", "CERTIFICATES.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_context(table_dir):
    table_path = os.path.join(table_dir, "ca_table.csv")
    table_rows = list(csv.DictReader(open(table_path, newline="", encoding="utf-8")))
    certs = load_certs(table_dir)
    # family_sha256 -> how it was checked when entered ("exact" or "screened"), from the
    # listings and from the table rows (a row may carry it without a listing only by mistake)
    fam = {}
    for c in certs:
        f = c.get("family_sha256") or ""
        if f:
            fam.setdefault(f, set()).add("screened" if "screened" in c["check"] else "exact")
    for r in table_rows:
        f = r.get("family_sha256") or ""
        if f and r["tier"] in ("VERIFIED", "SCREENED"):
            fam.setdefault(f, set()).add("exact" if r["tier"] == "VERIFIED" else "screened")
    return dict(refs=bo.load(table_dir), table_rows=table_rows, table_path=table_path, certs=certs,
                known_sha={r["array_sha256"] for r in table_rows if r["array_sha256"]},
                known_family=fam, seen_family=set(), table_dir=table_dir)


def read_claims(sub, builds_on_override=None):
    path = os.path.join(sub, "certificates.csv")
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f); hdr = [h.strip() for h in next(rd, [])]
        if hdr not in (HEADER, HEADER_NO_MODE, PREV_HEADER):
            raise SystemExit("certificates.csv header must be %s (the mode column may be left out)"
                             % ",".join(HEADER))
        claims = []
        for rec in rd:
            if not any(x.strip() for x in rec):
                continue
            if len(rec) != len(hdr):
                raise SystemExit("certificates.csv: a line has %d fields, expected %d" % (len(rec), len(hdr)))
            claims.append(dict(zip(hdr, rec)))
    if builds_on_override is not None:
        if hdr != PREV_HEADER:
            raise SystemExit("--builds-on is only for a certificates.csv without the builds_on column")
        for c in claims:
            c["builds_on"] = builds_on_override
    if not claims:
        raise SystemExit("certificates.csv has no claims")
    return claims


# ---------------------------------------------------------------------------------------------
# one claim: the cheap part (fields, identity, size, duplicates, comparison)

def prepare(raw, sub, exe, ctx, tmp):
    c = dict(raw=raw)
    c["builds_on"], c["builds_on_warnings"] = claim_builds_on(raw, ctx["refs"])
    for fld in ("file", "source_detail", "construction", "credit"):
        if not (raw.get(fld) or "").strip():
            raise CertError("certificates.csv field %s is empty" % fld)
    for fld in ("t", "v", "k", "N"):
        if not re.fullmatch(r"[0-9]+", (raw.get(fld) or "").strip()):
            raise CertError("certificates.csv field %s=%r is not a whole number" % (fld, raw.get(fld)))
    t, v, k, N = (int(raw[x]) for x in ("t", "v", "k", "N"))
    if not (2 <= t <= 8) or not (2 <= v <= 32):
        raise CertError("t must be 2..8 and v 2..32 (the range of cphfcheck)")
    m = MODE_RE.match((raw.get("mode") or "").strip())
    if not m:
        raise CertError("mode %r is not empty, 'auto', 'full', 'fullfast', 'progression', 'fastprog' or 'cyclic s', "
                        "optionally followed by ' affine'" % raw["mode"])
    method = m.group(1) if m.group(1) and m.group(1) != "auto" else None
    said_affine = bool(m.group(3))
    fname = raw["file"].strip()
    parts = fname.split("/")
    if not fname or any(not cs.SAFE_NAME.match(x) for x in parts) or len(parts) > 3:
        raise CertError("file %r is not a plain path inside the submission (names of letters, digits, '.', '_', '-', "
                        "at most two folders)" % fname)
    fam = os.path.join(sub, *parts)
    if any(os.path.islink(os.path.join(sub, *parts[:i + 1])) for i in range(len(parts))):
        raise CertError("family file %s or a folder on its path is a symbolic link" % fname)
    if not os.path.isfile(fam):
        raise CertError("family file %s is missing" % fname)
    if os.path.getsize(fam) > cs.MAX_FILE_BYTES:
        raise CertError("family file is over the 50 MiB limit")
    try:
        fsha, n, kk, all_first1 = cc.family_identity(fam, v, t)
    except UnicodeDecodeError:
        raise CertError("family file %s is not plain ASCII text" % fname)
    if kk != k:
        raise CertError("the family has %d columns, the claim says k=%d" % (kk, k))
    # the checker must read the family exactly as the identity does
    canon = os.path.join(tmp, "canon.txt")
    code, out, err = run(exe, [fam, t, v, "canon", canon])
    if code != 0:
        raise CertError("cphfcheck cannot read the family: %s" % (err.strip() or out.strip())[:300])
    if file_sha(canon) != fsha:
        raise CertError("cphfcheck reads the family differently from its identity (a bug)")
    plain, aff = n * (v ** t - 1) + 1, n * (v ** t - v) + v
    if said_affine:
        if not all_first1:
            raise CertError("mode says affine but not every vector has first coordinate 1")
        affine = True
    elif N == plain:
        affine = False
    elif N == aff and all_first1:
        affine = True
    else:
        raise CertError("N=%d, but CPHF(%d; %d, %d, %d) gives %d%s" % (
            N, n, k, v, t, plain, (" (or %d with the affine rule)" % aff) if all_first1 else ""))
    if N != (aff if affine else plain):
        raise CertError("N=%d, but the affine CPHF(%d; %d, %d, %d) gives %d" % (N, n, k, v, t, aff))
    if fsha in ctx["seen_family"]:
        raise CertError("duplicate: the same family is named twice in this submission")
    known = ctx["known_family"].get(fsha, set())
    if "exact" in known:
        raise CertError("duplicate: this family (family_sha256 %s) is already in the table" % fsha)
    c["upgrade"] = "screened" in known       # entered as SCREENED; only an exact check can add to it
    prev, prev_row = cs.best_known(ctx["table_rows"], t, v, k)
    c.update(t=t, v=v, k=k, N=N, n=n, fam=fam, fname=fname, fam_sha=fsha, file_sha=file_sha(fam),
             method=method, affine=affine, expansion=cc.expansion_id(affine),
             hashed=cc.array_is_hashed(N, k), prev=prev, prev_row=prev_row,
             comparison=("exceeds_table" if prev is None or N < prev else
                         "equals_best" if N == prev else "above_table"))
    return c


def mode_args(method, threads):
    """cphfcheck arguments of a method: "full", "fullfast", "progression", "fastprog", "cyclic s" or "auto"."""
    if method.startswith("cyclic"):
        return ["cyclic", method.split()[1], threads]
    return [method, threads]


def estimate(c, exe, threads):
    code, out, err = run(exe, [c["fam"], c["t"], c["v"], "estimate", threads])
    if code != 0:
        raise CertError("estimate failed: %s" % (err.strip() or out.strip())[:300])
    est = cc.parse_estimate(out)
    if c["method"]:                       # the submitter's method: its own estimate
        name = c["method"].split()[0]
        e = est["methods"].get(name)
        if name == "cyclic" and (e is None or e["method"] != c["method"]):
            s = int(c["method"].split()[1])
            units = cc.expected_totals(c["method"], c["k"], c["t"])["units"]
            e = dict(method=c["method"], units=units, core_seconds=units * cc.UNIT_NS["cyclic"] * 1e-9)
            if est["symmetry"] == 0 or s % est["symmetry"]:
                e["note"] = "cphfcheck found no certified symmetry col -> col+%d" % s
        if e is None and (name == "progression" or (name == "fastprog" and c["k"] <= 65535)):
            # no progression rows (fastprog at t = 2 runs the code of progression): every t-set is then
            # a representative tested by rank (correct, slow); fastprog needs k <= 65535
            import math
            k, t = c["k"], c["t"]
            e = dict(method=name, units=math.comb(k - 1, t - 2),
                     core_seconds=(math.comb(k - 1, t - 2) * cc.UNIT_NS[name]
                                   + math.comb(k, t) * cc.UNIT_NS["shift"]) * 1e-9)
        if e is None:
            raise CertError("method %s does not apply to this family (%s)" % (c["method"], name))
        est["cheapest"] = dict(method=e["method"], core_seconds=e["core_seconds"])
    return est


# ---------------------------------------------------------------------------------------------
# exact check (unsharded), screen, array hash

def exact_local(c, exe, threads):
    method = c["method"] or "auto"
    code, out, err = run(exe, [c["fam"], c["t"], c["v"]] + mode_args(method, threads))
    lines = out.strip().splitlines()
    if code == 3:
        raise CertError("symmetry or progression not certified: %s" % (err.strip() or " | ".join(lines[-2:]))[:300])
    if code == 4:
        raise CertError("checker internal consistency check failed (a bug, not a verdict): %s" % " | ".join(lines[-3:]))
    if code != 0:
        raise CertError("not a CPHF: %s" % " | ".join(lines[-2:]))
    chosen = c["method"]
    for l in lines:
        m = re.match(r"auto: method (.*)$", l)
        if m:
            chosen = m.group(1)
    checked = [l for l in lines if l.startswith("checked ")][0]
    return dict(method=chosen, checked=checked, sharded=False)


def screen(c, exe, threads, tmp, windows=None, width=None, samples=None):
    """Deterministic screen: column windows seeded from family_sha256 (as check_submission.py seeds
    them from the array hash), each sub-family checked exactly, then random t-sets. Any uncovered
    t-set found is a proof that the family is not a CPHF; none found is evidence, not proof."""
    windows = SCREEN_WINDOWS if windows is None else windows
    width = SCREEN_WIDTH if width is None else width
    samples = SCREEN_SAMPLES if samples is None else samples
    t, v, k = c["t"], c["v"], c["k"]
    rows = cc.read_family(c["fam"], v, t)
    done = []
    if k > width:
        wins = cs.screen_windows(k, c["fam_sha"], windows, width)
        sub = os.path.join(tmp, "window.txt")
        for wi, cols in enumerate(wins, 1):
            with open(sub, "w", encoding="ascii") as f:
                for r in rows:
                    f.write(" ".join(str(r[x]) for x in cols) + "\n")
            code, out, err = run(exe, [sub, t, v, "full", threads])
            if code == 1:
                m = re.search(r"first uncovered: (.*)", out)
                bad = [cols[int(x)] for x in m.group(1).split()] if m else []
                raise CertError("not a CPHF: screen window %d of %d has an uncovered t-set, columns (%s)"
                                % (wi, len(wins), ",".join(map(str, bad))))
            if code != 0:
                raise CertError("screen window %d failed: %s" % (wi, (err.strip() or out.strip())[:200]))
        done.append("%d random windows of %d columns checked exactly" % (len(wins), width))
    seed = int(c["fam_sha"][:15], 16)
    code, out, err = run(exe, [c["fam"], t, v, "sample", samples, seed, threads])
    if code == 1:
        raise CertError("not a CPHF: %s" % out.strip().splitlines()[-1])
    if code != 0:
        raise CertError("screen sample failed: %s" % (err.strip() or out.strip())[:200])
    done.append("%d random t-sets" % samples)
    return dict(text="; ".join(done), seed=c["fam_sha"][:16], windows=windows if k > width else 0,
                width=width, samples=samples)


def array_hash(c, exe, tmp):
    if not c["hashed"]:
        return None
    rows, sha = stream_hash(exe, c["fam"], c["t"], c["v"], c["affine"], tmp)
    if rows != c["N"]:
        raise CertError("expanded array has %d runs, expected %d" % (rows, c["N"]))
    return sha


# ---------------------------------------------------------------------------------------------
# rows

def previous_text(c):
    if c["prev"] is None:
        return "no previous entry for these parameters"
    r = c["prev_row"]
    src = "%s %s" % (r["tier"], r["source_id"])
    if r.get("snapshot_id"):
        src += " " + r["snapshot_id"]
    return "previous best %d (row k=%s, %s)" % (c["prev"], r["k"], src)


def write_rows(results, slug, ctx, today):
    """Append the table rows and the certificate listings of passed claims (results: claims with
    tier, stamp, check, sha, method fields)."""
    cdir = os.path.join(ctx["table_dir"], "certificates"); clist = os.path.join(cdir, "CERTIFICATES.csv")
    trows, crows = [], []
    by_fam = {x.get("family_sha256"): x["file"] for x in ctx["certs"] if x.get("family_sha256")}
    for c in results:
        raw = c["raw"]
        name = by_fam.get(c["fam_sha"])
        if name is None:
            name = "CPHF_%d_%d_%d_%d.txt" % (c["n"], c["k"], c["v"], c["t"])
            if os.path.exists(os.path.join(cdir, name)):
                name = "CPHF_%d_%d_%d_%d_%s.txt" % (c["n"], c["k"], c["v"], c["t"], c["file_sha"][:8])
            shutil.copyfile(c["fam"], os.path.join(cdir, name))
            by_fam[c["fam_sha"]] = name
        family = "CPHF(%d; %d, %d, %d)%s" % (c["n"], c["k"], c["v"], c["t"], ", affine" if c["affine"] else "")
        cmp_txt = {"exceeds_table": "exceeds table: ", "equals_best": "equals table: ",
                   "above_table": "above table best, not an improvement: "}[c["comparison"]] + previous_text(c)
        notes = ["credit: " + raw["credit"].strip(), cmp_txt,
                 "certificate table/certificates/%s, %s, %s, expansion %s" % (name, family, c["method_text"], c["expansion"]),
                 "from submissions/%s/certificates.csv" % slug]
        if c["tier"] == "SCREENED":
            notes.append("SCREENED, not exhaustively verified: %s, seed %s; %s"
                         % (c["screen"]["text"], c["screen"]["seed"], c["screen_why"]))
        if c.get("upgrade"):
            notes.append("exact check of the family entered earlier as SCREENED")
        if not c["hashed"]:
            notes.append("array of %d entries, identified by family_sha256 (array not hashed)" % (c["N"] * c["k"]))
        if raw.get("notes", "").strip():
            notes.append(raw["notes"].strip())
        trows.append([c["t"], c["v"], c["k"], c["N"], c["tier"], cs.SOURCE_ID, raw["source_detail"].strip(),
                      slug, c["sha"] or "", c["stamp"], today, "; ".join(notes), "", "",
                      raw["construction"].strip(), c["builds_on"], c["fam_sha"]])
        crows.append([name, c["t"], c["v"], c["k"], c["N"], family, c["file_sha"], c["sha"] or "",
                      c["check"], c["fam_sha"], c["expansion"]])
    eol = "\r\n" if b"\r\n" in open(ctx["table_path"], "rb").read(4096) else "\n"
    cs.append_text(ctx["table_path"], cs.table_csv_text(trows), eol)
    cs.append_text(clist, cs.manifest_csv_text(crows), "\n")
    return len(trows)


def finish(c, tool, date, machine, exact, how, sha):
    """stamp and check text of a claim that passed"""
    base = "cphfcheck %s %s %s" % (tool, date, machine)
    kind = "exact" if exact else "screened"
    c["tier"] = "VERIFIED" if exact else "SCREENED"
    c["sha"] = sha
    c["stamp"] = base + " (CPHF certificate, %s%s)" % (kind, "" if c["hashed"] else "; array not hashed")
    c["check"] = "%s: %s" % (base, how)


def report(slug, title, claims, ok, extra=()):
    L = ["## Certificate check: `%s`" % slug, "", title, ""]
    L.append("**Result: %s.**" % ("PASS" if ok else "FAIL"))
    L.append("")
    for i, c in enumerate(claims, 1):
        L.append("**%d. %s** (%s)" % (i, cs.md_cell(c["raw"].get("file", "")), "PASS" if c.get("passed") else "FAIL"))
        L.append("")
        for line in c.get("lines", []):
            L.append("- " + cs.md_cell(line))
        for r in c.get("reasons", []):
            L.append("- **%s**" % cs.md_cell(r))
        L.append("")
    L += list(extra)
    return "\n".join(L) + "\n"


def describe(c):
    out = ["CPHF(%d; %d, %d, %d) gives CA(%d; %d, %d, %d), expansion %s"
           % (c["n"], c["k"], c["v"], c["t"], c["N"], c["t"], c["k"], c["v"], c["expansion"]),
           "family_sha256 `%s`" % c["fam_sha"],
           "table: %s; %s" % (c["comparison"], previous_text(c))]
    if not c["hashed"]:
        out.append("array of %d entries, above 10^12: identified by family_sha256, array not hashed"
                   % (c["N"] * c["k"]))
    if c.get("upgrade"):
        out.append("this family is in the table as SCREENED; an exact check adds a VERIFIED row")
    out.append("builds on: %s" % c["builds_on"])
    for w in c["builds_on_warnings"]:
        out.append("note: builds_on: %s" % w)
    return out


# ---------------------------------------------------------------------------------------------
# the forms of the command

def budget_args(a):
    return dict(threads=a.runner_threads, max_shards=a.max_shards, shard_hours=a.shard_hours, safety=a.safety)


def make_plan(claims, sub, exe, ctx, tmp, a):
    """method and shards of every claim within one pool of a.max_shards shards"""
    pool = a.max_shards
    plan = []
    for i, raw in enumerate(claims):
        c = prepare(raw, sub, exe, ctx, tmp)
        ctx["seen_family"].add(c["fam_sha"])
        est = estimate(c, exe, a.threads)
        b = budget_args(a); b["max_shards"] = pool
        p = cc.plan_claim(est, c["k"], c["t"], **b)
        if p["exact"]:
            pool -= p["shards"]
        plan.append(dict(index=i, file=c["fname"], t=c["t"], v=c["v"], k=c["k"], N=c["N"], n=c["n"],
                         family_sha256=c["fam_sha"], file_sha256=c["file_sha"], affine=c["affine"],
                         hashed=c["hashed"], method=p["method"], shards=p["shards"], exact=p["exact"],
                         core_hours=p["core_hours"], shard_hours=p["shard_hours"], estimate=est,
                         prepared=c))
    return plan


def plan_text(p, a):
    if p["exact"]:
        return ("exact check with %s in %d shard%s on GitHub, about %.2g hours each (estimate times %g, "
                "%.3g core-hours in all); enters as VERIFIED" % (
                    p["method"], p["shards"], "" if p["shards"] == 1 else "s", p["shard_hours"], a.safety,
                    p["core_hours"]))
    return ("cheapest exact method %s, about %.3g core-hours (estimate times %g): over the budget of "
            "%d shards of %g hours on %d threads; screened on GitHub and enters as SCREENED until an "
            "exact check is run elsewhere" % (p["method"], p["core_hours"], a.safety, a.max_shards,
                                             a.shard_hours, a.runner_threads))


def tasks_of(plan):
    out = []
    for p in plan:
        if p["exact"]:
            out += ["c%d-s%d" % (p["index"], j) for j in range(p["shards"])]
        if p["hashed"]:
            out.append("c%d-hash" % p["index"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("submission")
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--builds-on", default=None,
                    help="builds_on for every claim of a submission whose certificates.csv "
                         "has no builds_on column (the maintainer's value, checked like a "
                         "submitter's)")
    ap.add_argument("--light", action="store_true", help="the pull request check (no exact check)")
    ap.add_argument("--plan", metavar="PLAN_JSON", help="write the plan of the exact checks")
    ap.add_argument("--run", metavar="PLAN_JSON", help="run one task of a plan (with --task)")
    ap.add_argument("--task", default=None)
    ap.add_argument("--results", metavar="PLAN_JSON", help="combine the task outputs of a plan (with --tasks)")
    ap.add_argument("--tasks", default=None, help="folder of task outputs")
    ap.add_argument("--apply-result", metavar="DIR", help="check a result folder again, enter it with --apply")
    ap.add_argument("--out", default=None, help="output folder")
    ap.add_argument("--runner-threads", type=int, default=cc.RUNNER_THREADS)
    ap.add_argument("--max-shards", type=int, default=cc.MAX_SHARDS)
    ap.add_argument("--shard-hours", type=float, default=cc.SHARD_HOURS)
    ap.add_argument("--safety", type=float, default=cc.SAFETY)
    ap.add_argument("--date", default=None)
    a = ap.parse_args(argv)
    sub = a.submission.rstrip("/"); slug = os.path.basename(sub)
    if not cs.SAFE_NAME.match(slug):
        raise SystemExit("bad submission directory name %r" % slug)
    try:
        claims = read_claims(sub, a.builds_on)
    except SystemExit as e:
        # on main the workflow needs a plan or a result even for a submission that cannot be read
        if a.plan:
            with open(a.plan, "w", encoding="utf-8") as f:
                json.dump(dict(slug=slug, tool=tool_hash(), failed=str(e), claims=[], tasks=[]), f, indent=1)
            print("plan failed: %s" % e)
            return 0
        if not a.results:
            raise
        claims = []
    ctx = load_context(a.table_dir)
    today = a.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    with tempfile.TemporaryDirectory(prefix="cacert-") as tmp:
        exe = build(tmp)
        if a.light:
            return form_light(claims, sub, slug, exe, ctx, tmp, a)
        if a.plan:
            return form_plan(claims, sub, slug, exe, ctx, tmp, a)
        if a.run:
            return form_run(sub, exe, tmp, a)
        if a.results:
            return form_results(claims, sub, slug, exe, ctx, tmp, a, today)
        if a.apply_result:
            return form_apply_result(claims, sub, slug, exe, ctx, tmp, a, today)
        return form_local(claims, sub, slug, exe, ctx, tmp, a, today)


def write_out(a, slug, text, summary):
    out = a.out or "check-%s" % slug
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, default=str); f.write("\n")
    print(text)


def form_local(claims, sub, slug, exe, ctx, tmp, a, today):
    """the exact check on this machine, unsharded"""
    results, ok = [], True
    tool = tool_hash()
    for raw in claims:
        print("checking %s ..." % raw.get("file"), file=sys.stderr, flush=True)
        try:
            c = prepare(raw, sub, exe, ctx, tmp)
            ctx["seen_family"].add(c["fam_sha"])
            ex = exact_local(c, exe, a.threads)
            sha = array_hash(c, exe, tmp)
            if sha and sha in ctx["known_sha"] and not c["upgrade"]:
                raise CertError("duplicate: this array is already in the table")
            c["method_text"] = ex["method"]
            finish(c, tool, today, machine_tag(), True, "method %s: %s" % (ex["method"], ex["checked"]), sha)
            c["passed"] = True
            print("  PASS %s: %s, %s; array sha256 %s; %s (previous best %s); builds on %s"
                  % (raw["file"], ex["method"], ex["checked"], (sha or "not hashed")[:12], c["comparison"],
                     c["prev"], c["builds_on"]), flush=True)
            for w in c["builds_on_warnings"]:
                print("    note: builds_on: %s" % w, flush=True)
            results.append(c)
        except (CertError, ValueError, OSError) as e:
            ok = False
            print("  FAIL %s: %s" % (raw.get("file"), e), flush=True)
    if not ok:
        print("Not every claim passed; nothing applied."); return 1
    if not a.apply:
        print("Every claim passed. Run again with --apply to enter them."); return 0
    n = write_rows(results, slug, ctx, today)
    print("Applied %d certificate rows." % n)
    return 0


def form_light(claims, sub, slug, exe, ctx, tmp, a):
    """pull request: everything but the exact check"""
    out, ok, pool = [], True, a.max_shards
    for raw in claims:
        c = dict(raw=raw, lines=[], reasons=[])
        try:
            p = prepare(raw, sub, exe, ctx, tmp)
            ctx["seen_family"].add(p["fam_sha"])
            c.update(p)
            c["lines"] += describe(c)
            est = estimate(c, exe, a.runner_threads)
            b = budget_args(a); b["max_shards"] = pool
            pl = cc.plan_claim(est, c["k"], c["t"], **b)
            if pl["exact"]:
                pool -= pl["shards"]
            ests = ", ".join("%s %.3g core-seconds" % (e["method"], e["core_seconds"])
                             for e in est["methods"].values())
            c["lines"].append("rows: %d progression, %d other, %d dead; %s" % (
                est["rows"] + ("symmetry col -> col+%d certified" % est["symmetry"] if est["symmetry"]
                               else "no cyclic symmetry",)))
            c["lines"].append("estimates: %s" % ests)
            c["lines"].append("on merge: " + plan_text(pl, a))
            if pl["exact"] is False and c.get("upgrade"):
                raise CertError("duplicate: this family is already SCREENED and would be screened again")
            sc = screen(c, exe, a.runner_threads, tmp, windows=LIGHT_WINDOWS, samples=LIGHT_SAMPLES)
            c["lines"].append("screen (evidence, not proof): %s, seed %s, nothing uncovered" % (sc["text"], sc["seed"]))
            c["passed"] = True
        except (CertError, ValueError, OSError) as e:
            ok = False; c["passed"] = False; c["reasons"].append(str(e))
        out.append(c)
    title = ("The exact check is not run on the pull request. After the merge the certificate workflow on "
             "main plans it from the estimate below, runs it in shards and enters the rows "
             "(tools/check_certificates.py, submissions/README.md).")
    text = report(slug, title, out, ok)
    write_out(a, slug, text, dict(slug=slug, passed=ok, certificates=True,
                                  claims=[dict(file=c["raw"].get("file"), passed=c.get("passed"),
                                               reasons=c.get("reasons"), family_sha256=c.get("fam_sha"))
                                          for c in out]))
    return 0 if ok else 1


def form_plan(claims, sub, slug, exe, ctx, tmp, a):
    try:
        plan = make_plan(claims, sub, exe, ctx, tmp, a)
        failed = None
    except (CertError, ValueError, OSError) as e:
        plan, failed = [], str(e)
    doc = dict(slug=slug, tool=tool_hash(), failed=failed,
               budget=dict(runner_threads=a.runner_threads, max_shards=a.max_shards,
                           shard_hours=a.shard_hours, safety=a.safety),
               claims=[{k2: v2 for k2, v2 in p.items() if k2 != "prepared"} for p in plan],
               tasks=tasks_of(plan))
    with open(a.plan, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1); f.write("\n")
    for p in plan:
        print("%s: %s" % (p["file"], plan_text(p, a)))
    if failed:
        print("plan failed: %s" % failed)
    print("tasks: %s" % (" ".join(doc["tasks"]) or "none"))
    return 0


def load_plan(path, sub):
    doc = json.load(open(path, encoding="utf-8"))
    if doc["slug"] != os.path.basename(sub.rstrip("/")):
        raise SystemExit("the plan is for %s" % doc["slug"])
    return doc


def form_run(sub, exe, tmp, a):
    doc = load_plan(a.run, sub)
    m = re.fullmatch(r"c(\d+)-(s(\d+)|hash)", a.task or "")
    if not m or a.task not in doc["tasks"]:
        raise SystemExit("task %r is not in the plan" % a.task)
    p = doc["claims"][int(m.group(1))]
    fam = os.path.join(sub, *p["file"].split("/"))
    if file_sha(fam) != p["file_sha256"]:
        raise SystemExit("the family file changed since the plan was made")
    os.makedirs(a.out, exist_ok=True)
    meta = ["# family_sha256: %s" % p["family_sha256"], "# tool: %s" % tool_hash(),
            "# method: %s" % p["method"], "# t: %d" % p["t"], "# q: %d" % p["v"], "# task: %s" % a.task]
    if m.group(3) is not None:
        j = int(m.group(3))
        args = [fam, p["t"], p["v"]] + mode_args(p["method"], a.threads) + ["shard", j, p["shards"]]
        meta.append("# command: cphfcheck %s" % " ".join(str(x) for x in args[1:]))
        code, out, err = run(exe, args)
        body = out + ("" if out.endswith("\n") or not out else "\n")
        if err.strip():
            body += "".join("# stderr: %s\n" % l for l in err.strip().splitlines()[:20])
    else:
        c = dict(fam=fam, t=p["t"], v=p["v"], affine=p["affine"], hashed=p["hashed"], N=p["N"])
        try:
            sha = array_hash(c, exe, tmp); code, body = 0, "array_sha256 %s\nruns %d\n" % (sha, p["N"])
        except CertError as e:
            code, body = 1, "# error: %s\n" % e
    path = os.path.join(a.out, "%s.txt" % a.task)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(meta) + "\n" + body + "# exit: %d\n" % code)
    print("%s: exit %d, written to %s" % (a.task, code, path))
    return 0 if code in (0, 1) else code


def read_tasks(folder, index):
    shards, hashtxt = [], None
    if folder and os.path.isdir(folder):
        for root, _, files in os.walk(folder):
            for fn in sorted(files):
                if re.fullmatch(r"c%d-s[\w-]+\.txt" % index, fn):
                    shards.append(open(os.path.join(root, fn), encoding="utf-8").read())
                elif fn == "c%d-hash.txt" % index:
                    hashtxt = open(os.path.join(root, fn), encoding="utf-8").read()
    return shards, hashtxt


def settle(c, p, shards, hashtxt, exe, tmp, a, today, tool):
    """Decide one claim from its task outputs: combine the shards (VERIFIED), or screen (SCREENED).
    Raises CertError when the family is shown not to be a CPHF or cannot be identified."""
    sha = None
    if p["hashed"]:
        m = re.search(r"^array_sha256 ([0-9a-f]{64})$", hashtxt or "", re.M)
        if not m:
            raise CertError("the array hash task did not finish; the array cannot be identified")
        sha = m.group(1)
        meta = cc.parse_shard(hashtxt)["meta"]
        if meta.get("family_sha256") != c["fam_sha"]:
            raise CertError("the array hash task was run on another family")
    exact, why = False, None
    if p["exact"]:
        try:
            res = cc.combine(shards, p["method"], c["k"], c["t"])
            if cc.parse_shard(shards[0])["meta"]["family_sha256"] != c["fam_sha"]:
                raise CertError("the shards were run on another family")
            if res["uncovered"]:
                raise CertError("not a CPHF: %d uncovered t-sets%s, the smallest (%s)" % (
                    res["uncovered"], "" if p["method"] in ("full", "fullfast") else " (as counted by the method)",
                    ",".join(map(str, res["first"]))))
            exact = True
            tool = cc.parse_shard(shards[0])["meta"]["tool"]
            unit = {"full": "t-sets", "fullfast": "t-sets",
                    "progression": "representatives (t-sets containing column 0; the others by translation)",
                    "fastprog": "representatives (t-sets containing column 0; the others by translation)"}.get(
                p["method"], "representative t-sets (smallest column below s; the others by the symmetry)")
            how = "method %s in %d shard%s: %d %s checked, uncovered 0" % (
                p["method"], res["m"], "" if res["m"] == 1 else "s", res["units"], unit)
        except CertError as e:
            if str(e).startswith("not a CPHF"):
                raise
            why = "the exact check planned on GitHub did not complete (%s)" % e
    else:
        why = ("the exact check (%s, about %.3g core-hours with the safety factor) is over the budget of "
               "%d shards of %g hours on %d threads" % (p["method"], p["core_hours"], a.max_shards,
                                                        a.shard_hours, a.runner_threads))
    if not exact:
        if c.get("upgrade"):
            raise CertError("duplicate: this family is already SCREENED and was screened again")
        sc = screen(c, exe, a.threads, tmp)
        c["screen"], c["screen_why"] = sc, why
        how = "screened: %s, nothing uncovered, seed %s; %s" % (sc["text"], sc["seed"], why)
    c["method_text"] = p["method"]
    finish(c, tool, today, machine_tag(), exact, how, sha)
    return how


def form_results(claims, sub, slug, exe, ctx, tmp, a, today):
    doc = load_plan(a.results, sub)
    if len(claims) != len(doc["claims"]) and not doc["failed"]:
        doc["failed"] = "certificates.csv no longer has the claims of the plan"
        doc["claims"] = []
    outdir = a.out or "result-%s" % slug
    os.makedirs(os.path.join(outdir, "tasks"), exist_ok=True)
    rep, ok = [], doc["failed"] is None
    results = []
    if doc["failed"]:
        rep.append(dict(raw=dict(file="(submission)"), passed=False, reasons=[doc["failed"]]))
    for p in doc["claims"]:
        raw = claims[p["index"]]
        c = dict(raw=raw, lines=[], reasons=[])
        try:
            c.update(prepare(raw, sub, exe, ctx, tmp))
            ctx["seen_family"].add(c["fam_sha"])
            if c["fam_sha"] != p["family_sha256"]:
                raise CertError("the family changed since the plan was made")
            shards, hashtxt = read_tasks(a.tasks, p["index"])
            for j, txt in enumerate(shards):        # kept with the result, for the check before entry
                name = cc.parse_shard(txt)["meta"].get("task", "")
                if not re.fullmatch(r"c%d-s\d+" % p["index"], name):
                    name = "c%d-s-unnamed%d" % (p["index"], j)
                with open(os.path.join(outdir, "tasks", name + ".txt"), "w", encoding="utf-8") as f:
                    f.write(txt)
            if hashtxt:
                with open(os.path.join(outdir, "tasks", "c%d-hash.txt" % p["index"]), "w", encoding="utf-8") as f:
                    f.write(hashtxt)
            how = settle(c, p, shards, hashtxt, exe, tmp, a, today, tool_hash())
            c["lines"] = describe(c) + ["%s: %s" % (c["tier"], how)]
            c["passed"] = True
            results.append(c)
        except (CertError, ValueError, OSError) as e:
            ok = False; c["passed"] = False; c["reasons"].append(str(e))
        rep.append(c)
    text = report(slug, "Checked on main by the certificate workflow (plan: %s)." % ", ".join(
        "%s %s" % (p["file"], ("exact in %d shard%s" % (p["shards"], "" if p["shards"] == 1 else "s"))
                   if p["exact"] else "screen")
        for p in doc["claims"]), rep, ok)
    res = dict(slug=slug, passed=ok, date=today, machine=machine_tag(), plan=doc,
               claims=[dict(index=i, file=c["raw"]["file"], family_sha256=c["fam_sha"], file_sha256=c["file_sha"],
                            tier=c["tier"], stamp=c["stamp"], check=c["check"], array_sha256=c["sha"],
                            method=c["method_text"], screen=c.get("screen"), screen_why=c.get("screen_why"))
                       for i, c in enumerate(results)])
    with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1); f.write("\n")
    with open(os.path.join(outdir, "report.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    return 0 if ok else 1


def form_apply_result(claims, sub, slug, exe, ctx, tmp, a, today):
    """Check a result folder again on the current table, and enter it (with --apply)."""
    rdir = a.apply_result
    res = json.load(open(os.path.join(rdir, "result.json"), encoding="utf-8"))
    rep, ok, results = [], bool(res.get("passed")), []
    if res.get("slug") != slug:
        raise SystemExit("the result is for %s" % res.get("slug"))
    if not res.get("passed"):
        rep.append(dict(raw=dict(file="(result)"), passed=False,
                        reasons=["the certificate workflow did not pass this submission; see its report"]))
    plan = res["plan"]
    done = {x["file"]: x for x in res.get("claims", [])}
    for p in plan["claims"] if res.get("passed") else []:
        raw = claims[p["index"]]
        c = dict(raw=raw, lines=[], reasons=[])
        try:
            c.update(prepare(raw, sub, exe, ctx, tmp))
            ctx["seen_family"].add(c["fam_sha"])
            r = done.get(p["file"])
            if r is None or r["family_sha256"] != c["fam_sha"] or r["file_sha256"] != c["file_sha"]:
                raise CertError("the result does not match the family file as it is now")
            if r["tier"] == "VERIFIED":
                shards, _ = read_tasks(os.path.join(rdir, "tasks"), p["index"])
                cm = cc.combine(shards, p["method"], c["k"], c["t"])
                if cm["uncovered"] or cc.parse_shard(shards[0])["meta"]["family_sha256"] != c["fam_sha"]:
                    raise CertError("the shard outputs do not show an exact check of this family")
            if r["array_sha256"] and r["array_sha256"] in ctx["known_sha"] and not c["upgrade"]:
                raise CertError("duplicate: this array is already in the table")
            if r["tier"] == "SCREENED" and c.get("upgrade"):
                raise CertError("duplicate: this family is already SCREENED")
            c.update(tier=r["tier"], stamp=r["stamp"], check=r["check"], sha=r["array_sha256"],
                     method_text=r["method"], screen=r.get("screen"), screen_why=r.get("screen_why"))
            c["lines"] = describe(c) + ["%s: %s" % (c["tier"], c["check"])]
            c["passed"] = True
            results.append(c)
        except (CertError, ValueError, OSError) as e:
            ok = False; c["passed"] = False; c["reasons"].append(str(e))
        rep.append(c)
    text = report(slug, "Checked again on main against the table at this moment.", rep, ok)
    if ok and a.apply:
        n = write_rows(results, slug, ctx, today)
        text += "\nApplied: %d rows appended to `table/ca_table.csv` and listed in `table/certificates/CERTIFICATES.csv`.\n" % n
    elif a.apply:
        text += "\nNot applied: the submission did not pass.\n"
    write_out(a, slug, text, dict(slug=slug, passed=ok, applied=bool(ok and a.apply)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
