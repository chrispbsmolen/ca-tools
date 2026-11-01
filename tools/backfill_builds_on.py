"""backfill_builds_on.py - one-off: adds the column builds_on to
table/ca_table.csv and fills it for the rows that predate it.

Rows are filled from the ids whose keywords (table/references.csv) match the
row's construction text, which for the Colbourn snapshot rows (S1) is
Colbourn's construction label and for the other rows names its sources.
Ids that name a source rather than a method (web-colbourn, web-tj) are never
filled in. The exceptions below are by hand: the Dwyer CA_Database method
codes (S5), and Bai XunDi's construction, described in his Zenodo deposit.
A row whose construction matches nothing is left empty rather than guessed.
Run from the repository root; prints a summary. Idempotent.
"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import builds_on  # noqa: E402

DWYER = {"CKRSsa": "fuse-ckrs2010", "CrossSum": "fuse-ckrs2010", "TJRT": "sa-tr2012",
         "Hnich": "sat-hpss2006", "PGL": "pgl-macc2018", "PGL+": "pgl-macc2018",
         "SCPHF+": "cphf-smc2006"}
BAI = "new doi:10.5281/zenodo.23787055"


def fill(r, refs):
    ids = builds_on.suggest(r["construction"], refs)
    if r["source_id"] == "S5":
        code = r["construction"].split('"')[1] if r["construction"].count('"') >= 2 else ""
        ids = [DWYER[code]] if code in DWYER else []
    if "zenodo.23787055" in r["source_detail"] and r["notes"].startswith("credit: Bai XunDi"):
        return ";".join(ids + [BAI])
    return ";".join(ids)


def main():
    path = os.path.join("table", "ca_table.csv")
    raw = open(path, "rb").read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(raw, newline="")))
    head = rows[0]
    if "builds_on" not in head:
        head.append("builds_on")
        for r in rows[1:]:
            r.append("")
    refs = builds_on.load("table")
    i = head.index("builds_on")
    filled = 0
    for r in rows[1:]:
        d = dict(zip(head, r))
        if not d["builds_on"]:
            r[i] = fill(d, refs)
        filled += bool(r[i])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\r\n").writerows(rows)
    open(path, "wb").write(buf.getvalue().encode("utf-8"))
    print("%d of %d rows have builds_on" % (filled, len(rows) - 1))


if __name__ == "__main__":
    main()
