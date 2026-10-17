# Loom: script, what to show, and description (≤ 5 minutes)

## Before you record (5 minutes)
- [ ] Chrome, one window, bookmarks bar hidden (Ctrl+Shift+B), zoom 100–110%, notifications off.
- [ ] Tabs open, in this order:
  1. https://parhlo-brown.vercel.app (landing, **signed out**)
  2. Your inbox with a ParhLo morning email (press **Send me today's email now** on your dashboard beforehand)
  3. n8n Cloud → the ParhLo workflow → **Executions**
  4. GitHub repo (README with the green CI badges)
  5. The architecture diagram (from `docs/diagrams/` once ready, or the README "Architecture" section)
- [ ] Use a **new Google account or email** for the onboarding part, so it's a real first-time flow. Google sign-in is fastest.
- [ ] On that account, keep **Formula 1 off** at onboarding (you switch it on live later).
- [ ] Do one dry run (it takes about 5 minutes); then record in one take.

## Script

| Time | Show (what's on screen) | Say |
|---|---|---|
| **0:00–0:20** | Landing page, scroll a little (headline, paper mock). | "News apps give you an endless feed. ParhLo gives you one short paper every morning, made for you, that you can actually finish. It reads the news from trusted outlets in Pakistan and around the world, picks what matters to you, and explains every choice." |
| **0:20–1:00** | **Get started** → Continue with Google → onboarding: name + city → pick 3 topics and watch the **live front-page preview** fill in → swipe 2–3 headlines → **Create my paper** → dashboard shows the paper ready. | "Onboarding takes a minute. The front page updates live as I pick topics, and these headline swipes adapt: pass on a topic twice and it stops appearing. … I click Create my paper, and it's ready in about three seconds." |
| **1:00–1:50** | **Read it now** → the paper: masthead with your name and city, morning box (weather, air quality, PKR), lead story. Point at **Why this story**, hover **✓ Checked against source**, point at a **Top story** badge and a **New for you** badge. Click **Download PDF**, scroll the PDF for 3 s. | "Every story says why it's here. Summaries are written from the original article and checked against it by Jev, a fast decision model; this percentage is its confidence. Two Top stories are the same for everyone, so I never miss the day's biggest news, and a few stories are deliberately outside my interests. The same paper as a newspaper PDF." |
| **1:50–2:30** | **Dashboard** → Topics → switch **Formula 1** on → the pill says *Updating your paper…* → *Updated for your new interests* (~3 s) → open **Today**: F1 now leads. Switch to the **n8n Executions** tab for 3 s. | "If my interests change, the paper changes now, not tomorrow. Formula 1 on … and in about three seconds the new paper is here, with F1 leading. The first version is printed without AI in the way; AI polish lands in the background a few seconds later. n8n orchestrates this too, so it happens even if I close the tab." |
| **2:30–3:10** | On a story card click **Ask about this story** → **Explain this simply** → answer with source chip. Then **New** → type *"Who won the Champions League final?"* → it says the paper doesn't cover it. | "Ask your paper answers only from my own paper, with sources. Ask about something that isn't in it, and it says so instead of making things up." |
| **3:10–3:40** | Press **/** → type *fuel prices* → results: **In your paper** first ("petrol price cut") → click one to open the original → back → type *Nvidia* → **Follow "Nvidia"**. | "Search works by meaning: 'fuel prices' finds the petrol price cut. Stories in my paper come first, clicking opens the original, and one tap on Follow adds it to my interests." |
| **3:40–4:10** | Dashboard: **What ParhLo remembers** and **Recent changes** (scroll), the **Morning email** switch → inbox tab: the morning email. Mention friends and saved stories while scrolling past them. | "Everything ParhLo learns from my reading is visible here, and I can remove any of it. Every morning at six the paper also arrives by email, with one-click unsubscribe. Friends can invite each other and, if both opt in, share what they liked." |
| **4:10–4:45** | Architecture diagram (or README). Then the GitHub README with green **CI** and **Smoke test** badges. | "Under the hood: Next.js and FastAPI on Vercel, Postgres with pgvector on Neon. Jev classifies every story for topic, junk and importance and checks every summary. Ranking runs inside the database in about two hundred milliseconds, gpt-5 models write and edit, and the morning email is a job queue in Postgres. Every push runs CI, and every deploy runs a live smoke test." |
| **4:45–5:00** | Back to the landing page. | "ParhLo: your news, in one paper. Short, personal, checked, and it gets better the more you read. Thanks for watching." |

**If you're running long:** cut search (3:10–3:40) to just "fuel prices", and say the architecture part over the README instead of switching tabs.

## Loom title
ParhLo: your personal morning paper (NaSCon'26 · Eynvision)

## Loom description (paste this)
ParhLo turns the day's news into one short, personal paper you can finish. It reads trusted outlets in Pakistan and around the world every night, picks what matters to you, explains why each story is there, and checks every AI summary against the original article.

In this video:
0:00 The idea
0:20 Onboarding with a live front-page preview
1:00 The paper: why-lines, checked summaries, Top stories, PDF
1:50 Change your interests → new paper in ~3 seconds
2:30 Ask your paper (answers only from your paper, with sources)
3:10 Search by meaning, follow from search
3:40 What ParhLo remembers, the morning email, friends
4:10 How it's built

Live: https://parhlo-brown.vercel.app · Try without an account: https://parhlo-brown.vercel.app/demo
Code: https://github.com/Tehman700/ParhLo

Built with Next.js, FastAPI, Neon Postgres + pgvector, OpenAI gpt-5, TypeSafe Jev, n8n and Vercel.
