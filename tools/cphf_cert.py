#!/usr/bin/env python3
"""cphf_cert - covering perfect hash family certificates: identity, expansion rules, plans and shards.

Standard library only. Used by tools/check_certificates.py, tools/consistency.py and the
certificate workflow (.github/workflows/certificate-check.yml). The definitions are in
tools/cphf/README.md ("Identity of a family", "Expansion rules", "Shards and the time budget").

Identity. family_sha256 is the SHA-256 of the canonical serialization "cphf1" of a family: the
line "cphf1 n k q t", then n lines of k decimal codes (the vector of GF(q)^t in base q, most
significant digit first, as in the family file), single spaces, a line feed after every line, no
comments, rows and columns in the order given. An array of at most ARRAY_HASH_MAX_ENTRIES entries
(N times k) is also identified by array_sha256, the SHA-256 of its canonical text; above that a
certificate row may leave array_sha256 empty and is identified by family_sha256 alone.

Expansion rules (the column "expansion" of table/certificates/CERTIFICATES.csv):
  smc-1          the all-zero run, then for r = 0..n-1 and beta = 1..q^t-1 in increasing base-q
                 code (most significant digit first) the run with entry beta . v_r[c] in column c:
                 n (q^t - 1) + 1 runs (Sherwood, Martirosyan and Colbourn 2006)
  smc-1-affine   as smc-1, but beta whose coordinates after the first are all zero are skipped, and
                 the constant runs b = 1..q-1 are appended at the end: n (q^t - q) + q runs (every
                 vector of the family has first coordinate 1)
  RULE+fuse a>b  then symbol a is written as b in every entry (Colbourn, Keri, Rivas Soriano and
                 Schlage-Puchta 2010, Lemma 3.1): same runs, one symbol fewer
  RULE+fuse2 a   then symbol a is removed with two runs, as tools/cphf/fuse2.c does: N - 2 runs

Shards. cphfcheck "MODE ... shard i m" does shard i of m of the outer loop of an exact mode and
prints its partial counts; combine() checks that the partial counts of shards 0..m-1, each present
exactly once, add up to the totals an unsharded run checks (computed here, independently of the C
code), and merges the uncovered t-sets.
"""
import hashlib
import heapq
import math
import re

ARRAY_HASH_MAX_ENTRIES = 10 ** 12     # N * k above this: array_sha256 may be left empty
FAMILY_FORMAT = "cphf1"
MAX_ROWS = 64                         # cphfcheck.c reads at most 64 rows

# Time budget of the exact check on GitHub-hosted runners (free for public repositories): a job may
# run up to 6 hours, on 4 cores, and up to 20 jobs run at once. A family is checked exactly on GitHub
# when its estimated work, times SAFETY, fits in at most MAX_SHARDS shards of at most SHARD_HOURS
# hours each on RUNNER_THREADS threads; otherwise it enters as SCREENED. The hour left in every job
# is the margin for building, the array hash and the upload.
RUNNER_THREADS = 4
MAX_SHARDS = 20
SHARD_HOURS = 5.0
SAFETY = 2.0
# expanding and hashing an array costs about 4 ns per entry on one core (cphfcheck expand into a
# pipe, measured 2026-11-02: 6.1e8 entries in 4.1 s); the array hash runs as its own job
HASH_NS_PER_ENTRY = 4.0
# the unit costs of cphfcheck.c (its function unit_ns, fitted 2026-11-02 to timed runs on one core of the
# test VM, tools/cphf/README.md "Unit costs"), mirrored here to estimate an explicit "cyclic s" that
# cphfcheck's own estimate does not list and the methods it lists as not applicable. n is the number of
# rows of the family. The two must stay equal (tools/cphf/tests/test_certificates.py compares them).
def unit_ns(method, t, q, k, n):
    """Nanoseconds on one core per unit of a method of cphfcheck: "full" and "cyclic" per t-set,
    "fullfast" per C(k, t-1), "progression" and "fastprog" per C(k-1, t-2), "shift" per shift test."""
    kq = k / float(q * q)
    if method in ("full", "cyclic"):
        return 0.15 * n * t * t
    if method == "fullfast":
        return n * (11.0 + 28.0 / q)
    if method == "progression":
        return 10.5 * (t - 3) ** 2 + 4.6 * kq
    if method == "fastprog":
        return 0.8 * (t - 3) ** 2 + 1.1 * kq
    if method == "shift":
        return 140.0
    raise CertError("unknown method %r" % method)


class CertError(Exception):
    pass


# ---------------------------------------------------------------------------------------------
# family files and identity

TOKEN_SPLIT = re.compile(r"[ \t,\r]+")


def read_family(path, q, t):
    """The family as a list of rows of integer codes, read with the rules of cphfcheck.c: lines
    starting with '#' are comments, blank lines are skipped, entries are separated by spaces, tabs or
    commas. Stricter than cphfcheck: every entry must be a plain decimal integer below q^t."""
    maxcode = q ** t
    rows = []
    with open(path, "r", encoding="ascii", errors="strict", newline="") as f:
        data = f.read()
    for lineno, line in enumerate(data.split("\n"), 1):
        if line.startswith("#"):
            continue
        toks = [x for x in TOKEN_SPLIT.split(line) if x]
        if not toks:
            continue
        row = []
        for tok in toks:
            if not re.fullmatch(r"[0-9]+", tok):
                raise CertError("family line %d: entry %r is not a decimal integer" % (lineno, tok[:20]))
            x = int(tok)
            if x >= maxcode:
                raise CertError("family line %d: entry %d is not below q^t = %d" % (lineno, x, maxcode))
            row.append(x)
        if rows and len(row) != len(rows[0]):
            raise CertError("family line %d has %d entries, the first row has %d" % (lineno, len(row), len(rows[0])))
        rows.append(row)
    if not rows:
        raise CertError("the family file has no rows")
    if len(rows) > MAX_ROWS:
        raise CertError("the family has %d rows; the checker reads at most %d" % (len(rows), MAX_ROWS))
    if len(rows[0]) < t:
        raise CertError("the family has %d columns, fewer than t = %d" % (len(rows[0]), t))
    return rows


def canonical_family(rows, q, t):
    """The canonical serialization cphf1, as bytes."""
    out = ["%s %d %d %d %d\n" % (FAMILY_FORMAT, len(rows), len(rows[0]), q, t)]
    out += [" ".join(str(x) for x in r) + "\n" for r in rows]
    return "".join(out).encode("ascii")


def family_identity(path, q, t):
    """(family_sha256, n, k, affine): affine when every vector has first coordinate 1."""
    rows = read_family(path, q, t)
    lo, hi = q ** (t - 1), 2 * q ** (t - 1)
    affine = all(lo <= x < hi for r in rows for x in r)
    return hashlib.sha256(canonical_family(rows, q, t)).hexdigest(), len(rows), len(rows[0]), affine


def array_is_hashed(N, k):
    return N * k <= ARRAY_HASH_MAX_ENTRIES


# ---------------------------------------------------------------------------------------------
# expansion rules

EXPANSION_RE = re.compile(r"^(smc-1|smc-1-affine)((?:\+fuse \d+>\d+|\+fuse2 \d+)*)$")


def expansion_id(affine):
    return "smc-1-affine" if affine else "smc-1"


def expansion_runs(rule, n, q, t):
    """Number of runs and of symbols of the array the rule gives from a CPHF(n; k, q, t)."""
    m = EXPANSION_RE.match(rule or "")
    if not m:
        raise CertError("unknown expansion rule %r" % rule)
    N = n * (q ** t - q) + q if m.group(1) == "smc-1-affine" else n * (q ** t - 1) + 1
    v = q
    for step in re.findall(r"\+(fuse \d+>\d+|fuse2 \d+)", m.group(2)):
        if step.startswith("fuse2"):
            N -= 2
        v -= 1
    return N, v


# ---------------------------------------------------------------------------------------------
# estimate and plan

def parse_estimate(text):
    """The output of "cphfcheck FILE t q estimate": methods with units and core seconds, the cheapest."""
    est = dict(methods={}, cheapest=None, symmetry=0, rows=None)
    for line in text.splitlines():
        m = re.match(r"rows: progression (\d+), other (\d+), dead (\d+)$", line)
        if m:
            est["rows"] = tuple(int(x) for x in m.groups())
        m = re.match(r"symmetry: col -> col\+(\d+) certified", line)
        if m:
            est["symmetry"] = int(m.group(1))
        m = re.match(r"estimate (cyclic \d+|fastprog|progression|fullfast|full) units=(\d+) .*core_seconds=(\S+)$", line)
        if m:
            est["methods"][m.group(1).split()[0]] = dict(
                method=m.group(1), units=int(m.group(2)), core_seconds=float(m.group(3)))
        m = re.match(r"cheapest: (cyclic \d+|fastprog|progression|fullfast|full) core_seconds=(\S+)", line)
        if m:
            est["cheapest"] = dict(method=m.group(1), core_seconds=float(m.group(2)))
    if est["cheapest"] is None or est["rows"] is None:
        raise CertError("could not read the estimate: %s" % " | ".join(text.splitlines()[-3:]))
    return est


def outer_domain(method, k, t):
    """(lo, hi, d) of the outer loop of an exact mode, as cphfcheck.c deals it to shards: index j has
    weight C(k-1-j, d), d = None for a domain of one index. method is "full", "fullfast",
    "progression", "fastprog" or "cyclic s". fastprog has the outer loop, the counts and the
    representatives of progression (the second column of the representative, t >= 4)."""
    if method.startswith("cyclic"):
        return 0, int(method.split()[1]), t - 1
    if method == "full":
        return 0, k - t + 1, t - 1
    if method == "fullfast":
        return (0, 1, None) if t == 2 else (0, k, t - 2)
    if method in ("progression", "fastprog"):
        return (0, 1, None) if t <= 3 else (1, k, t - 3)
    raise CertError("unknown method %r" % method)


def deal(method, k, t, m):
    """The deal of cphfcheck.c (a replica, used only to plan): the largest weight first, each index to
    the least loaded shard, ties to the lower index and the lower shard. Returns the shard loads."""
    lo, hi, d = outer_domain(method, k, t)
    w = [1 if d is None else math.comb(k - 1 - j, d) for j in range(lo, hi)]
    order = sorted(range(len(w)), key=lambda j: (-w[j], j))
    heap = [(0, s) for s in range(m)]          # (load, shard): the least load, then the lower shard
    for j in order:
        ld, s = heapq.heappop(heap)
        heapq.heappush(heap, (ld + w[j], s))
    load = [0] * m
    for ld, s in heap:
        load[s] = ld
    return load


def plan_claim(est, k, t, threads=RUNNER_THREADS, max_shards=MAX_SHARDS, shard_hours=SHARD_HOURS,
               safety=SAFETY):
    """Method and number of shards for the exact check: the cheapest method, and the smallest m whose
    largest shard (by the deal above) fits in shard_hours on `threads` threads, with the estimate
    times `safety`. Returns dict(method, shards, core_hours, shard_hours, exact) with exact False
    when no m up to max_shards fits."""
    method = est["cheapest"]["method"]
    core_s = est["cheapest"]["core_seconds"] * safety
    cap = shard_hours * 3600.0 * threads
    lo, hi, d = outer_domain(method, k, t)
    for m in range(1, max_shards + 1):
        if m > 1 and hi - lo < m:
            break
        load = deal(method, k, t, m)
        tot = sum(load) or 1
        worst = core_s * max(load) / tot
        if worst <= cap:
            return dict(method=method, shards=m, core_hours=core_s / 3600.0,
                        shard_hours=worst / threads / 3600.0, exact=True)
    return dict(method=method, shards=0, core_hours=core_s / 3600.0, shard_hours=None, exact=False)


# ---------------------------------------------------------------------------------------------
# shards

def expected_totals(method, k, t):
    """What an unsharded run of the method checks, computed here from the binomials: units (t-sets
    for full and cyclic, pairs for fullfast and progression), prefixes and candidate columns."""
    C = math.comb
    if method.startswith("cyclic"):
        s = int(method.split()[1])
        return dict(units=sum(C(k - 1 - c0, t - 1) for c0 in range(min(s, k))))
    if method == "full":
        return dict(units=C(k, t))
    if method == "fullfast":
        return dict(units=C(k, t), prefixes=C(k, t - 2), candidates=C(k, t - 1))
    if method in ("progression", "fastprog"):
        if t == 2:
            return dict(units=k - 1, prefixes=1, candidates=k - 1)
        return dict(units=C(k - 1, t - 1), prefixes=C(k - 1, t - 3), candidates=C(k - 1, t - 2))
    raise CertError("unknown method %r" % method)


def per_index(method, k, t, j):
    """What outer index j of a method stands for (as cphfcheck.c counts it): units, and for the hashing
    modes prefixes and candidate columns. For a domain of one index (j = 0) it is the whole run."""
    C = math.comb
    lo, hi, d = outer_domain(method, k, t)
    if d is None:
        return expected_totals(method, k, t)
    a = k - 1 - j
    if method.startswith("cyclic") or method == "full":
        return dict(units=C(a, t - 1))
    if method == "fullfast":
        return dict(units=C(a, t - 1), prefixes=C(a, t - 3), candidates=C(a, t - 2))
    return dict(units=C(a, t - 2), prefixes=C(a, t - 4), candidates=C(a, t - 3))   # progression, fastprog, t >= 4


def parse_ranges(text):
    out = []
    text = text.strip()
    if text == "none":
        return out
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def parse_shard(text):
    """One shard's output (the raw output of cphfcheck, as written by check_certificates.py --run:
    comment lines '# key: value' before and after it)."""
    meta, kv, tot, U, first, rows, head, idx = {}, None, None, [], None, [], None, None
    for line in text.splitlines():
        m = re.match(r"^# ([a-z0-9_]+): (.*)$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip()
            continue
        if line.startswith("CPHF candidate:"):
            head = re.sub(r" mode=\S+", "", line)
        elif re.match(r"^row \d+: ", line) or line.startswith(("symmetry col", "progression rows", "rows used",
                                                               "auto: method", "rows: ", "symmetry: ",
                                                               "estimate ", "cheapest: ")):
            rows.append(line)
        elif line.startswith("SHARD i="):
            kv = dict(x.split("=", 1) for x in line.split() if "=" in x)
        elif line.startswith("SHARD indices:"):
            idx = parse_ranges(line.split(":", 1)[1])
        elif line.startswith("SHARD totals"):
            tot = dict(x.split("=", 1) for x in line.split() if "=" in x)
        elif line.startswith("U "):
            U.append(tuple(int(x) for x in line.split()[1:]))
        elif line.startswith("first uncovered:"):
            first = tuple(int(x) for x in line.split(":")[1].split())
        elif line.startswith("INTERNAL CHECK FAILED"):
            meta["internal"] = line
    return dict(meta=meta, kv=kv, totals=tot, U=U, first=first, rows=rows, head=head, indices=idx)


def combine(texts, method, k, t):
    """Combine the outputs of the shards of one exact check. texts: the shard outputs (any order).
    Raises CertError unless shards 0..m-1 are each there exactly once, ran the same method on the same
    family with the same tool and classification, exited with 0 or 1, and their partial counts add up
    exactly to expected_totals(). Returns dict(m, uncovered, first, sets, listed_all, units)."""
    if not texts:
        raise CertError("no shard outputs")
    sh = [parse_shard(x) for x in texts]
    want = expected_totals(method, k, t)
    ms = set()
    seen = {}
    for i, s in enumerate(sh):
        if s["meta"].get("internal"):
            raise CertError("shard output %d: %s" % (i, s["meta"]["internal"]))
        if s["kv"] is None:
            raise CertError("shard output %d has no SHARD line (exit %s): the shard did not finish"
                            % (i, s["meta"].get("exit", "?")))
        if s["meta"].get("exit") not in ("0", "1"):
            raise CertError("shard output %d exited with %s" % (i, s["meta"].get("exit")))
        ms.add(int(s["kv"]["m"]))
        idx = int(s["kv"]["i"])
        if idx in seen:
            raise CertError("shard %d appears twice" % idx)
        seen[idx] = s
    if len(ms) != 1:
        raise CertError("the shard outputs disagree on the number of shards: %s" % sorted(ms))
    m = ms.pop()
    missing = sorted(set(range(m)) - set(seen))
    if missing:
        raise CertError("shard%s %s of %d missing" % ("s" if len(missing) > 1 else "",
                                                      ", ".join(map(str, missing[:20])), m))
    if set(seen) - set(range(m)):
        raise CertError("shard numbers outside 0..%d" % (m - 1))
    ref = sh[0]
    for key in ("family_sha256", "tool", "method", "t", "q"):
        vals = {s["meta"].get(key) for s in sh}
        if len(vals) != 1 or None in vals:
            raise CertError("the shard outputs disagree on %s: %s" % (key, sorted(map(str, vals))))
    if ref["meta"]["method"] != method:
        raise CertError("the shards ran %r, the plan says %r" % (ref["meta"]["method"], method))
    for s in sh:
        if s["head"] != ref["head"] or s["rows"] != ref["rows"]:
            raise CertError("the shard outputs disagree on the family or its row classification")
        if s["kv"]["mode"] != method.split()[0]:
            raise CertError("a shard ran mode %s, the plan says %s" % (s["kv"]["mode"], method))
    # every index of the outer loop in exactly one shard, and each shard's counts are those of its indices
    lo, hi, _ = outer_domain(method, k, t)
    cover = {}
    for s in sh:
        if s["indices"] is None:
            raise CertError("shard %s does not list its indices" % s["kv"]["i"])
        part = dict.fromkeys(want, 0)
        for j in s["indices"]:
            if j in cover:
                raise CertError("index %d of the outer loop is in shards %s and %s" % (j, cover[j], s["kv"]["i"]))
            if not lo <= j < hi:
                raise CertError("shard %s lists index %d, outside %d..%d" % (s["kv"]["i"], j, lo, hi - 1))
            cover[j] = s["kv"]["i"]
            for key, val in per_index(method, k, t, j).items():
                part[key] += val
        for key in want:
            if int(s["kv"][key]) != part[key]:
                raise CertError("shard %s: %s %s, its indices stand for %d" % (s["kv"]["i"], key, s["kv"][key], part[key]))
    if len(cover) != hi - lo:
        raise CertError("%d of the %d indices of the outer loop are in no shard" % (hi - lo - len(cover), hi - lo))
    got = {}
    for key in want:
        got[key] = sum(int(s["kv"][key]) for s in sh)
        if got[key] != want[key]:
            raise CertError("the shards' %s add up to %d, an unsharded run checks %d"
                            % (key, got[key], want[key]))
    unc = sum(int(s["kv"]["uncovered"]) for s in sh)
    listed = sum(int(s["kv"]["listed"]) for s in sh)
    sets = sorted(set(x for s in sh for x in s["U"]))
    if listed != sum(len(s["U"]) for s in sh):
        raise CertError("a shard output lost lines of its uncovered list")
    firsts = [s["first"] for s in sh if s["first"]]
    first = min(firsts) if firsts else None
    if (unc == 0) != (first is None):
        raise CertError("uncovered count and first uncovered set disagree")
    return dict(m=m, uncovered=unc, first=first, sets=sets, listed_all=listed == unc, units=got["units"])
