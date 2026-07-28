# Baseline voice-matching evaluation — Llama 3.3 70B (unconditioned)

> **WO-14** · closes the evidence gap of issue [#11] · gate **R1** (`docs/MVP.md:512`)
> **Status: AWAITING HUMAN SCORING.** The generations below are recorded. The
> 1–10 scores, the mean and the gate verdict are **deliberately blank** — they
> are Sergi's to fill in. See "Who scores this, and why not the agent" below.

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

## 5. Scores and mean — **to be filled in by Sergi**

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

## Appendix A — every other generation performed for this work order

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

## Appendix B — open items this run surfaced (reported, not fixed)

Both are outside the WO-14 scope and were left untouched:

1. **`max_new_tokens` is ignored on the chat path.**
   `autoria_ai.generator._GENERATION_PARAMS` sets `max_new_tokens: 512`, but
   `watsonx_client._call_watsonx` calls `ModelInference.chat()`, which takes
   `max_tokens`. Watsonx warned `The value of 'max_tokens' for this model was
   set to value 1024` on every call, so the configured 512-token cap is not in
   force in production either.
2. **The conditioned half of the R1 gate is still unmeasured**, blocked on the
   corpus seed (#86). See the scope note in §1.
