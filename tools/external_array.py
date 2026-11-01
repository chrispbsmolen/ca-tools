#!/usr/bin/env python3
"""external_array - check and enter arrays too large for the repository.

An array above the 50 MiB per-file limit stays in a public deposit (a Zenodo
record or a release of this repository). The submission names it in
submissions/<slug>/external.csv:

    t,v,k,N,location,sha256,source_detail,construction,credit,notes

location is an https URL of the file, or of a zip archive followed by
"::" and the member name (https://zenodo.org/records/1/files/a.zip::x/CA.txt).
sha256 is the SHA-256 of the canonical form (the form check_submission.py
hashes: 0-based, single spaces, NA for don't-care, LF after every row).

For every claim this script downloads the file, rebuilds the canonical form
as a stream (memory stays small whatever the size), compares the hash, runs
ca_verify at strength t (in full under the budget, otherwise on the same
deterministic column windows as check_submission.py) and compares N with the
table. With --apply, and only when every claim passes, it appends the rows to
table/ca_table.csv (tier VERIFIED or SCREENED, source S7, notes naming the
location) and to table/EXTERNAL.csv. The array itself is not copied.

It is run by the maintainer (it downloads large files), not by the pull
request check. Standard library only.

Usage:
  external_array.py SUBMISSION_DIR [--apply] [--threads N] [--budget-minutes M]
                    [--keep DIR] [--local-root DIR]
  external_array.py --fetch LOCATION SHA256 OUT   (download, canonicalize, verify the hash)
--local-root (tests only) reads locations of the form local:<path> under DIR.
"""
import argparse
import csv
import datetime
import hashlib
import math
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_submission as cs  # noqa: E402

EXTERNAL_HEADER = ["sha256", "t", "v", "k", "N", "bytes", "location", "status",
                   "source_detail", "verify_stamp"]
EXT_CLAIMS_HEADER = ["t", "v", "k", "N", "location", "sha256", "source_detail",
                     "construction", "credit", "notes"]
ALLOWED_HOSTS = ("zenodo.org", "github.com", "objects.githubusercontent.com")
LOCATION_RE = re.compile(r"^https://([A-Za-z0-9.-]+)/[^\s]+$")


class ExtError(Exception):
    pass


def check_location(loc, local_root=None):
    base, _, member = loc.partition("::")
    if local_root and base.startswith("local:"):
        return base, member
    m = LOCATION_RE.match(base)
    if not m:
        raise ExtError("location %r is not an https URL" % loc)
    host = m.group(1).lower()
    if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        raise ExtError("location host %s is not one of %s" % (host, ", ".join(ALLOWED_HOSTS)))
    return base, member


def download(loc, workdir, local_root=None):
    """Returns the path of the raw array file (extracted from the zip if needed)."""
    base, member = check_location(loc, local_root)
    raw = os.path.join(workdir, "download")
    if local_root and base.startswith("local:"):
        shutil.copyfile(os.path.join(local_root, base[len("local:"):]), raw)
    else:
        req = urllib.request.Request(base, headers={"User-Agent": "ca-tools external_array"})
        with urllib.request.urlopen(req, timeout=120) as r, open(raw, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    if not member:
        return raw
    if not zipfile.is_zipfile(raw):
        raise ExtError("location names member %r but the file is not a zip archive" % member)
    out = os.path.join(workdir, "member")
    with zipfile.ZipFile(raw) as z:
        try:
            info = z.getinfo(member)
        except KeyError:
            raise ExtError("zip archive has no member %r" % member)
        with z.open(info) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
    os.remove(raw)
    return out


def _tokens(line):
    return [s for s in cs.TOKEN_SPLIT.split(line) if s]


def canonicalize_stream(src, v, out):
    """Two passes over src, the rules of check_submission.parse_array, writing
    the canonical form to out. Returns (N, k, sha256, shifted)."""
    width, nrow, lo, hi = None, 0, None, None
    with open(src, "r", encoding="utf-8", errors="strict") as f:
        for lineno, line in enumerate(f, 1):
            toks = _tokens(line)
            if not toks:
                continue
            for tok in toks:
                if tok in cs.WILDCARD_TOKENS or tok.upper() == "NA":
                    continue
                if not re.fullmatch(r"-?[0-9]+", tok):
                    raise ExtError("line %d: entry %r is not a symbol or a don't-care mark"
                                   % (lineno, tok[:20]))
                val = int(tok)
                if val < 0:
                    raise ExtError("line %d: negative symbol %d" % (lineno, val))
                lo = val if lo is None or val < lo else lo
                hi = val if hi is None or val > hi else hi
            if width is None:
                width = len(toks)
            elif len(toks) != width:
                raise ExtError("line %d: ragged row, %d entries where the first row has %d"
                               % (lineno, len(toks), width))
            nrow += 1
    if nrow == 0:
        raise ExtError("array file holds no rows")
    if lo is None:
        raise ExtError("every entry of the array is a don't-care")
    if lo == 0 and hi <= v - 1:
        shift = 0
    elif lo >= 1 and hi == v:
        shift = 1
    elif hi > v or (lo == 0 and hi == v):
        raise ExtError("symbols out of range for v=%d (saw %d..%d)" % (v, lo, hi))
    else:
        raise ExtError("symbol range %d..%d is ambiguous for v=%d; write the array 0-based"
                       % (lo, hi, v))
    h = hashlib.sha256()
    with open(src, "r", encoding="utf-8") as f, open(out, "w", encoding="utf-8", newline="\n") as g:
        for line in f:
            toks = _tokens(line)
            if not toks:
                continue
            cells = []
            for tok in toks:
                if tok in cs.WILDCARD_TOKENS or tok.upper() == "NA":
                    cells.append("NA")
                else:
                    cells.append(str(int(tok) - shift))
            s = " ".join(cells) + "\n"
            if len(s) > cs.CA_VERIFY_MAX_LINE:
                raise ExtError("rows are too long for ca_verify's line buffer (k=%d)" % width)
            g.write(s)
            h.update(s.encode("utf-8"))
    return nrow, width, h.hexdigest(), bool(shift)


def screen_stream(canon, k, t, v, sha, ca_verify, threads, windows, width, stop_at, tmp):
    wins = cs.screen_windows(k, sha, windows, width)
    sub = os.path.join(tmp, "window.txt")
    for wi, cols in enumerate(wins, 1):
        left = stop_at - time.monotonic()
        if left <= 0:
            raise ExtError("screen did not finish: %d of %d windows done" % (wi - 1, len(wins)))
        with open(canon, "r", encoding="utf-8") as f, open(sub, "w", encoding="utf-8", newline="\n") as g:
            for line in f:
                cells = line.split()
                g.write(" ".join(cells[c] for c in cols) + "\n")
        r = cs.run_ca_verify(ca_verify, sub, t, v, threads, left)
        if r["outcome"] == "gaps":
            raise ExtError("NOT A COVERING ARRAY at strength %d: screen window %d of %d has gaps: %s"
                           % (t, wi, len(wins), r["summary"]))
        if r["outcome"] != "verified":
            raise ExtError("screen window %d of %d: %s" % (wi, len(wins),
                           "ran out of budget" if r["outcome"] == "timeout" else r["stderr"] or r["summary"]))
    return dict(windows=len(wins), width=width, seed=sha[:16])


def check_claim(raw, ctx, tmp):
    for fld in ("location", "sha256", "source_detail", "credit", "construction"):
        if not (raw.get(fld) or "").strip():
            raise ExtError("external.csv field %s is empty" % fld)
    t = int(raw["t"]); v = int(raw["v"]); k = int(raw["k"]); N = int(raw["N"])
    if t < 1 or t > k or v < 2 or v > cs.CA_VERIFY_MAX_V:
        raise ExtError("t, v, k out of range")
    want = raw["sha256"].strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", want):
        raise ExtError("sha256 %r is not 64 hex digits" % want)
    if want in ctx["known_sha"]:
        raise ExtError("duplicate: this array is already recorded in the table")
    if want in ctx["seen_sha"]:
        raise ExtError("duplicate: the same sha256 is claimed twice in this submission")
    ctx["seen_sha"].add(want)
    path = download(raw["location"].strip(), tmp, ctx["local_root"])
    nbytes = os.path.getsize(path)
    canon = os.path.join(tmp, "canon.txt")
    nrow, ncol, sha, shifted = canonicalize_stream(path, v, canon)
    os.remove(path)
    if nrow != N or ncol != k:
        raise ExtError("dimension mismatch: the file has %d rows x %d columns, the claim says N=%d, k=%d"
                       % (nrow, ncol, N, k))
    if sha != want:
        raise ExtError("sha256 of the canonical form is %s, the claim says %s" % (sha, want))
    prev, _ = cs.best_known(ctx["table_rows"], t, v, k)
    comparison = ("exceeds_table" if prev is None or N < prev else
                  "equals_best" if N == prev else "above_table")
    work = math.comb(k, t) * v ** t
    budget = ctx["budget"]
    status, screen, secs = None, None, {}
    mode = "screen" if (k > ctx["window"] and work > ctx["threshold"]) else "full"
    if mode == "full":
        r = cs.run_ca_verify(ctx["ca_verify"], canon, t, v, ctx["threads"], budget)
        secs["verify"] = r["seconds"]
        if r["outcome"] == "verified":
            status = "verified"
        elif r["outcome"] == "gaps":
            raise ExtError("NOT A COVERING ARRAY at strength %d: %s" % (t, r["summary"]))
        elif r["outcome"] == "error":
            raise ExtError("ca_verify error: %s" % (r["stderr"] or r["summary"]))
        elif k <= ctx["window"]:
            raise ExtError("full verification did not finish within the budget and the array is too narrow to screen")
        else:
            mode = "screen"
    if mode == "screen":
        s0 = time.monotonic()
        screen = screen_stream(canon, k, t, v, sha, ctx["ca_verify"], ctx["threads"],
                               ctx["windows"], ctx["window"], s0 + budget, tmp)
        secs["screen"] = time.monotonic() - s0
        status = "screened"
    if ctx["keep"]:
        shutil.copyfile(canon, os.path.join(ctx["keep"], "CA_%d_%d_%d_%d_%s.txt" % (N, t, k, v, sha[:8])))
    os.remove(canon)
    return dict(t=t, v=v, k=k, N=N, sha256=sha, bytes=nbytes, status=status, screen=screen,
                comparison=comparison, previous_best=prev, shifted=shifted, seconds=secs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("submission", nargs="?")
    ap.add_argument("--fetch", nargs=3, metavar=("LOCATION", "SHA256", "OUT"))
    ap.add_argument("--table-dir", default=os.path.join(cs.REPO, "table"))
    ap.add_argument("--ca-verify", default=os.path.join(cs.REPO, "ca_verify"))
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--budget-minutes", type=float, default=60.0)
    ap.add_argument("--screen-threshold", type=float, default=1e10)
    ap.add_argument("--windows", type=int, default=20)
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--keep", help="also keep the canonical arrays in this directory")
    ap.add_argument("--local-root", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    if a.fetch:
        loc, want, out = a.fetch
        with tempfile.TemporaryDirectory(prefix="caext-") as tmp:
            raw = download(loc, tmp, a.local_root)
            v = 127
            # v is not known here: canonical form does not depend on v except for the
            # 1-based shift, so read v from the table row
            rows = [r for r in csv.DictReader(open(os.path.join(a.table_dir, "EXTERNAL.csv"), newline=""))
                    if r["sha256"] == want.lower()]
            if not rows:
                raise SystemExit("no EXTERNAL.csv entry with sha256 %s" % want)
            v = int(rows[0]["v"])
            n, k, sha, _ = canonicalize_stream(raw, v, out)
        if sha != want.lower():
            os.remove(out)
            raise SystemExit("sha256 mismatch: got %s, expected %s" % (sha, want))
        print("OK %s (%d x %d) sha256 %s" % (out, n, k, sha))
        return 0

    if not a.submission:
        ap.error("give a submission directory, or --fetch")
    sub = a.submission.rstrip("/")
    slug = os.path.basename(sub)
    path = os.path.join(sub, "external.csv")
    if not os.path.isfile(path):
        raise SystemExit("%s not found" % path)
    if not (os.path.isfile(a.ca_verify) and os.access(a.ca_verify, os.X_OK)):
        raise SystemExit("ca_verify not built at %s (cc -O3 -pthread -o ca_verify ca_verify.c)" % a.ca_verify)
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        if [h.strip() for h in hdr] != EXT_CLAIMS_HEADER:
            raise SystemExit("external.csv header must be %s" % ",".join(EXT_CLAIMS_HEADER))
        claims = [dict(zip(EXT_CLAIMS_HEADER, rec)) for rec in rd if any(x.strip() for x in rec)]
    table_path = os.path.join(a.table_dir, "ca_table.csv")
    table_rows = list(csv.DictReader(open(table_path, newline="", encoding="utf-8")))
    ext_path = os.path.join(a.table_dir, "EXTERNAL.csv")
    known = {r["array_sha256"] for r in table_rows if r.get("array_sha256")}
    ctx = dict(table_rows=table_rows, known_sha=known, ca_verify=a.ca_verify, threads=a.threads,
               budget=a.budget_minutes * 60, threshold=a.screen_threshold, windows=a.windows,
               window=a.window, keep=a.keep, local_root=a.local_root, seen_sha=set())
    if a.keep:
        os.makedirs(a.keep, exist_ok=True)
    stamp = "external_array %s %s %s" % (cs.git_short_sha(), datetime.date.today().isoformat(),
                                         cs.machine_tag())
    results, ok = [], True
    for i, raw in enumerate(claims, 1):
        print("claim %d: %s" % (i, raw.get("location", "")[:100]), file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix="caext-") as tmp:
            try:
                res = check_claim(raw, ctx, tmp)
                res["passed"] = True
            except (ExtError, ValueError, UnicodeDecodeError, OSError, zipfile.BadZipFile) as e:
                res = dict(passed=False, reason=str(e))
                ok = False
        res["raw"] = raw
        results.append(res)
        print("  %s" % ("PASS %s %s (previous best %s)" % (res["status"], res["comparison"], res["previous_best"])
                        if res["passed"] else "FAIL " + res["reason"]), flush=True)
    if not ok:
        print("Not every claim passed; nothing applied.")
        return 1
    if a.apply:
        today = datetime.date.today().isoformat()
        snap = slug                        # as check_submission.py without --pr
        trows, erows = [], []
        for r in results:
            raw = r["raw"]
            tier = "VERIFIED" if r["status"] == "verified" else "SCREENED"
            # not "submission <slug>": table-page.yml reads that as "claims.csv applied"
            notes = ["external array: %s" % raw["location"].strip(),
                     "from submissions/%s/external.csv" % slug]
            if r["status"] == "screened":
                s = r["screen"]
                notes.append("SCREENED, not exhaustively verified: %d random windows of %d columns "
                             "verified in full, seed %s" % (s["windows"], s["width"], s["seed"]))
            if r["comparison"] == "above_table":
                notes.append("above table best, not an improvement")
            if raw.get("notes", "").strip():
                notes.append(raw["notes"].strip())
            trows.append([r["t"], r["v"], r["k"], r["N"], tier, cs.SOURCE_ID,
                          raw["source_detail"].strip(), snap, r["sha256"], stamp, today,
                          "; ".join(notes), "", "", raw["construction"].strip()])
            erows.append([r["sha256"], r["t"], r["v"], r["k"], r["N"], r["bytes"],
                          raw["location"].strip(), r["status"], raw["source_detail"].strip(), stamp])
        eol = "\r\n" if b"\r\n" in open(table_path, "rb").read(4096) else "\n"
        cs.append_text(table_path, cs.table_csv_text(trows), eol)
        if not os.path.isfile(ext_path):
            with open(ext_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\n").writerow(EXTERNAL_HEADER)
        with open(ext_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f, lineterminator="\n").writerows(erows)
        print("Applied %d rows to %s and %s." % (len(trows), table_path, ext_path))
    else:
        print("Every claim passed. Run again with --apply to enter them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
