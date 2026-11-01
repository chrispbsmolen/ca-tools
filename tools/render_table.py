#!/usr/bin/env python3
"""render_table - write the static table page (docs/index.html).

Reads table/ca_table.csv and table/MANIFEST.csv and writes one plain
HTML page: what the table is, counts of verified and screened arrays,
the community submissions with their credit, and for every (t, v) the
current best known N as a stair-step, each rung marked with its
evidence (verified rows with their stamp and credit). No JavaScript.
Standard library only.

Usage: render_table.py [--table-dir table] [--out docs/index.html] [--date YYYY-MM-DD]
"""
import argparse
import collections
import csv
import datetime
import html
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "table"))
from ca_table import counted, check_method, identity  # noqa: E402  (the one definition of the counted rows)
REPO_URL = "https://github.com/chrispbsmolen/ca-tools"
RAW_CSV = "https://raw.githubusercontent.com/chrispbsmolen/ca-tools/main/table/ca_table.csv"

CSS = """
:root { color-scheme: light dark; --fg:#1d1d1f; --bg:#fdfdfc; --mute:#5f6368;
  --line:#dcdcd8; --ver:#0b6e3a; --scr:#8a5a00; --dis:#a8321e; --soft:#f2f2ee; }
@media (prefers-color-scheme: dark) { :root { --fg:#e8e8e3; --bg:#18181a;
  --mute:#a0a0a0; --line:#3a3a3d; --ver:#5fd08f; --scr:#e0b050; --dis:#f08a74; --soft:#232326; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 52rem; margin: 0 auto; padding: 1.5rem 16px 4rem; }
h1 { font-size: 1.6rem; line-height:1.25; margin: 0 0 .5rem; }
h2 { font-size: 1.2rem; margin: 2rem 0 .5rem; border-bottom: 1px solid var(--line); padding-bottom:.25rem; }
p, li { overflow-wrap: anywhere; }
.mute { color: var(--mute); font-size: .9rem; }
.stats { display:flex; flex-wrap:wrap; gap:.5rem; margin:1rem 0; padding:0; list-style:none; }
.stats li { background:var(--soft); border-radius:6px; padding:.4rem .7rem; }
.stats b { font-variant-numeric: tabular-nums; }
table { border-collapse: collapse; width:100%; font-size:.9rem; margin:.5rem 0 1rem; }
th, td { text-align:left; vertical-align:top; padding:.3rem .4rem; border-bottom:1px solid var(--line); }
td.n, th.n { text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap; }
td.ev { overflow-wrap:anywhere; }
details { border-bottom:1px solid var(--line); padding:.35rem 0; }
summary { cursor:pointer; }
.tag { display:inline-block; font-size:.75rem; font-weight:600; border-radius:4px; padding:0 .35rem;
  border:1px solid currentColor; margin-right:.3rem; }
.ver { color:var(--ver); } .scr { color:var(--scr); } .dis { color:var(--dis); } .lit { color:var(--mute); }
.stamp { color:var(--mute); font-size:.8rem; display:block; }
.subhead { font-size:.9rem; margin:.4rem 0; overflow-wrap:anywhere; }
.lbl { color:var(--mute); font-size:.8rem; margin-right:.3rem; }
.bo { display:block; color:var(--mute); font-size:.8rem; }
details.sub > summary { padding:.15rem 0; }
a { color: inherit; }
@media (max-width: 480px) { body { font-size:15px; } table { font-size:.82rem; } th, td { padding:.25rem .2rem; } }
"""


def load(table_dir):
    with open(os.path.join(table_dir, "ca_table.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(os.path.join(table_dir, "MANIFEST.csv"), newline="", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    for r in rows:
        r["t"], r["v"], r["k"] = int(r["t"]), int(r["v"]), int(r["k"])
        r["N"] = int(float(r["N"]))
    return rows, manifest


def credit_of(r):
    """The text after "credit: " up to the first semicolon outside parentheses
    (a semicolon inside, as in CA(15; 3, 12, 2), belongs to the credit)."""
    notes = r.get("notes") or ""
    i = notes.find("credit: ")
    if i < 0:
        return ""
    s = notes[i + len("credit: "):]
    depth = 0
    for j, ch in enumerate(s):
        if ch == ";" and depth == 0:
            return s[:j].strip()
        depth = max(0, depth + (ch == "(") - (ch == ")"))
    # unbalanced parentheses: fall back to the first semicolon
    return (s.split(";", 1)[0] if depth > 0 else s).strip()


CR = {}


def constant_rows_of(r):
    c = CR.get(r.get("array_sha256") or "", "")
    return ("constant rows %s of %s" % (c, r["v"])) if c not in ("", None) else ""


SHA2FILE = {}
SHA2CERT = {}
SHA2EXT = {}      # table/EXTERNAL.csv: arrays kept in a public deposit
DERIVED_COUNT = [0]   # lines of table/derived.csv
CERT_URL = "https://raw.githubusercontent.com/chrispbsmolen/ca-tools/main/table/certificates/"
LOG_URL = REPO_URL + "/blob/main/table/VERIFICATION_LOG.md"
ARRAY_URL = "https://raw.githubusercontent.com/chrispbsmolen/ca-tools/main/table/arrays/"


def row_key(r):
    """What identifies a row's array on this page: its array_sha256, or, for a certificate row whose
    array is not hashed (more than 10^12 entries), "family:" and its family_sha256
    (table/ca_table.py identity())."""
    kind, ident = identity(r)
    return "family:" + ident if kind == "family" else ident


def identity_html(r):
    """sha256 abcdef123456, or identity: family abcdef123456 (array not hashed)"""
    kind, ident = identity(r)
    if kind == "family":
        return "identity: family %s (array not hashed)" % html.escape(ident[:12])
    return "sha256 %s" % html.escape(ident[:12])


def stamp_html(r):
    """The verification stamp with links: the verifier it names (caverify by
    version, on CRAN; ca_verify by the commit of its source), the stored array
    if there is one, and the verification log."""
    st = r.get("verify_stamp") or ""
    m = re.match(r"^(caverify) (\S+)(.*)$", st)
    m2 = re.match(r"^(ca_verify) ([0-9a-f]{7,40})(.*)$", st)
    m3 = re.match(r"^(repcheck|repcheck_pp|cphfcheck) ([0-9a-f]{12})(.*)$", st)
    if m:
        head = '<a href="https://cran.r-project.org/package=caverify">%s %s</a>%s' % (
            m.group(1), html.escape(m.group(2)), html.escape(m.group(3)))
    elif m2:
        head = '<a href="%s/blob/%s/ca_verify.c">%s %s</a>%s' % (
            REPO_URL, m2.group(2), m2.group(1), m2.group(2), html.escape(m2.group(3)))
    elif m3:
        head = '<a href="%s/blob/main/tools/cphf/%s.c">%s %s</a>%s' % (
            REPO_URL, m3.group(1), m3.group(1), m3.group(2), html.escape(m3.group(3)))
    else:
        head = html.escape(st)
    links = []
    f = SHA2FILE.get(r.get("array_sha256") or "")
    if f:
        links.append('<a href="%s%s">%s</a>' % (ARRAY_URL, html.escape(f), "array, gzip" if f.endswith(".gz") else "array"))
    x = SHA2EXT.get(r.get("array_sha256") or "")
    if x:
        links.append('<a href="%s">array, in deposit</a>' % html.escape(x.split("::", 1)[0], quote=True))
    c = SHA2CERT.get(row_key(r))
    if c:
        links.append('<a href="%s%s">certificate</a>' % (CERT_URL, html.escape(c)))
    links.append('<a href="%s">verification log</a>' % LOG_URL)
    m = check_method(r) if r.get("tier") == "VERIFIED" else None
    label = '<b class=method>%s</b>: ' % m if m else ""
    return label + head + " (" + ", ".join(links) + ")"


REFS = {}       # id -> reference (tools/builds_on.py), filled by main()
REFS_USED = set()


def short_ref(rid):
    """Author-year label for a reference: 'Paley 1933', 'Colbourn and Zhou
    2012', 'Sherwood et al. 2006'; the id when the reference cannot be read."""
    ref = REFS[rid]["reference"]
    m = re.search(r"\((\d{4})\)", ref) or re.search(r"\b(1[89]\d\d|20\d\d)\b", ref)
    year = m.group(1) if m else ""
    head = ref.split(", ")
    names = []
    for part in head:
        for a in part.split(" and "):
            a = a.strip()
            if re.fullmatch(r"(?:[A-Z][a-z]?\.(?:-[A-Z]\.)? ?)+[A-Z][\w'-]+(?: [A-Z][\w'-]+)*", a) \
                    or re.fullmatch(r"Tran Van Trung", a):
                names.append(a)
            else:
                break
        else:
            continue
        break
    sur = [re.sub(r"^(?:[A-Z][a-z]?\.(?:-[A-Z]\.)? ?)+", "", n) for n in names]
    if not sur:
        return rid
    who = sur[0] if len(sur) == 1 else ("%s and %s" % tuple(sur) if len(sur) == 2
                                        else sur[0] + " et al.")
    return (who + " " + year).strip()


def builds_on_html(r):
    """The works a row builds on, as author-year links to the list at the
    foot of the page, and 'new method' links for a submitter's own method."""
    out = []
    for part in (r.get("builds_on") or "").split(";"):
        part = part.strip()
        if part in REFS:
            REFS_USED.add(part)
            out.append('<a href=#r%d>%s</a>' % (list(REFS).index(part) + 1,
                                                html.escape(short_ref(part))))
        elif part.startswith("new "):
            link = part[4:].strip()
            url = link if link.startswith("http") else (
                "https://doi.org/" + link[4:] if link.startswith("doi:") else
                "https://arxiv.org/abs/" + link[6:] if link.startswith("arXiv:") else "")
            out.append('<a href="%s">new method</a>' % html.escape(url) if url
                       else "new method (%s)" % html.escape(link))
    return ", ".join(out)


def construction_of(r):
    """The construction column; for rows that predate it, the source_detail
    of a CITED row is Colbourn's construction label."""
    c = (r.get("construction") or "").strip()
    if not c and r.get("tier") == "CITED":
        c = (r.get("source_detail") or "").strip()
    return c


def slug_of(r):
    m = re.search(r"submission ([A-Za-z0-9._-]+)", r.get("notes") or "")
    return m.group(1) if m else "(unnamed)"


def submissions_html(subs):
    """One folded <details> per submission. Text that is the same for every
    array of a submission (credit, construction, stamp, entry date) is shown
    once above its table; text that differs stays in a column."""
    out = []
    groups = collections.OrderedDict()
    for r in sorted(subs, key=lambda r: (r["entered"], slug_of(r), r["t"], r["v"], r["k"]),
                    reverse=True):
        groups.setdefault(slug_of(r), []).append(r)
    shared_fields = (("credit", credit_of), ("construction", construction_of),
                     ("builds on", lambda r: r.get("builds_on", "")),
                     ("stamp", lambda r: r["verify_stamp"]), ("entered", lambda r: r["entered"]))
    for slug, rs in groups.items():
        rs = sorted(rs, key=lambda r: (r["t"], r["v"], r["k"]))
        nver = sum(1 for r in rs if r["tier"] == "VERIFIED")
        nscr = len(rs) - nver
        vs = sorted({r["v"] for r in rs}); ts = sorted({r["t"] for r in rs})
        span = lambda xs: str(xs[0]) if len(xs) == 1 else "%d to %d" % (xs[0], xs[-1])
        uniform = {name: len({f(r) for r in rs}) == 1 for name, f in shared_fields}
        # stamp and entry date: the most common value is shown once, and a
        # row with a different one carries it under its status, so a few
        # later checks do not add wide columns
        common = {}
        for name, f in shared_fields:
            if name in ("stamp", "entered") and not uniform[name]:
                common[name] = collections.Counter(f(r) for r in rs).most_common(1)[0][0]
        credits = sorted({credit_of(r) for r in rs})
        out.append("<details class=sub><summary><b>%s</b>, %s: %d array%s (%s), t = %s, "
                   "v = %s, entered %s</summary>" % (
                       html.escape(", ".join(credits)), html.escape(slug), len(rs),
                       "" if len(rs) == 1 else "s",
                       ", ".join(x for x in ("%d verified" % nver if nver else "",
                                             "%d screened" % nscr if nscr else "") if x),
                       span(ts), span(vs), html.escape(min(r["entered"] for r in rs))))
        lines = []
        for name, f in shared_fields:
            show = ((lambda r0: stamp_html(r0)) if name == "stamp" else
                    (lambda r0: builds_on_html(r0)) if name == "builds on" else
                    (lambda r0, f=f: html.escape(f(r0))))
            if uniform[name] and f(rs[0]):
                lines.append("<span class=lbl>%s</span> %s" % (name, show(rs[0])))
            elif name in common:
                n = sum(1 for r in rs if f(r) == common[name])
                r0 = next(r for r in rs if f(r) == common[name])
                lines.append("<span class=lbl>%s</span> %s (%d of %d arrays, the others noted "
                             "in their rows)" % (name, show(r0), n, len(rs)))
        if lines:
            out.append("<p class=subhead>%s</p>" % "<br>".join(lines))
        cols = [name for name, _ in shared_fields if not uniform[name] and name not in common]
        out.append("<table><thead><tr><th class=n>t</th><th class=n>v</th><th class=n>k</th>"
                   "<th class=n>N</th><th class=n>prev. best</th><th class=n>const. rows</th>"
                   "<th>status</th>%s</tr></thead><tbody>"
                   % "".join("<th>%s</th>" % c for c in cols))
        for r in rs:
            prev = re.search(r"previous best (\d+)", r["notes"])
            c = CR.get(r.get("array_sha256") or "", "")
            tag = ('<span class="tag ver">verified</span>' if r["tier"] == "VERIFIED"
                   else '<span class="tag scr">screened</span>')
            extra = "".join("<td class=ev>%s</td>" % html.escape(f(r))
                            for name, f in shared_fields if name in cols)
            note = "".join("<span class=stamp>%s %s</span>" % (name, stamp_html(r) if name == "stamp" else html.escape(f(r)))
                           for name, f in shared_fields
                           if name in common and f(r) != common[name])
            af = SHA2FILE.get(r.get("array_sha256") or "")
            cf = SHA2CERT.get(row_key(r))
            tag = tag + note + ('<span class=stamp><a href="%s%s">array</a></span>' % (ARRAY_URL, html.escape(af)) if af else "")
            tag = tag + ('<span class=stamp><a href="%s%s">certificate</a></span>' % (CERT_URL, html.escape(cf)) if cf else "")
            xf = SHA2EXT.get(r.get("array_sha256") or "")
            tag = tag + ('<span class=stamp><a href="%s">array, in deposit</a></span>' % html.escape(xf.split("::", 1)[0], quote=True) if xf else "")
            out.append("<tr><td class=n>%d</td><td class=n>%d</td><td class=n>%d</td>"
                       "<td class=n>%d</td><td class=n>%s</td><td class=n>%s</td><td>%s</td>%s</tr>"
                       % (r["t"], r["v"], r["k"], r["N"], prev.group(1) if prev else "",
                          ("%s of %d" % (c, r["v"])) if c not in ("", None) else "", tag, extra))
        out.append("</tbody></table></details>")
    return out


# the page legend for the table's columns; table/README.md "Schema" is the full text
LEGEND = [
    ("t, v, k, N", "the claim: N runs suffice for a covering array of strength t on up to k "
     "columns of v symbols (stair-step: the best known N at k is the smallest N among "
     "entries with at least k columns)"),
    ("tier", "the evidence class. <b>CITED</b>: traceable to a dated snapshot or publication, "
     "no array in hand (the 13,641 baseline rows are Colbourn's tables of November 2024). "
     "<b>VERIFIED</b>: an explicit array was checked exhaustively at strength t. "
     "<b>SCREENED</b>: an array too large for the public check, screened on random column "
     "windows, listed but not counted as best known. <b>FAILED_PENDING_RECHECK</b>: a "
     "verification attempt that failed its dimension check, kept and superseded by a later "
     "row. <b>DISPUTED</b> (since 2026-10-23): an added row beside a CITED entry whose cited "
     "construction, as implemented and checked here, did not give a covering array at the "
     "recorded size; the CITED "
     "row stays as recorded and is still counted, and the rung is marked disputed"),
    ("source_id", "the source class. <b>S1</b> Colbourn's tables (the CAs snapshot), "
     "<b>S4</b> NIST covering array library, <b>S5</b> Dwyer CA_Database, <b>S6</b> data "
     "and constructions of the CAs package, <b>S7</b> literature and community submissions, <b>S8</b> arrays "
     "built by this project with its own scripts (tools/own_arrays, tools/cphf), verified in full, an array too "
     "large to store through its checked certificate (table/certificates)"),
    ("source_detail", "the exact retrieval or generation recipe (URL and commit, or the "
     "generating call and package version)"),
    ("snapshot_id", "the dated source: <code>colbourn-2024-11-ug</code> for the baseline, "
     "<code>pr-N</code> (or the submission folder name) for a submission, the DOI or the "
     "arXiv id with version (for example <code>doi:10.3390/math12121908</code>, "
     "<code>arXiv:2510.13122v2</code>) for a paper, empty where "
     "<code>source_detail</code> already carries a dated recipe"),
    ("array_sha256", "SHA-256 of the array in canonical form (0-based symbols, one run per "
     "line), for rows with an array"),
    ("verify_stamp", "the verifier, its version or commit, the date and the machine; on this page "
     "each stamp links to that verifier (caverify on CRAN, or the ca_verify source at that commit), "
     "to the array file or certificate where one is stored, and to the verification log"),
    ("entered", "the date the row was added"),
    ("notes", "comparison with the previous best as of entry, credit, submission, and supersession "
     "notes; every construction belongs to the sources the row names, and a row whose construction "
     "is this project's own says so"),
    ("builds_on", "the published work the entry's construction rests on: ids of "
     "<a href=\"%s/blob/main/table/references.csv\">table/references.csv</a>, shown on this page "
     "as author-year links to the list at the foot of the page, and 'new' with a link for a "
     "method of the submitter's own. Empty where the source of a construction is not known; "
     "never guessed" % REPO_URL),
    ("lb, lb_evidence", "reserved for lower-bound evidence, empty in every row so far"),
    ("construction", "the construction or search that produced the entry, in a researcher's "
     "words; for the baseline it is Colbourn's own label. Where Colbourn's table and a verified "
     "array give the same entry, the page shows both, labelled. The Dwyer source codes are "
     "Aaron Dwyer's abbreviations for the method; many of his arrays cite personal "
     "communication with Colbourn"),
    ("family_sha256", "since 2026-11-02, for a row given by a covering perfect hash family: the SHA-256 "
     "of the family in its canonical form (cphf1, tools/cphf/README.md). An array of more than 10^12 "
     "entries is not hashed; such a row has an empty array_sha256 and is identified by its family, "
     "shown on this page as \"identity: family ... (array not hashed)\""),
]


def stair(rows_tv):
    """Rungs (N, k_from, k_to, evidence rows) from the counted rows (CITED and
    VERIFIED, less retracted rows; table/ca_table.py counted())."""
    ev = counted(rows_tv)
    pairs = sorted({(r["N"], r["k"]) for r in ev})
    rungs, bestk = [], (rows_tv[0]["t"] - 1 if rows_tv else 0)
    for n, k in pairs:
        if k > bestk:
            rungs.append([n, bestk + 1, k])
            bestk = k
    out = []
    for n, k0, k1 in rungs:
        rs = [r for r in ev if r["N"] == n and r["k"] == k1]
        out.append((n, k0, k1, rs))
    return out


DWYER_TAIL = " (Aaron Dwyer's abbreviation for the method; many of his arrays cite personal communication with Colbourn)"


def page_text(c):
    """Construction text as shown on the page: the sentence every Dwyer row
    repeats is said once in the legend instead (the data are unchanged)."""
    return c[:-len(DWYER_TAIL)] if c.endswith(DWYER_TAIL) else c


def evidence_html(rs):
    """A rung's evidence. Every verified array on the rung is shown (one per
    array, by hash), each with its verified tag, and when Colbourn's table
    has the same entry its own construction label is shown beside it, so a
    reader does not take the verified array to come from Colbourn's
    construction."""
    ver, seen = [], set()
    # when several rows carry the same array, show the one built here (S8) first
    for r in sorted(rs, key=lambda x: x.get("source_id") != "S8"):
        if r["tier"] == "VERIFIED" and row_key(r) not in seen:
            seen.add(row_key(r)); ver.append(r)
    cited = [r for r in rs if r["tier"] == "CITED" and r["source_id"] == "S1"]
    lit = [r for r in rs if r["tier"] == "CITED" and r["source_id"] != "S1"]
    parts = []
    if cited and (ver or lit):
        bo = builds_on_html(cited[0])
        parts.append('<span class=lbl>Colbourn\'s table</span> %s%s<br>' %
                     (html.escape(construction_of(cited[0]) or cited[0]["source_detail"]),
                      '<span class=bo>builds on %s</span>' % bo if bo else ""))
    for r in lit:
        # a size published in a paper, no array in hand (tier CITED, source S7)
        cr = credit_of(r)
        con = construction_of(r)
        bo = builds_on_html(r)
        parts.append('<span class="tag lit">published</span>%s%s%s%s<br>' % (
            html.escape(cr + "; ") if cr else "",
            ("<i>%s</i>; " % html.escape(con)) if con else "",
            html.escape(r["source_detail"]),
            '<span class=bo>builds on %s</span>' % bo if bo else ""))
    vparts = []
    for r in ver:
        cr = credit_of(r)
        con = page_text(construction_of(r))
        crs = constant_rows_of(r)
        vparts.append('<span class="tag ver">verified</span>%s%s%s'
                     '<span class="stamp">%s%s, %s%s</span>' % (
                         html.escape(cr + "; ") if cr else "",
                         ("<i>%s</i>; " % html.escape(con)) if con else "",
                         html.escape(r["source_detail"]),
                         ("builds on %s; " % builds_on_html(r)) if builds_on_html(r) else "",
                         stamp_html(r), identity_html(r),
                         (", " + crs) if crs else ""))
    parts.append("".join(vparts))
    if not ver and not lit:
        r = rs[0]
        bo = builds_on_html(r)
        parts.append(html.escape(construction_of(r) or r["source_detail"] or r["source_id"]) +
                     ('<span class=bo>builds on %s</span>' % bo if bo else ""))
    return "".join(parts)


def disputed_html(d, rows_tv):
    """The mark for a CITED entry that has a DISPUTED row: what was checked, and
    the best value at this point once the disputed CITED rows are left out, when
    that value is a verified array."""
    dis = {(r["k"], r["N"]) for r in rows_tv if r["tier"] == "DISPUTED"}
    rest = [r for r in rows_tv if r["k"] >= d["k"] and (
        r["tier"] == "VERIFIED" or (r["tier"] == "CITED" and (r["k"], r["N"]) not in dis))]
    out = ('<br><span class="tag dis">disputed</span>the construction recorded for this entry, '
           '<i>%s</i>, did not give a covering array at the recorded size when checked here '
           '(<code>%s</code>); the recorded size stays listed and counted, and is not shown to '
           'be unreachable (<a href="%s">verification log</a>)'
           % (html.escape(d["construction"] or d["source_detail"]),
              html.escape(d["source_detail"]), LOG_URL))
    if any(r["tier"] == "VERIFIED" and r["N"] <= d["N"] for r in rest):
        out += ('<span class="stamp">a verified array of at most %d rows now covers this point</span>'
                % d["N"])
    elif rest:
        best = min(r["N"] for r in rest)
        ver = sorted((r for r in rest if r["tier"] == "VERIFIED" and r["N"] == best),
                     key=lambda r: -r["k"])
        if ver:
            a = ver[0]
            out += ('<span class="stamp">verified at this point: N = %d (%s), %s, %s%s</span>'
                    % (a["N"], html.escape(page_text(construction_of(a))), stamp_html(a),
                       identity_html(a),
                       (", " + constant_rows_of(a)) if constant_rows_of(a) else ""))
    return out


def render(rows, manifest, date):
    global CR
    CR = {m["sha256"]: m.get("constant_rows", "") for m in manifest}
    SHA2FILE.clear(); SHA2FILE.update({m["sha256"]: m["file"] for m in manifest})
    # a SCREENED row whose array was later verified in full (a VERIFIED row
    # with the same hash) is superseded: kept in the table, not shown
    verified_sha = {row_key(r) for r in rows if r["tier"] == "VERIFIED" and row_key(r)}
    rows_shown = [r for r in rows if not (r["tier"] == "SCREENED" and row_key(r) in verified_sha)]
    tiers = collections.Counter(r["tier"] for r in rows_shown)
    mstat = collections.Counter(m["status"] for m in manifest)
    # community submissions are the S7 rows that came through the submission check (their notes
    # name the submission); S7 rows entered from the literature appear in the stair-steps only
    subs = [r for r in rows_shown if r["source_id"] == "S7" and r["tier"] in ("VERIFIED", "SCREENED")
            and slug_of(r) != "(unnamed)"]
    by_tv = collections.defaultdict(list)
    for r in rows:
        by_tv[(r["t"], r["v"])].append(r)

    H = []
    H.append("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
             "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
             "<title>Covering Array Table</title><style>%s</style></head><body><main>" % CSS)
    H.append("<h1>Best known covering arrays, with evidence</h1>")
    H.append("<p>A covering array CA(N; t, k, v) is an N by k array over v symbols in which "
             "every choice of t columns shows every one of the v<sup>t</sup> value "
             "combinations in some row. This table records, for each strength t and "
             "alphabet size v, the smallest known N for each number of columns k, and "
             "says where every entry comes from. The baseline is the November 2024 "
             "status of Charles J. Colbourn's covering array tables as preserved by "
             "Ulrike Groemping in the CAs R package (tier CITED). Sizes published in papers "
             "and not in the snapshot are also tier CITED, each naming its paper (source S7, marked "
             "published), until an array is in hand. Entries with an "
             "explicit array in hand were checked exhaustively by a verifier and carry "
             "the array's SHA-256 and a stamp (tier VERIFIED). Arrays too large to check "
             "in full on the public runner were screened on random column windows "
             "(tier SCREENED); they are listed but do not count as best known. Where Colbourn's "
             "construction for an entry, as checked here, did not give a covering array at the "
             "recorded size, the "
             "entry stays as recorded and its rung is marked disputed (tier DISPUTED). No entry "
             "here is a computed size. Sizes that follow from these entries by published "
             "constructions (fusing symbols, deriving a strength, Power CT and others) are "
             "recomputed on every change and listed separately, each with its arithmetic, on "
             "<a href=\"derived.html\">the derived sizes page</a> (%s points); they are not "
             "counted as best known here.</p>" % DERIVED_COUNT[0])
    H.append("<p>Rows are stair-steps: an entry (t, v, k, N) means N runs suffice for up "
             "to k columns, so the best known N at k is the smallest N among entries with "
             "at least k columns. The construction column names the construction or "
             "search that produced each entry, where it is known. For every array on file, "
             "constant rows is the largest number of its rows that can be made constant by "
             "permuting symbols within columns, a property that matters when the array is an "
             "ingredient of another construction. Anyone can add an array by pull request; see "
             "<a href=\"%s/blob/main/submissions/README.md\">how to submit</a>. The data "
             "is <a href=\"%s/tree/main/table\">table/ in the repository</a>; the raw file "
             "<a href=\"%s\">table/ca_table.csv</a> is the machine-readable form "
             "(see the README for the stair-step rule and an R snippet).</p>"
             % (REPO_URL, REPO_URL, RAW_CSV))
    H.append("<ul class=\"stats\">")
    for label, n in (("table rows", len(rows)), ("verified rows", tiers["VERIFIED"]),
                     ("rows cited from papers", sum(1 for r in rows if r["tier"] == "CITED" and r["source_id"] != "S1")),
                     ("screened rows, not yet verified in full", tiers["SCREENED"]),
                     ("disputed entries", tiers["DISPUTED"]), ("arrays on file", len(manifest)),
                     ("verified arrays", len(manifest) - mstat["screened"]),
                     ("screened arrays", mstat["screened"]),
                     ("community submissions", len({slug_of(r) for r in subs})),
                     ("arrays from submissions", len(subs))):
        H.append("<li>%s <b>%s</b></li>" % (label, "{:,}".format(n)))
    H.append("</ul>")
    H.append("<p class=\"mute\">Generated %s from table/ca_table.csv and "
             "table/MANIFEST.csv.</p>" % html.escape(date))

    H.append("<details><summary>What the columns of ca_table.csv mean</summary>")
    H.append("<table><thead><tr><th>column</th><th>meaning</th></tr></thead><tbody>")
    for col, meaning in LEGEND:
        H.append("<tr><td><code>%s</code></td><td class=ev>%s</td></tr>" % (html.escape(col), meaning))
    H.append("</tbody></table><p class=\"mute\">The full schema is in "
             "<a href=\"%s/blob/main/table/README.md\">table/README.md</a>.</p></details>" % REPO_URL)

    H.append("<h2>Community submissions</h2>")
    if not subs:
        H.append("<p>None yet.</p>")
    else:
        H.append("<p class=\"mute\">One entry per submission, newest first. Open one to "
                 "see its arrays.</p>")
        H.extend(submissions_html(subs))

    H.append("<h2>Best known N by strength and alphabet</h2>")
    H.append("<p class=\"mute\">Open a (t, v) pair to see its stair-step. Each rung gives "
             "the column range it serves, the best known N, and its evidence.</p>")
    for (t, v) in sorted(by_tv):
        rs = by_tv[(t, v)]
        steps = stair(rs)
        nver = sum(1 for _, _, _, e in steps if any(r["tier"] == "VERIFIED" for r in e))
        scr = [r for r in rs if r["tier"] == "SCREENED" and row_key(r) not in verified_sha]
        dis = {(r["k"], r["N"]): r for r in rs if r["tier"] == "DISPUTED"}
        H.append("<details><summary>t = %d, v = %d: %d rungs, %d verified%s%s</summary>"
                 % (t, v, len(steps), nver,
                    ", %d screened" % len(scr) if scr else "",
                    ", %d disputed" % len(dis) if dis else ""))
        H.append("<table><thead><tr><th class=n>k</th><th class=n>N</th>"
                 "<th>evidence</th></tr></thead><tbody>")
        for n, k0, k1, e in steps:
            krange = str(k1) if k0 == k1 else "%d to %d" % (k0, k1)
            H.append("<tr><td class=n>%s</td><td class=n>%d</td><td class=ev>%s%s</td></tr>"
                     % (krange, n, evidence_html(e),
                        disputed_html(dis[(k1, n)], rs) if (k1, n) in dis else ""))
        rung_keys = {(k1, n) for n, _, k1, _ in steps}
        for (dk, dn), d in sorted(dis.items()):
            if (dk, dn) not in rung_keys:
                H.append("<tr><td class=n>%d</td><td class=n>%d</td><td class=ev>%s%s</td></tr>"
                         % (dk, dn, html.escape(construction_of(next(
                             (r for r in rs if r["tier"] == "CITED" and r["k"] == dk and r["N"] == dn), d))),
                            disputed_html(d, rs)))
        for r in scr:
            H.append("<tr><td class=n>%d</td><td class=n>%d</td><td class=ev>"
                     "<span class=\"tag scr\">screened</span>%s%s<span class=stamp>%s, "
                     "not counted as best known%s</span></td></tr>"
                     % (r["k"], r["N"], html.escape(credit_of(r) + "; ") if credit_of(r) else "",
                        ("<i>%s</i>; " % html.escape(construction_of(r)) if construction_of(r) else "")
                        + html.escape(r["source_detail"]), stamp_html(r),
                        (", " + constant_rows_of(r)) if constant_rows_of(r) else ""))
        H.append("</tbody></table></details>")
    if REFS_USED:
        H.append("<h2 id=references>Works the table builds on</h2>")
        H.append("<p class=\"mute\">Every construction named above, with the paper it comes "
                 "from. Cite these with the table.</p><ol>")
        for rid in REFS:                 # file order, which groups related work
            if rid in REFS_USED:
                d = REFS[rid]["doi"]
                link = ("" if not d else ' <a href="%s">%s</a>' % (
                    "https://arxiv.org/abs/" + d[6:] if d.startswith("arXiv:") else "https://doi.org/" + d,
                    html.escape(d if d.startswith("arXiv:") else "doi:" + d)))
                H.append('<li id=r%d>%s%s <span class=mute>(%s)</span></li>'
                         % (list(REFS).index(rid) + 1, html.escape(REFS[rid]["reference"]), link, rid))
        H.append("</ol>")
    H.append("</main></body></html>")
    return "\n".join(H) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--table-dir", default=os.path.join(REPO, "table"))
    ap.add_argument("--out", default=os.path.join(REPO, "docs", "index.html"))
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    date = a.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows, manifest = load(a.table_dir)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import builds_on
    REFS.update(builds_on.load(a.table_dir))
    cp = os.path.join(a.table_dir, "certificates", "CERTIFICATES.csv")
    if os.path.exists(cp):
        with open(cp, newline="", encoding="utf-8") as f:
            for c in csv.DictReader(f):
                if c["array_sha256"]:
                    SHA2CERT[c["array_sha256"]] = c["file"]
                elif c.get("family_sha256"):
                    SHA2CERT["family:" + c["family_sha256"]] = c["file"]
    dp = os.path.join(a.table_dir, "derived.csv")
    if os.path.exists(dp):
        with open(dp, newline="", encoding="utf-8") as f:
            DERIVED_COUNT[0] = sum(1 for _ in csv.DictReader(f))
    xp = os.path.join(a.table_dir, "EXTERNAL.csv")
    if os.path.exists(xp):
        with open(xp, newline="", encoding="utf-8") as f:
            for e in csv.DictReader(f):
                SHA2EXT[e["sha256"]] = e["location"]
    page = render(rows, manifest, date)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote %s (%d bytes)" % (a.out, len(page.encode("utf-8"))))


if __name__ == "__main__":
    main()
