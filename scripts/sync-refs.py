#!/usr/bin/env python3
"""Top up references.bib from the master Zotero export.

Scans the project's .qmd files for citation keys and appends any that are
cited but missing from references.bib, pulling the entries out of the
master Better BibTeX export. Keeps the book's bibliography self-contained
and current without a manual copy step.

Runs as a Quarto pre-render hook. Design choices:
  - Append-only: never rewrites or reorders existing entries, so diffs stay
    minimal and a hand-edited references.bib is safe.
  - Graceful: if the master export is absent (a fresh clone, CI), it prints
    a notice and exits 0 so the build proceeds on the committed bib.
  - Never fails the build: unresolved keys are warned about, not fatal.

Override paths with env vars MASTER_BIB and REFERENCES_BIB if needed.
"""
import os
import re
import sys
import glob

# Quarto sets QUARTO_PROJECT_DIR during pre-render; fall back to the repo root
# (this script lives in <repo>/scripts/).
ROOT = os.environ.get("QUARTO_PROJECT_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
MASTER = os.environ.get(
    "MASTER_BIB", os.path.expanduser("~/Documents/bibs/zotero.bib")
)
REFS = os.environ.get("REFERENCES_BIB", os.path.join(ROOT, "references.bib"))

# Quarto crossref prefixes — these @refs are not citations.
CROSSREF = re.compile(
    r"^(fig|tbl|sec|eq|lst|thm|lem|cor|prp|cnj|def|exm|exr|sol|rem|fnref)-"
)
CITE = re.compile(r"@([A-Za-z][A-Za-z0-9_-]*)")


def cited_keys():
    keys = set()
    for path in glob.glob(os.path.join(ROOT, "**", "*.qmd"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            for m in CITE.finditer(fh.read()):
                k = m.group(1)
                if not CROSSREF.match(k):
                    keys.add(k)
    return keys


def parse_entries(text):
    """Return {key: raw entry text}, brace-balanced."""
    entries, i, n = {}, 0, len(text)
    while i < n:
        if text[i] == "@":
            brace = text.find("{", i)
            if brace == -1:
                break
            key = text[brace + 1:text.find(",", brace)].strip()
            depth, j = 0, brace
            while j < n:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            entries[key] = text[i:j + 1]
            i = j + 1
        else:
            i += 1
    return entries


def main():
    refs_text = open(REFS, encoding="utf-8").read() if os.path.exists(REFS) else ""
    have = set(re.findall(r"@[a-zA-Z]+\{([^,]+),", refs_text))
    missing = sorted(cited_keys() - have)

    if not missing:
        print("[sync-refs] references.bib is up to date.")
        return 0

    if not os.path.exists(MASTER):
        print(
            f"[sync-refs] NOTE: master bib not found at {MASTER}; "
            f"building on the committed references.bib.\n"
            f"           Uncited-in-bib keys: {', '.join(missing)}"
        )
        return 0

    master = parse_entries(open(MASTER, encoding="utf-8").read())
    appended, unresolved = [], []
    chunks = []
    for k in missing:
        if k in master:
            chunks.append(master[k])
            appended.append(k)
        else:
            unresolved.append(k)

    if chunks:
        with open(REFS, "a", encoding="utf-8") as fh:
            fh.write("\n" + "\n\n".join(chunks) + "\n")
        print(f"[sync-refs] added {len(appended)} entry(ies): {', '.join(appended)}")

    if unresolved:
        print(
            "[sync-refs] WARNING: cited but not in master export "
            f"(check for typos or add to Zotero): {', '.join(unresolved)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
