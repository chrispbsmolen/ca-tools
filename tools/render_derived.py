#!/usr/bin/env python3
"""render_derived - docs/derived.html from table/derived.csv (tools/derive_table.py).

Lists every size that follows from the counted table by a published construction,
grouped by strength and alphabet, with the counted value it improves on, the
construction and its arithmetic (every ingredient written as CAN(t,k,v)=N, the value
of the lookup at that point). These are computed sizes, not arrays.
"""
import argparse
import collections
import csv
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_table import CSS, REPO_URL  # noqa: E402

LAWS = {
    "fuse": "fusing symbols (Colbourn, Kéri, Rivas Soriano, Schlage-Puchta 2010, Lemma 3.1)",
    "derive": "deriving a strength (CKRS 2010, (7))",
    "comp": "composition (CKRS 2010, (3))",
    "CK": "Chateauneuf-Kreher doubling (Cohen, Colbourn, Ling 2008, Thm 2)",
    "CMTW34": "Colbourn, Martirosyan, Trung, Walker 2006, Thm 3.4",
    "kRoux": "k-ary Roux (CMTW 2006, Thm 3.3; DCAN values of Yin 2003)",
    "PCT": "Power CT (Colbourn and Zhou 2012, Thm 2.1 with Lemma 2.4; Colbourn and Torres-Jimenez 2013)",
    "DP2": "direct product (Colbourn and Torres-Jimenez 2013, Cor 4.3)",
    "OD": "ordered design (Cohen, Colbourn, Ling 2008, Construction 1)",
    "SM": "Shokri and Moura (J. Combin. Des. 2025)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table-dir", default="table")
    ap.add_argument("--out", default="docs/derived.html")
    ap.add_argument("--date", default="")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(os.path.join(a.table_dir, "derived.csv"), newline="", encoding="utf-8")))
    by = collections.defaultdict(list)
    for r in rows:
        by[(int(r["t"]), int(r["v"]))].append(r)
    H = ["<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
         "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
         "<title>Derived sizes</title><style>%s</style></head><body><main>" % CSS,
         "<h1>Sizes that follow by published constructions</h1>",
         "<p>Each line is a size that follows from the <a href=\"index.html\">counted table</a> "
         "(cited and verified entries) by a published construction, and is smaller than the "
         "counted value at that point. These are computed sizes, not arrays in hand; the "
         "counted table does not include them. The list is recomputed from scratch on every "
         "change by <a href=\"%s/blob/main/tools/derive_table.py\">tools/derive_table.py</a> and "
         "checked line by line, independently of that program, by tools/consistency.py. Every "
         "ingredient is written CAN(t,k,v)=N, the value of the lookup (counted or derived) at "
         "that point, so each line can be followed back to table entries. Stair-step as in "
         "the table: a line (t, v, k, N) gives N for up to k columns. %d lines%s.</p>"
         % (REPO_URL, len(rows), (", " + html.escape(a.date)) if a.date else ""),
         "<p>Constructions: " + "; ".join("<b>%s</b> %s" % (k, html.escape(v)) for k, v in LAWS.items()) + ".</p>"]
    for (t, v) in sorted(by):
        rs = sorted(by[(t, v)], key=lambda r: int(r["k"]))
        H.append("<details class=sub><summary>t = %d, v = %d (%d)</summary><table><thead><tr>"
                 "<th>k</th><th>N</th><th>counted</th><th>gain</th><th>construction</th><th>arithmetic</th>"
                 "</tr></thead><tbody>" % (t, v, len(rs)))
        for r in rs:
            H.append("<tr><td class=n>%s</td><td class=n>%s</td><td class=n>%s</td><td class=n>%s%%</td>"
                     "<td>%s</td><td class=ev>%s</td></tr>"
                     % (r["k"], r["N"], r["lookup_N"], r["gain_pct"], html.escape(r["law"]),
                        html.escape(r["arithmetic"])))
        H.append("</tbody></table></details>")
    H.append("</main></body></html>")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(H) + "\n")
    print("wrote %s (%d lines)" % (a.out, len(rows)))


if __name__ == "__main__":
    main()
