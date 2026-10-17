# 01: Problem Analysis: "Build a personal morning paper" (NaSCon'26, by Eynvision)

**Product name: PrhLo** (Urdu "parh lo", "read it"). Only the name is Urdu; the product, UI and content are in English.

Source: `NaSCon'26 Problem Statement.pdf` (repo root).

## In one sentence
A product that learns what a reader cares about, gathers the articles that matter to them from across the web every day, and delivers **one personal morning paper**. It can be read on the web (click through to originals, skip items) or downloaded as a **newspaper-style PDF**, and it **gets better the more it's used**.

## The pain (their framing)
News is scattered across dozens of sites, apps and newsletters, with no single feed like Instagram's. People hop between links "and still can't name three things they learned."
**Our hook: the paper should make the reader remember three things.**

## Required parts
| # | Part | What it must do | What "great" looks like |
|---|---|---|---|
| 1 | **Onboarding** | Capture enough interest signal to personalize, with great UX | Under 60 s, fun (pick topics plus react to real headlines), produces a visible interest profile |
| 2 | **PDF** | Fresh daily; structure and layout inspired by a traditional newspaper; content and *presentation* personalized | Masthead, date and edition no., lead story, columns, sections ordered by the reader's interests, consistent with the web edition |
| 3 | **Webpage** | Full reading experience; click through to originals; skip what you don't want; same edition as the PDF; **archive of previous papers** | Newspaper feel on screen, skip/like controls, edition archive by date |
| 4 | **Learning** | Gets better with use; signal capture and interpretation are up to us | Implicit signals (clicks, dwell, skips) plus explicit ones (more/less like this), a visible "your paper learned…" panel, measurable change across editions |
| 5 | **Room to explore** | Go beyond news and use AI in unexpected ways | 1–2 memorable extras, not ten half-built ones |

## Rules and deliverables
- **Create our own GitHub repo at the start; all commits are monitored.** It must be public at submission. ⚠️ Our pre-built starter predates the event. Decide how to handle it (see "Open questions").
- Submit: **GitHub link**, **Loom video ≤5 min** of the product, and an **architecture design diagram**.
- **No API ban** is stated (unlike the practice problem), so hosted LLMs, Vercel AI Gateway and Jev appear to be allowed. ⚠️ Confirm on site.
- Not stated: time limit, judging rubric, team size, deployment requirement.

## Implications
- This is a **product/UX + personalization + content pipeline** problem, not a model-accuracy one. The demo video is the main judged artifact, so the paper must look beautiful and personalization must be visibly real.
- The hard parts are reliable daily ingestion, good ranking/dedup, quality summaries, a **newspaper-grade PDF**, and a believable learning loop to show within one demo.
- The Urdu/offline kit is mostly not needed. It could become a "Room to explore" differentiator (Urdu edition / Pakistani sources).

## Open questions (ask organizers / decide)
1. Time limit? Judging criteria?
2. Are paid or hosted LLM APIs allowed? (Nothing says no.)
3. Must the product be deployed (live URL), or is a local Loom demo fine?
4. Can we reuse our pre-built boilerplate in the new repo? (Safest: commit it on the first commit and label it as boilerplate.)
