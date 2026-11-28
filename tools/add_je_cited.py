#!/usr/bin/env python3
"""add_je_cited.py - appends to table/ca_table.csv, as CITED S7 rows, the Johnson-Entringer sizes
CAN(t, t+2, 2) = floor(2^(t+2)/3) for t = 3, 4, 5 and 7 to 10 (t = 6 is already a Colbourn row
dated by cube-je1989, and t = 2 is Kleitman-Spencer and Katona 1973).

Source: K. A. Johnson and R. Entringer, Largest induced subgraphs of the n-cube that contain no
4-cycles, J. Combin. Theory Ser. B 46 (1989) 346-355. The covering array form is stated in
Colbourn, Keri, Rivas Soriano and Schlage-Puchta, Discrete Appl. Math. 158 (2010) 1158-1180,
Section 5.1 ("Johnson and Entringer [24] establish that CAN(n - 2, n, 2) = floor(2^n/3) and that
the corresponding covering array is unique") and Table 7, key beta = [24].

These rows were missing because tools/add_bin_t7_cited.py does not enter values a paper quotes
from another, and CKRS 2010 quotes these from Johnson and Entringer.

Usage, from the repository root:
    python3 tools/add_je_cited.py YYYY-MM-DD           # dry run
    python3 tools/add_je_cited.py YYYY-MM-DD --apply   # append
"""
import csv, io, sys, datetime

DATE = sys.argv[1]
datetime.datetime.strptime(DATE, "%Y-%m-%d")
APPLY = "--apply" in sys.argv[2:]
DOI = "doi:10.1016/0095-8956(89)90054-3"
TS = (3, 4, 5, 7, 8, 9, 10)

raw = open("table/ca_table.csv", "rb").read().decode("utf-8")
lines = raw.split("\r\n"); assert lines[-1] == ""
rows = list(csv.reader(lines[:-1]))
assert rows[0][:5] == ["t", "v", "k", "N", "tier"] and len(rows[0]) == 17
if any(r[7] == DOI and r[4] == "CITED" for r in rows[1:]):
    sys.exit("the rows of add_je_cited.py are already in the table")
new = []
for t in TS:
    k = t + 2; N = 2 ** k // 3
    detail = ("Johnson and Entringer, J. Combin. Theory Ser. B 46 (1989) 346-355, CAN(n-2, n, 2) = floor(2^n/3), "
              "in covering array form in Colbourn, Keri, Rivas Soriano and Schlage-Puchta, Discrete Appl. Math. 158 "
              "(2010) 1158-1180, Section 5.1 and Table 7 key beta: CA(%d; %d, %d, 2)" % (N, t, k))
    notes = ("credit: K. A. Johnson and R. Entringer 1989 (the size, %s); covering array form stated in CKRS 2010 "
             "Section 5.1; no array file checked here" % DOI)
    con = "Johnson-Entringer: CAN(t, t+2, 2) = floor(2^(t+2)/3), the unique optimal array"
    new.append([t, 2, k, N, "CITED", "S7", detail, DOI, "", "", DATE, notes, "", "", con, "cube-je1989", ""])
for r in new:
    print("CA(%d; %d, %d, 2)" % (r[3], r[0], r[2]))
if APPLY:
    b = io.StringIO(); w = csv.writer(b, lineterminator="\r\n")
    for r in new:
        w.writerow(r)
    open("table/ca_table.csv", "wb").write((raw + b.getvalue()).encode("utf-8"))
    print("%d CITED S7 rows added; date %s" % (len(new), DATE))
else:
    print("dry run: %d rows" % len(new))
