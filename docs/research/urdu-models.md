# Open-Source Urdu / Multilingual Models: Shortlist

_Researched 2026-10-17. Hardware target: our laptop, a **Ryzen 5 5600H, 16 GB RAM, no NVIDIA GPU (CPU-only)**, 143 GB free disk._
Assume a rule like "no APIs, models loaded in your own code". Everything below runs locally.

Legend: ✅ = recommended to pre-download · ⚪ = backup / test if time · ⚠️ = verify before relying on it

## 1. Embeddings (dense retrieval): the most important piece
| Model | Size | Why | CPU |
|---|---|---|---|
| ✅ `BAAI/bge-m3` | 568M (~2.3 GB) | 100+ languages incl. Urdu. **Dense + sparse + multi-vector in one model**, 8k context. Strong cross-lingual results (Urdu query ↔ English doc) | OK; embed the corpus once and cache it |
| ✅ `intfloat/multilingual-e5-small` / `-base` | 118M / 278M | Fast fallback/baseline, supports Urdu. Needs `query:` / `passage:` prefixes; 512-token limit | Fast |
| ⚪ `Qwen/Qwen3-Embedding-0.6B` | 0.6B | Qwen3-Embedding family tops MTEB multilingual (8B variant); 0.6B is CPU-viable | OK |
| ⚪ `sentence-transformers/LaBSE` | 471M | Classic cross-lingual sentence alignment; good for checking cross-script consistency | OK |

No public Urdu or Roman Urdu retrieval benchmark exists, so **we must build our own small eval set** (which the competition wants anyway). Roman Urdu is weak in all of these models. Normalization, transliteration and BM25 over char n-grams compensate for that.

## 2. Rerankers (precision@top + abstention signal)
| Model | Size | Notes |
|---|---|---|
| ✅ `BAAI/bge-reranker-v2-m3` | 568M | Multilingual cross-encoder. In the LAMAR benchmark, Hindi (close to Urdu) scored 85.9. Its score is also our **abstention confidence** |
| ⚪ `Qwen/Qwen3-Reranker-0.6B` | 0.6B | Alternative; LLM-style reranker, slower to call |

Rerank only the top 20–30 candidates to keep CPU latency down.

## 3. Generators (local LLMs for writing answers)
Given CPU-only hardware: run **GGUF Q4 via `llama-cpp-python` (in-process)**. Expect roughly 15–25 tok/s for ~2–4B models and ~4–7 tok/s for 8B models (estimates, **benchmark on our machine**). Default to **extractive answers**; use an LLM only to rephrase within the evidence.

| Model | Size | Urdu | Notes |
|---|---|---|---|
| ✅ `CohereLabs/tiny-aya-global` | 3.35B | Urdu among 70+ langs | Released Feb 2026. Small, multilingual, made for offline/edge use. **Best size/Urdu trade-off for CPU.** ⚠️ check the license (Cohere models are often non-commercial; fine for a hackathon) and GGUF availability |
| ✅ `Qwen/Qwen3-4B-Instruct` (GGUF) | 4B | Decent | Strong instruction following/JSON; mediocre Urdu (UrduMMLU puts Qwen3-4B/8B behind Gemma) |
| ⚪ Gemma 4 `E2B` / `E4B` (instruct) | ~2B / ~4B effective | 140+ langs | Released 2026-03-31. Gemma-2-9B was among the best small models on UrduMMLU, so this family is promising. ⚠️ verify llama.cpp support |
| ⚪ `enstazao/Qalb-1.0-8B-Instruct` | 8B | **Urdu-specialised** (Llama-3.1 + 1.97B Urdu tokens CPT) | Apache-2.0. Paper reports it beats Alif. Slow on CPU; ⚠️ no confirmed GGUF (we'd convert/quantize ourselves) |
| ⚪ `large-traversaal/Alif-1.0-8B-Instruct` | 8B | Urdu-English | Earlier Urdu SOTA claim (vendor). Same CPU caveat |
| ⚪ UrduLLaMA 1.1 (+ 3B "Tiny") | 8B / 3B | Urdu | LREC 2026 paper (CLE Pakistan); ⚠️ HF repo not confirmed |

## 4. Translation / transliteration (query expansion across scripts)
| Model | Use | Notes |
|---|---|---|
| ✅ `facebook/nllb-200-distilled-600M` | Urdu (`urd_Arab`) ↔ English | Translate the query into the corpus language so BM25 works too. CC-BY-NC license; OK for a hackathon, but note it in the report |
| ⚪ AI4Bharat IndicTrans2 (`indictrans2-indic-en-dist-200M`, `en-indic`) | Urdu ↔ English | MIT license, distilled 200M versions are CPU-friendly. ⚠️ needs its own toolkit |
| ⚠️ Roman Urdu → Urdu | Script conversion | **No reliable off-the-shelf model found.** Candidates: `hasyarshad/roman-urdu-translator`, `Redgerd/Roman-Urdu-Transliteration` (both unverified); a 2025 paper reports m2m100 fine-tuned to 97.4 char-BLEU (weights unconfirmed). The `Mavkif/Roman-Urdu-Parl-split` dataset is on HF. **Plan: rule-based Roman Urdu canonicalizer + domain glossary**, plus a model only if it tests well |

## 5. Libraries (all pip/uv installable, no servers)
`sentence-transformers`, `FlagEmbedding` (bge-m3 sparse + reranker), `transformers`, `llama-cpp-python` (CPU wheels), `bm25s` or `rank-bm25`, `rapidfuzz` (fuzzy/char similarity), `faiss-cpu` (optional; numpy is enough for <50k passages), `pypdf` / `trafilatura` (HTML → text), `streamlit` (fallback UI).
Urdu text normalization is mostly custom code:
- Unify ي/ى → ی, ك → ک, ه/ۀ variants → ہ/ۂ.
- Strip diacritics (aerab) and tatweel; fix zero-width characters.
- Convert Urdu digits ۰-۹ → 0-9; normalize ۔ and ؟.
- Apply NFKC.

`urduhack` is outdated and has heavy dependencies, so skip it.

## 6. Downloaded kit → `C:\Users\Tehman Hassan\Desktop\AI-Models\`
Re-runnable script: `download_models.ps1` (uses the `hf` CLI, installed with `uv tool install huggingface_hub`). Folder layout and loading snippets are in that folder's `README.md`. LLMs are GGUF Q4_K_M:
- tiny-aya 2.1 GB, from the official `CohereLabs/tiny-aya-global-GGUF`
- Qwen3-4B 2.5 GB, from `unsloth/...-GGUF`
- Qalb 4.9 GB, from `mradermacher/...-GGUF`

None of them needed a login.

### First offline check (2026-10-17, CPU, `HF_HUB_OFFLINE=1`)
bge-m3 cosine similarity, passport-renewal doc vs. an unrelated cricket doc:

| Query | Passport doc | Cricket doc |
|---|---|---|
| Urdu script "پاسپورٹ کی تجدید کے لیے کون سی دستاویزات…" | **0.758** | 0.363 |
| Roman Urdu "Passport renew karwanay ke liye kya documents chahiye?" | **0.716** | 0.383 |
| Misspelled Roman Urdu "pasport renu karwana hy" | **0.563** | 0.363 |

- Cross-script retrieval works out of the box. **Misspellings cost about 0.15 in similarity**, so Roman Urdu normalization will measurably help. This is a good ablation to report.
- bge-reranker-v2-m3: Urdu query vs. passport doc = **0.99**, vs. cricket doc = **0.00**. That clear separation makes its score a strong abstention signal.
- Load times: bge-m3 4 s, reranker 8 s. e5-small loads OK (dim 384).
- The LLMs (GGUF) have **not been tested yet**; they need `llama-cpp-python`.

**Windows gotchas:**
- Set `PYTHONUTF8=1` or Urdu text crashes `print()` (cp1252 console).
- Don't run Python scripts from `%TEMP%`: a stray `h11.py` there shadowed a library.

### Original proposed set
1. `BAAI/bge-m3`
2. `intfloat/multilingual-e5-small`
3. `BAAI/bge-reranker-v2-m3`
4. `facebook/nllb-200-distilled-600M`
5. One generator in GGUF Q4: `tiny-aya-global` **or** `Qwen3-4B-Instruct` (pick after a quick Urdu test)
6. Optional: `Qalb-1.0-8B-Instruct` (only if an 8B model's speed is acceptable)

Then **benchmark on this laptop**: embedding throughput (passages/s), rerank latency for 20 pairs, LLM tok/s and first-token time, plus a 10-question Urdu/Roman Urdu sanity check. Record the results here.

## Sources
- UrduMMLU benchmark (2026): https://arxiv.org/html/2606.07167v1
- Qalb paper: https://arxiv.org/abs/2601.08141 · model: https://featherless.ai/models/enstazao/Qalb-1.0-8B-Instruct
- Alif 1.0: https://blog.traversaal.ai/announcing-alif-1-0-our-first-urdu-llm-outperforming-other-open-source-llms/
- UrduLLaMA (LREC 2026): https://www.cle.org.pk/Publication/papers/2026/LREC_2026_Urdu_LLM.pdf
- Urdu LLM resources list: https://github.com/traversaal-ai/urdu-llm-resources
- Tiny Aya launch: https://techcrunch.com/2026/02/17/cohere-launches-a-family-of-open-multilingual-models/
- Qwen3 Embedding: https://arxiv.org/html/2506.05176v1 · https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- LAMAR reranker benchmark: https://arxiv.org/pdf/2607.22042
- Gemma 4 release: https://ai.google.dev/gemma/docs/releases
- Roman-Urdu transliteration (2025): https://preview.aclanthology.org/setup/2025.loresmt-1.13 · dataset: https://huggingface.co/datasets/Mavkif/Roman-Urdu-Parl-split
