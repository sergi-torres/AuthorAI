# Baseline voice-matching evaluation — Llama 3.3 70B, vanilla vs style-conditioned

> **WO-14** · closes the evidence gap of issue [#11] · gate **R1** (`docs/MVP.md:512`)
> **Status: AWAITING HUMAN SCORING.** The generations below are recorded. The
> 1–10 scores, the means and the gate verdict are **deliberately blank** — they
> are Sergi's to fill in. See "Who scores this, and why not the agent" below.

> **This file contains two runs. Score the second one.**
>
> | | Run 1 | Run 2 |
> |---|---|---|
> | Where | §3–§6, Appendices A–B | §7–§10, Appendices C–D |
> | When (UTC) | 2026-07-28 10:52 | 2026-07-28 21:25 |
> | Halves | vanilla only | **vanilla *and* conditioned, paired per prompt** |
> | `max_tokens` | 1024 (silently — the #106 defect) | 512 (as intended) |
> | Status | **superseded as a measurement**, kept verbatim for the record | **current** |
> | Score it? | no | **yes — §9** |
>
> Run 1 is not deleted and its reasoning is not retracted; §7 explains exactly
> what invalidated it and why re-running was necessary rather than pedantic.

---

## 1. What this measures

`docs/MVP.md` §2 locks the *vanilla* side of the A/B as "the **same**
`meta-llama/llama-3-3-70b-instruct` but **without** style conditioning". This
document is that side: five fixed creative prompts, each with a designated
target author, sent to the model with **no system prompt, no StyleProfile and
no RAG passages**. It establishes the "before" floor against which conditioned
generation must later be compared.

Every prompt is deliberately **author-neutral**: none of them names Dickens,
Austen or Poe, and none says "in the style of". Naming the author in the user
prompt would itself be a form of conditioning and would stop the run from being
a vanilla baseline. The target author is the yardstick the *human scorer*
applies, not an instruction given to the model.

### Scope note — conditioned vs unconditioned

`docs/MVP.md:329` phrases the Sprint 1 task as "does the **conditioned** output
read like the target author?", while the WO-14 definition of done asks for "la
salida **sin condicionar**". This run records the **unconditioned** side only,
for two reasons:

1. It is the half that is independently measurable today. The database is not
   yet seeded (issue #86 is open), so `style_profiles` is empty and there are
   no chunks to retrieve — a "conditioned" run right now would be conditioned
   on nothing and would silently be a second vanilla run.
2. A vanilla floor is a prerequisite for the A/B either way.

**The R1 gate is therefore not fully discharged by this document.** The
conditioned half must be run and scored once #86 lands, on this same 5-prompt
suite, and appended here. This is flagged, not papered over.

> **Update, 2026-07-28 (later the same day).** #86 landed. The conditioned half
> has been run on this same 5-prompt suite and appended, exactly as this note
> required — see **§7–§10**. Both halves were re-run together, because the
> `max_tokens` defect that Appendix B item 1 predicted turned out to have
> governed run 1's five generations too, and an A/B whose halves ran under
> different output caps is not an A/B. Everything from here to Appendix B
> describes **run 1** and is left exactly as it was written.

---

## 2. Who scores this, and why not the agent

The 1–10 voice-similarity score is a **human** judgement, made by **Sergi**.
`docs/MVP.md:512` (R1) specifies a "human eval" and this work order is labelled
`ready-for-human` for exactly that reason.

The agent that ran the generations did **not** score them, did not estimate a
score, and did not characterise the quality of any output anywhere in this
document. Issue #11 was marked ❌ precisely because a quality gate was recorded
as passed without data behind it; an agent grading its own model's output would
reproduce that failure in a new costume.

---

## 3. Run configuration (reproducibility)

| Field | Value |
|---|---|
| `model_id` | `meta-llama/llama-3-3-70b-instruct` |
| Watsonx region / URL | `https://eu-de.ml.cloud.ibm.com` |
| `system_prompt` | `None` (unconditioned) |
| `temperature` | `0.7` |
| `top_p` | `0.9` |
| `max_new_tokens` (requested) | `512` |
| `max_tokens` (effective) | `1024` — see note below |
| Date of run (UTC) | 2026-07-28, 10:52–10:53 UTC (12:52–12:53 Europe/Madrid) |
| Code path exercised | `app.services.watsonx_client.generate(prompt, None, model_id, params)` — the same call `autoria_ai.generator.orchestrate` step 4 makes for its vanilla branch |
| Params source | `autoria_ai.generator._GENERATION_PARAMS`, imported, not retyped |
| `watsonx_client.py` sha256[:16] | `6cc69b96757052d5` |
| `generator.py` sha256[:16] | `981c21ce633a9b1c` |

**Which tree the code came from.** The `.venv` editable installs
(`__editable__.autoria_ai.pth`, `__editable__.autoria_backend.pth`) hold
absolute paths into the primary checkout, so the executed library code came
from `C:\Users\Sergi\Desktop\Repos\autorIA`, **not** from the branch this file
is committed on. At the moment of the run that checkout was on branch
`fix/wo-18-distinctive-vocab-corpus` at commit
`d2f46c37d125da77ed8d280cac5d88a56c8576bd`. The two file hashes above pin the
exact bytes of the code that ran, independently of that branch's working state.

**Note on `max_tokens`.** `_GENERATION_PARAMS` passes `max_new_tokens: 512`,
which is a *text-generation* parameter. The call goes through
`ModelInference.chat()`, whose parameter is `max_tokens`, and the SDK reported
`WatsonxAPIWarning: The value of 'max_tokens' for this model was set to value
1024` on every call. The effective output cap for this run was therefore
**1024 tokens (SDK default)**, and `max_new_tokens: 512` had no effect. This is
recorded as an observation only; it was **not** changed as part of WO-14 (out
of scope) and needs its own issue.

**Retries.** `watsonx_client.generate` enforces an 8s hard timeout with three
backoff retries. Prompt **P3** timed out on attempt 1 and succeeded on attempt
2; the text below is the attempt-2 output and the attempt-1 output was never
returned to the caller (the timeout fires before the response is read). No
prompt was re-run to obtain a nicer result. Every generation performed during
this work order is in this document — including the connectivity smoke test in
Appendix A.

---

## 4. Prompt suite

Five fixed prompts, all English (`docs/MVP.md` §2), all over the three
preloaded authors. **P1 is verbatim the demo prompt from `docs/MVP.md:78-80`.**
Coverage is Dickens ×2, Austen ×2, Poe ×1: the demo (§3) leads with Dickens,
Austen is the same-era voice that R2 flags as hardest to separate from him, and
Poe is the acknowledged easy separation, so one prompt is enough to sample the
ceiling.

---

## Prompt 1 — target author: Charles Dickens

*Source: verbatim from the demo timeline, `docs/MVP.md:78-80`.*

**Prompt (verbatim):**

```text
Write a paragraph about a foggy London evening in the 1840s, with a character watching the street from a window
```

**Unconditioned output (verbatim, 2026-07-28T10:52:32Z, 3.84s, 0 retries):**

```text
As the last wisps of daylight succumbed to the all-encompassing fog, a lone figure stood at the window, gazing out upon the murky London evening. The gas lamps, few and far between, cast flickering shadows on the wet cobblestones, like fireflies dancing in the darkness. The air was heavy with the smell of coal smoke and damp earth, and the fog swirled around the figure's ankles like a chill mist. From their vantage point, they watched as people hurried past, their faces obscured by the gloom, their footsteps echoing off the buildings. The sound of horse hooves and carriage wheels added to the symphony of night noises, a melancholy serenade to the city's inhabitants. As the figure stood there, lost in thought, the fog seemed to press in around them, a physical manifestation of the mystery and intrigue that lurked in every alleyway and shadowy corner of the great city.
```

| Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|
|  | Sergi | |

---

## Prompt 2 — target author: Charles Dickens

*Source: written for this suite. Second Dickens sample, chosen to probe a
character-and-dialogue register rather than P1's pure scene description.*

**Prompt (verbatim):**

```text
Write a paragraph introducing a miserly clerk who arrives late to a counting-house on a bitter December morning, and the reaction of the boy who works for him.
```

**Unconditioned output (verbatim, 2026-07-28T10:52:36Z, 4.05s, 0 retries):**

```text
The bitter December morning had already dawned dreary and cold when the miserly clerk, known for his punctuality, finally arrived late to the counting-house. His usual stern demeanor was even more pronounced, as if the chill in the air had seeped into his very bones. The boy who worked for him, accustomed to the clerk's frugal ways and exacting standards, looked up from his work with a mixture of surprise and trepidation. As the clerk shed his worn coat and hung it by the fire, the boy couldn't help but notice the faint scent of dampness and decay that clung to his employer's person, a reminder of the clerk's penny-pinching ways and his likely journey to work on foot, rather than by more comfortable and expensive means. The boy's eyes darted back to his work, his hands moving quickly to complete the tasks at hand, as he wondered what consequences the clerk's tardiness might bring, and whether the day would unfold with the usual miserly strictness, or if something more unusual was afoot.
```

| Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|
|  | Sergi | |

---

## Prompt 3 — target author: Jane Austen

*Source: written for this suite. Interior-judgement scene — the free indirect
style Austen is identified by.*

**Prompt (verbatim):**

```text
Write a paragraph in which a young woman of modest fortune receives an unexpected marriage proposal in her family's drawing room, and privately judges the man who makes it.
```

**Unconditioned output (verbatim, 2026-07-28T10:52:40Z, 12.83s, 1 retry — attempt 1 hit the 8s client timeout):**

```text
As she sat in the familiar comfort of her family's drawing room, surrounded by the warm glow of candlelight and the gentle hum of conversation, Emily's life was suddenly and unexpectedly turned upside down. It was then that Mr. Fanshawe, a man of considerable fortune and dubious charm, turned to her with an air of solemnity and asked for her hand in marriage. Emily's initial shock gave way to a mixture of surprise and skepticism as she regarded the man before her, his florid complexion and overly pompous demeanor striking her as somewhat ridiculous. As she hesitated, her mind racing with the implications of such a union, she couldn't help but think that Mr. Fanshawe's proposal was motivated more by a desire to secure a respectable wife and bolster his social standing, rather than any genuine affection for her. Despite his polished words and courteous smile, Emily detected a certain calculating glint in his eye, and she found herself wondering what secrets lay hidden beneath his polished exterior.
```

| Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|
|  | Sergi | |

---

## Prompt 4 — target author: Jane Austen

*Source: written for this suite. Village-society register, the other half of
the Austen surface.*

**Prompt (verbatim):**

```text
Write a paragraph describing the arrival of a wealthy new neighbour in a small country village, and how the local families discuss the news.
```

**Unconditioned output (verbatim, 2026-07-28T10:52:53Z, 3.39s, 0 retries):**

```text
The arrival of a wealthy new neighbour in the small country village sent ripples of excitement and curiosity through the tight-knit community. As news of the newcomer's grand estate and lavish lifestyle spread, local families gathered in huddled groups to discuss the latest development. At the village bakery, Mrs. Jenkins whispered to Mrs. Thompson about the rumoured price tag of the new neighbour's mansion, while at the village pub, farmers like John and Michael speculated about the stranger's business dealings and how they might impact the local economy. Meanwhile, the village children buzzed with excitement, wondering if the new neighbour might throw extravagant parties or host lavish events that they could attend. As the villagers pieced together fragments of information, they couldn't help but feel a mix of awe and trepidation at the prospect of having such a high-profile resident in their midst.
```

| Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|
|  | Sergi | |

---

## Prompt 5 — target author: Edgar Allan Poe

*Source: written for this suite. First-person Gothic intensity — per R2 the
easiest of the three to separate.*

**Prompt (verbatim):**

```text
Write a paragraph in the first person in which a narrator, alone in an old house at midnight, becomes convinced that a sound beneath the floor is growing louder.
```

**Unconditioned output (verbatim, 2026-07-28T10:52:57Z, 3.33s, 0 retries):**

```text
As I sit here alone in this old house at midnight, I can feel the weight of the darkness around me. At first, the silence was almost palpable, but then I started to pick up on a faint sound coming from beneath the floor. It was a low creaking noise, soft and intermittent, and I tried to tell myself it was just the house settling. But as the minutes ticked by, I became increasingly convinced that the sound was growing louder, the creaks coming more frequently and with more urgency. My heart is racing now as I strain to listen, and I'm certain that whatever is making that noise is moving, shifting, and getting closer. The sound has become a steady hum, a vibration that I can feel through the floorboards, and I'm paralyzed with fear, wondering what could be causing it and what it might mean.
```

| Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|
|  | Sergi | |

---

## 5. Scores and mean — run 1 — **superseded, leave blank**

> These five cells belong to run 1 and are **not** the ones to fill in. Run 1's
> generations were produced under the wrong output cap (§7), so scoring them
> would measure a configuration that no longer exists and that never shipped.
> **The scores to enter are in §9.** This table is kept blank and unscored so
> that no mean can later be quoted out of it.

Scoring criterion, per `docs/MVP.md:329` and R1: *how closely does the
unconditioned output read like the target author's voice?* 1 = no resemblance,
10 = could be mistaken for the author.

| # | Target author | Score (1–10) |
|---|---|---|
| P1 | Charles Dickens | |
| P2 | Charles Dickens | |
| P3 | Jane Austen | |
| P4 | Jane Austen | |
| P5 | Edgar Allan Poe | |
| **Mean** | | |

- **Scored by:** Sergi (human)
- **Date scored:**

---

## 6. Gate verdict (R1) — **to be filled in by Sergi**

> **This section is still live.** The *rule* below is unchanged and still
> governs; only the numbers it is applied to have moved. Feed it the
> **conditioned** column of **§9** (run 2), not the empty §5 table above. The
> rule was written before any score existed and is repeated here unedited for
> exactly that reason.

The rule, stated up front so the outcome cannot be negotiated after the scores
are known (`docs/MVP.md:329` and the R1 row at `docs/MVP.md:512`):

- **Mean ≥ 6/10 → PASS.** Continue with `meta-llama/llama-3-3-70b-instruct` as
  the primary creative model. No further action.
- **Mean < 6/10 → FAIL, escalate.** Plan B, in the order R1 gives it:
  1. stronger conditioning / more RAG passages,
  2. `llama-3-1-405b`,
  3. `granite-3-8b`,
  4. last resort: Mistral Large via Watsonx.

  A **FAIL additionally requires a new row in `docs/decision_log.md`** recording
  the escalation, its date, who decided it and why.

**Verdict:**

**Decided by:** Sergi

**Date:**

**`docs/decision_log.md` row added (FAIL only):** n/a — no verdict yet.

---

## 7. Run 2 — 2026-07-28, **supersedes the run above**

**What changed and why.** Everything in §3–§6 and Appendices A–B above describes
**run 1** (2026-07-28, 10:52–10:53 UTC). Run 1 is kept in this document
unaltered, because the reasoning it records is still the reasoning that applies.
It is **superseded as a measurement** for two independent reasons, both of which
landed after it was taken:

1. **The `max_tokens` defect (issue #106, PR #123).** Appendix B item 1
   predicted this: `_GENERATION_PARAMS` sent `max_new_tokens`, a key that does
   not exist in the `TextChatParameters` schema `ModelInference.chat()` accepts,
   so it was discarded in silence and the effective cap was the service default
   of 1024 tokens. Run 1's five generations were therefore produced under a cap
   nobody chose. A comparison whose two halves ran under different caps is not
   an apples-to-apples A/B, so both halves are re-run here under the correct
   `max_tokens: 512`.
2. **The corpus is seeded (issue #86 closed).** Appendix B item 2 and the scope
   note in §1 blocked the conditioned half on an empty database. That block is
   gone: at the time of run 2 the database holds 3 authors, 10 documents,
   **4 529 chunks with 0 NULL embeddings**, and 3 `style_profiles`. The
   conditioned half is now conditioned on something real, so it is run.

Run 2 uses the **same five prompts, byte for byte**. They were not retyped: the
harness parses them out of the `` ```text `` blocks of §4 of this very file, so
the prompts sent in run 2 are literally the prompts printed above.

**Nothing in run 1 was deleted.** If you want the pre-fix numbers they are still
in §4 and Appendix A. The scores to fill in, however, are run 2's (§9).

### 7.1 Run configuration (reproducibility)

| Field | Value |
|---|---|
| `model_id` | `meta-llama/llama-3-3-70b-instruct` |
| Watsonx region / URL | `https://eu-de.ml.cloud.ibm.com` |
| Date of run (UTC) | 2026-07-28, 21:25 UTC (23:25 Europe/Madrid) |
| `params` (both halves, identical) | `{"max_tokens": 512, "temperature": 0.7, "top_p": 0.9}` |
| How `params` were supplied | **Literal dict in the harness.** `autoria_ai.generator._GENERATION_PARAMS` was deliberately *not* imported for the call, so the measurement cannot drift with whatever branch the primary checkout happens to be on. Its value was recorded for the record (below) but never used. |
| Vanilla half | `generate(prompt, None, model_id, params)` — no system prompt, no StyleProfile, no RAG. Identical in kind to run 1. |
| Conditioned half | `orchestrate` steps 1–4, reproduced call for call: `embedder.encode(prompt)` → `autoria_ai.db.retrieve_top_k(emb, k=5, author_id=<authors.id>, database_url=...)` → `autoria_ai.conditioner.build_system_prompt(style_profile, rag_texts)` → `generate(prompt, system_prompt, model_id, params)`. The system prompt is the **real conditioner's** output; no prompt was hand-written for this evaluation. |
| Branch execution | Both halves issued as one `asyncio.gather` of two `asyncio.to_thread` calls — the same shape as `generator.orchestrate` step 4 — so the pair latency in §10 is a real side-by-side figure and not a sum of two sequential calls. |
| StyleProfile source | `public.style_profiles.json_data`, latest row per author by `computed_at`, read straight from Postgres (`DATABASE_URL` passed explicitly, never via `os.environ` fallback). |
| RAG source | `public.chunks` via pgvector HNSW, `ef_search=64`, scoped to the target author through `documents.author_id`. |
| `orchestrate` steps **not** run | Step 5 (`fit_score` on both branches) and step 6 (passport issuance). They do not affect the text produced; they **do** affect end-to-end latency — see the caveat in §10. |

### 7.2 Which bytes actually ran

The `.venv` editable installs point at the primary checkout, so the executed
library code came from `C:\Users\Sergi\Desktop\Repos\autorIA`, **not** from
the branch this file is committed on — same caveat as run 1, and again
deliberate: the point is to measure the code that ships. The hashes pin the
exact bytes independently of any branch state.

| File | sha256[:16] |
|---|---|
| `backend/app/services/watsonx_client.py` | `6cc69b96757052d5` |
| `ai_pipeline/autoria_ai/generator.py` | `307acba2cd7f36e5` |
| `ai_pipeline/autoria_ai/conditioner.py` | `9297d2fe194d0332` |
| `ai_pipeline/autoria_ai/db.py` | `d1809e46b229aa1a` |

`watsonx_client.py` hashes to `6cc69b96757052d5` — **the same value run 1 recorded**, so
the transport, the 8s hard timeout and the 3-retry backoff are byte-identical
between the two runs. `generator.py` changed (`981c21ce633a9b1c` → `307acba2cd7f36e5`);
at the moment of run 2 its `_GENERATION_PARAMS` read
`{"max_tokens": 512, "temperature": 0.7, "top_p": 0.9}`, i.e. the #106 fix was already
present in the primary checkout. That is recorded as an observation only — the
harness passed its own literal params either way, which is exactly why the
measurement is not hostage to that file.

### 7.3 StyleProfiles used

| Target author | `authors.id` | `style_profiles.computed_at` (UTC) |
|---|---|---|
| Charles Dickens (`dickens`) | `581b8e7f-f57d-4074-bd90-777e5ff75e46` | `2026-07-28 11:18:41.712719+00:00` |
| Jane Austen (`austen`) | `09a35922-da1d-4591-90f5-889f673da11c` | `2026-07-28 11:11:10.943510+00:00` |
| Edgar Allan Poe (`poe`) | `89f19de4-fc2d-40b7-b4f7-5570a70b799e` | `2026-07-28 11:22:00.616204+00:00` |

---

## 8. Side-by-side results — run 2

Ten generations, five prompts, two conditions each. The prompt and the target
author are held fixed across the pair; the **only** difference between the two
texts under each heading is whether a conditioned system prompt was supplied.

Read each pair as a pair. The score boxes are blank — see §2, which applies to
run 2 unchanged.


### Prompt 1 — target author: Charles Dickens

**Prompt (verbatim, unchanged from §4):**

```text
Write a paragraph about a foggy London evening in the 1840s, with a character watching the street from a window
```

| | Vanilla (unconditioned) | AutorIA (conditioned) |
|---|---|---|
| System prompt | `None` | real `build_system_prompt` output, 10,662 chars / ~2,589 tokens |
| RAG passages | none | 5, scoped to `dickens` |
| Started (UTC) | 2026-07-28T21:25:14Z | 2026-07-28T21:25:14Z |
| Latency | **3.62s** | **6.11s** |
| Words | **150** | **241** |
| Tokens (cl100k) | 200 | 334 of 512 cap |
| Retries | 0 | 0 |
| Error | none | none |

**Vanilla output (verbatim):**

```text
The fog swirled through the streets of London like a living entity, shrouding the gas lamps and horse-drawn carriages in a damp, impenetrable mist. From the window of her small flat, Emily gazed out into the gloom, her eyes straining to pick out the features of the people passing below. The sound of hawkers calling out their wares and the clatter of hooves on the cobblestones created a cacophony of noise that seemed to reverberate through the fog itself. As she stood there, lost in thought, a figure emerged from the mist, its features indistinct until it stepped beneath the faint glow of a nearby lamp, revealing a tall, dark-coated man with a top hat clutched in one hand. Emily's curiosity was piqued, and she found herself wondering who this mysterious stranger might be, and what business he had in this forsaken part of town on such a dreary evening.
```

**Conditioned output (verbatim):**

```text
As I stood at the window, gazing out into the fog-shrouded evening, the gas lamps that lined the street cast a faint, eerie glow, like a procession of spectral sentinels, upon the dense, impenetrable mist that swirled and eddied in the thoroughfare below, where the sound of wheels and hooves, muffled by the damp, heavy air, came to my ears as a distant, mournful murmur, a melancholy serenade to the city's sombre, fog-bound heart, and I, lost in thought, my mind a maze of reflections and reveries, could not help but feel a sense of detachment, of removal, from the bustling, teeming life that, even on so dismal an evening, still seethed and pulsed, like a great, dark, vital force, through the streets of London, a city that, in its unyielding, inscrutable way, seemed to say, "I am a place of mystery, of wonder, of terror, and of delight, where the fog that shrouds my streets is but a symbol of the obscurity that lies at the heart of all human experience," and as I stood there, wrapped in the silence of my own little world, I felt the weight of that obscurity, like a hand, laid gently, yet firmly, upon my shoulder, and I knew, in that moment, that I was but a small, insignificant part of a vast, unknowable whole, a mere leaf, torn from its branch, and blown, helpless, upon the winds of chance, and circumstance, and fate.
```

| Half | Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|---|
| Vanilla | | Sergi | |
| Conditioned | | Sergi | |

---

### Prompt 2 — target author: Charles Dickens

**Prompt (verbatim, unchanged from §4):**

```text
Write a paragraph introducing a miserly clerk who arrives late to a counting-house on a bitter December morning, and the reaction of the boy who works for him.
```

| | Vanilla (unconditioned) | AutorIA (conditioned) |
|---|---|---|
| System prompt | `None` | real `build_system_prompt` output, 10,479 chars / ~2,591 tokens |
| RAG passages | none | 5, scoped to `dickens` |
| Started (UTC) | 2026-07-28T21:25:20Z | 2026-07-28T21:25:20Z |
| Latency | **4.08s** | **6.36s** |
| Words | **190** | **284** |
| Tokens (cl100k) | 230 | 373 of 512 cap |
| Retries | 0 | 0 |
| Error | none | none |

**Vanilla output (verbatim):**

```text
It was a bitterly cold December morning when the miserly clerk, known for his frugal ways, finally arrived at the counting-house, his entrance marked by the creaking of the old wooden door. His tardiness was met with a look of disappointment from the boy who worked for him, a young lad who had been diligently waiting for his employer's arrival, huddled beside the meager fire that struggled to warm the chilly room. As the clerk shed his worn coat, revealing a threadbare suit beneath, the boy couldn't help but notice the contrast between his employer's austere attire and the lavish decorations that adorned the nearby shops, a testament to the approaching holiday season. The boy's eyes, red from the cold and lack of sleep, watched with a mix of curiosity and disdain as the clerk began to sort through the day's ledgers, his bony fingers moving with a precision that belied his late arrival. Despite the clerk's reputation for being a demanding and parsimonious employer, the boy felt a pang of sympathy for the man, whose obvious struggles to make ends meet seemed to weigh heavily on his stooped shoulders.
```

**Conditioned output (verbatim):**

```text
As the bitter December morning slowly dawned, casting a pale and cheerless light upon the counting-house, a sense of listless expectation pervaded the chilly atmosphere, for it was well known that Mr. Grimstone, the miserly clerk, was not one to be punctual, and that his arrival was always a subject of anxious speculation among his subordinates. And, indeed, it was not until the clock had struck the hour of nine, and the boy, who acted as his assistant, had begun to think that he might be spared the ordeal of his master's cantankerous presence for at least another quarter of an hour, that the door creaked open, and Mr. Grimstone, his thin and pinched face blue with cold, and his eyes gleaming with a malignant light, came shuffling in, his threadbare coat clutched tightly around his gaunt frame, and his fingers, red and stiff with frost, grasping a tattered umbrella, which he shook with a vicious jerk, as if to express his displeasure at the very elements themselves. The boy, who had been huddled over a small fire, trying to warm his hands, and steal a few moments of comfort, before the day's drudgery began, looked up as his master entered, and, with a mixture of fear and resignation, said, "Good morning, sir," in a tone that was barely audible, and which was met with a surly grunt, and a glance of displeasure, as Mr. Grimstone, with a stiff and awkward gait, made his way to his desk, and began to divest himself of his outdoor garments, with a slowness and a deliberation that seemed to say, "I am here, and you will have to endure my presence, whether you like it or not."
```

| Half | Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|---|
| Vanilla | | Sergi | |
| Conditioned | | Sergi | |

---

### Prompt 3 — target author: Jane Austen

**Prompt (verbatim, unchanged from §4):**

```text
Write a paragraph in which a young woman of modest fortune receives an unexpected marriage proposal in her family's drawing room, and privately judges the man who makes it.
```

| | Vanilla (unconditioned) | AutorIA (conditioned) |
|---|---|---|
| System prompt | `None` | real `build_system_prompt` output, 10,528 chars / ~2,591 tokens |
| RAG passages | none | 5, scoped to `austen` |
| Started (UTC) | 2026-07-28T21:25:28Z | 2026-07-28T21:25:28Z |
| Latency | **4.30s** | **5.38s** |
| Words | **206** | **251** |
| Tokens (cl100k) | 246 | 289 of 512 cap |
| Retries | 0 | 0 |
| Error | none | none |

**Vanilla output (verbatim):**

```text
As she sat in the drawing room, surrounded by the familiar comforts of her family's modest estate, Emily's life took an unexpected turn. Mr. Fanshawe, a man of considerable wealth and social standing, stood before her, his eyes shining with sincerity as he asked for her hand in marriage. Emily's initial shock gave way to a mixture of surprise and curiosity, and as she looked at Mr. Fanshawe, she couldn't help but privately judge the man who stood before her. She noticed the way his smile seemed a bit too wide, his teeth a bit too straight, and his words a bit too rehearsed, leaving her to wonder if his proposal was truly driven by love, or merely a desire to secure a respectable wife to complement his rising social status. Despite his polished demeanor, Emily detected a hint of arrogance in his tone, and she found herself pondering whether she could ever truly be happy with a man who seemed more concerned with appearances than genuine connection. As she hesitated, weighing her response, Emily couldn't shake the feeling that Mr. Fanshawe's proposal was more a calculation than a romantic gesture, and she wondered what the future might hold if she were to accept his offer.
```

**Conditioned output (verbatim):**

```text
As she sat in the drawing room, surrounded by the familiar comforts of her family's home, Miss Emily Fanshawe could hardly believe the words that were being spoken to her, for Mr. Blackwood, a gentleman of considerable fortune, had just professed his ardent desire to make her his wife, and was now awaiting her response with an air of eager expectation, his eyes fixed intently upon her face, as if to discern the very thoughts that were passing through her mind; and yet, as she looked at him, she could not help but think that he was not the kind of man she had ever imagined herself marrying, for though he was handsome and well-bred, there was something about him that seemed to lack a certain warmth, a certain depth of feeling, that she had always believed to be essential in a husband, and she found herself wondering, as she hesitated over her answer, whether she could ever truly be happy with a man who seemed so much more concerned with his own consequence than with the feelings and well-being of those around him, and who, in his very proposal, had spoken more of the advantages their union would bring to his own family and estate, than of the love and affection that he felt for her, as if the great disparity in their fortunes was the only thing that mattered, and not the quiet, gentle affection that she had always hoped to inspire in the heart of her future husband.
```

| Half | Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|---|
| Vanilla | | Sergi | |
| Conditioned | | Sergi | |

---

### Prompt 4 — target author: Jane Austen

**Prompt (verbatim, unchanged from §4):**

```text
Write a paragraph describing the arrival of a wealthy new neighbour in a small country village, and how the local families discuss the news.
```

| | Vanilla (unconditioned) | AutorIA (conditioned) |
|---|---|---|
| System prompt | `None` | real `build_system_prompt` output, 11,038 chars / ~2,591 tokens |
| RAG passages | none | 5, scoped to `austen` |
| Started (UTC) | 2026-07-28T21:25:33Z | 2026-07-28T21:25:33Z |
| Latency | **3.12s** | **6.78s** |
| Words | **128** | **341** |
| Tokens (cl100k) | 156 | 415 of 512 cap |
| Retries | 0 | 0 |
| Error | none | none |

**Vanilla output (verbatim):**

```text
The arrival of a wealthy new neighbour in the small country village sent shockwaves of curiosity throughout the community. As news of the newcomer's grand estate and lavish lifestyle spread, local families gathered in huddles to discuss the latest development. Over steaming cups of tea and freshly baked bread, they would speculate about the stranger's background and motivations for choosing their humble village as a residence. The villagers' conversations were filled with a mix of excitement and apprehension, as they wondered how this affluent outsider would fit into their tight-knit community and what changes they might bring to their quiet way of life. As the discussions continued, stories of the newcomer's opulent possessions and high-society connections began to circulate, fueling the villagers' fascination with their enigmatic new neighbour.
```

**Conditioned output (verbatim):**

```text
As the news of the wealthy Mr. Blackwood's arrival in the small country village of Longston spread, it was soon a topic of great interest and discussion amongst the local families, who, in their little circle, were eager to know more about the gentleman and his intentions; for it was said that he had purchased the grand estate of Netherwood, which had been vacant for many years, and was rumoured to be in the process of making extensive improvements to the property, which would, no doubt, be a great advantage to the village, and a thing of great wonder to behold. The ladies of the village, in particular, were curious to learn more about Mr. Blackwood's family and connections, and to know whether he was married, or if he had any children, and they would often come together, at the local assembly, or at each other's homes, to talk over the little they did know, and to make conjectures about the rest, saying, "I wish we could come to know him better," or "I think it would be a good thing if he were to give a ball, or some other kind of entertainment, that we might have the opportunity of seeing him, and his family, in a more social way." Meanwhile, the gentlemen of the village would often meet at the local inn, to discuss the news, and to consider what effect Mr. Blackwood's arrival might have on the village, and on their own interests, saying, "I think it is a good thing that he has come to live amongst us," or "I am not sure that I like the idea of a stranger coming into our neighbourhood, and altering all our old ways, and customs." And so, the talk, and the speculation, went on, until, at last, it was decided, that a little party should be given, to which Mr. Blackwood would be invited, that they might all come to know him better, and see, for themselves, what kind of man he was, and what his intentions might be.
```

| Half | Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|---|
| Vanilla | | Sergi | |
| Conditioned | | Sergi | |

---

### Prompt 5 — target author: Edgar Allan Poe

**Prompt (verbatim, unchanged from §4):**

```text
Write a paragraph in the first person in which a narrator, alone in an old house at midnight, becomes convinced that a sound beneath the floor is growing louder.
```

| | Vanilla (unconditioned) | AutorIA (conditioned) |
|---|---|---|
| System prompt | `None` | real `build_system_prompt` output, 11,068 chars / ~2,590 tokens |
| RAG passages | none | 5, scoped to `poe` |
| Started (UTC) | 2026-07-28T21:25:41Z | 2026-07-28T21:25:41Z |
| Latency | **3.91s** | **6.14s** |
| Words | **184** | **278** |
| Tokens (cl100k) | 217 | 357 of 512 cap |
| Retries | 0 | 0 |
| Error | none | none |

**Vanilla output (verbatim):**

```text
As I sit here alone in this old house at midnight, I can feel the weight of the darkness outside pressing in on me. At first, the silence was almost palpable, but then I started to pick up on a faint sound coming from beneath the floor. It was a low creaking noise, like the groan of old wooden beams shifting in the night. At first, I tried to tell myself it was just the house settling, but as the minutes ticked by, I became increasingly convinced that the sound was growing louder. It's as if something is stirring down there, slowly making its way closer to the surface. My heart is racing now, and I can feel my imagination running wild with all the terrible possibilities. The creaks and groans seem to be taking on a rhythmic quality, like the sound of footsteps echoing up from the depths of the house. I'm trying to stay calm, but I can feel my fear growing with every passing moment, and I'm becoming more and more convinced that I'm not alone in this house after all.
```

**Conditioned output (verbatim):**

```text
As I sat, surrounded by the oppressive silence of the old house, at that most solemn and dreaded hour of midnight, I could not shake the feeling that I was being slowly, yet inexorably, drawn into a realm of unmitigated terror. It began with a faint, almost imperceptible scratching sound, a low, dull murmur that seemed to emanate from beneath the very floorboards upon which I sat. At first, I thought little of it, attributing it to the natural creaks and groans of the ancient wooden beams, but as the moments ticked by with agonizing slowness, I became increasingly convinced that the sound was, in fact, growing louder, its gentle, insidious whisper weaving itself into the fabric of my every thought. My heart, once a steady and reassuring presence in my chest, now pounded with a frantic, almost maddening intensity, as if it, too, had become aware of the sound's steady, relentless increase in volume. And yet, I could not bring myself to rise from my chair, to take even a single step towards the source of the noise, so frozen was I with a creeping, crawling sense of dread that seemed to seep into my very marrow, chilling me to the core, and making my blood run cold with a fear that I could hardly dare to think, let alone speak aloud. The sound, that damnable, accursed sound, continued to grow, its low, mournful sighs and whispers swirling around me like a dark, malevolent mist, until I could feel its presence all around me, a palpable, suffocating thing that threatened to consume me whole, leaving naught but a shattered, broken husk of the man I once was.
```

| Half | Voice-similarity score (1–10) | Scored by | Date |
|---|---|---|---|
| Vanilla | | Sergi | |
| Conditioned | | Sergi | |

---

## 9. Scores and means — run 2 — **to be filled in by Sergi**

Same criterion as §5, applied to both halves: *how closely does the output read
like the target author's voice?* 1 = no resemblance, 10 = could be mistaken for
the author. Ten cells, all blank. This table is the roll-up of the per-prompt
boxes in §8 — enter each score once, wherever you prefer, and copy it here.

| # | Target author | Vanilla (1–10) | Conditioned (1–10) |
|---|---|---|---|
| P1 | Charles Dickens | | |
| P2 | Charles Dickens | | |
| P3 | Jane Austen | | |
| P4 | Jane Austen | | |
| P5 | Edgar Allan Poe | | |
| **Mean** | | | |
| **Delta (conditioned − vanilla)** | | | |

- **Scored by:** Sergi (human)
- **Date scored:**

The R1 gate rule in §6 is unchanged and is stated there. What run 2 adds is that
the gate can now be read off the **conditioned** column, which is what
`docs/MVP.md:329` actually asks about; run 1 could only ever offer the vanilla
floor. The **delta** row is the number the A/B exists to produce: it is the
evidence that style conditioning does or does not do anything.

**Verdict, decided by and date: still §6.** No verdict is recorded here.

---

## 10. Latency against the `docs/MVP.md` SLA — first real measurement

`docs/MVP.md` sets the target **"side-by-side < 8 s P95"**. Until run 2 the
project had no measurement of it at all. This is that measurement, with its
limits stated before its numbers.

### 10.1 What was timed

Wall-clock, client side, from Madrid over the public internet to Watsonx
`eu-de`. Each row of §8 contributes one *pair*: the vanilla and conditioned
calls were issued concurrently, so **pair latency ≈ the slower of the two**, not
their sum. That is the shape the product ships and the shape the SLA is about.

| Stage | Included? | Note |
|---|---|---|
| `embedder.encode(prompt)` | yes | model already warm; cold load is startup cost, not per-request |
| `retrieve_top_k` (pgvector HNSW, k=5) | yes | Supabase pooler, `ef_search=64` |
| `build_system_prompt` | yes | pure string work, sub-millisecond |
| Both Watsonx calls, in parallel | yes | the dominant term |
| `fit_score` ×2 (orchestrate step 5) | **no** | spaCy + sentence-transformers over both outputs |
| Passport issuance + signing (step 6) | **no** | |
| FastAPI/HTTP overhead, Supabase author+profile lookup | **no** | |

So the figures below are a **lower bound** on what `POST /api/generate` costs.
They are not the endpoint's latency; they are the part of it this evaluation
exercised.

### 10.2 Measured (n = 5 pairs, seconds)

| Stage | min | median | mean | max |
|---|---|---|---|---|
| Vanilla call alone | 3.12 | 3.91 | 3.81 | 4.30 |
| Conditioned call alone | 5.38 | 6.14 | 6.15 | 6.78 |
| **Pair (side-by-side, parallel)** | **5.38** | **6.14** | **6.16** | **6.80** |
| Pair + embed + RAG | 6.36 | 6.83 | 6.90 | 7.38 |

Per-prompt detail:

| # | embed (s) | RAG (s) | vanilla (s) | conditioned (s) | pair (s) | pair+embed+RAG (s) |
|---|---|---|---|---|---|---|
| P1 | 0.06 | 1.20 | 3.62 | 6.11 | 6.11 | 7.38 |
| P2 | 0.09 | 0.38 | 4.08 | 6.36 | 6.36 | 6.83 |
| P3 | 0.09 | 0.89 | 4.30 | 5.38 | 5.38 | 6.36 |
| P4 | 0.06 | 0.31 | 3.12 | 6.78 | 6.80 | 7.17 |
| P5 | 0.06 | 0.56 | 3.91 | 6.14 | 6.14 | 6.76 |

### 10.3 What this says about the SLA — read the caveat first

**There is no P95 here and this document will not pretend otherwise.** A P95
from five samples is the maximum with extra decimal places; the honest
statistics from n=5 are the max and the spread. The number to argue with is
therefore the **worst observed pair: 6.80s**, or **7.38s** once
embedding and retrieval are added.

Against an 8s budget that is **inside, with roughly 0.6s of headroom** — and
that headroom has to absorb everything §10.1 excludes: two `fit_score`
computations, passport signing, the Supabase round-trips, and HTTP. Whether it
does is not measured yet.

Three things are worth saying plainly:

1. **The conditioned half is the whole cost.** It ran 2.35s slower than
   vanilla on average (6.15s vs 3.81s) and was the slower branch in
   **5/5** pairs, so it set the pair latency every time. Because the
   two calls run in parallel, the vanilla branch is effectively free; the SLA is
   a statement about the conditioned branch alone.
2. **The gap is output length, not conditioning overhead.** Conditioned outputs
   averaged 279 words against vanilla's 172 — 1.63× as many tokens to
   decode. Normalise for that and the two branches are the *same speed*:
   **22.2 ms/word vanilla vs 22.1 ms/word conditioned**. The ~2 600-token system
   prompt is prefill and costs essentially nothing; the entire 2.35s difference
   is that the conditioned model chose to write more. The slowest pair of all,
   P4 at 6.80s, is also the longest conditioned output (341 words), and the
   fastest, P3 at 5.38s, is near the shortest. This points the fix: trimming
   the system prompt would buy almost nothing, and `max_tokens` is the only
   lever that touches latency.

   One caveat on that lever. The 512-token cap **did not truncate anything** in
   this run: the longest output was 415 tokens (P4) and all ten ended on a
   complete sentence. The model stopped because it was finished, not because it
   was cut off. So lowering `max_tokens` to buy latency headroom would start
   truncating real output rather than merely trimming waste — it is a lever,
   but not a free one.
3. **The 8s SLA and the 8s client timeout are the same number, and that is a
   design smell.** `watsonx_client.HARD_TIMEOUT_SECONDS` is 8.0s per attempt.
   A generation that merely *approaches* the SLA does not degrade — it is killed
   and retried, and a retry costs the 1s/2s/4s backoff on top. There is no
   band in which the product is late but working. Reported, not fixed.

### 10.4 Reliability, same run

**10/10 generations succeeded on the first attempt. Zero retries, zero
timeouts, zero errors.** Contrast run 1, where P3 burned an 8s timeout before
succeeding on attempt 2 — under the 1024-token cap nobody had chosen. That is
the #106 fix showing up as reliability, and it is the strongest argument that
re-running was necessary rather than pedantic.

---

## Appendix A — run 1: every other generation performed for this work order

Full disclosure of the run history, so that "the output" in §4 cannot be a
hand-picked best-of. Exactly **one** generation exists outside the recorded
suite: a single-prompt connectivity smoke test run four minutes before the
suite, to confirm Watsonx credentials and the model endpoint worked before
spending five calls. It used prompt P1 and identical settings. It was run as a
smoke test and excluded by that rule before its text was read — not chosen
against.

**Smoke test, P1, 2026-07-28T10:52:08Z, 5.38s, 0 retries — output (verbatim):**

```text
As the last wisps of daylight succumbed to the all-encompassing fog, a lone figure stood at the window, gazing out into the murky London evening. The gas lamps, few and far between, cast flickering shadows on the damp cobblestones, making it seem as though the very spirits of the city were dancing in the mist. The air was heavy with the smell of coal smoke and damp earth, and the distant clang of a blacksmith's hammer echoed through the fog, a haunting melody that seemed to match the rhythm of the figure's own thoughts. As they stood there, lost in contemplation, the fog swirled and eddied, revealing glimpses of passersby hurrying to find shelter from the chill, their faces obscured by the mist, making them seem like ghosts from another world. The figure's eyes, however, remained fixed on some point outside, their mind a thousand miles away, lost in the labyrinthine streets of their own imagination.
```

No other prompt was generated more than once.

---

## Appendix B — run 1: open items that run surfaced (reported, not fixed)

> Both items below are **now closed** — see Appendix D, which records how
> and supersedes them. Kept here because the prediction in item 1 is the
> reason run 2 exists.

Both are outside the WO-14 scope and were left untouched:

1. **`max_new_tokens` is ignored on the chat path.**
   `autoria_ai.generator._GENERATION_PARAMS` sets `max_new_tokens: 512`, but
   `watsonx_client._call_watsonx` calls `ModelInference.chat()`, which takes
   `max_tokens`. Watsonx warned `The value of 'max_tokens' for this model was
   set to value 1024` on every call, so the configured 512-token cap is not in
   force in production either.
2. **The conditioned half of the R1 gate is still unmeasured**, blocked on the
   corpus seed (#86). See the scope note in §1.

---

## Appendix C — run-2 full disclosure

Same rule as Appendix A: every generation performed for run 2 is in this
document. **There were exactly ten** — the ten in §8. No smoke test was needed
(Watsonx connectivity had already been confirmed independently that day), no
prompt was run twice, nothing was discarded, and nothing was re-rolled for a
nicer result. Had a generation failed, it would appear in §8 with its literal
error text in the Error row; none did.

### C.1 RAG provenance

The passages the conditioner actually interpolated, by `documents.id` and
`chunks.chunk_index`. Together with the StyleProfile `computed_at` values in
§7.3 these make each conditioned system prompt reconstructible byte for byte.

| # | Author | Retrieved chunks (`document_id`#`chunk_index`) |
|---|---|---|
| P1 | dickens | `7a06757c`#0, `c7519784`#95, `7a06757c`#34, `8bb35236`#180, `7a06757c`#523 |
| P2 | dickens | `7a06757c`#149, `7a06757c`#960, `7a06757c`#954, `11538f06`#56, `7a06757c`#47 |
| P3 | austen | `aa4ab559`#259, `89bd6fb0`#281, `89bd6fb0`#58, `aa4ab559`#269, `dc1f95a9`#244 |
| P4 | austen | `89bd6fb0`#145, `89bd6fb0`#58, `dc1f95a9`#24, `dc1f95a9`#0, `fec0eeb0`#188 |
| P5 | poe | `be5e013d`#282, `be5e013d`#140, `be5e013d`#279, `be5e013d`#111, `9a474a9d`#137 |

All five retrievals returned 5 chunks and none is degenerate, but the spread is
narrow: the five passages came from only **2–3 distinct documents** per
prompt (P2 and P5 drew 4 of their 5 from a single document). With 4 529 chunks
in the corpus that is worth a glance later; it is not scored here.

### C.2 A conditioned system prompt, in full shape

The conditioner's output is long (10,479–11,068 chars, 2,589–2,591 tokens).
The five example passages are **97%** of it and are reproducible from C.1, so
only the directive head is reproduced here — P1, verbatim:

```text
Write in the style of author dickens. Your writing must have: average sentence length ~27.0 tokens with high variation, heavy use of subordinate clauses, and vocabulary including terms like say, know, look, come, make, man, time, little, think, hand, old, good, like, dear, way.
Here are example passages: <5 passages, 10,301 chars total, listed in C.1>.
Write only in that style; do not explain.
```

The other four heads differ only in the author name, the sentence-length figure
and the vocabulary list; the subordination clause resolved to "heavy use of
subordinate clauses" for all three authors.

---

## Appendix D — open items run 2 surfaced (reported, not fixed)

Appendix B's two items are both **closed** by run 2: item 1 was fixed as #106 /
PR #123 and re-measured here; item 2 is discharged — the conditioned half exists
now. Three new items take their place. None was touched.

1. **The conditioner blows its own token budget by ~2×.**
   `conditioner.py`'s module docstring states the system prompt "is kept under
   ~1200 tokens (architecture.md §6)" and names the 5-chunk cap as the
   safeguard. Measured on the five real prompts: 10,479–11,068 chars,
   **2,589–2,591 tokens (cl100k)** — more than **2× the stated budget**, on
   every single call. The cause is that the cap counts the wrong thing: each
   retrieved chunk is ~2 000 chars (~500 tokens) by itself, so 5 × 500 blows
   through 1200 before a word of the directives is added. `_MAX_CHUNKS = 5`
   can never enforce a token budget it does not measure. Per §10.3 this costs
   little latency (it is prefill), so the impact is context-window and cost,
   not speed — but the docstring's claim is simply false as written, and either
   the code or the claim should move.

2. **`distinctive_vocab` is not distinctive.** The 15 terms the conditioner fed
   the model, verbatim from the profiles used in this run:

   | Author | Terms passed to the model |
   |---|---|
   | Dickens | `say, know, look, come, make, man, time, little, think, hand, old, good, like, dear, way` |
   | Austen | `say, know, think, make, come, time, good, great, look, little, sister, thing, soon, wish, dear` |
   | Poe | `say, make, great, time, long, man, know, day, eye, little, far, think, come, fall, point` |

   **7 of 15 lemmas — `come, know, little, make, say, think, time` — are common to all
   three authors.** These are high-frequency English verbs and nouns, not an
   author's fingerprint; the extractor looks to be ranking by raw corpus
   frequency rather than frequency *relative to* a reference corpus (a
   TF-IDF-style or log-odds measure would be the usual fix). This does not
   invalidate run 2 — it is the profile production actually uses, which is
   exactly what an honest baseline should exercise — but it means one of the
   three conditioning signals is close to inert, and any voice-similarity the
   scorer finds in §9 is coming from the RAG passages and the syntactic
   directives, not from the vocabulary list. A branch named
   `fix/wo-12-distinctive-vocab` exists, so this may already be known.

3. **The 8s SLA equals the 8s per-attempt client timeout.** See §10.3 item 3.
   Any generation that would merely be *slow* is instead killed and retried,
   and the retry adds backoff on top. There is no graceful-degradation band.
