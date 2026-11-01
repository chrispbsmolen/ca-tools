"""builds_on.py - the published work a table row builds on.

Every row of table/ca_table.csv has a field builds_on: the ids of the
methods its construction uses, from table/references.csv, separated by
semicolons, and for a method of the submitter's own the word new followed
by a link to where it is described. Examples:

    cphf-smc2006;fuse-ckrs2010
    new https://arxiv.org/abs/2601.01234
    new https://github.com/someone/repo;fuse-ckrs2010

references.csv has the columns id, keywords, reference, doi. keywords is a
case-insensitive regular expression that matches the usual names of the
method, used to suggest ids from a construction text. Standard library only.
"""
import csv
import os
import re

HEADER = ["id", "keywords", "reference", "doi"]
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"^(https?://\S+|doi:\S+|arXiv:\S+)$")
# ids that name where an array came from rather than a method; they may be
# listed, but are never suggested or filled in automatically
SOURCE_IDS = {"web-colbourn", "web-tj"}


def load(table_dir):
    """id -> dict(id, keywords (compiled), reference, doi), in file order."""
    path = os.path.join(table_dir, "references.csv")
    refs = {}
    if not os.path.isfile(path):
        return refs
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != HEADER:
            raise SystemExit("table/references.csv header is %s, expected %s"
                             % (reader.fieldnames, HEADER))
        for r in reader:
            refs[r["id"]] = dict(id=r["id"], reference=r["reference"], doi=r["doi"],
                                 keywords=re.compile(r["keywords"], re.I) if r["keywords"] else None)
    return refs


def parse(value, refs):
    """Split a builds_on value. Returns (ids, links, errors): ids known to
    references.csv, links given after 'new', and what is wrong."""
    ids, links, errors = [], [], []
    for part in (value or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if part == "new" or part.startswith("new "):
            link = part[3:].strip()
            if not LINK_RE.match(link):
                errors.append("'new' must be followed by a link to where the method is "
                              "described (https://..., doi:... or arXiv:...), got %r" % part)
            else:
                links.append(link)
        elif part in refs:
            if part not in ids:
                ids.append(part)
        elif ID_RE.match(part):
            errors.append("%r is not an id in table/references.csv; if the method is "
                          "missing there, say so in the pull request and it will be added" % part)
        else:
            errors.append("%r is neither an id from table/references.csv nor 'new' "
                          "with a link" % part)
    if not ids and not links and not errors:
        errors.append("builds_on is empty: list the ids of the methods used, from "
                      "table/references.csv, or write 'new' and a link")
    return ids, links, errors


def suggest(text, refs):
    """Ids whose keywords match a construction text (sources excluded)."""
    out = []
    for rid, r in refs.items():
        if rid in SOURCE_IDS or r["keywords"] is None:
            continue
        if r["keywords"].search(text or ""):
            out.append(rid)
    return out


def citation(rid, refs):
    r = refs[rid]
    if r["doi"] and r["doi"] not in r["reference"]:
        doi = r["doi"]
        return "%s, %s" % (r["reference"], doi if doi.startswith("arXiv:") else "doi:" + doi)
    return r["reference"]


def check(value, construction, refs):
    """For a submitted claim: (normalized value, errors, warnings, new_links)."""
    ids, links, errors = parse(value, refs)
    warnings = []
    missing = [s for s in suggest(construction, refs) if s not in ids]
    if missing:
        warnings.append("the construction text matches %s, not listed in builds_on; "
                        "add %s if the construction uses %s"
                        % (", ".join(missing), "it" if len(missing) == 1 else "them",
                           "it" if len(missing) == 1 else "them"))
    norm = ";".join(ids + ["new " + l for l in links])
    return norm, errors, warnings, links
