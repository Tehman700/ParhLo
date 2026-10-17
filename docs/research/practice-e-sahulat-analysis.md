# Practice Analysis: "Multilingual E-Sahulat AI" (from another competition)

Source: `Hackathon.pdf` (repo root). **Not our problem statement.** It's a reference for the style and rules NaSCon may use.

## The problem in one line
Build an **evidence-grounded, multilingual retrieval + QA system** for one Pakistani public-service domain (e.g. passports). Users ask in Urdu script, Roman Urdu, English or a mix. The system must cite official sources, **abstain** when the evidence is missing, and **prove** its quality with metrics.

## Rules that matter most (and how they'd change our plan)
| Rule | Impact |
|---|---|
| **No API calls. Models must be open-source and loaded in your own code.** Using Gemini/ChatGPT/Claude = disqualified | Our starter's API-based LLM service would be unusable. Jev and AI Gateway would also be out. **We need a local-model path** (transformers / llama-cpp-python, in-process). |
| 3–3.5 hours total | No time to research models or download weights on the day. **Pre-download and pre-test everything.** |
| Team of 2–3 (we're solo) | Ruthless scope. Reuse prepared code. |
| Free/open data, documented provenance | Corpus must list a URL, date and doc ID per document. |
| Python / Streamlit permitted | Our FastAPI + Next.js is fine; Streamlit is a fallback if time is short. |

## What's actually scored (100 pts)
- NLP depth (normalization, retrieval design): **20**
- Retrieval quality across scripts, paraphrases and spelling: **20**
- Answer reliability, citations and abstention: **20**
- Validation rigor (test set, baselines, metrics, error analysis): **15**
- Working prototype and UI (language selection, source inspection): **10**
- Practical impact: **10**
- Presentation: **5**

**75% of the score is retrieval, grounding and evaluation, not the UI or fluent generation.** "A simple interface backed by reliable retrieval… scores higher than an elaborate interface with unsupported answers."

## Required behaviours (12 validation cases)
- **Script handling:** Urdu-script, Roman Urdu, English and code-mixed queries should all retrieve the *same* evidence.
- **Spelling variants:** "passport renew karwana hai" and "pasport renu karwana hy" should both work. Show whether normalization or semantic retrieval is what helps.
- **Paraphrases:** "replace my expired passport" should still find the renewal content.
- **Abstention:**
  - Unsupported (guaranteed processing time)
  - Out-of-domain (cricket)
  - Random text
- **Clarification** for ambiguous questions ("How much does it cost?").
- **Conflicting or outdated sources:** detect the conflict, prefer the current authoritative source, otherwise disclose it.
- **Citation integrity:** the cited passage must really support the answer, and URLs must match.
- **Safety:** prompt injection and requests for unsupported claims.

## Required metrics
- Recall@5
- MRR@5
- Citation support rate
- Abstention performance (precision and recall on answerable vs. unanswerable)
- Cross-script consistency
- Latency

All of these must be measured on ≥30 queries (45+ preferred), with the test set kept separate from tuning data.

## A winning architecture for this type of problem (CPU-friendly)
```
query → language/script detect → normalize
      (Unicode + Urdu char unification + Roman Urdu spelling rules + domain glossary)
      → [optional] Roman→Urdu transliteration / Urdu↔English translation for query expansion
      → retrieve: BM25 (char n-grams)  +  dense (BGE-M3)   → hybrid (RRF)
      → rerank (bge-reranker-v2-m3) → confidence threshold → ABSTAIN / CLARIFY / ANSWER
      → answer: extractive sentences (default, always faithful)
                or small local LLM constrained to the passages
      → citation check: each answer sentence vs. cited passage (reranker/NLI score)
      → UI: answer in chosen language + expandable evidence with URL + passage ID
```
**Technical contributions to pitch:**
1. Script-aware normalization and Roman Urdu spelling canonicalization (ablation: with vs. without).
2. Hybrid retrieval beating keyword-only and dense-only (table of Recall@5 and MRR@5 per language style).
3. Calibrated abstention: a threshold tuned on the dev split and reported on the test split.
4. Automatic citation verification.

## What we should prepare in advance (generic, reusable for any Urdu/multilingual problem)
1. **Local model runtime:** pre-downloaded weights plus an in-process loader (no servers, no APIs). See [urdu-models.md](urdu-models.md).
2. **Urdu/Roman Urdu normalizer:** a module with unit tests.
3. **Retrieval kit:**
   - BM25 and dense search
   - Hybrid search with RRF (reciprocal rank fusion)
   - Reranker
   - Thresholded abstention
4. **Evaluation harness:** a JSONL test-set format (id, query, style, intent group, answerable, gold passage IDs, reference answer). It computes Recall@k, MRR@k, citation support, abstention P/R/F1, cross-script consistency and latency, and outputs a Markdown/CSV report.
5. **Corpus ingestion:** PDF/HTML → passages with `doc_id`, `url`, `date`, `passage_id`.
6. **UI pieces:**
   - Language selector
   - Answer card
   - Evidence drawer with source links
   - Retrieval-method comparison table
