# Make the Call

**Knowing What You Know, Learning What You Can, and Acting Under Uncertainty in Entrepreneurship**

The source for *Make the Call*, a practical book on entrepreneurial decision-making under uncertainty — a disciplined alternative to "fail fast," built on learning and judgment rather than luck. Read it at **https://mc.nilehatch.com**.

## The method: five gates

The book walks a decision from a question in the fog to a call you can stand behind, through five gates:

- **Frame** — what are we really deciding?
- **Prior** — what you already believe, and why you can't ignore it
- **Evidence** — gather what exists, test what doesn't
- **Sense** — is it credible, and what do you now believe?
- **Call** — is it enough, and which way?

Two framing parts bracket the gates — *Into the Fog* (the terrain and the method) and *Becoming* (someone who navigates the fog) — and a companion **Method Layer** turns the reader's AI into a gate-aware partner.

## Build it locally

Requires [Quarto](https://quarto.org/). A handful of figures are drawn in R (ggplot2 / ggforce).

```
git clone git@github.com:nilehatch/make_call.git
cd make_call
quarto preview      # live local preview
quarto render       # build to _book/
```

Figure results are cached in `_freeze/` (`execute: freeze: true`), so a normal build does **not** re-run R. To refresh a figure after changing its code, render that one file — `quarto render <file>.qmd`, which always executes — then commit the updated `_freeze/`.

## Deployment

Published at **https://mc.nilehatch.com** via Netlify.

Deployment is automatic: every push to `main` triggers a GitHub Actions workflow (`.github/workflows/publish.yml`) that renders the book and deploys `_book/` with the Netlify CLI. Because figures are frozen, CI never installs R. **Do not run `quarto publish` by hand** — the Action owns deploys, and a second path would race it. (`_publish.yml` is retained only as a manual-publish fallback.)

## Status

Public working draft, under active revision and open for friendly review. To collaborate, contact **@nilehatch**.

---
Made with [Quarto](https://quarto.org/).
