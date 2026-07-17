#!/usr/bin/env python3
"""Mirror references.bib to the master Zotero export for every cited key.

Scans the project's .qmd files for citation keys and makes references.bib
match the master Better BibTeX export for each one: appends cited entries
that are missing, and refreshes cited entries whose master version has
changed (e.g. after a metadata cleanup in Zotero). Keeps the book's
bibliography self-contained and always current without a manual step.

Runs as a Quarto pre-render hook. Design choices:
  - Mirror, not append-only: a cited entry edited in Zotero (cleaned Extra
    field, fixed metadata) propagates on the next render.
  - Minimal diff: only changed/added entry blocks are rewritten; everything
    else in references.bib is left byte-for-byte, including uncited entries
    and cited entries that exist only locally (not in the master).
  - Graceful: if the master export is absent (a fresh clone, CI), it prints
    a notice and exits 0 so the build proceeds on the committed bib.
  - Never fails the build: unresolved keys are warned about, not fatal.

Override paths with env vars MASTER_BIB and REFERENCES_BIB if needed.
"""
import os
import re
import sys
import glob

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


def normws(s):
    return " ".join(s.split())


def main():
    ref_text = open(REFS, encoding="utf-8").read() if os.path.exists(REFS) else ""
    local = parse_entries(ref_text)
    cited = cited_keys()
    missing = sorted(cited - set(local))

    if not os.path.exists(MASTER):
        if missing:
            print(
                f"[sync-refs] NOTE: master bib not found at {MASTER}; "
                f"building on the committed references.bib.\n"
                f"           Not in bib: {', '.join(missing)}"
            )
        else:
            print("[sync-refs] references.bib is up to date (master not present).")
        return 0

    master = parse_entries(open(MASTER, encoding="utf-8").read())
    new_text = ref_text
    refreshed, added, local_only, unresolved = [], [], [], []

    # Refresh cited entries already present whose master version differs.
    for k in sorted(cited):
        if k in local:
            if k in master:
                if normws(local[k]) != normws(master[k]):
                    new_text = new_text.replace(local[k], master[k], 1)
                    refreshed.append(k)
            else:
                local_only.append(k)

    # Append cited entries missing from references.bib.
    to_append = []
    for k in missing:
        if k in master:
            to_append.append(master[k])
            added.append(k)
        else:
            unresolved.append(k)
    if to_append:
        new_text = new_text.rstrip() + "\n\n" + "\n\n".join(to_append) + "\n"

    if new_text != ref_text:
        with open(REFS, "w", encoding="utf-8") as fh:
            fh.write(new_text)

    if not refreshed and not added:
        print("[sync-refs] references.bib is up to date.")
    else:
        if added:
            print(f"[sync-refs] added {len(added)}: {', '.join(added)}")
        if refreshed:
            print(f"[sync-refs] refreshed {len(refreshed)}: {', '.join(refreshed)}")

    if local_only:
        print(
            "[sync-refs] NOTE: cited entries kept as-is (in references.bib but "
            f"not in the master): {', '.join(local_only)}"
        )
    if unresolved:
        print(
            "[sync-refs] WARNING: cited but not in master export "
            f"(check for typos or add to Zotero): {', '.join(unresolved)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
