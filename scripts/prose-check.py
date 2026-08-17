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

       Two checks. Inline bolds are measured directly. Line-start bolds are
       run-in labels and exempt — except when the bold opens with a term that
       has a margin gloss and then runs on into a proposition, e.g.
       "**Expected profit is conditional rather than speculative.**" where the
       gloss defines "Expected profit". That form is the term bold and the
       sentence bold confused for each other, and the fix is to close the bold
       after the term. Narrow on purpose: the exemption exists because run-in
       labels are legitimate, and a blanket rule flags over a hundred of them.

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

  §2   stub bullets — a bullet that carries an idea is a sentence; a bullet
       that only names where an idea would sit is three words. That is §2's
       own test ("does this bullet carry the idea, or only name the place the
       idea would sit?") made measurable, and it is what makes a draft read as
       an outline of its content rather than the content. Bullet COUNT does
       not discriminate — Make the Call runs a 26% median list density and
       Is This Worth Doing 29%. Bullet LENGTH separates them completely:
       median bullet 22 words against 6, and 3% of bullets under seven words
       against 60%. Run-in bold labels are stripped before counting, so
       "**Keep the reps yours.** Use the AI to..." is scored on its
       explanation; a bare label with no explanation scores zero and is
       correctly flagged.

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

STUB_WORDS = 6             # a bullet this short names a place, it does not carry an idea
STUB_SHARE = 0.25          # fail above this share; MtC's worst file sits at 0.10
MIN_BULLETS = 8            # below this the share is noise, not signal
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*)$")

# --- British spellings (added 2026-08-17, after ITWD's sweep) -----------------
# Two traps shaped this list, both hit while sweeping ITWD by hand.
#
#   A \b after the stem MISSES COMPOUNDS. greyscale, colourblind and
#   unlabelled all survived a word-anchored pass and the file reported clean.
#   So most entries below are bare stems with no trailing boundary.
#
#   The obvious stem for some pairs MATCHES CORRECT US WORDS. "analys" hits
#   analysis and analyses; "realis" hits realism and realistic; "emphasis" and
#   "practice" are correct nouns. Those get explicit suffix groups instead.
#
# Prose only: R/ and scripts/ are not scanned, and neither are code chunks,
# which prose_only() strips. Comments in R sources need their own pass.
BRITISH = (
    (r"colour",                            "color"),
    (r"behaviour",                         "behavior"),
    (r"favour",                            "favor"),
    (r"neighbour",                         "neighbor"),
    (r"centre",                            "center"),
    (r"defence",                           "defense"),
    (r"licence",                           "license"),
    (r"judgement",                         "judgment"),
    (r"programme",                         "programme -> program"),
    (r"modelling",                         "modeling"),
    (r"labell",                            "label-"),
    (r"travell",                           "travel-"),
    (r"cancell",                           "cancel-"),
    (r"organis",                           "organiz-"),
    (r"whilst",                            "while"),
    (r"amongst",                           "among"),
    (r"sceptic",                           "skeptic"),
    (r"practise",                          "practice"),
    (r"\blearnt\b",                        "learned"),
    (r"grey",                              "gray"),
    (r"\bmetre",                           "meter"),
    (r"\bfibre",                           "fiber"),
    (r"\btheatre",                         "theater"),
    (r"analys(?:e|ed|ing)\b",              "analyz-"),
    (r"realis(?:e|es|ed|ing|ation)\b",     "realiz-"),
    (r"recognis(?:e|es|ed|ing|able)\b",    "recogniz-"),
    (r"summaris(?:e|es|ed|ing)\b",         "summariz-"),
    (r"emphasis(?:e|es|ed|ing)\b",         "emphasiz-"),
    (r"specialis(?:e|es|ed|ing|ation)\b",  "specializ-"),
    (r"prioritis(?:e|es|ed|ing)\b",        "prioritiz-"),
    (r"criticis(?:e|es|ed|ing)\b",         "criticiz-"),
)

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


def stub_bullets(text):
    """(stub_list, total) — bullets whose body is too short to carry an idea.

    The run-in bold label is stripped first: a label plus its explanation is
    the legitimate `<dl>` form (§12a), so only the explanation is scored. A
    bullet that is nothing but a label scores zero words, which is the case
    this rule exists to catch.
    """
    lengths = []
    for line in text.split("\n"):
        m = BULLET_RE.match(line)
        if not m:
            continue
        body = re.sub(r"\*\*[^*]+\*\*", "", m.group(1))    # drop run-in label
        body = re.sub(r"[`*_\[\]()]", "", body).strip()
        lengths.append((len(body.split()), " ".join(m.group(1).split())))
    return [t for n, t in lengths if n <= STUB_WORDS], len(lengths)


def britishisms(text):
    """British spellings in prose, collapsed to one entry per distinct token."""
    found = {}
    for pat, am in BRITISH:
        for m in re.finditer(pat, text, re.I):
            # widen the match to the whole word, so a compound reports as
            # "colourblind" rather than the bare stem it matched on
            lo, hi = m.start(), m.end()
            while lo > 0 and (text[lo - 1].isalpha() or text[lo - 1] == "-"):
                lo -= 1
            while hi < len(text) and (text[hi].isalpha() or text[hi] == "-"):
                hi += 1
            tok = text[lo:hi]
            k = tok.lower()
            if k in found:
                found[k][1] += 1
            else:
                found[k] = [tok, 1, am]
    return list(found.values())


def signpost_ending(text):
    """The formulaic forward-pointer, if the file ends on one."""
    tail = text.rstrip()[-SIGNPOST_TAIL:]
    # last non-empty block, so a closing paragraph is judged on its own
    blocks = [b for b in re.split(r"\n\s*\n", tail) if b.strip()]
    if not blocks:
        return None
    last = " ".join(blocks[-1].split())
    return last if SIGNPOST.search(last) else None


GLOSS = re.compile(r"\{[^}]*\.def-margin[^}]*\}\s*\n\*\*([^*]+)\*\*\s*[—-]")
ARTICLE = re.compile(r"^(the|a|an)\s+", re.I)


def _stem(word):
    word = word.lower()
    for suffix in ("ing", "ies", "es", "ed", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def term_key(s):
    """Normalized comparison key: leading article dropped, words stemmed.

    So "Access test" matches "access testing" and "The base rate" matches
    "base rate" — variants that are the same term, not a violation.
    """
    return tuple(_stem(w) for w in re.findall(r"[A-Za-z']+", ARTICLE.sub("", s.strip())))


def buried_terms(raw):
    """A margin-glossed term swallowed inside a whole-sentence bold.

    §12a permits bolding a defined term at first teaching use. The slip this
    catches is bolding the *proposition* instead of the term —
    "**Expected profit is conditional rather than speculative.**" where the
    gloss defines "Expected profit". The fix is always to close the bold after
    the term.

    Deliberately narrow. A line-start bold is normally a legitimate run-in
    label, so this fires only when the bold both begins with a glossed term and
    is sentence-like by the same test used for inline bolds. Across Make the
    Call, Expeditionary Innovation and Is This Worth Doing it finds one case,
    which is the point: a general rule on run-in labels flags over a hundred
    legitimate ones and is useless.
    """
    keys = [(m.group(1).strip(), term_key(m.group(1).strip()), m.span())
            for m in GLOSS.finditer(raw)]
    found = []
    for term, key, span in keys:
        outside = raw[: span[0]] + raw[span[1]:]
        for line in outside.split("\n"):
            # A bullet run-in label is the documented <dl> form (§2, §12a) and
            # is legitimate even when it is a full proposition. The confusion
            # this rule targets happens in running paragraphs.
            if BULLET_RE.match(line):
                continue
            for bold in re.findall(r"\*\*([^*\n]+)\*\*", line):
                bold = bold.strip()
                bkey = term_key(bold)
                if bkey[: len(key)] != key or len(bkey) <= len(key):
                    continue
                n = len(bold.split())
                if n > SENTENCE_BOLD_WORDS or (
                    bold.rstrip().endswith((".", "!", "?")) and n > LABEL_WORDS
                ):
                    found.append((term, bold))
    return found


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
    for tok, n, am in britishisms(body):
        violations.append(
            f'British spelling "{tok}"' + (f" ({n}\u00d7)" if n > 1 else "")
            + f" — use {am}"
        )
    stubs, n_bullets = stub_bullets(body)
    stub_share = len(stubs) / n_bullets if n_bullets else 0
    if n_bullets >= MIN_BULLETS and stub_share > STUB_SHARE:
        violations.append(
            f"stub bullets {stub_share:.0%} of {n_bullets} are ≤{STUB_WORDS} words "
            f"(ceiling {STUB_SHARE:.0%}) — naming ideas instead of carrying them"
        )
        for s in stubs[:4]:
            violations.append(f"    • {s[:66]}")
        if len(stubs) > 4:
            violations.append(f"    …and {len(stubs) - 4} more")
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

    # A glossed term bolded as part of a proposition rather than on its own.
    for term, bold in buried_terms(raw):
        violations.append(
            f'glossed term "{term}" bolded inside a sentence: "{bold[:56]}…" '
            f"— close the bold after the term"
        )

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
          f"contrastive negation <= {NEG_PER_1K}/1k, "
          f"stub bullets <= {STUB_SHARE:.0%}, no sentence-length bold, "
          f"US spelling\n")
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
