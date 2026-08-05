#!/usr/bin/env python3
"""Check .qmd prose against the family style guide's emphasis rules.

Run this after ANY writing pass, before committing. It exists because the rules
were violated three times in one session by the same person who had just
written them — including twice within an hour. A habit did not work; a check
does.

Enforces two settled rules from the family style guide:

  §15  em-dash density  — target <= 4.0 per 1000 words of prose, i.e. roughly
       one per 250 words. Parenthetical pairs (— like this —) are called out
       separately because §15 names them the most flag-prone form and says to
       convert those first.

  §12a emphasis — bold is permitted for exactly three things: run-in labels,
       a defined term at first teaching use, and a word the reader must find
       again. Never a whole sentence or clause, and never for stress (that is
       italic's job).

What is NOT counted, because it is structure rather than prose:
  - YAML front matter, fenced code, HTML comments
  - `**Term** — gloss` definition lists and margin glosses
  - bold-only label lines (`**Trap to Avoid — The confirmation test**`)
  - `<summary>For the Curious — …` drawer labels
  - headings
  - bold at the start of a line or list item (run-in labels)

Exit status is 1 if any hard violation is found, so it can gate a commit.
Shared verbatim with Make the Call; fix bugs in both, or in neither.

    python3 scripts/prose-check.py              # default: only what this pass touched
    python3 scripts/prose-check.py Chapter.qmd  # named files
    python3 scripts/prose-check.py --all        # sweep the whole book, demos included

The default is deliberate. The check is for prose written since the rules
existed, not for relitigating a manuscript that predates them; a check that
fails on forty files is a check that gets ignored.
"""
import glob
import os
import re
import sys

DASH_PER_1K = 4.0          # §15
SENTENCE_BOLD_WORDS = 9    # a bold this long is a clause, not a label
LABEL_WORDS = 4            # "**Weak.**" is a label; a period does not make it a sentence
MIN_WORDS = 400            # below this the per-1k rate is noise, not signal

SKIP = {"references.qmd"}

# Demo files are verbatim transcripts, worksheets and field notes. They are
# records of what people said, not authored prose, and dashes in a transcript
# are the speaker's. Checked only with --all.
TRANSCRIPT_DIRS = ("demo/",)

# A different register, exempt by design rather than by neglect. The method
# layer is written FOR an AI to execute, and says so in its own opening: "not
# written for you... optimized for a machine to execute, not for you to read"
# (family style guide §3, the dual layer). The em-dash rule exists because a
# human reader registers dash density as an AI tell. A machine does not.
EXEMPT = {"method-layer.qmd"}


def prose_only(text):
    """Strip everything that is not running prose."""
    text = re.sub(r"\A---.*?^---", "", text, flags=re.S | re.M)   # YAML
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)    # code chunks
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)            # HTML comments
    text = re.sub(r"^#{1,6} .*$", "", text, flags=re.M)           # headings
    text = re.sub(r"^:::.*$", "", text, flags=re.M)               # div fences
    text = re.sub(r"^<(summary|details|/details)[^>]*>.*$", "", text, flags=re.M)
    text = re.sub(r"^\s*\|.*$", "", text, flags=re.M)             # table rows
    # Block labels: a bold-only line such as "**Trap to Avoid — The confirmation
    # test**" or "**Halo Alert — A first test**". Same Label — Name form as a
    # definition gloss, but with the dash inside the bold, so it is structure
    # rather than prose and must not count against the density budget.
    text = re.sub(r"^\s*\*\*[^*\n]*\*\*\s*$", "", text, flags=re.M)
    return text


def structural_dashes(text):
    """Em-dashes that are definition-list punctuation, not prose."""
    return len(re.findall(r"\*\*[^*]+\*\*\s+—", text))


def audit(path):
    raw = open(path, encoding="utf-8").read()
    body = prose_only(raw)
    words = len(body.split())
    if not words:
        return None

    dashes = body.count("—") - structural_dashes(body)
    pairs = re.findall(r"—[^—\n]{3,70}—", body)
    density = dashes / (words / 1000) if words else 0
    budget = int(words / 250)

    violations, warnings = [], []
    if density > DASH_PER_1K and words >= MIN_WORDS:
        violations.append(
            f"em-dash density {density:.1f}/1k exceeds {DASH_PER_1K} "
            f"({dashes} in prose, budget {budget})"
        )
    for p in pairs:
        warnings.append(f"parenthetical pair: {p[:66].strip()}…")

    # --- bold audit: only inline bolds; run-in labels are legitimate ---
    for line in body.split("\n"):
        for m in re.finditer(r"\*\*([^*]+)\*\*", line):
            before = line[: m.start()]
            if re.match(r"^\s*>?\s*(?:[-*+]|\d+\.)?\s*$", before):
                continue                       # run-in label — permitted
            s = m.group(1).strip()
            n_words = len(s.split())
            sentence_like = n_words > SENTENCE_BOLD_WORDS or (
                s.endswith((".", "!", "?")) and n_words > LABEL_WORDS
            )
            if sentence_like:
                violations.append(f'whole sentence/clause in bold: "{s[:64]}…"')

    return dict(path=path, words=words, density=density, dashes=dashes,
                budget=budget, violations=violations, warnings=warnings)


def changed_files():
    """.qmd files touched in the working tree or not yet pushed."""
    import subprocess
    out = set()
    for cmd in (["git", "diff", "--name-only", "HEAD"],
                ["git", "diff", "--name-only", "--cached"],
                ["git", "diff", "--name-only", "@{u}...HEAD"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            out |= {l for l in r.stdout.split() if l.endswith(".qmd")}
        except Exception:
            pass
    return sorted(f for f in out if os.path.exists(f))


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}

    if args:
        targets = args
    elif "--all" in flags:
        targets = sorted(set(glob.glob("*.qmd")) | set(glob.glob("toolkit/*.qmd"))
                         | set(glob.glob("demo/*.qmd")))
    else:
        # default: only what this pass touched — the check is for new prose,
        # not for relitigating everything written before the rules existed
        targets = changed_files()
        if not targets:
            print("prose-check — nothing changed; use --all to sweep the book")
            return 0

    targets = [t for t in targets
               if os.path.basename(t) not in SKIP | EXEMPT]
    if "--all" not in flags:
        targets = [t for t in targets
                   if not any(t.startswith(d) for d in TRANSCRIPT_DIRS)]

    failed = False
    print(f"prose-check — em-dash <= {DASH_PER_1K}/1k, no sentence-length bold\n")
    for t in targets:
        r = audit(t)
        if not r:
            continue
        flag = "FAIL" if r["violations"] else ("warn" if r["warnings"] else "ok")
        if r["violations"]:
            failed = True
        if flag == "ok" and len(targets) > 6:
            continue                            # keep a full-book run readable
        print(f"[{flag:4}] {r['path']}  {r['words']}w  "
              f"em-dash {r['density']:.1f}/1k ({r['dashes']}/{r['budget']})")
        for v in r["violations"]:
            print(f"         ✗ {v}")
        for w in r["warnings"]:
            print(f"         · {w}")

    print("\nclean" if not failed else "\nviolations found — fix before committing")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
