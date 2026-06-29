# Provenance Guard

A Flask API that classifies submitted text as human-written or AI-generated using a three-signal ensemble detection pipeline. Returns a structured classification, confidence score, and plain-language transparency label. Supports appeals and maintains a full audit log.

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create a .env file with your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env

# 3. Start the server
python app.py
# → Serving on http://127.0.0.1:5001
```

---

## Demo

All scenarios below were verified against a live server (`python app.py`).

### POST /submit — high-confidence AI

```
POST /submit  {"content": "Artificial intelligence represents a transformative paradigm shift..."}
```
```json
{
    "classification": "ai_generated",
    "confidence_level": "high",
    "confidence_score": 0.8125,
    "content_id": "05379789-ebcd-4ec1-9ee5-ea6839606e06",
    "label_text": "Our automated analysis found strong signals that this content may be AI-generated. This is not a definitive finding — our system can be wrong, especially for polished or formally written human work. If you are the creator and believe this assessment is incorrect, you can submit an appeal.",
    "signals": { "llm_score": 0.8, "stylo_score": 0.7298, "formality_score": 1.0 },
    "status": "classified",
    "appeal_url": "/appeal/05379789-ebcd-4ec1-9ee5-ea6839606e06"
}
```

### POST /submit — high-confidence human

```
POST /submit  {"content": "ok so i finally tried that new ramen place downtown and honestly?..."}
```
```json
{
    "classification": "human",
    "confidence_level": "high",
    "confidence_score": 0.2237,
    "content_id": "9dd3c745-c2b4-40aa-b3cc-b769b9135507",
    "label_text": "Our automated analysis found strong signals that this content was written by a human. This assessment is based on stylistic and semantic patterns and reflects our best confidence at this time.",
    "signals": { "llm_score": 0.2, "stylo_score": 0.3504, "formality_score": 0.1071 },
    "status": "classified",
    "appeal_url": "/appeal/9dd3c745-c2b4-40aa-b3cc-b769b9135507"
}
```

### POST /appeal — submit, duplicate, not-found

```
POST /appeal/05379789-...  {"reasoning": "I wrote this myself for a business report..."}
```
```json
{ "appeal_id": "26e7aa87-...", "content_id": "05379789-...", "status": "under_review",
  "message": "Your appeal has been received and the content is now under review." }
```
```
POST /appeal/05379789-...  (same appeal again)  →  HTTP 409
{ "error": "appeal already submitted for this content" }

POST /appeal/does-not-exist                     →  HTTP 404
{ "error": "content_id not found" }
```

### GET /log — structured audit log with appeal visible

```
GET /log
```
```json
{
  "entries": [
    {
      "content_id": "05379789-...", "classification": "ai_generated",
      "final_score": 0.8125, "timestamp": "2026-06-29T06:45:27Z",
      "status": "under_review",
      "appeal_reasoning": "I wrote this myself for a business report. The formal tone is intentional — it is a professional document, not AI output.",
      "appeal_timestamp": "2026-06-29T06:47:33Z"
    },
    {
      "content_id": "9dd3c745-...", "classification": "human",
      "final_score": 0.2237, "timestamp": "2026-06-29T06:45:37Z",
      "status": "classified", "appeal_reasoning": null
    },
    {
      "content_id": "9de5f48a-...", "classification": "human",
      "final_score": 0.2509, "timestamp": "2026-06-29T06:45:45Z",
      "status": "classified", "appeal_reasoning": null
    }
  ],
  "total": 4
}
```

`GET /log?limit=2` returns at most 2 entries (`"total": 2`).

### Rate limiting — 429 on the 5th request per minute

```
Request 1 → HTTP 200
Request 2 → HTTP 200
Request 3 → HTTP 200
Request 4 → HTTP 200
Request 5 → HTTP 429  ← rate limit hit
Request 6 → HTTP 429

Response body: 429 Too Many Requests — "5 per 1 minute"
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/submit` | Submit text for classification |
| `POST` | `/appeal/<content_id>` | Submit an appeal for a prior classification |
| `GET` | `/log` | View the audit log (add `?limit=N` for N entries) |

---

## Detection Signals

### Signal 1: LLM Classifier (Groq `llama-3.3-70b-versatile`)

**What it measures:** holistic semantic and stylistic coherence — whether the text reads like a human with opinions, experience, and imprecision, or like a model averaging over training data. The LLM looks for tonal consistency, specificity of detail, idiosyncratic voice, and the "covering all bases" structure that AI prose tends to produce.

**How it works:** the text is sent to Groq with a structured prompt requesting a JSON object with `ai_probability` (0.0–1.0) and a short rationale. The `ai_probability` value becomes `llm_score`. On any parse failure, the score defaults to `0.5`.

**What it misses:**
- AI text deliberately prompted with typos, contradictions, or informal registers can fool this signal.
- Polished human writing (professional essays, revised fiction) may score as AI-like.
- The detector and the content share training biases — the model may not reliably recognize its own output patterns.

---

### Signal 2: Stylometric Heuristics (pure Python)

**What it measures:** four statistical surface properties that differ between human and AI writing — sentence length variance, vocabulary diversity (type-token ratio), expressive punctuation diversity, and average word length. AI text generated token-by-token for local coherence tends to be statistically smoother; human writing has higher variance across all four.

**Sub-signals:**
- **Sentence length variance** — low coefficient of variation → AI-like (uniform sentence lengths)
- **Type-token ratio** — low vocabulary diversity → AI-like (suppressed for texts under 30 words)
- **Expressive punctuation** — fewer em-dashes, semicolons, ellipses → AI-like
- **Average word length** — longer average word length → AI-like (AI trends toward formal diction)

Each sub-signal is normalized to [0, 1] and averaged into `stylo_score`.

**What it misses:**
- Anaphoric or repetitive poetry (deliberate repetition) scores as AI-like due to low TTR and uniform sentence structure — a known false-positive category.
- Very short texts (< 30 words) produce unreliable statistics; TTR is suppressed, others return neutral.
- Heavily edited AI drafts inherit human variance introduced during revision and are under-flagged.

---

### Signal 3: Formality / Register (pure Python)

**What it measures:** the density of informal language markers — contractions ("won't", "I'd", "can't") and colloquial tokens ("gonna", "kinda", "yeah") — as a fraction of total words. AI models default to a formal written register and almost never produce contractions unless explicitly prompted to. Human writing, especially casual and personal work, uses them naturally.

**How it works:** a regex matches contractions and a fixed set of informal tokens. The ratio of informal tokens to total words is mapped to a [0, 1] score: 0% informal → 1.0 (AI-like, maximally formal), 2%+ informal → 0.0 (human-like, casual register). The 2% threshold is calibrated to typical human prose — most informal human texts carry at least one contraction per 50 words.

**What it misses:**
- Formal human writing (legal briefs, academic essays, literary fiction) uses few or no contractions and will score as AI-like on this signal alone. The LLM and stylometric signals provide the necessary counter-weight.
- AI text prompted to sound casual ("write informally") will suppress this signal. However, most platform-submitted AI content is not deliberately style-prompted.

---

## Confidence Scoring

**Combination formula (3-signal ensemble):**

```
final_score = 0.60 × llm_score + 0.25 × stylo_score + 0.15 × formality_score
```

**Weight rationale:**
- **LLM (0.60):** captures holistic semantic properties — voice, naturalness, coherence — that surface statistics cannot. Retains the largest weight because it is the most robust signal across content types.
- **Stylometric (0.25):** corroborates the LLM with statistical surface properties. Meaningful when the signals agree; not strong enough to override the LLM alone.
- **Formality (0.15):** a clean binary-like signal for register. Near-perfect on typical platform content (AI rarely produces contractions unprompted) but degrades on formally written human prose, so it receives the smallest weight.

**Conflict resolution:** the weighted average naturally resolves inter-signal disagreement. If the LLM disagrees with both heuristic signals (e.g., LLM says AI at 0.8, both heuristics say human at 0.2), the LLM's 0.60 weight pulls the result toward the uncertain band (0.60×0.8 + 0.25×0.2 + 0.15×0.2 = 0.56) rather than committing to either label. When all three signals agree, the combined weight produces high-confidence results well outside the uncertain band.

**Thresholds:**

| `final_score` range | classification | confidence_level |
|---------------------|----------------|-----------------|
| < 0.35 | `human` | `high` |
| 0.35 – 0.65 | `uncertain` | `uncertain` |
| > 0.65 | `ai_generated` | `high` |

The uncertain band is intentionally wide (30 points). A false positive — labeling a human's work as AI-generated — causes concrete harm to a creator. The system is designed to err toward "I don't know" rather than confident accusation.

**Example submissions showing score variation:**

*High-confidence AI text* — a formal paragraph about AI transforming industries:
```json
{
  "classification": "ai_generated",
  "confidence_score": 0.819,
  "confidence_level": "high",
  "signals": { "llm_score": 0.8, "stylo_score": 0.755, "formality_score": 1.0 }
}
```
All three signals agree strongly. The LLM detects the "covering all bases" structure; stylometrics catches uniform sentence lengths and formal vocabulary; formality detects zero contractions.

*High-confidence human text* — an informal personal anecdote:
```json
{
  "classification": "human",
  "confidence_score": 0.224,
  "confidence_level": "high",
  "signals": { "llm_score": 0.2, "stylo_score": 0.350, "formality_score": 0.107 }
}
```
All three signals agree. The LLM detects the idiosyncratic voice; stylometrics catches sentence length variation; formality detects contractions and informal tokens.

---

## Calibration Reference Set

5 known-human texts and 5 known-AI texts submitted to verify that the scoring distributions are meaningfully separated. Expected: AI texts cluster above 0.65, human texts cluster below 0.35.

**Known-human texts**

| Text | llm_score | stylo_score | formality_score | final_score | result |
|------|-----------|-------------|-----------------|-------------|--------|
| Informal personal anecdote (ramen rant) | 0.200 | 0.350 | 0.107 | 0.224 | human / high |
| Journal entry with self-correction | 0.100 | 0.385 | 0.091 | 0.170 | human / high |
| Personal essay fragment with em-dashes | 0.200 | 0.263 | 0.000 | 0.186 | human / high |
| Opinionated blog-style rant | 0.200 | 0.359 | 0.000 | 0.210 | human / high |
| Memoir-style observation | 0.200 | 0.388 | 0.206 | 0.248 | human / high |

Human average `final_score`: **0.207** (range 0.170–0.248)

**Known-AI texts**

| Text | llm_score | stylo_score | formality_score | final_score | result |
|------|-----------|-------------|-----------------|-------------|--------|
| Corporate transformation paragraph | 0.800 | 0.755 | 1.000 | 0.819 | ai_generated / high |
| Educational overview with enumeration | 0.800 | 0.807 | 1.000 | 0.832 | ai_generated / high |
| Structured benefits essay | 0.800 | 0.817 | 1.000 | 0.834 | ai_generated / high |
| Comprehensive guide introduction | 0.800 | 0.680 | 1.000 | 0.800 | ai_generated / high |
| Balanced analysis paragraph | 0.800 | 0.794 | 1.000 | 0.829 | ai_generated / high |

AI average `final_score`: **0.823** (range 0.800–0.834)

**Interpretation:** the two distributions do not overlap — the highest human score (0.248) is well below the lowest AI score (0.800), with a gap of ~0.55. All three signals agree in every case: the LLM signal cleanly separates at 0.1–0.2 vs 0.8, stylometrics corroborate at 0.26–0.39 vs 0.68–0.82, and formality is near-zero for all human texts vs 1.0 for all AI texts. The ensemble scoring is meaningful across this reference set.

---

## Transparency Labels

All three label variants, written out exactly as shown to users:

**High-confidence AI** (`final_score > 0.65`):

> "Our automated analysis found strong signals that this content may be AI-generated. This is not a definitive finding — our system can be wrong, especially for polished or formally written human work. If you are the creator and believe this assessment is incorrect, you can submit an appeal."

**Uncertain** (`0.35 ≤ final_score ≤ 0.65`):

> "Our system could not determine with confidence whether this content was written by a human or generated by AI. The signals were mixed or inconclusive. If you are the creator, you may submit an appeal to provide additional context that can help with review."

**High-confidence human** (`final_score < 0.35`):

> "Our automated analysis found strong signals that this content was written by a human. This assessment is based on stylistic and semantic patterns and reflects our best confidence at this time."

---

## Rate Limiting

**Limits:** 5 requests per minute per IP; 50 requests per hour per IP.

**Reasoning:** A real creative writer submits finished work — a poem, a story, a blog post. Submitting more than 5 pieces per minute is implausible for legitimate use. An adversary probing the classifier or exhausting the Groq API quota would need to submit at volume; 5/minute forces any flood to take at minimum 12× longer. The hourly cap of 50 backstops slow-drip attacks that stay under the per-minute limit. Both limits are per-IP to avoid blocking other users when one IP hits the cap.

When the limit is exceeded, the API returns HTTP `429 Too Many Requests`.

---

## Audit Log

The audit log is available at `GET /log`. Each entry includes:

| Field | Description |
|-------|-------------|
| `content_id` | UUID of the submission |
| `timestamp` | ISO 8601 UTC timestamp |
| `content_preview` | First 200 characters of the submitted text |
| `llm_score` | Raw LLM signal output (0–1) |
| `stylo_score` | Raw stylometric signal output (0–1) |
| `final_score` | Weighted combined score |
| `classification` | `human`, `ai_generated`, or `uncertain` |
| `confidence_level` | `high` or `uncertain` |
| `label_text` | The exact transparency label shown to the user |
| `status` | `classified` or `under_review` |
| `appeal_reasoning` | Creator's appeal text (if submitted) |
| `appeal_timestamp` | When the appeal was submitted |

---

## Known Limitations

**Anaphoric and repetitive poetry will be falsely flagged as AI-generated.** A poem that uses deliberate structural repetition — e.g., every stanza begins with the same phrase, uses simple vocabulary, and keeps line lengths uniform — will score high on the stylometric signal. Sentence length variance will be near zero, type-token ratio will be low, and expressive punctuation may be minimal. The stylometric signal was designed around statistical properties of prose; poetry deliberately violates those properties as a literary device, and the signal has no way to distinguish intentional repetition from AI-generated uniformity. The plain-language label for AI classifications explicitly acknowledges the system can be wrong for "polished or formally written human work," and the appeal pathway exists as the safety valve.

---

## Spec Reflection

**How the spec guided implementation:** the detailed signal design in `planning.md` — including exact formulas for all four stylometric sub-signals, the threshold table, and the verbatim label strings — meant implementing `signals.py` and `scoring.py` was essentially transcription rather than design work. Having the formula and all three label strings written out before writing any code eliminated ambiguity at every step.

**Where implementation diverged from the spec:** the spec says texts under 15 words should still call the LLM but be noted as potentially unreliable. The implementation uses a stricter threshold of 10 words and skips the LLM call entirely, returning `llm_score = 0.5` directly. The reason: calling Groq on a 7-word sentence burns an API call and returns a score that is noise — the LLM's confidence at that length is not calibrated. Skipping the call and returning the neutral score is more honest about what the system actually knows.

---

## AI Usage

**Instance 1: Generating the Flask skeleton and Signal 1 (Milestone 3)**

I provided Claude with the Architecture § Submission Flow diagram, the Signal 1 spec (exact prompt, output format, parse error handling), the `POST /submit` request/response shape, and the audit log schema. I asked it to generate a Flask app that called Groq, extracted `llm_score`, wrote to SQLite, and returned the specified JSON shape — with `stylo_score = 0.5` as a placeholder and no rate limiting yet.

Claude produced a working single-file `app.py`. What I revised: the generated code used a single `try/except` block around the entire Groq call that swallowed parse errors silently and returned 0.5 without any indication of failure. I broke this into a separate JSON-parse step that distinguishes a Groq API failure from a malformed response, so the error handling is explicit rather than silent.

**Instance 2: Refactoring into modules (post-Milestone 4)**

After all three milestones, the full implementation lived in a single `app.py` that had grown to ~200 lines mixing routing, signal computation, scoring, and database access. I asked Claude to split it into `database.py`, `signals.py`, and `scoring.py` using the existing code as input, with no logic changes — just extraction.

Claude split the file correctly but placed the LLM call inside `scoring.py`, creating a dependency where the pure math module was importing from the signal module. I caught this during review and moved the LLM call back to `app.py` where it belonged, keeping `scoring.py` a pure computation module with no external dependencies. The final module boundaries — `signals` owns detection, `scoring` owns math, `database` owns persistence, `app` owns routing — are cleaner than the AI's first pass.

---

## Architecture Overview

```
POST /submit
     │
     ▼
Rate Limiter (5/min, 50/hr per IP) ──► 429 if exceeded
     │
     ▼
Signal 1: LLM Classifier (Groq)  → llm_score
Signal 2: Stylometric Heuristics → stylo_score
     │
     ▼
final_score = 0.65 × llm_score + 0.35 × stylo_score
     │
     ▼
classify() → classification, confidence_level
generate_label() → label_text
     │
     ▼
SQLite audit_log (INSERT)
     │
     ▼
JSON response: content_id, classification, confidence_score,
               label_text, signals, status, appeal_url
```
