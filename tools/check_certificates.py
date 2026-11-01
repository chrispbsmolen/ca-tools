#!/usr/bin/env python3
"""check_certificates - check covering perfect hash family certificates and enter their arrays.

A certificate submission is a directory submissions/<slug>/ holding certificates.csv

    t,v,k,N,file,mode,source_detail,construction,builds_on,credit,notes

(builds_on as in submissions/README.md; files without that column are still read,
and get cphf-smc2006 plus the ids their construction text matches)

and the family files it names (the format of tools/cphf/cphfcheck.c: n lines of k integers,
each a vector of GF(v)^t in base v). mode is "full" (every t-set of columns checked), "fullfast" (the same answer, found by
projection hashing), "progression" (rows that are affine progressions are certified and the
check reduced by translation, see tools/cphf/README.md), "cyclic s"
(the symmetry col -> col + s is certified first, then every t-set with smallest column < s), and
may end in " affine" (every vector has first coordinate 1; the array then has n (v^t - v) + v
runs instead of n (v^t - 1) + 1). N must be the size the family gives.

For every claim this script runs tools/cphf/cphfcheck exactly (never by sampling), expands the
family to the covering array in the table's canonical form and hashes it as a stream (the array
is never written to disk, so a family for an array of many gigabytes is fine), and compares N
with the table. With --apply, and only when every claim passes, it copies each family to
table/certificates/, lists it in table/certificates/CERTIFICATES.csv and appends a VERIFIED
row (source S7) stamped "cphfcheck <tool hash> <date> <machine> (CPHF certificate, exact)".

Run by the maintainer (exact checks can take hours), not by the pull request check.
Usage: check_certificates.py SUBMISSION_DIR [--threads N] [--apply] [--builds-on VALUE]
"""
import argparse
import csv
import datetime
import hashlib
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

HEADER = ["t", "v", "k", "N", "file", "mode", "source_detail", "construction", "builds_on", "credit",
          "notes"]
# the header before builds_on (2026-11), still read; such claims get
# builds_on = cphf-smc2006 plus the ids their construction text matches
PREV_HEADER = ["t", "v", "k", "N", "file", "mode", "source_detail", "construction", "credit", "notes"]
SRC = os.path.join(HERE, "cphf", "cphfcheck.c")
MODE_RE = re.compile(r"^(full|fullfast|progression|cyclic (\d+))( affine)?$")


class CertError(Exception):
    pass


def build(tmp):
    exe = os.path.join(tmp, "cphfcheck")
    for cmd in (["cc", "-O3", "-fopenmp", "-o", exe, SRC, "-lm"],
                ["cc", "-O3", "-o", exe, SRC, "-lm"]):          # without OpenMP: one thread
        if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return exe
    raise SystemExit("could not build %s" % SRC)


def tool_hash():
    return hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:12]


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


def check_claim(raw, sub, exe, threads, ctx, tmp):
    raw["builds_on_value"], raw["builds_on_warnings"] = claim_builds_on(raw, ctx["refs"])
    for fld in ("file", "mode", "source_detail", "construction", "credit"):
        if not (raw.get(fld) or "").strip():
            raise CertError("certificates.csv field %s is empty" % fld)
    t, v, k, N = (int(raw[x]) for x in ("t", "v", "k", "N"))
    m = MODE_RE.match(raw["mode"].strip())
    if not m:
        raise CertError("mode %r is not 'full', 'fullfast', 'progression' or 'cyclic s', optionally "
                        "followed by ' affine'" % raw["mode"])
    affine = bool(m.group(3))
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
    mode = m.group(1).split()[0]
    args = [exe, fam, str(t), str(v)] + ([mode, str(threads)] if mode != "cyclic"
                                         else ["cyclic", m.group(2), str(threads)])
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    out = p.stdout.strip().splitlines()
    if p.returncode == 3:
        raise CertError("symmetry not certified: %s" % p.stderr.strip()[:300])
    if p.returncode == 4:
        raise CertError("checker internal consistency check failed (a bug, not a verdict): %s"
                        % " | ".join(out[-3:]))
    if p.returncode != 0:
        raise CertError("not a CPHF: %s" % " | ".join(out[-2:]))
    head = out[0]
    mm = re.search(r"n=(\d+) k=(\d+) q=(\d+) t=(\d+)", head)
    n, kk = int(mm.group(1)), int(mm.group(2))
    if kk != k:
        raise CertError("the family has %d columns, the claim says k=%d" % (kk, k))
    if affine and "affine" not in head:
        raise CertError("mode says affine but not every vector has first coordinate 1")
    want = n * (v ** t - v) + v if affine else n * (v ** t - 1) + 1
    if N != want:
        raise CertError("N=%d, but CPHF(%d; %d, %d, %d) gives %d" % (N, n, k, v, t, want))
    checked = [l for l in out if l.startswith("checked ")][0]
    rows, sha = stream_hash(exe, fam, t, v, affine, tmp)
    if rows != N:
        raise CertError("expanded array has %d runs, expected %d" % (rows, N))
    if sha in ctx["known_sha"]:
        raise CertError("duplicate: this array is already in the table")
    prev, _ = cs.best_known(ctx["table_rows"], t, v, k)
    comparison = ("exceeds_table" if prev is None or N < prev else
                  "equals_best" if N == prev else "above_table")
    return dict(t=t, v=v, k=k, N=N, n=n, fam=fam, fam_sha=hashlib.sha256(open(fam, "rb").read()).hexdigest(),
                sha=sha, checked=checked, mode=raw["mode"].strip(), comparison=comparison, prev=prev, raw=raw)


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
    a = ap.parse_args(argv)
    sub = a.submission.rstrip("/"); slug = os.path.basename(sub)
    path = os.path.join(sub, "certificates.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f); hdr = [h.strip() for h in next(rd)]
        if hdr not in (HEADER, PREV_HEADER):
            raise SystemExit("certificates.csv header must be %s" % ",".join(HEADER))
        claims = [dict(zip(hdr, r)) for r in rd if any(x.strip() for x in r)]
    if a.builds_on is not None:
        if hdr != PREV_HEADER:
            raise SystemExit("--builds-on is only for a certificates.csv without the builds_on column")
        for c in claims:
            c["builds_on"] = a.builds_on
    table_path = os.path.join(a.table_dir, "ca_table.csv")
    table_rows = list(csv.DictReader(open(table_path, newline="", encoding="utf-8")))
    ctx = dict(refs=bo.load(a.table_dir), table_rows=table_rows, known_sha={r["array_sha256"] for r in table_rows if r["array_sha256"]})
    stamp = "cphfcheck %s %s %s-%s" % (tool_hash(), datetime.date.today().isoformat(), platform.system(),
                                       platform.machine())
    results, ok = [], True
    with tempfile.TemporaryDirectory(prefix="cacert-") as tmp:
        exe = build(tmp)
        for raw in claims:
            print("checking %s ..." % raw.get("file"), file=sys.stderr, flush=True)
            try:
                r = check_claim(raw, sub, exe, a.threads, ctx, tmp); r["passed"] = True
                ctx["known_sha"].add(r["sha"])
                print("  PASS %s: %s; array sha256 %s; %s (previous best %s); builds on %s"
                      % (raw["file"], r["checked"], r["sha"][:12], r["comparison"], r["prev"],
                         raw["builds_on_value"]), flush=True)
                for w in raw["builds_on_warnings"]:
                    print("    note: builds_on: %s" % w, flush=True)
            except (CertError, ValueError, OSError) as e:
                r = dict(passed=False, raw=raw); ok = False
                print("  FAIL %s: %s" % (raw.get("file"), e), flush=True)
            results.append(r)
    if not ok:
        print("Not every claim passed; nothing applied."); return 1
    if not a.apply:
        print("Every claim passed. Run again with --apply to enter them."); return 0
    cdir = os.path.join(a.table_dir, "certificates"); clist = os.path.join(cdir, "CERTIFICATES.csv")
    today = datetime.date.today().isoformat()
    trows, crows = [], []
    for r in results:
        raw = r["raw"]
        name = "CPHF_%d_%d_%d_%d.txt" % (r["n"], r["k"], r["v"], r["t"])
        if os.path.exists(os.path.join(cdir, name)):
            name = "CPHF_%d_%d_%d_%d_%s.txt" % (r["n"], r["k"], r["v"], r["t"], r["fam_sha"][:8])
        shutil.copyfile(r["fam"], os.path.join(cdir, name))
        family = "CPHF(%d; %d, %d, %d)%s" % (r["n"], r["k"], r["v"], r["t"], ", affine" if r["mode"].endswith("affine") else "")
        rstamp = stamp + " (CPHF certificate, exact)"
        notes = ["credit: " + raw["credit"].strip(),
                 "certificate table/certificates/%s, %s, %s" % (name, family, r["mode"]),
                 "from submissions/%s/certificates.csv" % slug]
        if raw.get("notes", "").strip():
            notes.append(raw["notes"].strip())
        trows.append([r["t"], r["v"], r["k"], r["N"], "VERIFIED", cs.SOURCE_ID, raw["source_detail"].strip(),
                      slug, r["sha"], rstamp, today, "; ".join(notes), "", "", raw["construction"].strip(),
                      raw["builds_on_value"]])
        crows.append([name, r["t"], r["v"], r["k"], r["N"], family, r["fam_sha"], r["sha"],
                      "%s: %s" % (stamp, r["checked"])])
    eol = "\r\n" if b"\r\n" in open(table_path, "rb").read(4096) else "\n"
    cs.append_text(table_path, cs.table_csv_text(trows), eol)
    cs.append_text(clist, cs.manifest_csv_text(crows), "\n")
    print("Applied %d certificate rows." % len(trows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
