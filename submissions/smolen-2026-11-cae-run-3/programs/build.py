#!/usr/bin/env python3
"""build.py - rebuild every array of this submission from programs/recipes.json (ca-tools; C. Smolen).
Usage, from the submission folder:  python3 programs/build.py programs/recipes.json OUTDIR [REPO]
REPO (default ../..) is a ca-tools checkout: table arrays are read from REPO/table/arrays, table certificate and
construction commands run in REPO, CAs constructions need R with the package CAs 0.24.4 (constructions only).
Each recipe is a tree: a leaf is a table array, a table command, a CAs construction or an array of this submission;
an inner node is one published construction (programs/laws.py, references in claims.csv)."""
import json, os, sys, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import laws
def load(p):
    with open(p) as f: return [list(map(int, l.split())) for l in f if l.strip()]
def save(p, X):
    with open(p, "w") as f: f.write("\n".join(" ".join(map(str, r)) for r in X) + "\n")
def node(n, repo, here):
    t, v, k = n["t"], n["v"], n["k"]
    if n["kind"] == "file": return laws.cut(load(os.path.join(repo, "table", "arrays", os.path.basename(n["src"]))), k)
    if n["kind"] == "self": return laws.cut(load(os.path.join(here, n["src"])), k)
    if n["kind"] == "cmd":
        d = tempfile.mkdtemp(); cmd = n["src"].replace("CA.txt", os.path.join(d, "CA.txt"))
        if cmd.startswith("tools/cphf/cphfcheck"):
            subprocess.run(["cc", "-O3", "-o", os.path.join(d, "cphfcheck"), os.path.join(repo, "tools/cphf/cphfcheck.c"), "-lm"], check=True)
            cmd = cmd.replace("tools/cphf/cphfcheck", os.path.join(d, "cphfcheck"), 1)
        subprocess.run(["bash", "-c", cmd], cwd=repo, check=True)
        return laws.cut(load(os.path.join(d, "CA.txt")), k)
    if n["kind"] == "cas":
        d = tempfile.mkdtemp(); p = os.path.join(d, "a.txt")
        subprocess.run(["Rscript", "-e", f'suppressMessages(library(CAs)); set.seed(20261112); D <- eval(parse(text=gsub(", ...", "", fixed=TRUE, CAs:::labelToCode("{n["src"]}",{t},{k},{v})))); D <- unclass(D); D <- D - min(D); write.table(D[,1:{k}], "{p}", row.names=FALSE, col.names=FALSE)'], check=True)
        return load(p)
    if n["kind"] == "cyclo":
        return laws.cyclotomic(n["p"], v, k) if n["form"] == "plain" else laws.paley_doubled(n["p"], k) if n["form"] == "doubled" else laws.cyclotomic_shifted(n["p"], v, k)
    if n["kind"] == "direct":
        d = n["src"] if isinstance(n["src"], list) else eval(n["src"])
        X = laws.ksk(d[1], k) if d[0] == "ksk" else laws.bush(d[1], d[2], k) if d[0] == "bush" else laws.rms(d[1], k) if d[0] == "rms" else laws.weight_class(d[1], d[2])
        return laws.cut(X, k)
    A = [node(x, repo, here) for x in n["ing"]]; law = n["law"]
    if law == "fuse": X = laws.fuse(laws.cut(A[0], k), n["params"]["from_v"], v)
    elif law == "derive": X = laws.derive(A[0], v)
    elif law == "dp2": X = laws.direct_product(A[0], A[1], 0, 0)
    elif law == "ctj":
        S = laws.disagreeing_rows(A[0], n["params"]["s"]); T = laws.disagreeing_rows(A[1], n["params"]["r"])
        X = laws.ctj_product(A[0], A[1], v, S[:n["params"]["s"]], T[:n["params"]["r"]])
    elif law == "add1": X = laws.add_column(laws.cut(A[0], k - 1), laws.cut(laws.strength1(k - 2, v) if t == 3 else A[1], k - 2), v)
    elif law == "comp": X = laws.composition(laws.cut(A[0], k), laws.cut(A[1], k), v // n["params"]["v1"])
    elif law == "ck": h = -(-k // 2); X = laws.ck_doubling(laws.cut(A[0], h), laws.cut(A[1], h), v)
    elif law == "cmtw34": h = max(3, -(-k // v)); X = laws.cmtw34(laws.cut(A[0], h), laws.cut(A[1], h), v)
    elif law == "hartman4":
        h = -(-k // 2); X = laws.hartman4(laws.cut(A[0], h), laws.cut(A[1], h), laws.cut(A[2], h), v)
    elif law == "kroux":
        h, l = n["params"]["h"], n["params"]["l"]; X = laws.kary_roux(laws.cut(A[0], h), laws.cut(A[1], l), laws.cut(A[2], l), v, h, l)
    elif law == "od": X = laws.ordered_design(v - 1, A[0], k)
    elif law == "phf": X = laws.power_phf(n["params"]["q"], n["params"]["e"], t, laws.cut(A[0], n["params"]["q"]), v, k)
    elif law == "pdouble": X = laws.partial_doubling(A[0], n["params"]["r"], n["params"]["s"])
    else: raise SystemExit("unknown construction " + law)
    return laws.cut(X, k)
if __name__ == "__main__":
    R = json.load(open(sys.argv[1])); out = sys.argv[2]; repo = sys.argv[3] if len(sys.argv) > 3 else os.path.join("..", "..")
    here = os.getcwd(); os.makedirs(out, exist_ok=True)
    for name, tree in R.items():
        X = node(tree, repo, here); save(os.path.join(out, name), X); print(name, len(X), "x", len(X[0]))
