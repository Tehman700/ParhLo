# 04: Plan: ParhLo Flow, Architecture and Build Schedule

_Agreed 2026-10-17, 10:40._ **Hard deadline 21:00. Submit (Loom + repo + diagram) by 20:20.**

## Decisions
| Topic | Decision |
|---|---|
| Hosting | **Hybrid.** Vercel (Next.js + FastAPI via Vercel Services, cron, AI Gateway; account `tehmanhassan-4631`) + Neon Postgres (pgvector) + **AWS ap-south-1**: S3 (PDFs, audio), Polly (audio edition), SES (6 AM email; sandbox means verified recipients only, 200/day). Scale path in the diagram: SQS → Lambda workers for per-user generation |
| Why not all-AWS | Hosting on Lambda/ECS + API Gateway + CloudFront + IAM costs ~2–3 h of a 9 h build. The real scaling cost is LLM calls and per-user generation, solved by shared ingest + queue fan-out. Use AWS where it is best-in-class (S3, Polly, SES, SQS) |
| LLM | **Vercel AI Gateway** (cheap fast model for per-article summaries, stronger model for the per-user editor; embeddings via the gateway). **Jev**: evaluate later for topic tagging and relevance scoring if it fits |
| Research-driven features (see 02/03) | Verified grounded summaries (✓ badge, AI label); morning box (weather, AQI/smog alert, USD→PKR, cricket); "Also reported by" + Pakistani vs. international framing; editor's note; finite edition ("You're done ✓"); 3 things + recall quiz; WhatsApp-forward check (if time) |
| Build priority (cut from the bottom) | ingest → rank+edit → web+archive → **deploy** → PDF/S3 → onboarding → learning → morning box + verified badge → two-persona → ask your paper → audio (Polly) → email (SES) → framing toggle → recall quiz → push (Web Push) → WhatsApp check |
| Design | Paper pages use a newspaper look (serif headlines, columns, rules, masthead). App screens (onboarding, profile) use the clean Apple-style tokens from `Design-Files/` |

## User flow
```
Landing → Onboarding (≈60 s) → "Printing your first paper…" → Today's Paper (web)
   ├─ read / open original / skip / 👍 / 👎 / save → events
   ├─ Download PDF (same frozen edition)
   ├─ Archive → any past edition (web + PDF)
   ├─ Ask your paper (chat with citations)   ├─ Listen (audio edition)
   └─ Profile: "Your paper is learning" (what changed and why, editable)
Nightly: events → profile update → tomorrow's edition is better
```
**Onboarding:**
1. Name, reading time (5/10/20 min), and region mix (Pakistan/World).
2. Topic chips with sub-topics.
3. Yes/no on about 10 of today's real headlines.
4. Optional free text, which the LLM turns into entities and interests.

It ends on an editable interest profile card.

**Paper:**
- Masthead: "ParhLo", date, edition no., "Good morning, {name}".
- Front page: lead story, top stories, and a **"3 things to remember today"** box.
- Sections ordered by interest weight and sized to the chosen reading time.
- Each story: headline, summary, "why you're seeing this", source link, and actions.

## Architecture
```
Next.js (Vercel)  /onboarding  /paper/[date]  /paper/[date]/print  /archive  /profile  /compare
   │  event tracker (click, dwell via IntersectionObserver, skip, 👍/👎, save)
   ▼
FastAPI (Vercel, Python)
 ① INGEST (shared, cron hourly): RSS registry (~50 feeds) + Google News RSS per interest
    → fetch → extract (trafilatura) → dedupe/cluster → embed → topic-tag → summarize once (cached)
 ② RANK (per user): similarity to interest vectors + topic weight + recency + source quality
    + cluster size − dislikes → MMR diversity → 10–15% discovery slot
 ③ EDIT (per user, LLM → JSON): headlines, "why for you", lead, sections, 3 things
 ④ PUBLISH: frozen edition JSON (web == PDF) → PDF via headless Chromium printing /print → Blob
 ⑤ LEARN (nightly cron + on demand): events → topic weights (EMA), interest vectors (Rocchio),
    source affinity → profile snapshot (drives the "learning" panel)
   ▼
Neon Postgres + pgvector: users, profiles, profile_snapshots, articles(+embedding), clusters,
                          editions(json), events     |  Vercel Blob: PDFs, audio
```
**Key principle:** articles are ingested and summarized **once, shared by all users**. Only selection and the "why for you" line are per user. This keeps cost and latency low and scales.

### Learning signals
| Signal | Weight |
|---|---|
| 👍 / save | +1.0 |
| Open original | +0.6 |
| Long dwell | +0.3 |
| Skip | −0.3 |
| 👎 | −1.0 |

Older signals decay over time.

## Build schedule (commit at every ✔)
| Time | Phase | Done when |
|---|---|---|
| 10:45–11:15 | Setup: Vercel project link, Neon + AI Gateway env, DB schema, quick competitor scan for the pitch | `vercel env pull` works, tables exist |
| 11:15–13:00 | ① Ingest pipeline | ~300+ fresh, deduped, tagged, summarized articles in DB |
| 13:00–14:30 | ②③ Profile + ranking + LLM editor | Edition JSON generated for a test persona |
| 14:30–16:00 | Web paper + archive. **First production deploy** | Live URL shows a real paper |
| 16:00–17:00 | ④ PDF + onboarding | Newspaper PDF downloads; new user → first paper |
| 17:00–18:00 | ⑤ Learning loop + cron + learning panel | "Next day" edition visibly changes after interactions |
| 18:00–19:15 | Extras in priority order | Each extra demoable or cut |
| 19:15–19:30 | Code freeze, prod smoke test | — |
| 19:30–20:20 | Architecture diagram, README, record Loom, **submit** | Form submitted |

## Risks
| Risk | Mitigation |
|---|---|
| Slow or failing feeds | Hourly shared ingest; generation never waits on the web |
| Paywalls | Fall back to RSS summary |
| PDF on serverless | Chromium for serverless; fallback: browser print-to-PDF of the same page |
| LLM output errors | Structured JSON + validation + plain fallback layout |
| Time | Core first; extras are cuttable |

## Module status (updated 2026-10-17, ~16:30)
| Module | Status | Notes |
|---|---|---|
| Setup + auto-deploy | ✅ | Vercel services, Neon, AWS, GitHub → Vercel |
| Login | ✅ | Own email OTP (SES) + Google OAuth; Clerk removed |
| UI redesign | ✅ | Apple design system, GSAP, plain English |
| **A** Live AI pipeline | ✅ | Ingest → rank → summarize → edit → paper → PDF on production (19–34 s) |
| **B** Jev decision layer | ✅ | Topic/junk/importance at ingest, 2 Top-story slots, Jev summary check (434 ms vs 941 ms LLM, same accuracy) |
| **C** Onboarding upgrade | ✅ | Live front-page preview, adaptive swipes (topic dropped after 2 passes), name prefill, transparency note, onboarding interests fade (×0.988/night). E2E 15/15 on production |
| Account batch | ✅ | Real sign-in always beats a demo session; OTP to any email (Gmail SMTP, SES fallback, SES out of sandbox); `/dashboard` (profile, topic switches, following, about you, memory, account, delete); `/privacy`, `/terms`, `/about`, `/how-it-works`, site footer; no event branding. Production E2E 32/32 |
| **D** Full flow test | ⏳ next | Sign in → onboarding → paper → react → learn → tomorrow's paper → PDF |
| E Demo readers | ⬜ | 2 personas, delete Fixture Reader |
| F Two-persona compare | ⬜ | `/compare` page |
| G Ask your paper | ⬜ | Jev routes, LLM answers from today's stories with sources |
| H Audio edition | ⬜ | Script → Polly → S3 → player |
| I Morning email | ⬜ | SES, top stories + PDF link |
| J Submission | from 19:15 | README, architecture diagram (research session), Loom, form |

The original timetable above is superseded by this table. Push notifications and the WhatsApp-forward check are dropped for time.
