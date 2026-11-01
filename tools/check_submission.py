#!/usr/bin/env python3
"""check_submission - verify a covering array submission against the table.

A submission is a directory submissions/<slug>/ holding claims.csv
(header t,v,k,N,file,source_detail,construction,credit,notes) and the
array files it
names. For every claim this script parses the array, checks its shape
and symbols, canonicalizes it exactly as table/verify_pipeline.R does,
hashes it, rejects duplicates, runs ca_verify at strength t under a
wall-clock budget (or a column-window screen for very large checks),
and compares N with the best known N in table/ca_table.csv.

It writes report.md, summary.json and, when every claim passes, the
rows to append (ca_table_rows.csv, manifest_rows.csv) and the
canonical array files (arrays/) into the output directory. With
--apply it also appends the rows to the table and copies the arrays
into table/arrays; without --apply nothing under the table directory
is touched.

Standard library only. Exit status: 0 every claim passed, 1 otherwise,
2 usage or setup error.

Usage:
  check_submission.py SUBMISSION_DIR [options]
  check_submission.py --selftest [--table-dir DIR]
"""
import argparse
import collections
import csv
import datetime
import gzip
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "table"))
from ca_table import counted  # noqa: E402  (the one definition of the counted rows)
sys.path.insert(0, os.path.join(REPO, "tools"))
import builds_on  # noqa: E402  (references.csv and the builds_on field)

CLAIMS_HEADER = ["t", "v", "k", "N", "file", "source_detail", "construction",
                 "builds_on", "credit", "notes"]
# the header before builds_on (2026-11); accepted only for the submissions in
# submissions/BUILDS_ON_EXEMPT.txt, opened before the field existed, whose
# builds_on the maintainer fills in
PREV_CLAIMS_HEADER = ["t", "v", "k", "N", "file", "source_detail", "construction",
                      "credit", "notes"]
OLD_CLAIMS_HEADER = ["t", "v", "k", "N", "file", "source_detail", "credit", "notes"]
TABLE_HEADER = ["t", "v", "k", "N", "tier", "source_id", "source_detail",
                "snapshot_id", "array_sha256", "verify_stamp", "entered",
                "notes", "lb", "lb_evidence", "construction", "builds_on",
                "family_sha256"]
# family_sha256 (since 2026-11-02): the identity of the covering perfect hash family that gives a
# certificate row (tools/cphf_cert.py); empty in every row this script writes
MANIFEST_HEADER = ["file", "t", "v", "k", "N", "status", "sha256",
                   "source_id", "source_detail", "verify_stamp", "constant_rows"]
SOURCE_ID = "S7"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")
# Size limits. GitHub refuses files over 100 MiB and warns above 50 MiB
# (docs.github.com, "About large files on GitHub"); the table stores
# every accepted array, so one submission must stay well inside that.
# Larger arrays go by arrangement (submissions/README.md, "Size limits").
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_SUBMISSION_BYTES = 200 * 1024 * 1024
# Arrays above this size (canonical text) are stored in table/arrays gzip-compressed (CA_N_t_k_v.txt.gz,
# gzip header time 0, so the file is reproducible); the MANIFEST hash stays the hash of the text.
GZIP_ABOVE = int(os.environ.get("CA_GZIP_ABOVE", 1024 * 1024))
CA_VERIFY_MAX_LINE = 65000   # ca_verify reads lines into a 64 KiB buffer
CA_VERIFY_MAX_V = 127        # ca_verify stores symbols as int8


class ClaimError(Exception):
    """A problem that fails one claim; the message goes into the report."""


# ---------------------------------------------------------------------------
# Parsing and canonical form
# ---------------------------------------------------------------------------

WILDCARD_TOKENS = {"-", "*", "x", "X", "-1"}
TOKEN_SPLIT = re.compile(r"[ \t,\r\n]+")


def parse_array(path, v):
    """Read an array file with the conventions of ca_verify.c.

    Entries are separated by spaces, tabs or commas; blank lines are
    skipped; NA (any case), '-', '*', 'x', 'X' and -1 are don't-care.
    Symbols are 0..v-1 or 1..v. Unlike ca_verify, any other token is an
    error instead of being skipped. Returns (rows, shifted) with rows a
    list of lists of int (None for don't-care), already 0-based.
    """
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise ClaimError("cannot read array file: %s" % e)
    if size > MAX_FILE_BYTES:
        raise ClaimError("array file is %.1f MiB, above the %d MiB limit per "
                         "file (see \"Size limits\" in submissions/README.md)"
                         % (size / 1048576.0, MAX_FILE_BYTES // 1048576))
    rows = []
    width = None
    lo, hi = None, None
    with open(path, "r", encoding="utf-8", errors="strict") as f:
        for lineno, line in enumerate(f, 1):
            toks = [s for s in TOKEN_SPLIT.split(line) if s]
            if not toks:
                continue
            row = []
            for tok in toks:
                if tok in WILDCARD_TOKENS or tok.upper() == "NA":
                    row.append(None)
                    continue
                if not re.fullmatch(r"-?[0-9]+", tok):
                    raise ClaimError("line %d: entry %r is not a symbol or a "
                                     "don't-care mark" % (lineno, tok[:20]))
                val = int(tok)
                if val < 0:
                    raise ClaimError("line %d: negative symbol %d (only -1 "
                                     "is allowed, as don't-care)" % (lineno, val))
                row.append(val)
                lo = val if lo is None or val < lo else lo
                hi = val if hi is None or val > hi else hi
            if width is None:
                width = len(row)
            elif len(row) != width:
                raise ClaimError("line %d: ragged row, %d entries where the "
                                 "first row has %d" % (lineno, len(row), width))
            rows.append(row)
    if not rows:
        raise ClaimError("array file holds no rows")
    shifted = False
    if lo is None:
        raise ClaimError("every entry of the array is a don't-care")
    elif lo == 0 and hi <= v - 1:
        pass                              # 0-based
    elif lo >= 1 and hi == v:
        shifted = True                    # 1-based, as ca_verify auto-shifts
    elif hi > v or (lo == 0 and hi == v):
        raise ClaimError("symbols out of range for v=%d (saw %d..%d)" % (v, lo, hi))
    else:
        raise ClaimError("symbol range %d..%d is ambiguous for v=%d (neither 0 "
                         "nor %d occurs); write the array 0-based" % (lo, hi, v, v))
    if shifted:
        rows = [[None if x is None else x - 1 for x in r] for r in rows]
    return rows, shifted


def canon_serialize(rows):
    """Exactly verify_pipeline.R::canon_serialize on a 0-based matrix:
    one run per line, space separated, NA for don't-care, newline after
    every line including the last, no header, no trailing whitespace."""
    return "".join(" ".join("NA" if x is None else str(x) for x in r) + "\n"
                   for r in rows)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_of_file(path, v):
    rows, _ = parse_array(path, v)
    text = canon_serialize(rows)
    return rows, text, sha256_text(text)


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------

def load_table(table_dir):
    with open(os.path.join(table_dir, "ca_table.csv"), newline="",
              encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if reader.fieldnames != TABLE_HEADER:
            raise SystemExit("table/ca_table.csv header is %s, this checker "
                             "writes %s" % (reader.fieldnames, TABLE_HEADER))
    with open(os.path.join(table_dir, "MANIFEST.csv"), newline="",
              encoding="utf-8") as f:
        mreader = csv.DictReader(f)
        manifest = list(mreader)
        if mreader.fieldnames != MANIFEST_HEADER:
            raise SystemExit("table/MANIFEST.csv header is %s, this checker "
                             "writes %s" % (mreader.fieldnames, MANIFEST_HEADER))
    return rows, manifest


# ---------------------------------------------------------------------------
# Similarity (disguised copies) and prior work to cite
# ---------------------------------------------------------------------------

FP_MAX_WORK = 4 * 10**7     # entries examined by the fingerprint, at most


def fingerprint(rows):
    """A fingerprint of an array that does not change when its rows are
    reordered, its columns are reordered, or the symbols of any column are
    renamed: the sorted symbol counts of every column, the sorted cell counts
    of every pair of columns, and the distribution of Hamming distances
    between rows. Equal fingerprints mean the arrays are very likely the same
    array relabelled; it is a flag for the maintainer, not a proof. Returns
    None when the array is too large to fingerprint within FP_MAX_WORK."""
    n, k = len(rows), len(rows[0])
    pair_work = k * (k - 1) // 2 * n
    dist_work = n * (n - 1) // 2 * k
    if pair_work > FP_MAX_WORK:
        return None
    cols = [tuple(-1 if x is None else x for x in c) for c in zip(*rows)]
    colprof = sorted(tuple(sorted(collections.Counter(c).values())) for c in cols)
    pairprof = []
    for i in range(k):
        ci = cols[i]
        for j in range(i + 1, k):
            pairprof.append(tuple(sorted(collections.Counter(zip(ci, cols[j])).values())))
    pairprof.sort()
    parts = [str(n), str(k), repr(colprof), repr(pairprof)]
    if dist_work <= FP_MAX_WORK:
        rr = [tuple(-1 if x is None else x for x in r) for r in rows]
        dist = collections.Counter()
        for a in range(n):
            ra = rr[a]
            for b in range(a + 1, n):
                dist[sum(1 for x, y in zip(ra, rr[b]) if x != y)] += 1
        parts.append(repr(sorted(dist.items())))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def read_table_array(table_dir, name, v):
    path = os.path.join(table_dir, "arrays", name)
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return [[None if x == "NA" else int(x) for x in line.split()] for line in f if line.strip()]
    return parse_array(path, v)[0]


def similar_known(rows, v, ctx):
    """Known arrays with the same N, k and v whose fingerprint equals this
    array's: arrays on file in the table, and the arrays withdrawn on
    2026-10-27 (table/withdrawn_fingerprints.csv). Returns a list of texts."""
    n, k = len(rows), len(rows[0])
    cand_table = [m for m in ctx["manifest"] if int(m["v"]) == v and int(m["k"]) == k and int(m["N"]) == n]
    cand_wd = [w for w in ctx["withdrawn_fp"] if int(w["v"]) == v and int(w["k"]) == k and int(w["N"]) == n]
    if not cand_table and not cand_wd:
        return [], "no known array with the same N, k and v"
    fp = fingerprint(rows)
    if fp is None:
        return [], ("%d known arrays have the same N, k and v, but the array is too large "
                    "for the fingerprint" % (len(cand_table) + len(cand_wd)))
    found = []
    for m in cand_table:
        try:
            other = fingerprint(read_table_array(ctx["table_dir"], m["file"], v))
        except (OSError, ClaimError, ValueError):
            continue
        if other == fp:
            found.append("table/arrays/%s (%s)" % (m["file"], m["source_detail"]))
    for w in cand_wd:
        if w["fingerprint"] == fp:
            found.append("withdrawn array %s (%s)" % (w["file"], w["source_detail"]))
    checked = "compared by fingerprint with %d known arrays of the same N, k and v" % (
        len(cand_table) + len(cand_wd))
    return found, checked


def load_withdrawn_fp(table_dir):
    path = os.path.join(table_dir, "withdrawn_fingerprints.csv")
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_references(table_dir):
    return builds_on.load(table_dir)


def exempt_slugs():
    path = os.path.join(REPO, "submissions", "BUILDS_ON_EXEMPT.txt")
    if not os.path.isfile(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}


def cite_text(cl, ctx):
    """Prior work to cite for this claim: the source of the entry it is
    compared with, any reference whose pattern matches that entry or the
    claim's own construction and source, and the table itself."""
    out = []
    r = cl.get("previous_row")
    texts = []
    if r is not None:
        if r["source_id"] == "S1":
            out.append("the previous best is an entry of the Colbourn tables (November 2024 "
                       "status, preserved in the CAs package as colbournBigFrame), labelled "
                       "\"%s\"" % r["construction"])
        elif r.get("snapshot_id", "").startswith(("doi:", "arXiv:")):
            out.append("the previous best is from %s" % r["snapshot_id"])
        else:
            out.append("the previous best is a %s row of this table (%s, entered %s)"
                       % (r["tier"], r["source_detail"], r["entered"]))
        texts.append(r.get("construction", "") + " " + r.get("source_detail", "") + " " + r.get("notes", ""))
    refs = ctx["references"]
    ids = list(cl.get("builds_on_ids") or [])
    if r is not None:
        for rid in (r.get("builds_on") or "").split(";"):
            if rid in refs and rid not in ids:
                ids.append(rid)
    for rid in ids:
        out.append(builds_on.citation(rid, refs))
    for link in cl.get("builds_on_new") or []:
        out.append("the method of this submission, described at %s" % link)
    out.append("this table: C. Smolen, ca-tools, https://github.com/chrispbsmolen/ca-tools, "
               "with the commit used")
    return out


def best_known(rows, t, v, k):
    """Stair-step lookup over the counted rows (table/ca_table.py counted():
    CITED and VERIFIED, less retracted rows): the minimum N over rows with the
    same t and v and k' >= k. Returns (N, row) or (None, None)."""
    best, best_row = None, None
    for r in counted(rows):
        if int(r["t"]) != t or int(r["v"]) != v or int(r["k"]) < k:
            continue
        n = int(float(r["N"]))
        if best is None or n < best:
            best, best_row = n, r
    return best, best_row


# ---------------------------------------------------------------------------
# Running ca_verify
# ---------------------------------------------------------------------------

MISSING_RE = re.compile(r"missing: columns \(([0-9,]+)\) tuple \(([0-9,]+)\)")


def run_ca_verify(ca_verify, path, t, v, threads, timeout):
    """Returns dict(outcome=verified|gaps|error|timeout, seconds, missing,
    summary, stderr)."""
    start = time.monotonic()
    try:
        p = subprocess.run([ca_verify, path, str(t), str(v), str(threads)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=max(1.0, timeout))
    except subprocess.TimeoutExpired:
        return dict(outcome="timeout", seconds=time.monotonic() - start,
                    missing=[], summary="", stderr="")
    secs = time.monotonic() - start
    out = p.stdout.strip().splitlines()
    missing = []
    for line in out:
        m = MISSING_RE.search(line)
        if m:
            missing.append(([int(c) for c in m.group(1).split(",")],
                            [int(s) for s in m.group(2).split(",")]))
    outcome = {0: "verified", 1: "gaps"}.get(p.returncode, "error")
    return dict(outcome=outcome, seconds=secs, missing=missing,
                summary=out[0] if out else "", stderr=p.stderr.strip())


def screen_windows(k, sha, count, width):
    """Deterministic random column windows, seeded from the array's hash so
    anyone can rerun exactly the same screen."""
    rng = random.Random(int(sha[:16], 16))
    return [sorted(rng.sample(range(k), width)) for _ in range(count)]


# ---------------------------------------------------------------------------
# Checking one claim
# ---------------------------------------------------------------------------

def fmt_secs(s):
    return "%.1f s" % s if s < 120 else "%.1f min" % (s / 60.0)


def int_field(row, name, lo, hi=None):
    raw = (row.get(name) or "").strip()
    if not re.fullmatch(r"[0-9]+", raw):
        raise ClaimError("claims.csv field %s=%r is not a whole number" % (name, raw))
    val = int(raw)
    if val < lo or (hi is not None and val > hi):
        raise ClaimError("claims.csv field %s=%d is out of range" % (name, val))
    return val


def check_claim(cl, ctx, deadline):
    """Fill cl (a dict) with the outcome of checking one claim."""
    sub = ctx["subdir"]
    raw = cl["raw"]
    cl.update(passed=False, status="failed", comparison=None, reasons=[],
              notes_out=[], uncovered=None, seconds={}, sha256=None,
              constant_rows=None)
    t0 = time.monotonic()
    try:
        for fld in ("file", "source_detail", "credit"):
            if not (raw.get(fld) or "").strip():
                raise ClaimError("claims.csv field %s is empty" % fld)
        if not (raw.get("construction") or "").strip():
            raise ClaimError("claims.csv field construction is empty: name the "
                             "construction or search that produced the array "
                             "(write 'unknown' if it is not known)")
        for fld in CLAIMS_HEADER:
            if any(ch in (raw.get(fld) or "") for ch in "\r\n"):
                raise ClaimError("claims.csv field %s contains a line break" % fld)
        if "builds_on" in raw:
            norm, errs, warns, links = builds_on.check(raw["builds_on"], raw["construction"],
                                                       ctx["references"])
            if errs:
                sug = builds_on.suggest(raw["construction"], ctx["references"])
                raise ClaimError("builds_on: %s%s" % ("; ".join(errs),
                                 (" (suggested from the construction text: %s)" % ";".join(sug))
                                 if sug else ""))
            cl["builds_on"] = norm
            cl["builds_on_ids"] = [x for x in norm.split(";") if x in ctx["references"]]
            cl["builds_on_new"] = links
            for w in warns:
                cl["notes_out"].append("builds_on: " + w)
            if links:
                cl["notes_out"].append("builds_on names a new method (%s); the maintainer "
                                       "confirms it before the merge" % ", ".join(links))
        else:
            cl["builds_on"] = ""
            cl["notes_out"].append("builds_on: not given (submission opened before the field "
                                   "existed); the maintainer fills it in; suggested from the "
                                   "construction text: %s"
                                   % (";".join(builds_on.suggest(raw["construction"],
                                                                 ctx["references"])) or "none"))
        t = int_field(raw, "t", 1, 31)
        v = int_field(raw, "v", 2, CA_VERIFY_MAX_V)
        k = int_field(raw, "k", 1)
        N = int_field(raw, "N", 1)
        cl.update(t=t, v=v, k=k, N=N)
        if t > k:
            raise ClaimError("strength t=%d exceeds k=%d" % (t, k))
        if v ** t > (1 << 40):
            raise ClaimError("v^t is too large for ca_verify")
        fname = raw["file"].strip()
        if not SAFE_NAME.match(fname) or fname == "claims.csv":
            raise ClaimError("file name %r is not a plain file name in the "
                             "submission directory" % fname)
        path = os.path.join(sub, fname)
        if os.path.islink(path) or not os.path.isfile(path):
            raise ClaimError("array file %s is missing (or is not a regular file)"
                             % fname)

        # parse, shape, canonical form, hash
        rows, shifted = parse_array(path, v)
        nrow, ncol = len(rows), len(rows[0])
        if nrow != N or ncol != k:
            raise ClaimError("dimension mismatch: the file has %d rows x %d "
                             "columns, the claim says N=%d, k=%d"
                             % (nrow, ncol, N, k))
        if shifted:
            cl["notes_out"].append("symbols read as 1..v and shifted to 0-based")
        text = canon_serialize(rows)
        sha = sha256_text(text)
        cl["sha256"] = sha
        cl["canon_text"] = text
        if max(len(line) for line in text.split("\n")) > CA_VERIFY_MAX_LINE:
            raise ClaimError("rows are too long for ca_verify's line buffer "
                             "(k=%d)" % k)

        # duplicates
        if sha in ctx["manifest_sha"]:
            raise ClaimError("duplicate: this array is already in the table as "
                             "table/arrays/%s (sha256 %s)"
                             % (ctx["manifest_sha"][sha], sha))
        if sha in ctx["table_sha"]:
            r = ctx["table_sha"][sha]
            raise ClaimError("duplicate: this array is already recorded in "
                             "ca_table.csv (t=%s v=%s k=%s N=%s, %s, sha256 %s)"
                             % (r["t"], r["v"], r["k"], r["N"], r["source_detail"], sha))
        if sha in ctx["seen_sha"]:
            raise ClaimError("duplicate: same array as %s in this submission"
                             % ctx["seen_sha"][sha])
        ctx["seen_sha"][sha] = fname

        # disguised copies: same array with rows, columns or symbols permuted
        found, checked = similar_known(rows, v, ctx)
        cl["similar"] = found
        cl["similar_checked"] = checked

        # table comparison (done before verification so the report has it
        # even when verification fails)
        prev, prev_row = best_known(ctx["table_rows"], t, v, k)
        cl["previous_best"] = prev
        cl["previous_row"] = prev_row
        if prev is None:
            cl["comparison"] = "exceeds_table"
            cl["notes_out"].append("no previous entry for t=%d, v=%d at k>=%d"
                                   % (t, v, k))
        elif N < prev:
            cl["comparison"] = "exceeds_table"
        elif N == prev:
            cl["comparison"] = "equals_best"
        else:
            cl["comparison"] = "above_table"
            cl["notes_out"].append("verified size is above the current best "
                                   "%d, recorded but not an improvement" % prev)

        # verification
        with tempfile.TemporaryDirectory(prefix="casub-") as tmp:
            canon_path = os.path.join(tmp, "canon.txt")
            with open(canon_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            work = math.comb(k, t) * v ** t
            cl["work"] = work
            budget = ctx["budget"]
            mode = "full"
            if k > ctx["window"] and work > ctx["threshold"]:
                mode = "screen"
                cl["notes_out"].append(
                    "estimated work C(%d,%d)*%d^%d = %.3g exceeds the screen "
                    "threshold %.3g" % (k, t, v, t, work, ctx["threshold"]))
            if mode == "full":
                left = deadline() - time.monotonic()
                if left <= 0:
                    raise ClaimError("not checked: total time budget exhausted")
                r = run_ca_verify(ctx["ca_verify"], canon_path, t, v,
                                  ctx["threads"], min(budget, left))
                cl["seconds"]["verify"] = r["seconds"]
                if r["outcome"] == "verified":
                    cl["status"] = "verified"
                elif r["outcome"] == "gaps":
                    if r["missing"]:
                        cols, tup = r["missing"][0]
                        cl["uncovered"] = dict(columns=cols, tuple=tup)
                    raise ClaimError("NOT A COVERING ARRAY at strength %d: %s"
                                     % (t, r["summary"].replace(
                                         "NOT A COVERING ARRAY: ", "")))
                elif r["outcome"] == "error":
                    raise ClaimError("ca_verify error: %s" % (r["stderr"] or r["summary"]))
                else:
                    if k <= ctx["window"]:
                        raise ClaimError("full verification did not finish within "
                                         "%s and the array is too narrow to "
                                         "screen" % fmt_secs(min(budget, left)))
                    cl["notes_out"].append("full verification did not finish "
                                           "within %s; fell back to the screen"
                                           % fmt_secs(min(budget, left)))
                    mode = "screen"
            if mode == "screen":
                wins = screen_windows(k, sha, ctx["windows"], ctx["window"])
                screen_start = time.monotonic()
                stop_at = min(screen_start + budget, deadline())
                sub_path = os.path.join(tmp, "window.txt")
                for wi, cols in enumerate(wins, 1):
                    left = stop_at - time.monotonic()
                    if left <= 0:
                        raise ClaimError("screen did not finish: %d of %d windows "
                                         "done when the budget ran out"
                                         % (wi - 1, len(wins)))
                    with open(sub_path, "w", encoding="utf-8", newline="\n") as f:
                        for row in rows:
                            f.write(" ".join("NA" if row[c] is None else str(row[c])
                                             for c in cols) + "\n")
                    r = run_ca_verify(ctx["ca_verify"], sub_path, t, v,
                                      ctx["threads"], left)
                    if r["outcome"] == "gaps":
                        if r["missing"]:
                            wc, tup = r["missing"][0]
                            cl["uncovered"] = dict(columns=[cols[c] for c in wc],
                                                   tuple=tup)
                        raise ClaimError("NOT A COVERING ARRAY at strength %d: screen "
                                         "window %d of %d has gaps: %s"
                                         % (t, wi, len(wins), r["summary"].replace(
                                             "NOT A COVERING ARRAY: ", "")))
                    if r["outcome"] == "error":
                        raise ClaimError("ca_verify error in screen window %d: %s"
                                         % (wi, r["stderr"] or r["summary"]))
                    if r["outcome"] == "timeout":
                        raise ClaimError("screen did not finish: window %d of %d "
                                         "ran out of budget" % (wi, len(wins)))
                cl["seconds"]["screen"] = time.monotonic() - screen_start
                cl["status"] = "screened"
                cl["screen"] = dict(windows=len(wins), width=ctx["window"],
                                    seed=sha[:16])
            # a property of the array for its use as an ingredient: the
            # largest number of rows that symbol permutations make constant
            cr_start = time.monotonic()
            cr_budget = min(ctx["constant_rows_budget"], deadline() - time.monotonic())
            cl["constant_rows"] = (run_constant_rows(ctx["constant_rows"], canon_path, v,
                                                     cr_budget) if cr_budget > 1 else None)
            cl["constant_rows_why"] = ("no constant_rows program (no C compiler?)"
                                       if ctx["constant_rows"] is None else
                                       "over the time or memory budget" if cl["constant_rows"] is None
                                       else "")
            cl["seconds"]["constant_rows"] = time.monotonic() - cr_start
        cl["passed"] = True
    except ClaimError as e:
        cl["reasons"].append(str(e))
    except (UnicodeDecodeError, ValueError) as e:
        cl["reasons"].append("could not read the array: %s" % e)
    cl["seconds"]["total"] = time.monotonic() - t0
    return cl


# ---------------------------------------------------------------------------
# Constant rows (tools/constant_rows.c, the computation of cafast::maxconstant_c)
# ---------------------------------------------------------------------------

def constant_rows_binary():
    """Path of the constant_rows program, built from tools/constant_rows.c
    next to it if it is missing or older than the source. None if no C
    compiler is available."""
    src = os.path.join(REPO, "tools", "constant_rows.c")
    exe = os.path.join(REPO, "tools", "constant_rows")
    if not os.path.isfile(src):
        return None
    if (not os.path.isfile(exe) or os.path.getmtime(exe) < os.path.getmtime(src)):
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if cc is None:
            return None
        p = subprocess.run([cc, "-O2", "-o", exe, src], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
        if p.returncode != 0:
            return None
    return exe if os.access(exe, os.X_OK) else None


CONSTANT_ROWS_MAX_BYTES = 2 * 1024 ** 3   # memory limit of the constant_rows program


def _limit_memory():
    """Run in the child before exec: cap its address space, so that a large
    array makes constant_rows fail cleanly instead of exhausting the
    machine's memory (on the GitHub runner that kills the whole job)."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (CONSTANT_ROWS_MAX_BYTES, CONSTANT_ROWS_MAX_BYTES))
    except (ImportError, ValueError, OSError):
        pass


def run_constant_rows(exe, path, v, timeout):
    """Returns the number of rows that can be made constant, or None when
    the program is unavailable, fails (for example at its memory limit,
    CONSTANT_ROWS_MAX_BYTES), or runs out of its time budget."""
    if exe is None:
        return None
    try:
        p = subprocess.run([exe, path, str(v)], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True,
                           timeout=max(1.0, timeout), preexec_fn=_limit_memory)
    except subprocess.TimeoutExpired:
        return None
    m = re.match(r"constant_rows (\d+) of", p.stdout)
    return int(m.group(1)) if (p.returncode == 0 and m) else None


# ---------------------------------------------------------------------------
# Rows to append
# ---------------------------------------------------------------------------

def canonical_name(cl, taken):
    """CA_N_t_k_v.txt, or CA_N_t_k_v_<8 hex>.txt when the plain name is
    already used by a different array (table/README.md convention)."""
    base = "CA_%d_%d_%d_%d" % (cl["N"], cl["t"], cl["k"], cl["v"])
    name = base + ".txt"
    for n in (name, name + ".gz"):
        if n in taken and taken[n] != cl["sha256"]:
            name = "%s_%s.txt" % (base, cl["sha256"][:8])
    if len(cl["canon_text"].encode("utf-8")) > GZIP_ABOVE:
        name += ".gz"
    return name


def write_array(path, text):
    """plain text, or gzip (header time 0) for a .gz name"""
    if path.endswith(".gz"):
        with open(path, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as g:
                g.write(text.encode("utf-8"))
    else:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def previous_text(cl):
    if cl["previous_best"] is None:
        return "no previous entry for these parameters"
    r = cl["previous_row"]
    src = "%s %s" % (r["tier"], r["source_id"])
    if r.get("snapshot_id"):
        src += " " + r["snapshot_id"]
    if r.get("source_detail"):
        src += ": " + r["source_detail"]
    return "previous best %d (row k=%s, %s)" % (cl["previous_best"], r["k"], src)


def table_notes(cl, ctx):
    raw = cl["raw"]
    parts = ["credit: " + raw["credit"].strip()]
    if cl["comparison"] == "exceeds_table":
        parts.append("exceeds table: " + previous_text(cl))
    elif cl["comparison"] == "equals_best":
        parts.append("equals table: " + previous_text(cl))
    else:
        parts.append("above table best, not an improvement: " + previous_text(cl))
    if cl["status"] == "screened":
        s = cl["screen"]
        parts.append("SCREENED, not exhaustively verified: %d random windows of "
                     "%d columns verified in full, seed %s"
                     % (s["windows"], s["width"], s["seed"]))
    parts.append("submission " + ctx["slug"])
    if (raw.get("notes") or "").strip():
        parts.append(raw["notes"].strip())
    return "; ".join(parts)


def build_rows(claims, ctx):
    taken = dict(ctx["taken_names"])
    table_rows, manifest_rows, files = [], [], []
    for cl in claims:
        name = canonical_name(cl, taken)
        taken[name] = cl["sha256"]
        cl["canonical_name"] = name
        tier = "VERIFIED" if cl["status"] == "verified" else "SCREENED"
        table_rows.append([cl["t"], cl["v"], cl["k"], cl["N"], tier, SOURCE_ID,
                           cl["raw"]["source_detail"].strip(), ctx["snapshot_id"],
                           cl["sha256"], ctx["stamp"], ctx["date"],
                           table_notes(cl, ctx), "", "",
                           cl["raw"]["construction"].strip(), cl.get("builds_on", ""), ""])
        if cl["status"] == "screened":
            mstatus = "screened"
        else:
            mstatus = {"exceeds_table": "exceeds_snapshot",
                       "equals_best": "equals_best",
                       "above_table": "above_best"}[cl["comparison"]]
        manifest_rows.append([name, cl["t"], cl["v"], cl["k"], cl["N"], mstatus,
                              cl["sha256"], SOURCE_ID,
                              cl["raw"]["source_detail"].strip(), ctx["stamp"],
                              cl.get("constant_rows") if cl.get("constant_rows") is not None else ""])
        files.append((name, cl["canon_text"]))
    return table_rows, manifest_rows, files


def table_csv_text(rows):
    """ca_table.csv style: minimal quoting, CRLF line endings."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(rows)
    return buf.getvalue()


def manifest_csv_text(rows):
    """MANIFEST.csv style (R write.csv): strings quoted, numbers bare, LF."""
    out = []
    for r in rows:
        cells = []
        for x in r:
            if isinstance(x, int):
                cells.append(str(x))
            else:
                cells.append('"' + str(x).replace('"', '""') + '"')
        out.append(",".join(cells) + "\n")
    return "".join(out)


def append_text(path, text, eol):
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        last = b""
        if size:
            f.seek(-1, 2)
            last = f.read(1)
    with open(path, "a", encoding="utf-8", newline="") as f:
        if size and last != b"\n":
            f.write(eol)
        f.write(text)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def md_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_report(claims, ctx, all_pass, elapsed):
    L = []
    L.append("## Covering array submission check: `%s`" % ctx["slug"])
    L.append("")
    n_pass = sum(1 for c in claims if c["passed"])
    if all_pass:
        L.append("**Result: PASS.** %d of %d claims passed." % (len(claims), len(claims)))
    else:
        L.append("**Result: FAIL.** %d of %d claims passed; nothing is applied "
                 "to the table until every claim passes." % (n_pass, len(claims)))
    L.append("")
    L.append("Checked %s with `ca_verify` (%s), %d threads, budget %s per array, "
             "screen threshold %.3g (C(k,t) times v^t), screen of %d windows x %d "
             "columns. Total time %s."
             % (ctx["date"], ctx["stamp"], ctx["threads"], fmt_secs(ctx["budget"]),
                ctx["threshold"], ctx["windows"], ctx["window"], fmt_secs(elapsed)))
    L.append("")
    L.append("| # | file | t | v | k | N | result | status | vs table | previous best | time |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(claims, 1):
        L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            i, md_cell(c["raw"].get("file", "")), c.get("t", "?"), c.get("v", "?"),
            c.get("k", "?"), c.get("N", "?"), "PASS" if c["passed"] else "FAIL",
            c["status"], c["comparison"] or "", "" if c.get("previous_best") is None
            else c["previous_best"], fmt_secs(c["seconds"].get("total", 0))))
    L.append("")
    L.append("### Details")
    L.append("")
    for i, c in enumerate(claims, 1):
        L.append("**%d. %s** (%s)" % (i, md_cell(c["raw"].get("file", "")),
                                      "PASS" if c["passed"] else "FAIL"))
        L.append("")
        if c.get("sha256"):
            L.append("- sha256 (canonical form): `%s`" % c["sha256"])
        if (c["raw"].get("construction") or "").strip():
            L.append("- construction: %s" % md_cell(c["raw"]["construction"].strip()))
        if c.get("builds_on"):
            L.append("- builds on: %s" % md_cell(c["builds_on"]))
        for r in c["reasons"]:
            L.append("- **%s**" % md_cell(r))
        if c["uncovered"]:
            L.append("- uncovered: columns (%s) with values (%s), columns "
                     "numbered from 0 in the submitted file, values 0-based"
                     % (",".join(map(str, c["uncovered"]["columns"])),
                        ",".join(map(str, c["uncovered"]["tuple"]))))
        if c["status"] == "verified":
            L.append("- verified exhaustively at strength %d in %s"
                     % (c["t"], fmt_secs(c["seconds"].get("verify", 0))))
        if c.get("constant_rows") is not None:
            L.append("- constant rows: %d of %d can be made constant by permuting "
                     "symbols within columns (computed in %s)"
                     % (c["constant_rows"], c["v"], fmt_secs(c["seconds"].get("constant_rows", 0))))
        elif c["passed"]:
            L.append("- constant rows: not computed (%s)" % c.get("constant_rows_why", "unknown"))
        if c["status"] == "screened":
            L.append("- screened, not exhaustively verified: %d random windows of "
                     "%d columns each verified in full at strength %d in %s "
                     "(window seed %s, from the hash)"
                     % (c["screen"]["windows"], c["screen"]["width"], c["t"],
                        fmt_secs(c["seconds"].get("screen", 0)), c["screen"]["seed"]))
        if c.get("previous_best") is not None or c["comparison"]:
            L.append("- table: %s; %s" % (c["comparison"] or "not compared",
                                          md_cell(previous_text(c)) if "previous_best" in c
                                          else "not looked up"))
        if c.get("similar_checked"):
            if c.get("similar"):
                L.append("- **similarity: flagged for the maintainer.** Same structure, up to "
                         "reordering rows and columns and renaming symbols, as %s. This may be "
                         "an independent rediscovery (small optimal arrays are often unique); "
                         "the maintainer decides." % md_cell("; ".join(c["similar"])))
            else:
                L.append("- similarity: no match (%s)" % c["similar_checked"])
        if c.get("comparison"):
            L.append("- prior work to cite: %s" % md_cell("; ".join(cite_text(c, ctx))))
        for n in c["notes_out"]:
            L.append("- note: %s" % md_cell(n))
        if c.get("canonical_name"):
            L.append("- recorded as `table/arrays/%s`" % c["canonical_name"])
        L.append("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def git_short_sha():
    try:
        p = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True, timeout=10)
        s = p.stdout.strip()
        return s if p.returncode == 0 and s else "tools"
    except (OSError, subprocess.SubprocessError):
        return "tools"


def machine_tag():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"
    return "%s-%s" % (platform.system(), platform.machine())


def selftest(table_dir):
    """Re-hash every file in table/arrays and compare with MANIFEST.csv."""
    _, manifest = load_table(table_dir)
    by_file = {m["file"]: m for m in manifest}
    adir = os.path.join(table_dir, "arrays")
    bad = 0
    names = sorted(os.listdir(adir))
    for name in names:
        m = by_file.get(name)
        if m is None:
            print("NO MANIFEST ROW  %s" % name)
            bad += 1
            continue
        if name.endswith(".gz"):
            # a stored compressed file (table/README.md, arrays/): the hash of its
            # decompressed bytes must equal the MANIFEST hash, which is the hash
            # of the canonical text, so the file decompresses to the canonical
            # text itself; it is hashed in chunks, not parsed, to keep memory low
            h = hashlib.sha256()
            with gzip.open(os.path.join(adir, name), "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            sha = raw_sha = h.hexdigest()
        else:
            _, _, sha = canonical_of_file(os.path.join(adir, name), int(m["v"]))
            with open(os.path.join(adir, name), "rb") as f:
                raw_sha = hashlib.sha256(f.read()).hexdigest()
        ok = sha == m["sha256"] and raw_sha == m["sha256"]
        print("%s  %s  %s" % ("OK      " if ok else "MISMATCH", name, sha))
        bad += not ok
    print("%d files checked, %d problems (%d MANIFEST rows in total)"
          % (len(names), bad, len(manifest)))
    return 1 if bad else 0


def certificate_light(sub, a, out):
    """The pull request check of certificates.csv (tools/check_certificates.py --light): returns
    (passed, report text). Nothing exact is run here."""
    import contextlib
    import check_certificates
    cout = os.path.join(out, "certificates")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = check_certificates.main([sub, "--light", "--table-dir", a.table_dir, "--out", cout,
                                          "--threads", str(max(1, min(64, a.threads)))])
    except SystemExit as e:
        return False, "## Certificate check\n\n**Result: FAIL.** %s\n" % md_cell(e)
    try:
        with open(os.path.join(cout, "report.md"), encoding="utf-8") as f:
            return rc == 0, f.read()
    except OSError:
        return False, "## Certificate check\n\n**Result: FAIL.** the check stopped without a report\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("submission", nargs="?", help="submissions/<slug> directory")
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--ca-verify", default=os.path.join(REPO, "ca_verify"))
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--budget-minutes", type=float, default=20.0,
                    help="wall-clock budget per array (default 20)")
    ap.add_argument("--total-budget-minutes", type=float, default=None,
                    help="wall-clock budget for the whole submission")
    ap.add_argument("--screen-threshold", type=float, default=1e10,
                    help="screen instead of full check when C(k,t)*v^t exceeds this")
    ap.add_argument("--screen-windows", type=int, default=20)
    ap.add_argument("--constant-rows-minutes", type=float, default=10.0,
                    help="time budget for the constant rows count per array "
                         "(default 10; left empty when exceeded)")
    ap.add_argument("--screen-width", type=int, default=30)
    ap.add_argument("--out", default=None, help="output directory "
                    "(default ./check-<slug>)")
    ap.add_argument("--pr", default=None, help="pull request number, used as snapshot_id")
    ap.add_argument("--stamp-version", default=None,
                    help="version in the verify stamp (default git short sha or 'tools')")
    ap.add_argument("--date", default=None, help="entry date (default today, UTC)")
    ap.add_argument("--apply", action="store_true",
                    help="append the rows and copy the arrays into the table")
    ap.add_argument("--selftest", action="store_true",
                    help="re-hash table/arrays against MANIFEST.csv and exit")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest(a.table_dir)
    if not a.submission:
        ap.error("a submission directory is required")
    sub = os.path.abspath(a.submission)
    slug = os.path.basename(sub.rstrip(os.sep))
    if not SAFE_NAME.match(slug):
        print("bad submission directory name %r" % slug, file=sys.stderr)
        return 2
    if not (os.path.isfile(a.ca_verify) and os.access(a.ca_verify, os.X_OK)):
        print("ca_verify not found at %s (build: cc -O3 -pthread -o ca_verify "
              "ca_verify.c)" % a.ca_verify, file=sys.stderr)
        return 2
    out = os.path.abspath(a.out or "check-%s" % slug)
    os.makedirs(out, exist_ok=True)
    date = a.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    stamp = "ca_verify %s %s %s" % (a.stamp_version or git_short_sha(), date,
                                    machine_tag())
    table_rows, manifest = load_table(a.table_dir)
    adir = os.path.join(a.table_dir, "arrays")
    taken = {m["file"]: m["sha256"] for m in manifest}
    if os.path.isdir(adir):
        for name in os.listdir(adir):
            taken.setdefault(name, None)
    ctx = dict(subdir=sub, slug=slug, ca_verify=os.path.abspath(a.ca_verify),
               threads=max(1, min(64, a.threads)), budget=a.budget_minutes * 60.0,
               threshold=a.screen_threshold, windows=a.screen_windows,
               window=a.screen_width, table_rows=table_rows,
               manifest_sha={m["sha256"]: m["file"] for m in manifest},
               table_sha={r["array_sha256"]: r for r in table_rows
                          if r.get("array_sha256")},
               seen_sha={}, taken_names=taken, date=date, stamp=stamp,
               snapshot_id=("pr-%s" % a.pr) if a.pr else slug,
               constant_rows=constant_rows_binary(),
               constant_rows_budget=a.constant_rows_minutes * 60.0,
               table_dir=a.table_dir, manifest=manifest,
               withdrawn_fp=load_withdrawn_fp(a.table_dir),
               references=load_references(a.table_dir))

    start = time.monotonic()
    total = (max(0.0, a.total_budget_minutes) * 60.0
             if a.total_budget_minutes is not None else float("inf"))
    deadline = lambda: start + total  # noqa: E731

    claims = []
    problems = []
    total_bytes = (sum(os.path.getsize(os.path.join(sub, n)) for n in os.listdir(sub)
                       if os.path.isfile(os.path.join(sub, n))
                       and not os.path.islink(os.path.join(sub, n)))
                   if os.path.isdir(sub) else 0)
    if total_bytes > MAX_SUBMISSION_BYTES:
        problems.append("the submission holds %.1f MiB of files, above the %d MiB "
                        "limit per submission; split it into several pull requests "
                        "(see \"Size limits\" in submissions/README.md)"
                        % (total_bytes / 1048576.0, MAX_SUBMISSION_BYTES // 1048576))
    cpath = os.path.join(sub, "claims.csv")
    # certificates (certificates.csv) get the light check of tools/check_certificates.py here: format,
    # identity, duplicates, the estimate and plan of the exact check, and a small screen; the exact
    # check runs after merge (.github/workflows/certificate-check.yml). Arrays kept in a deposit
    # (external.csv) are checked by the maintainer (tools/external_array.py), not here.
    others = [n for n in ("certificates.csv", "external.csv") if os.path.isfile(os.path.join(sub, n))]
    cert_ok, cert_text = True, ""
    if "certificates.csv" in others and not problems:
        cert_ok, cert_text = certificate_light(sub, a, out)
    if not os.path.exists(cpath) and others and not problems:
        lines = ["## Covering array submission check: %s" % slug, ""]
        if "external.csv" in others:
            lines.append("This submission holds `external.csv`. Arrays kept in a deposit are checked by the "
                         "maintainer on a larger machine (`tools/external_array.py`), as submissions/README.md "
                         "describes, and the result is posted here.")
            lines.append("")
        if cert_text:
            lines.append(cert_text)
        with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(dict(slug=slug, passed=cert_ok, maintainer_check=[n for n in others if n == "external.csv"],
                           certificates="certificates.csv" in others, claims=[]), f)
        print("\n".join(lines))
        return 0 if cert_ok else 1
    if total_bytes > MAX_SUBMISSION_BYTES:
        pass                              # refused before reading any claim
    elif os.path.islink(sub.rstrip(os.sep)) or os.path.islink(cpath):
        problems.append("the submission directory and claims.csv must not be "
                        "symbolic links")
    elif not os.path.isfile(cpath):
        problems.append("claims.csv is missing from submissions/%s/" % slug)
    else:
        with open(cpath, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            hdr = [h.strip() for h in header]
            if hdr == PREV_CLAIMS_HEADER and slug not in exempt_slugs():
                problems.append("claims.csv needs the builds_on column after construction "
                                "(%s); see submissions/README.md" % ",".join(CLAIMS_HEADER))
            elif hdr == OLD_CLAIMS_HEADER:
                problems.append("claims.csv uses the header without the "
                                "construction column; add it (%s)"
                                % ",".join(CLAIMS_HEADER))
            elif hdr not in (CLAIMS_HEADER, PREV_CLAIMS_HEADER):
                problems.append("claims.csv header must be exactly %s (found %s)"
                                % (",".join(CLAIMS_HEADER), ",".join(header)))
            else:
                for n, rec in enumerate(reader, 2):
                    if not any(x.strip() for x in rec):
                        continue
                    if len(rec) != len(hdr):
                        problems.append("claims.csv line %d has %d fields, "
                                        "expected %d" % (n, len(rec), len(hdr)))
                        continue
                    claims.append(dict(raw=dict(zip(hdr, rec)), line=n))
        if not claims and not problems:
            problems.append("claims.csv has no claims")

    for cl in claims:
        print("checking %s ..." % cl["raw"]["file"], file=sys.stderr, flush=True)
        check_claim(cl, ctx, deadline)
        print("  %s %s %s %s" % ("PASS" if cl["passed"] else "FAIL", cl["status"],
                                 cl["comparison"] or "", "; ".join(cl["reasons"])),
              file=sys.stderr, flush=True)

    all_pass = bool(claims) and not problems and all(c["passed"] for c in claims)
    rows = None
    if all_pass:
        rows = build_rows(claims, ctx)
    elapsed = time.monotonic() - start
    report = render_report(claims, ctx, all_pass, elapsed)
    if problems:
        # the list goes once, ahead of the per-claim details
        report = report.replace("### Details", "### Submission problems\n\n" +
                                "".join("- **%s**\n" % md_cell(p) for p in problems)
                                + "\n### Details", 1)

    # outputs
    for stale in ("ca_table_rows.csv", "manifest_rows.csv"):
        if os.path.exists(os.path.join(out, stale)):
            os.remove(os.path.join(out, stale))
    if os.path.isdir(os.path.join(out, "arrays")):
        shutil.rmtree(os.path.join(out, "arrays"))
    if rows:
        trows, mrows, files = rows
        with open(os.path.join(out, "ca_table_rows.csv"), "w", encoding="utf-8",
                  newline="") as f:
            f.write(table_csv_text(trows))
        with open(os.path.join(out, "manifest_rows.csv"), "w", encoding="utf-8",
                  newline="") as f:
            f.write(manifest_csv_text(mrows))
        os.makedirs(os.path.join(out, "arrays"))
        for name, text in files:
            write_array(os.path.join(out, "arrays", name), text)
    summary = dict(
        slug=slug, passed=all_pass, date=date, stamp=stamp,
        threads=ctx["threads"], budget_seconds=ctx["budget"],
        screen_threshold=ctx["threshold"], elapsed_seconds=round(elapsed, 2),
        problems=problems, applied=False,
        claims=[dict(line=c["line"], file=c["raw"].get("file"), t=c.get("t"),
                     v=c.get("v"), k=c.get("k"), N=c.get("N"), passed=c["passed"],
                     status=c["status"], comparison=c["comparison"],
                     previous_best=c.get("previous_best"), sha256=c.get("sha256"),
                     canonical_name=c.get("canonical_name"), reasons=c["reasons"],
                     uncovered=c["uncovered"], notes=c["notes_out"],
                     seconds={k2: round(v2, 2) for k2, v2 in c["seconds"].items()})
                for c in claims])

    if a.apply and rows:
        trows, mrows, files = rows
        os.makedirs(adir, exist_ok=True)
        for name, text in files:
            dest = os.path.join(adir, name)
            if os.path.exists(dest):
                print("refusing to overwrite %s" % dest, file=sys.stderr)
                return 2
        append_text(os.path.join(a.table_dir, "ca_table.csv"),
                    table_csv_text(trows), "\r\n")
        append_text(os.path.join(a.table_dir, "MANIFEST.csv"),
                    manifest_csv_text(mrows), "\n")
        for name, text in files:
            write_array(os.path.join(adir, name), text)
        summary["applied"] = True
        report += ("\nApplied: %d rows appended to `table/ca_table.csv`, %d to "
                   "`table/MANIFEST.csv`, %d files added to `table/arrays/`.\n"
                   % (len(trows), len(mrows), len(files)))
    elif a.apply:
        report += "\nNot applied: the submission did not pass.\n"

    if cert_text:
        report += "\n" + cert_text
        summary["certificates_passed"] = cert_ok
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
        f.write("\n")
    print(report)
    return 0 if all_pass and cert_ok else 1


if __name__ == "__main__":
    sys.exit(main())
