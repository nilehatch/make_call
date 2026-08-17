# CLAUDE.md — book-make-the-call

*Make the Call: Knowing what you know, learning what you can, and acting under uncertainty in
entrepreneurship.* Quarto book, published at mc.nilehatch.com. Repo remote is
`git@github.com:nilehatch/make_call.git`.

**The draft is finished.** This book is further along than its two siblings: it has had its
voice sweep, and the prose-check thresholds that now govern all three books were *calibrated
against this book's post-sweep prose*. When a rule says "MtC's worst file sits at X", that is
this repo being used as the reference standard. Treat regressions here as more serious than
elsewhere, because a drift here silently loosens the bar for *Is This Worth Doing?* and
*Expeditionary Innovation*.

Written for BYU semester use. As of 16 Aug 2026 the semester is roughly 18 days out.

## The thinking lives in the vault, not here

`~/notes/10-Books/ent-evidence-mc/` holds the real design record — seventeen notes
including `_overview.md`, `book-architecture-v1.md`, `architecture-dual-layer-and-gates.md`,
`chapter-review-status.md`, `follow-ups.md`, `backlog-2026-06-26.md`, `callout-cheatsheet.md`,
`red-team-objections-and-positioning.md`, and `nwh-notes-on-chapters/`. Read there before
proposing structural change; most structural questions have already been argued.

Per global CLAUDE.md: audits, plans and summaries go to the vault. The `.qmd` files here are
the book itself.

## Architecture

Five parts named as gates — **The Frame Gate**, **The Prior Gate**, **The Evidence Gate**,
**The Sense Gate**, **The Call Gate** — bracketed by "Into the Fog" and "Becoming". The gate
sequence is the book's spine and `method-layer.qmd` mirrors it one-for-one.

The **dual layer** (family style guide §3) is sharper here than in the siblings: chapters are
written for a human reader, and `method-layer.qmd` is written for a machine and says so in its
own opening. It is in prose-check's `EXEMPT` set for exactly that reason — the em-dash rule
exists because a *human* reads dash density as an AI tell.

## Open item — the gate callout is designed and unused

Found 16 Aug 2026 while working in ITWD. `.threshold` is the family's gate callout: green,
with rules above and below and square corners so it reads as a gate in grayscale. Its own
comment in `base.css` predicts *"Make the Call's whole subject is when evidence is enough, so
it has more use for this than EI does."*

**This book uses it zero times.** EI uses it once. The concept is in five part titles and
throughout the prose, but never in the apparatus, so a reader cannot find the bar on the page.
That is an adoption gap rather than a design one, and it is probably the highest-value small
pass available here.

The boundary against `.checkpoint`, sharpened the same day when ITWD reclassified two boxes:
the test is **who clears the bar**. `.threshold` = a human must clear a bar before proceeding,
even if an AI or an app produced the artifact. `.checkpoint` = an AI's output is being
supervised. This book has 22 checkpoints and 20 `.ask-ai` boxes, so its AI cluster is
well-established; what is missing is the green.

## Two hazards this repo carries

**`execute: freeze: true`, not `auto`.** Seven documents here have R chunks. With `true`,
Quarto never re-executes during a project render, so an edit to a chunk is *silently ignored*
and the stale frozen markdown ships. ITWD deliberately chose `auto` over `true` for this
reason and documents the choice in its `_quarto.yml`. If a figure here ever fails to reflect a
code change, this is why. Deleting the relevant `_freeze/` directory forces re-execution.

**No `_headers` file.** ITWD hit a bug on 15–16 Aug 2026 where corrected pages kept serving
their previous version through repeated reloads, including DevTools "Empty Cache and Hard
Reload" — because the stale copy was at Netlify's *edge*, not in the browser, with
`cache-status: "Netlify Edge"; hit; ttl=31535985`. `Cache-Control` governs the browser;
`Netlify-CDN-Cache-Control` governs the edge, and only the second fixes it. This repo has the
same exposure and no fix. Copy `_headers` from ITWD and add `resources: - _headers` to
`_quarto.yml` if it bites. Symptom to recognize: a hard reload changes nothing but appending
`?v=2` shows the correct page.

## Shared tooling — fix in all three books or in none

`scripts/prose-check.py`, `scripts/sync-refs.py` and `base.css` are byte-identical across
*Make the Call*, *Expeditionary Innovation* and *Is This Worth Doing?*. Verify with `md5` after
any edit. Run prose-check after any writing pass:

```
python3 scripts/prose-check.py              # only what this pass touched
python3 scripts/prose-check.py --all        # whole book
```

`sync-refs.py` runs as a pre-render hook and mirrors `references.bib` to the Better BibTeX
auto-export at `~/Documents/bibs/zotero.bib`. Never hand-write a bib entry. Cite keys are
BBT's `authorTitleWordsYear`; this book is fully migrated.

## Build and deploy

`.github/workflows/publish.yml` renders and deploys `_book/` to Netlify on every push to
`main`. The runner has no R, so it relies on the committed `_freeze/`. `_book/` is gitignored;
`_freeze/` is tracked deliberately.

**Render the whole project before committing, never named files.** `quarto render <file>` does
not write `_freeze/`, so a targeted render leaves the freeze stale while local HTML looks
correct.

```
quarto render && git status --short _freeze    # commit freeze changes with the prose
```

## Conventions

Per global CLAUDE.md: preserve the author's voice, and cite when changing facts or claims.
`number-sections: false` here — this book is the family's deliberate outlier on that, where
ITWD and EI number chapters at depth 1.

## Open: British spellings (found 17 Aug 2026, not fixed)

`scripts/prose-check.py` gained a US-spelling check on 17 Aug, added in the ITWD
session and copied here byte-identical. Running it surfaces **8 instances of "grey"**
in this book, none of them fixed:

- `ways-of-knowing.qmd` — lines 37, 56, 57, 60, 68, 70, 71 (seven, clustered; likely one
  passage about grey areas or a figure description)
- `seeing-probability.qmd` — line 117

`python3 scripts/prose-check.py --all` lists them. Check whether the `ways-of-knowing`
cluster is prose or a deliberate reference before a blanket replace — seven in one file
suggests a single passage, and if it names a colour in a figure the figure needs the same
change.

**Also here:** this book's `intro.qmd` is numbered, while EI and now ITWD leave their
opening chapter unnumbered and outside the parts. Family style guide §14 settled the
unnumbered pattern on 17 Aug and names MtC as the outlier. Changing it renumbers every
chapter, which is cheap here — MtC already links chapters by descriptive text rather than
by number, so nothing breaks. ITWD had to convert 20 numeric links first.
