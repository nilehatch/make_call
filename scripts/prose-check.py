#!/usr/bin/env python3
"""Check .qmd prose against the family style guide's emphasis rules.

Run this after ANY writing pass, before committing. It exists because the rules
were violated three times in one session by the same person who had just
written them — including twice within an hour. A habit did not work; a check
does.

Enforces four settled rules from the family style guide:

  §15  em-dash density  — target <= 4.0 per 1000 words of prose, i.e. roughly
       one per 250 words. Parenthetical pairs (— like this —) are called out
       separately because §15 names them the most flag-prone form and says to
       convert those first.

  §12a emphasis — bold is permitted for exactly three things: run-in labels,
       a defined term at first teaching use, and a word the reader must find
       again. Never a whole sentence or clause, and never for stress (that is
       italic's job).

  contrastive negation — "The problem is not X. It is Y." Defines a thing by
       what it isn't and then often stops. It has the shape of a distinction
       without the substance of one, which is why a model reaches for it and
       why a reader stops trusting it. Threshold 6.0/1k is calibrated, not
       chosen: no file in Make the Call exceeds 5.8 after its sweep, while
       Is This Worth Doing runs a median of 7.5 and a worst file of 13.9.

  forward-pointer endings — "The chapters that follow take up that task
       directly." One is fine prose. Nine chapters in a row ending the same
       way is a template. Reported as a warning per file, with a tally across
       a --all run, because the defect is the repetition and not the instance.

What is NOT counted, because it is structure rather than prose:
  - YAML front matter, fenced code, HTML comments
  - `**Term** — gloss` definition lists and margin glosses
  - bold-only label lines (`**Trap to Avoid — The confirmation test**`)
  - `<summary>For the Curious — …` drawer labels
  - headings
  - bold at the start of a line or list item (run-in labels)

Exit status is 1 if any hard violation is found, so it can gate a commit.
Shared verbatim across Make the Call, Expeditionary Innovation, and Is This
Worth Doing; fix bugs in all three, or in none.

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
NEG_PER_1K = 6.0           # contrastive negation; MtC's worst post-sweep file is 5.8
SENTENCE_BOLD_WORDS = 9    # a bold this long is a clause, not a label
LABEL_WORDS = 4            # "**Weak.**" is a label; a period does not make it a sentence
MIN_WORDS = 400            # below this the per-1k rate is noise, not signal

# Contrastive negation, in the four forms that actually show up. The first is
# the classic sentence pair; the rest are its compressed variants. Kept as
# separate patterns rather than one alternation so that a false positive can be
# traced to the clause that produced it.
NEG_PATTERNS = (
    # "Demand is not market size. It is a relationship."
    r"\b(?:is|are|was|were|do|does|did|can|will|has|have)\s+not\b"
    r"[^.!?\n]{0,90}[.!?]\s+(?:It|They|This|That|The\s+\w+)\s+(?:is|are|was|were|does|do)\b",
    # "not a failure of planning, but a feature of acting in unfamiliar territory"
    r"\bnot\s+(?:because\s+)?[^,.\n]{2,60},\s*but\b",
    # "The problem is not that the decision is irrational."
    r"^\s*(?:The|This|That|It|Its)\b[^.\n]{0,40}\bis\s+not\b",
    r"\bis\s+not\s+(?:that|simply|merely|about)\b",
)

# Formulaic forward-pointers, matched only against the tail of a file. A
# chapter may legitimately say where it is going; the tell is that every
# chapter says it the same way.
SIGNPOST = re.compile(
    r"(?:the\s+(?:chapters?|sections?|toolkits?)\s+that\s+follows?"
    r"|(?:in\s+)?the\s+next\s+(?:chapter|section|toolkit|part)"
    r"|that\s+(?:step|question|task|work)\s+comes\s+next"
    r"|takes?\s+up\s+(?:that|this)\s+(?:task|question|tension)"
    r"|we\s+(?:will\s+)?(?:now\s+)?turn\s+to"
    r"|turns?\s+to\s+that\s+(?:question|task)"
    r"|only\s+then\s+does\s+it\s+make\s+sense)",
    re.I,
)
SIGNPOST_TAIL = 500        # characters of prose from the end to inspect

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


def contrastive(text):
    """Every contrastive-negation hit, as (pattern index, matched text)."""
    hits = []
    for i, pat in enumerate(NEG_PATTERNS):
        for m in re.finditer(pat, text, flags=re.M):
            hits.append((i, " ".join(m.group(0).split())))
    return hits


def signpost_ending(text):
    """The formulaic forward-pointer, if the file ends on one."""
    tail = text.rstrip()[-SIGNPOST_TAIL:]
    # last non-empty block, so a closing paragraph is judged on its own
    blocks = [b for b in re.split(r"\n\s*\n", tail) if b.strip()]
    if not blocks:
        return None
    last = " ".join(blocks[-1].split())
    return last if SIGNPOST.search(last) else None


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

    negs = contrastive(body)
    neg_density = len(negs) / (words / 1000) if words else 0
    signpost = signpost_ending(body)

    violations, warnings = [], []
    if density > DASH_PER_1K and words >= MIN_WORDS:
        violations.append(
            f"em-dash density {density:.1f}/1k exceeds {DASH_PER_1K} "
            f"({dashes} in prose, budget {budget})"
        )
    if neg_density > NEG_PER_1K and words >= MIN_WORDS:
        violations.append(
            f"contrastive negation {neg_density:.1f}/1k exceeds {NEG_PER_1K} "
            f"({len(negs)} in prose, budget {int(words / 1000 * NEG_PER_1K)})"
        )
        for _, s in negs[:4]:
            violations.append(f"    “{s[:72]}…”")
        if len(negs) > 4:
            violations.append(f"    …and {len(negs) - 4} more")
    for p in pairs:
        warnings.append(f"parenthetical pair: {p[:66].strip()}…")
    if signpost:
        warnings.append(f"forward-pointer ending: “{signpost[:66]}…”")

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
                budget=budget, neg_density=neg_density, signpost=bool(signpost),
                violations=violations, warnings=warnings)


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
    audited, signposts = 0, 0
    print(f"prose-check — em-dash <= {DASH_PER_1K}/1k, "
          f"contrastive negation <= {NEG_PER_1K}/1k, no sentence-length bold\n")
    for t in targets:
        r = audit(t)
        if not r:
            continue
        audited += 1
        signposts += r["signpost"]
        flag = "FAIL" if r["violations"] else ("warn" if r["warnings"] else "ok")
        if r["violations"]:
            failed = True
        if flag == "ok" and len(targets) > 6:
            continue                            # keep a full-book run readable
        print(f"[{flag:4}] {r['path']}  {r['words']}w  "
              f"em-dash {r['density']:.1f}/1k ({r['dashes']}/{r['budget']})  "
              f"neg {r['neg_density']:.1f}/1k")
        for v in r["violations"]:
            print(f"         ✗ {v}")
        for w in r["warnings"]:
            print(f"         · {w}")

    # The forward-pointer defect is repetition, so it is only legible in the
    # aggregate. One chapter closing on "the next chapter turns to" is prose;
    # most of them doing it is a template.
    if audited > 3 and signposts:
        share = signposts / audited
        print(f"\n{signposts} of {audited} files end on a forward-pointer "
              f"({share:.0%})" + ("  — that is a template, not a transition"
                                  if share > 0.25 else ""))

    print("\nclean" if not failed else "\nviolations found — fix before committing")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
