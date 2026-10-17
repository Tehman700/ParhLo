# 02: Market Research: Personal News

_Researched 2026-10-17. Figures cite secondary coverage where noted; verify before quoting in the pitch._

## 1. Global audience trends (Reuters Institute Digital News Report 2026: 48 markets, ~100k respondents)
| Finding | Number | What it means for ParhLo |
|---|---|---|
| Trust in news | **37%**, the lowest since 2015. Trust in news on social media: 22%. Concern about fake news: 62% (+4pp) | Trust is the scarce resource. **Every AI line must be traceable to a source** |
| News avoidance | **42%** sometimes or often avoid news (29% in 2017); news updates "risk creating a sense of overload" | A **finite** paper with a clear end, reading-time budget and balanced tone |
| Platforms vs. publishers | Access via platforms (54%) exceeded direct access to publishers (51%) for the first time | People want **one place**, which is exactly the brief's "Instagram for news" framing |
| Young people | 52% of 18–24s get news mainly from social, video or AI; Instagram is #1 for them (42%); 56% of non-newspaper-reading 18–24s have *never* read one regularly | Mobile-first, visual, skimmable. The PDF should feel like a *designed object*, not homework |
| AI chatbots for news | 10% weekly (16% under-35s). Trust in chatbot answers only 20%. **The most valued feature is asking follow-up questions (42%).** 42% click through to sources. Users value compiling stories from multiple outlets and translation | Validates **"Ask your paper"** and **multi-source story cards** |
| Paying for news | 17%, flat | Value must come from curation and utility, not exclusive content |
| News podcasts | 11%, flat | Audio is a nice extra, not the core |

Sources:
- [DNR 2026 executive summary](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary)
- [GIJN summary](https://gijn.org/stories/2026-reuters-institute-digital-news-report/)
- [IFJ takeaways](https://www.ifj.org/media-centre/news/detail/category/ai/article/reuters-digital-news-report-2026-key-takeaways-for-newsrooms-and-journalists-unions)

## 2. AI-in-news accuracy problem (the trust gap we can exploit)
- **BBC study (Feb 2025)** on ChatGPT, Copilot, Gemini and Perplexity:
  - **51%** of answers had significant issues.
  - 19% of answers citing the BBC had factual errors.
  - **13% of quotes were altered or invented.**
  - Sources: [The Register](https://www.theregister.com/2025/02/12/bbc_ai_news_accuracy/), [Computing](https://www.computing.co.uk/news/2025/ai/bbc-releases-damning-research-on-ai-news-accuracy)
- **EBU study (2025):** 45% of answers had at least one significant issue; 20% had major accuracy problems. Source: [ASIS summary](https://www.asisonline.org/security-management-magazine/latest-news/today-in-security/2025/october/ai-assistant-news-inaccuracies/)
- **Apple Intelligence** produced a false BBC headline, so Apple **disabled news summaries**. Source: [The Hill](https://thehill.com/policy/technology/5138279-bbc-report-ai-summaries-inaccurate/)
- **Washington Post "Your Personal Podcast"** launched with factual errors and editorializing, and caused an internal and external uproar. Sources: [Futurism](https://futurism.com/artificial-intelligence/media-execs-end-journalism), [Poynter](https://www.poynter.org/commentary/2025/artificial-intelligence-wins-fails-newsrooms/)

→ **Opportunity: "AI that shows its work."** Summaries are grounded in the source text, verified, labelled as AI, and one tap away from the original.

## 3. Pakistan context
- **Misinformation is a felt problem.** 9 in 10 people see misinformation as a challenge; about 5 in 10 meet it weekly; only 3 in 10 can always spot it ([Media Matters for Democracy](https://www.ohchr.org/sites/default/files/Documents/Issues/Expression/disinformation/2-Civil-society-organisations/Media-Matters-for-Democracy2.pdf)).
- **Youth get news from social platforms** (2025 study, 300 students): WhatsApp 93%, Facebook 83%, and 66% get news mainly via social media or the internet rather than TV. They see TV channels as biased ([ResearchGate](https://www.researchgate.net/publication/401587388_NEWS_CONSUMPTION_TRENDS_AMONG_PAKISTANI_YOUTH_A_COMPARATIVE_STUDY_OF_SOCIAL_MEDIA_AND_MAINSTREAM_MEDIA)).
- **Low-income adults accept forwarded WhatsApp content from close contacts without scrutiny** ([arXiv 2511.06147](https://arxiv.org/html/2511.06147v1)). False messages also persist longer on Pakistani WhatsApp than reliable ones ([arXiv 2106.09338](https://arxiv.org/pdf/2106.09338)).
- **Dawn** is the oldest and most-read English daily. Its app covers Dawn.com, the newspaper and DawnNews, with sections, bookmarks and night mode, but **no personalization**. Its e-paper is a scan of the print edition, and a reader called it "mandatory intake with my breakfast" ([Play Store](https://play.google.com/store/apps/details?id=com.mictronicx.dawn&hl=en), [Dawn](https://www.dawn.com/news/1480808)).
- **Daily utilities Pakistanis check every morning:** dollar rate, petrol/gold prices, weather and, in Oct–Jan, **Lahore smog/AQI**, prayer times and cricket. These are scattered across news sites today.

## 4. Habit and format lessons
- **Morning Brew** has a ~45% unique open rate and ~10% CTR; its **short, voicey editor's note** is cited as the main reason people open it. **TLDR** has ~41–47% opens with ~5-minute reads. These are vendor or self-reported figures ([Salestech](https://salestechstar.com/guest-authors/how-morning-brew-engaged-its-subscribers-through-email-marketing-tactics/), [Readless](https://www.readless.app/blog/tldr-newsletter-review-2026)).
- **ChatGPT Pulse** is praised because "the stories do not overwhelm and actually have an end." It has curate controls and thumbs up/down per card ([itdaily](https://itdaily.com/news/software/openai-chatgpt-pulse), [anchorchange](https://anchorchange.substack.com/p/the-next-phase-of-chatgpt-a-personalized)).
- **Serendipity:** personalization shouldn't optimize accuracy alone; leave room for non-profile items ([Reviglio taxonomy](https://informationr.net/ir/24-4/colis/colis1943.html)). Doomscrolling is reinforced by infinite feeds ([scoping review](https://www.researchgate.net/publication/399453882_The_influence_of_doomscrolling_on_mental_health_a_scoping_review)).
- **Notifications:** granular per-topic settings beat a single on/off toggle (practitioner guidance).

## 5. Verified data sources (tested live 2026-10-17)
| Source | Status |
|---|---|
| Dawn RSS (`/feeds/home`, `/pakistan`, `/business`, …) | ✅ 27–30 items each |
| Express Tribune `tribune.com.pk/feed/home` | ✅ 73 |
| Business Recorder `brecorder.com/feeds/latest-news` | ✅ 30 |
| Geo `geo.tv/rss/1/1` · The News `thenews.com.pk/rss/1/1` | ✅ 20 · 50 |
| BBC World · Guardian · NYT | ✅ |
| TechCrunch · The Verge · Ars Technica · Hacker News (hnrss) | ✅ |
| ESPNcricinfo | ✅ 100 |
| **Google News RSS search** (any interest, PK edition) | ✅ 100. **Covers niche interests dynamically** |
| Open-Meteo weather + air quality (Lahore AQI/PM2.5), no key | ✅ |
| open.er-api.com USD→PKR (277.0 today), no key | ✅ |
| Al Jazeera RSS, Aladhan prayer times | ⚠️ TLS failure from this network; retry from Vercel |
