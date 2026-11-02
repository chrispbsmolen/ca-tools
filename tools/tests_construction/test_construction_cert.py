#!/usr/bin/env python3
"""Tests of tools/construction_cert.py.

Random small certificates (valid ones and ones with planted faults) are written to disk and
checked by construction_cert.run(). Independently of the checker, this file regenerates the hash
family (its own GF arithmetic and direct polynomial evaluation), evaluates every hypothesis by
direct definition (pairwise column agreement, every tuple of every declared species on every
t-set), assembles the array and hashes its canonical text, and runs the exact brute-force checker
ca_verify (from the table repository, compiled from source) on the assembled array.

Assertions per case:
  A1 the checker's verdict equals the conjunction of the independently computed hypotheses
  A2 if the case is faulted, the failure the fault plants is among the checker's failures
  A3 every accepted certificate gives a covering array (ca_verify, exact) whose canonical sha256
     equals the independently computed one
  A4 (theorem) every case whose hypotheses hold (independent evaluation) is a covering array
Then mutation testing: each check of the checker is disabled in turn (and four boundary mutants
are applied); a mutant is killed when A1 or A2 fails on some case, and it is a soundness kill
when the mutant accepts a certificate whose array is not a covering array or not the claimed one.

Usage: test_construction_cert.py [--cases N] [--seed S] [--keep DIR] [--no-mutation]
"""
import hashlib
import itertools
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # repository root
BUILD = os.environ.get("CZTEST_BUILD", __import__("tempfile").gettempdir())
sys.path.insert(0, os.path.join(ROOT, "tools"))
import construction_cert as cc  # noqa: E402

CA_VERIFY_SRC = os.environ.get("CA_VERIFY_SRC", os.path.join(
    ROOT, "ca_verify.c"))
CA_VERIFY = os.path.join(BUILD, "ca_verify_cztest")


# ---------------------------------------------------------------------------
# independent arithmetic and definitions (deliberately written differently from the checker)
# ---------------------------------------------------------------------------

class TField:
    """GF(p^m) by repeated multiplication by x (shift and reduce); element <-> base-p digits"""
    def __init__(self, p, m, modulus):
        self.p, self.m, self.q, self.mod = p, m, p ** m, modulus
        self.cache = {}

    def vec(self, a):
        return [(a // self.p ** j) % self.p for j in range(self.m)]

    def num(self, d):
        return sum(c * self.p ** j for j, c in enumerate(d))

    def add(self, a, b):
        return self.num([(x + y) % self.p for x, y in zip(self.vec(a), self.vec(b))])

    def times_x(self, d):
        top = d[-1]
        sh = [0] + d[:-1]
        return [(sh[j] - top * self.mod[j]) % self.p for j in range(self.m)]

    def mul(self, a, b):
        key = (a, b)
        if key not in self.cache:
            self.cache[key] = self._mul(a, b)
        return self.cache[key]

    def _mul(self, a, b):
        res = [0] * self.m
        cur = self.vec(a)
        for c in self.vec(b):
            res = [(r + c * x) % self.p for r, x in zip(res, cur)]
            cur = self.times_x(cur)
        return self.num(res)

    def is_field(self):
        q = self.q
        for a in range(1, q):
            if not any(self.mul(a, b) == 1 for b in range(1, q)):
                return False
        return True


_SPC = {}


def t_species(tup, v):
    key = (tup, v)
    if key not in _SPC:
        _SPC[key] = tuple(sum(1 for x in tup if x == s) for s in range(v))
    return _SPC[key]


def t_tau(sp):
    vals = [s for s, c in enumerate(sp) for _ in range(c)]
    return sum(1 for i in range(len(vals)) for j in range(i + 1, len(vals)) if vals[i] != vals[j])


def t_all_species(t, v):
    return sorted({t_species(tup, v) for tup in itertools.product(range(v), repeat=t)})


def t_family(sc):
    """returns (H rows, widths) built independently"""
    if sc["family"]["type"] == "explicit":
        return [list(r) for r in sc["family"]["values"]], list(sc["family"]["widths"])
    p, m, mod = sc["field"]
    F = TField(p, m, mod)
    q, e = F.q, sc["e"]
    pts, fbs = sc["family"]["points"], sc["family"]["forbidden"]
    powtab = {}
    cols = []
    for coeffs in itertools.product(range(q), repeat=e):
        vals = []
        for x in pts:
            if x == q:
                vals.append(coeffs[-1])
                continue
            acc = 0
            for j, cj in enumerate(coeffs):
                if (x, j) not in powtab:
                    pw = 1
                    for _ in range(j):
                        pw = F.mul(pw, x)
                    powtab[(x, j)] = pw
                acc = F.add(acc, F.mul(cj, powtab[(x, j)]))
            vals.append(acc)
        if all(vals[i] not in fbs[i] for i in range(len(pts))):
            cols.append(vals)
    lim = sc["family"].get("column_limit")
    sc["_limit_short"] = False
    if lim is not None:
        sc["_limit_short"] = lim > len(cols)
        cols = cols[:lim]
    H, widths = [], []
    for i in range(len(pts)):
        kept = [s for s in range(q) if s not in fbs[i]]
        H.append([kept.index(col[i]) for col in cols])
        widths.append(len(kept))
    return H, widths


def t_qa_ok(rows, t, v, declared):
    """direct: on every t-set of columns, every tuple whose species is declared appears"""
    if not rows:
        return False
    w = len(rows[0])
    if any(len(r) != w for r in rows):
        return False
    for cols in itertools.combinations(range(w), t):
        seen = {tuple(r[c] for c in cols) for r in rows}
        for tup in itertools.product(range(v), repeat=t):
            if t_species(tup, v) in declared and tup not in seen:
                return False
    return True


def t_truth(sc):
    """independent evaluation of every condition; returns (failed condition names, H, array)"""
    t, v, e = sc["t"], sc["v"], sc["e"]
    fails = set()
    if sc["family"]["type"] == "rs":
        p, m, mod = sc["field"]
        if not TField(p, m, mod).is_field():
            fails.add("field")
    H, widths = t_family(sc)
    k = len(H[0])
    M = len(H)
    ings = sc["ingredients"]
    assign = sc["assign"]
    # shape: k >= t, ingredients rectangular over 0..v-1, columns = width of its rows
    if k < t or sc.pop("_limit_short", False):
        fails.add("shape")
    for name, ing in ings.items():
        rows = ing["rows"]
        if not rows or any(len(r) != len(rows[0]) for r in rows) or \
                any(x >= v for r in rows for x in r):
            fails.add("shape")
            continue
        for i in range(M):
            if assign[i] == name and len(rows[0]) != widths[i]:
                fails.add("shape")
    if any(w < t for w in widths):
        fails.add("width")
    for name, ing in ings.items():
        if ing["file"] and ing["sha_recorded"] != hashlib.sha256(ing["text"].encode()).hexdigest():
            fails.add("ingredient_hash")
    # agreement: pairwise, direct
    worst = 0
    for a in range(k):
        for b in range(a + 1, k):
            ag = sum(1 for i in range(M) if H[i][a] == H[i][b])
            if ag > worst:
                worst = ag
    if worst > e - 1:
        fails.add("agreement")
    for name, ing in ings.items():
        if not t_qa_ok(ing["rows"], t, v, ing["covers"]):
            fails.add("quilting")
    for sp in t_all_species(t, v):
        n = sum(1 for i in range(M) if sp in ings[assign[i]]["covers"])
        if not n > (e - 1) * t_tau(sp):
            fails.add("species")
    # assembly
    arr = None
    try:
        arr = []
        for i in range(M):
            Q = ings[assign[i]]["rows"]
            for qr in Q:
                arr.append([qr[H[i][c]] for c in range(k)])
    except IndexError:
        arr = None
        fails.add("assembly")
    sha = None
    if arr is not None:
        text = "".join(" ".join(str(x) for x in r) + "\n" for r in arr)
        sha = hashlib.sha256(text.encode()).hexdigest()
        if not any(x == 0 for r in arr for x in r):
            fails.add("symbols")
        if len(arr) != sc["exp"]["N"]:
            fails.add("N")
        if k != sc["exp"]["k"]:
            fails.add("k")
        if sha != sc["exp"]["sha"]:
            fails.add("sha256")
    return fails, H, widths, arr, sha


def brute_cover(arr, t, v):
    """pure Python exact check, used to validate ca_verify on small arrays"""
    k = len(arr[0])
    need = v ** t
    for cols in itertools.combinations(range(k), t):
        if len({tuple(r[c] for c in cols) for r in arr}) != need:
            return False
    return True


def ca_verify(arr, t, v, tmpdir):
    if arr is None or len(arr[0]) < t:
        return False
    if any(x >= v for r in arr for x in r):
        return False
    path = os.path.join(tmpdir, "arr.txt")
    with open(path, "w") as f:
        f.write("".join(" ".join(str(x) for x in r) + "\n" for r in arr))
    r = subprocess.run([CA_VERIFY, path, str(t), str(v), "2"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    os.remove(path)
    if r.returncode not in (0, 1):
        raise RuntimeError("ca_verify error %d" % r.returncode)
    return r.returncode == 0


# ---------------------------------------------------------------------------
# random generation
# ---------------------------------------------------------------------------

FIELDS = {3: (3, 1, [0, 1]), 4: (2, 2, [1, 1, 1]), 5: (5, 1, [0, 1]), 7: (7, 1, [0, 1]),
          8: (2, 3, [1, 1, 0, 1]), 9: (3, 2, [1, 0, 1])}
REDUCIBLE = {4: [1, 0, 1], 8: [1, 0, 0, 1], 9: [2, 0, 1]}

# (t, v, e, q choices, max k)
CONFIGS = [(2, 2, 1, [3, 4, 5], 125), (2, 2, 2, [3, 4, 5], 125), (2, 3, 2, [3, 4, 5], 125),
           (2, 2, 3, [4, 5], 125), (3, 2, 2, [3, 4, 5, 7], 200), (3, 2, 3, [4, 5], 125),
           (3, 3, 2, [3, 4, 5], 125), (4, 2, 2, [4, 5, 7], 90), (4, 2, 3, [8, 9], 90),
           (3, 2, 2, [5, 7], 200)]


def build_qa(w, t, v, declared, rng):
    """a quilting array covering exactly at least the declared species: greedy, then pruned"""
    rows = []
    sps = set(declared)
    for cols in itertools.combinations(range(w), t):
        seen = {tuple(r[c] for c in cols) for r in rows}
        for tup in itertools.product(range(v), repeat=t):
            if t_species(tup, v) in sps and tup not in seen:
                r = [rng.randrange(v) for _ in range(w)]
                for c, x in zip(cols, tup):
                    r[c] = x
                rows.append(r)
                seen.add(tup)
    if not rows:
        rows.append([rng.randrange(v) for _ in range(w)])
    rng.shuffle(rows)
    i = 0
    while i < len(rows) and len(rows) > 1:
        trial = rows[:i] + rows[i + 1:]
        if t_qa_ok(trial, t, v, sps):
            rows = trial
        else:
            i += 1
    return rows


def mat_text(rows):
    return "".join(" ".join(str(x) for x in r) + "\n" for r in rows)


def new_ing(sc, rows, covers, rng):
    name = "I%d" % len(sc["ingredients"])
    as_file = rng.random() < 0.5
    text = mat_text(rows)
    sc["ingredients"][name] = {"rows": rows, "covers": set(covers), "file": as_file,
                               "text": text,
                               "sha_recorded": hashlib.sha256(text.encode()).hexdigest()}
    return name


def gen_valid(rng):
    while True:
        t, v, e, qs, kmax = rng.choice(CONFIGS)
        q = rng.choice(qs)
        allsp = t_all_species(t, v)
        needmax = max((e - 1) * t_tau(sp) + 1 for sp in allsp)
        if needmax > q + 1:
            continue
        M = rng.randint(max(needmax, 1), q + 1)
        if t == 4 and e == 3:
            M = 9
        explicit = rng.random() < 0.15
        pts = rng.sample(list(range(q + 1)), M)
        fbs = []
        for i in range(M):
            nf = rng.randint(0, max(0, q - t)) if rng.random() < 0.5 else 0
            fbs.append(sorted(rng.sample(range(q), nf)))
        sc = {"t": t, "v": v, "e": e, "field": FIELDS[q], "ingredients": {},
              "family": {"type": "rs", "points": pts, "forbidden": fbs}}
        H, widths = t_family(sc)
        k = len(H[0])
        if k < t + 1:
            continue
        if k > kmax:
            sc["family"]["column_limit"] = rng.randint(max(t + 1, kmax // 2), kmax)
            H, widths = t_family(sc)
            k = len(H[0])
        if explicit:   # relabel symbols within rows and permute columns: still a valid family
            perm = list(range(k))
            rng.shuffle(perm)
            vals = []
            for i in range(M):
                sym = list(range(widths[i]))
                rng.shuffle(sym)
                vals.append([sym[H[i][c]] for c in perm])
            sc["family"] = {"type": "explicit", "values": vals, "widths": widths}
            sc.pop("field")
        # declared species per row
        dens = rng.uniform(0.2, 0.9)
        decl = [set(sp for sp in allsp if rng.random() < dens) for _ in range(M)]
        for sp in allsp:
            need = (e - 1) * t_tau(sp) + 1
            target = need if rng.random() < 0.6 else rng.randint(need, M)
            lacking = [i for i in range(M) if sp not in decl[i]]
            rng.shuffle(lacking)
            while sum(1 for d in decl if sp in d) < target:
                decl[lacking.pop()].add(sp)
        # ingredients, shared between rows of equal width and declaration with prob 0.7
        cache = {}
        assign = []
        for i in range(M):
            key = (widths[i], frozenset(decl[i]))
            if key in cache and rng.random() < 0.7:
                assign.append(cache[key])
                continue
            build_for = set(decl[i])
            if rng.random() < 0.2:
                build_for |= set(rng.sample(allsp, 1))
            rows = build_qa(widths[i], t, v, build_for, rng)
            name = new_ing(sc, rows, decl[i], rng)
            cache[key] = name
            assign.append(name)
        sc["assign"] = assign
        sc["exp"] = {"N": 0, "k": 0, "sha": "0" * 64}
        _, _, _, arr, sha = t_truth(sc)
        sc["exp"] = {"N": len(arr), "k": k, "sha": sha}
        return sc


def clone(sc):
    return _deep(sc)


def _deep(x):
    if isinstance(x, dict):
        return {k: _deep(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_deep(v) for v in x]
    if isinstance(x, set):
        return set(x)
    return x


def refresh_ing(ing, update_sha=True):
    ing["text"] = mat_text(ing["rows"])
    if update_sha:
        ing["sha_recorded"] = hashlib.sha256(ing["text"].encode()).hexdigest()


def finalize_expected(sc):
    """recompute expected N, k, sha for a faulted scenario so only the planted fault shows"""
    sc["exp"] = {"N": 0, "k": 0, "sha": "0" * 64}
    _, H, _, arr, sha = t_truth(sc)
    if arr is not None:
        sc["exp"] = {"N": len(arr), "k": len(H[0]), "sha": sha}
    else:
        sc["exp"] = {"N": 1, "k": len(H[0]), "sha": "0" * 64}


def to_explicit(sc):
    if sc["family"]["type"] == "explicit":
        return
    H, widths = t_family(sc)
    sc["family"] = {"type": "explicit", "values": H, "widths": widths}
    sc.pop("field")


# each fault returns (scenario, planted condition) or None when it does not apply
def f_agree_dup(sc, rng):
    if sc["family"]["type"] != "rs" or len(sc["family"]["points"]) < 2:
        return None
    pts = sc["family"]["points"]
    i, j = rng.sample(range(len(pts)), 2)
    pts[i] = pts[j]
    finalize_expected(sc)
    return sc, "agreement"


def f_agree_explicit(sc, rng):
    to_explicit(sc)
    H = sc["family"]["values"]
    M, k, e = len(H), len(H[0]), sc["e"]
    if M < e:
        return None
    a, b = rng.sample(range(k), 2)
    for i in rng.sample(range(M), e):
        H[i][b] = H[i][a]
    finalize_expected(sc)
    return sc, "agreement"


def f_ing_missing(sc, rng):
    t, v = sc["t"], sc["v"]
    cands = [n for n, g in sc["ingredients"].items() if g["covers"]]
    if not cands:
        return None
    name = rng.choice(cands)
    g = sc["ingredients"][name]
    w = len(g["rows"][0])
    if w < t:
        return None
    sp = rng.choice(sorted(g["covers"]))
    tup = rng.choice([x for x in itertools.product(range(v), repeat=t) if t_species(x, v) == sp])
    cols = sorted(rng.sample(range(w), t))
    keep = [r for r in g["rows"] if tuple(r[c] for c in cols) != tup]
    if not keep:
        keep = [[(x + 1) % v for x in g["rows"][0]]]
        if tuple(keep[0][c] for c in cols) == tup:
            return None
    g["rows"] = keep
    refresh_ing(g)
    finalize_expected(sc)
    return sc, "quilting"


def f_species_short(sc, rng):
    t, v, e = sc["t"], sc["v"], sc["e"]
    M = len(sc["assign"])
    sp = rng.choice(t_all_species(t, v))
    need = (e - 1) * t_tau(sp) + 1
    rows_with = [i for i in range(M) if sp in sc["ingredients"][sc["assign"][i]]["covers"]]
    drop = len(rows_with) - (need - 1)
    if drop <= 0:
        return None
    _, widths = t_family(sc)
    for i in rng.sample(rows_with, drop):
        old = sc["ingredients"][sc["assign"][i]]
        covers = set(old["covers"]) - {sp}
        rows = build_qa(widths[i], t, v, covers, rng)
        sc["assign"][i] = new_ing(sc, rows, covers, rng)
    # drop ingredients no longer assigned
    used = set(sc["assign"])
    sc["ingredients"] = {n: g for n, g in sc["ingredients"].items() if n in used}
    finalize_expected(sc)
    return sc, "species"


def f_corrupt_sem(sc, rng):
    """one ingredient entry changed, sha256 recomputed: a semantic corruption (it may leave the
    ingredient valid, then nothing fails and the case counts as not effective)"""
    name = rng.choice(sorted(sc["ingredients"]))
    g = sc["ingredients"][name]
    i = rng.randrange(len(g["rows"]))
    j = rng.randrange(len(g["rows"][0]))
    g["rows"][i][j] = (g["rows"][i][j] + rng.randrange(1, sc["v"])) % sc["v"]
    refresh_ing(g)
    finalize_expected(sc)
    return sc, "quilting"


def f_corrupt_hash(sc, rng):
    # the recorded sha256 stays that of the original file
    name = rng.choice(sorted(sc["ingredients"]))
    g = sc["ingredients"][name]
    g["file"] = True
    g["sha_recorded"] = hashlib.sha256(mat_text(g["rows"]).encode()).hexdigest()
    i = rng.randrange(len(g["rows"]))
    j = rng.randrange(len(g["rows"][0]))
    g["rows"][i][j] = (g["rows"][i][j] + rng.randrange(1, sc["v"])) % sc["v"]
    g["text"] = mat_text(g["rows"])
    finalize_expected(sc)
    return sc, "ingredient_hash"


def f_wrong_N(sc, rng):
    sc["exp"]["N"] += rng.choice([-1, 1, 5])
    return sc, "N"


def f_wrong_k(sc, rng):
    sc["exp"]["k"] += rng.choice([-1, 1, 3])
    return sc, "k"


def f_wrong_sha(sc, rng):
    s = sc["exp"]["sha"]
    i = rng.randrange(64)
    sc["exp"]["sha"] = s[:i] + ("0" if s[i] != "0" else "1") + s[i + 1:]
    return sc, "sha256"


def f_width(sc, rng):
    """one row narrowed below t with a vacuous all-species ingredient replacing a row"""
    t, v = sc["t"], sc["v"]
    if sc["family"]["type"] != "rs":
        return None
    q = sc["field"][0] ** sc["field"][1]
    M = len(sc["assign"])
    i = rng.randrange(M)
    w = rng.randint(1, t - 1)
    sc["family"]["forbidden"][i] = sorted(rng.sample(range(q), q - w))
    sc["family"].pop("column_limit", None)
    H, widths = t_family(sc)
    if len(H[0]) < t + 1 or len(H[0]) > (120 if t == 4 else 200):
        return None
    rows = [[rng.randrange(v) for _ in range(w)] for _ in range(rng.randint(1, 3))]
    if not any(0 in r for r in rows):
        rows[0][0] = 0
    sc["assign"][i] = new_ing(sc, rows, set(t_all_species(t, v)), rng)
    used = set(sc["assign"])
    sc["ingredients"] = {n: g for n, g in sc["ingredients"].items() if n in used}
    finalize_expected(sc)
    return sc, "width"


def f_symbol(sc, rng):
    name = rng.choice(sorted(sc["ingredients"]))
    g = sc["ingredients"][name]
    g["rows"][rng.randrange(len(g["rows"]))][rng.randrange(len(g["rows"][0]))] = sc["v"]
    refresh_ing(g)
    finalize_expected(sc)
    return sc, "shape"


def f_ing_width(sc, rng):
    name = rng.choice(sorted(sc["ingredients"]))
    g = sc["ingredients"][name]
    if rng.random() < 0.5:
        g["rows"] = [r[:-1] for r in g["rows"]]
    else:
        g["rows"] = [r + [rng.randrange(sc["v"])] for r in g["rows"]]
    refresh_ing(g)
    finalize_expected(sc)
    return sc, "shape"


def f_field(sc, rng):
    if sc["family"]["type"] != "rs":
        return None
    p, m, _ = sc["field"]
    if p ** m not in REDUCIBLE:
        return None
    sc["field"] = (p, m, REDUCIBLE[p ** m])
    finalize_expected(sc)
    return sc, "field"


def f_no_zero(sc, rng):
    """every 0 in every ingredient becomes 1: the array never uses symbol 0"""
    for g in sc["ingredients"].values():
        g["rows"] = [[max(x, 1) for x in r] for r in g["rows"]]
        refresh_ing(g)
    finalize_expected(sc)
    return sc, "symbols"


FAULTS = [("agree_dup_point", f_agree_dup), ("agree_explicit", f_agree_explicit),
          ("ingredient_missing_pattern", f_ing_missing), ("species_too_few_rows", f_species_short),
          ("ingredient_entry_corrupt", f_corrupt_sem), ("ingredient_file_changed", f_corrupt_hash),
          ("wrong_N", f_wrong_N), ("wrong_k", f_wrong_k), ("wrong_sha", f_wrong_sha),
          ("width_below_t", f_width), ("symbol_out_of_range", f_symbol),
          ("ingredient_width_mismatch", f_ing_width), ("reducible_modulus", f_field),
          ("no_symbol_0", f_no_zero)]


# ---------------------------------------------------------------------------
# writing a scenario as a certificate
# ---------------------------------------------------------------------------

def covers_json(covers, t, v, rng):
    allsp = t_all_species(t, v)
    if set(covers) == set(allsp) and rng.random() < 0.5:
        return {"all": True}
    if v == 2:
        ws = sorted(sp[1] for sp in covers)
        if ws and ws == list(range(ws[0], ws[-1] + 1)) and rng.random() < 0.7:
            return {"weights": [ws[0], ws[-1]]}
    return {"species": [list(sp) for sp in sorted(covers)]}


def write_cert(sc, d, rng):
    os.makedirs(d, exist_ok=True)
    t, v = sc["t"], sc["v"]
    cert = {"format": "construction-cert-1", "construction": "powercz-1",
            "t": t, "v": v, "e": sc["e"]}
    if sc["family"]["type"] == "rs":
        p, m, mod = sc["field"]
        q = p ** m
        f = {"q": q, "p": p, "m": m}
        if m > 1:
            f["modulus"] = mod
        cert["field"] = f
        rows = []
        for i, x in enumerate(sc["family"]["points"]):
            r = {"point": "inf" if x == q else x, "ingredient": sc["assign"][i]}
            if sc["family"]["forbidden"][i] or rng.random() < 0.5:
                r["forbidden"] = sc["family"]["forbidden"][i]
            rows.append(r)
        fam = {"type": "reed-solomon", "rows": rows}
        if sc["family"].get("column_limit") is not None:
            fam["column_limit"] = sc["family"]["column_limit"]
    else:
        fam = {"type": "explicit", "rows": [
            {"width": w, "values": vals, "ingredient": sc["assign"][i]}
            for i, (w, vals) in enumerate(zip(sc["family"]["widths"], sc["family"]["values"]))]}
    cert["family"] = fam
    ings = {}
    for name, g in sc["ingredients"].items():
        j = {"covers": covers_json(g["covers"], t, v, rng)}
        if g["file"]:
            fn = name + ".txt"
            with open(os.path.join(d, fn), "w") as f:
                f.write(g["text"])
            j["file"] = fn
            j["sha256"] = g["sha_recorded"]
        else:
            j["rows"] = g["rows"]
        ings[name] = j
    cert["ingredients"] = ings
    cert["expected"] = {"N": sc["exp"]["N"], "k": sc["exp"]["k"], "array_sha256": sc["exp"]["sha"]}
    path = os.path.join(d, "cert.json")
    with open(path, "w") as f:
        json.dump(cert, f)
    return path


# ---------------------------------------------------------------------------
# mutants of the checker
# ---------------------------------------------------------------------------

def _species_ge(c):
    t, v, e = c["t"], c["v"], c["e"]
    decl = [c["ingredients"][r["ingredient"]]["covers"] for r in c["family"]["rows"]]
    return ["x" for sp in cc.species_list(t, v)
            if sum(1 for d in decl if sp in d) < (e - 1) * cc.tau(sp)]


def _agreement_weak(c):
    c2 = dict(c)
    c2["e"] = c["e"] + 1
    return ORIG["agreement"](c2)


def _quilting_any_arrangement(c):
    """bug: a declared species counts as covered on a t-set if one of its tuples appears"""
    t, v = c["t"], c["v"]
    out = []
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        w = len(rows[0])
        for cols in itertools.combinations(range(w), t):
            present = set(tuple(r[j] for j in cols) for r in rows)
            for sp in ing["covers"]:
                if not any(tup in present for tup in cc.arrangements(sp, v)):
                    out.append(name)
    return out


def _quilting_contiguous(c):
    """bug: only contiguous t-sets of columns are checked"""
    t, v = c["t"], c["v"]
    out = []
    for name, ing in c["ingredients"].items():
        rows = ing["rows"]
        w = len(rows[0])
        for s in range(0, w - t + 1):
            cols = tuple(range(s, s + t))
            present = set(tuple(r[j] for j in cols) for r in rows)
            for sp in ing["covers"]:
                if any(tup not in present for tup in cc.arrangements(sp, v)):
                    out.append(name)
    return out


ORIG = dict(cc.CHECKS + cc.POST_CHECKS)
MUTANTS = [("disable:" + n, n, (lambda c: [])) for n in ORIG] + [
    ("species uses >= instead of >", "species", _species_ge),
    ("agreement bound e instead of e-1", "agreement", _agreement_weak),
    ("quilting: one tuple per species suffices", "quilting", _quilting_any_arrangement),
    ("quilting: contiguous t-sets only", "quilting", _quilting_contiguous)]


def install(name, fn):
    cc.CHECKS[:] = [(n, fn if n == name else f) for n, f in cc.CHECKS]
    cc.POST_CHECKS[:] = [(n, fn if n == name else f) for n, f in cc.POST_CHECKS]


def restore():
    cc.CHECKS[:] = [(n, ORIG[n]) for n, _ in cc.CHECKS]
    cc.POST_CHECKS[:] = [(n, ORIG[n]) for n, _ in cc.POST_CHECKS]


def run_checker(path, write=None):
    try:
        res = cc.run(path, write)
        return res["ok"], {f[0] for f in res["failures"]}, res["sha256"]
    except cc.CertError as ex:
        return False, {"malformed:" + str(ex)}, None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    ncases = int(args[args.index("--cases") + 1]) if "--cases" in args else 300
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20261101
    keep = args[args.index("--keep") + 1] if "--keep" in args else None
    rng = random.Random(seed)
    if not os.path.exists(CA_VERIFY):
        os.makedirs(os.path.dirname(CA_VERIFY), exist_ok=True)
        subprocess.check_call(["gcc", "-O3", "-o", CA_VERIFY, CA_VERIFY_SRC, "-lpthread"])
    work = keep or tempfile.mkdtemp(prefix="cztest_", dir=BUILD)
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    cases = []        # (label, cert path, expected fails, planted, covering?, truth sha)
    stats = {}
    oracle_cross = [0, 0]
    errors = []
    n = 0
    while n < ncases:
        base = gen_valid(rng)
        key = "t=%d v=%d e=%d q=%d %s" % (base["t"], base["v"], base["e"],
                                         (base["field"][0] ** base["field"][1]) if "field" in base
                                         else 0, base["family"]["type"])
        if "field" not in base:
            key = "t=%d v=%d e=%d explicit" % (base["t"], base["v"], base["e"])
        stats[key] = stats.get(key, 0) + 1
        variants = [("valid", base)]
        for fname, ffn in FAULTS:
            r = ffn(clone(base), random.Random(rng.random()))
            if r is not None:
                variants.append((fname, r[0], r[1]))
        for var in variants:
            label, sc = var[0], var[1]
            planted = var[2] if len(var) > 2 else None
            d = os.path.join(work, "c%05d_%s" % (len(cases), label))
            path = write_cert(sc, d, rng)
            fails, H, widths, arr, sha = t_truth(sc)
            cover = ca_verify(arr, sc["t"], sc["v"], work)
            # cross-check the oracle with the pure Python brute force on small arrays
            if arr is not None and len(arr[0]) >= sc["t"] and \
                    not any(x >= sc["v"] for r in arr for x in r) and \
                    cc.comb(len(arr[0]), sc["t"]) * len(arr) <= 200000:
                oracle_cross[0] += 1
                if brute_cover(arr, sc["t"], sc["v"]) != cover:
                    oracle_cross[1] += 1
                    errors.append("%s: ca_verify and brute force disagree" % d)
                    with open(os.path.join(BUILD, "disagree_%d.txt" % len(cases)), "w") as f:
                        f.write(mat_text(arr))
            cases.append((label, path, fails, planted, cover, sha, sc["t"], sc["v"]))
        n += 1
    gen_secs = time.time() - t0

    # ---- the real checker on every case
    t1 = time.time()
    by = {}
    theorem_cases = [0, 0]
    agreement_cmp = [0]
    rejected_but_covering = 0
    for label, path, fails, planted, cover, sha, t, v in cases:
        st = by.setdefault(label, {"cases": 0, "accepted": 0, "rejected": 0, "covering": 0,
                                   "planted_effective": 0, "planted_caught": 0})
        st["cases"] += 1
        outp = os.path.join(work, "out.txt")
        ok, got, csha = run_checker(path, outp)
        exp_ok = not fails
        # A5: both exact agreement methods of the checker agree with the independent pairwise
        # evaluation, on the family the checker generated
        try:
            c = cc.load_certificate(path)
            cc.build_family(c)
            if len(c["H"][0]) >= 2:
                agreement_cmp[0] += 1
                m1 = cc.agreement_by_subsets(c["H"], c["e"]) is None
                m2 = cc.agreement_by_pairs(c["H"], c["e"]) is None
                if m1 != m2 or m1 != ("agreement" not in fails):
                    errors.append("A5 %s: subsets %s pairs %s independent %s"
                                  % (path, m1, m2, "agreement" not in fails))
        except cc.CertError:
            pass
        st["accepted" if ok else "rejected"] += 1
        st["covering"] += cover
        if ok != exp_ok:
            errors.append("A1 %s: checker %s, independent evaluation fails %s, checker fails %s"
                          % (path, ok, sorted(fails), sorted(got)))
        if planted and planted in fails:
            st["planted_effective"] += 1
            if planted in got:
                st["planted_caught"] += 1
            else:
                errors.append("A2 %s: planted %s not reported (got %s)" % (path, planted, sorted(got)))
        if ok:
            # A3: the array the checker wrote is the one hashed, it is covering, sha agrees
            with open(outp, "rb") as f:
                wsha = hashlib.sha256(f.read()).hexdigest()
            if not cover or wsha != csha or csha != sha:
                errors.append("A3 %s: accepted but cover=%s sha %s/%s/%s" % (path, cover, wsha, csha, sha))
        elif cover:
            rejected_but_covering += 1
        hyp = {"field", "shape", "width", "agreement", "quilting", "species", "assembly"}
        if not (fails & hyp):
            theorem_cases[0] += 1
            if not cover:
                theorem_cases[1] += 1
                errors.append("A4 %s: hypotheses hold but the array is not covering" % path)
        if os.path.exists(outp):
            os.remove(outp)
    check_secs = time.time() - t1

    print("seed %d, %d base scenarios, %d certificates (generation and ca_verify %.0f s, "
          "checker %.1f s)" % (seed, ncases, len(cases), gen_secs, check_secs))
    print("base scenarios by configuration: " + "; ".join("%s: %d" % kv for kv in sorted(stats.items())))
    print("oracle cross-check: ca_verify vs Python brute force on %d small arrays, %d disagreements"
          % tuple(oracle_cross))
    print("%-28s %6s %8s %8s %8s %10s %8s" % ("case", "certs", "accepted", "rejected", "covering",
                                             "fault real", "caught"))
    for label in ["valid"] + [f for f, _ in FAULTS]:
        if label in by:
            s = by[label]
            print("%-28s %6d %8d %8d %8d %10d %8d" % (label, s["cases"], s["accepted"],
                                                      s["rejected"], s["covering"],
                                                      s["planted_effective"], s["planted_caught"]))
    print("theorem: %d certificates satisfy every hypothesis (independent evaluation); "
          "%d of their arrays fail coverage" % tuple(theorem_cases))
    print("agreement: both exact methods compared with the independent pairwise count on %d "
          "families" % agreement_cmp[0])
    print("rejected certificates whose array is nevertheless covering: %d (the hypotheses are "
          "sufficient, not necessary)" % rejected_but_covering)

    # ---- mutation testing
    if "--no-mutation" not in args:
        print("mutation testing (%d mutants):" % len(MUTANTS))
        survivors = 0
        for mname, check, fn in MUTANTS:
            install(check, fn)
            killed = 0
            unsound = 0
            wrongrec = 0
            try:
                for label, path, fails, planted, cover, sha, t, v in cases:
                    ok, got, csha = run_checker(path)
                    bad = (ok != (not fails)) or (planted and planted in fails and planted not in got)
                    if bad:
                        killed += 1
                    if ok and (not cover or csha != sha):
                        unsound += 1
                    if ok and fails & {"N", "k", "sha256", "ingredient_hash", "symbols"}:
                        wrongrec += 1
            finally:
                restore()
            survivors += killed == 0
            print("  %-44s %-8s by %4d cases; accepts a non-covering array: %4d; accepts a wrong "
                  "record (N, k, sha256, ingredient hash, symbol 0): %4d"
                  % (mname, "KILLED" if killed else "SURVIVED", killed, unsound, wrongrec))
        print("mutants surviving: %d" % survivors)
        if survivors:
            errors.append("%d mutant(s) survived" % survivors)

    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    print("total %.0f s" % (time.time() - t0))
    if errors:
        print("ERRORS (%d):" % len(errors))
        for e in errors[:40]:
            print("  " + e)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
