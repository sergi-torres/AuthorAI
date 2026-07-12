# AutorIA Design System — "The Authorship Studio"

Single source of truth for all UI work in Sprints 1–3. Extend this file and the tokens in
`frontend/src/app/globals.css`; never restyle from scratch. Every color is a token, every
string lives in `frontend/src/lib/i18n/en.ts`, every async surface has loading / error /
empty states.

---

## 1. Brand & voice

**Principles**

1. **Ink on parchment.** Warm paper surfaces, deep warm-ink text. Calm and literary, never
   sterile SaaS gray.
2. **The signature is the product.** One confident sepia-bronze accent (`--primary`) marks
   authorial/trusted moments; seal-green marks *verified*. Nothing else shouts.
3. **Author-coded voices.** Austen, Dickens, and Poe each own a signature hue. Anything
   "in voice" — card accents, DNA clusters, the AutorIA output column, highlighted vocab —
   carries that hue. This is the engine of the 5-second bar.

**Do**

- Use serif (`font-heading` / `font-serif`, Fraunces) for author names, hero headings,
  passport headings, and generated literary passages.
- Use `font-mono` for anything forensic: fit scores, latencies, hashes, JWS, JSON.
- Pair every color signal with a word or icon (e.g. "87% Dickens-fit" next to the green
  bar; a check icon inside the verified banner).
- Keep interactions ≤ 250ms; reserve the 600ms reveal for the generate moment.

**Don't**

- No purple gradients, neon, glassmorphism, or emoji-as-UI.
- No hardcoded hex/oklch in components — tokens only.
- No new UI/animation/chart libraries without a Decision Log entry below.
- No color-only meaning, ever (fit bands and verified states must read in grayscale).
- No spinner without a timeout path. Watsonx can hang; the demo is recorded live.

---

## 2. Color system

All values are oklch and live in `globals.css` (`:root` = light, `.dark` = dark). Utilities
come from the `@theme inline` mapping (`bg-voice-tint`, `text-fit-high`, `shadow-paper`…).

### 2.1 Core semantic tokens

| Token | Light | Dark | Role |
|---|---|---|---|
| `--background` | `oklch(0.977 0.006 90)` | `oklch(0.185 0.01 55)` | Parchment page |
| `--foreground` | `oklch(0.24 0.015 55)` | `oklch(0.945 0.008 85)` | Warm ink text |
| `--card` | `oklch(0.99 0.004 95)` | `oklch(0.225 0.012 55)` | Raised paper |
| `--muted` / `--muted-foreground` | `0.946` / `0.49` | `0.265` / `0.72` | Quiet surfaces / secondary text |
| `--primary` | `oklch(0.44 0.085 55)` | `oklch(0.78 0.075 70)` | **Brand signature** (sepia-bronze ink) |
| `--secondary`, `--accent` | warm near-parchment washes | warm near-ink washes | Chips, hovers |
| `--border` / `--input` | `oklch(0.902 0.012 80)` | `oklch(1 0 0 / 12–16%)` | Hairlines |
| `--ring` | `oklch(0.55 0.08 55)` | `oklch(0.68 0.06 70)` | Focus ring (always visible) |
| `--destructive` | `oklch(0.52 0.19 27)` | `oklch(0.66 0.17 25)` | Errors / invalid passport |

### 2.2 State colors

| Token | Light | Dark | Use |
|---|---|---|---|
| `--success` | `oklch(0.50 0.11 155)` | `oklch(0.70 0.12 155)` | Seal-green: VERIFIED banner, stamp |
| `--success-tint` | `oklch(0.955 0.03 155)` | `oklch(0.30 0.05 155)` | Verified banner background |
| `--warning` | `oklch(0.62 0.12 75)` | `oklch(0.75 0.12 80)` | Timeouts, degraded service (icon/border only) |
| `--warning-tint` + `--warning-foreground` | wash + dark amber text | | Warning surfaces |

### 2.3 Fit-score scale (used by `FitScoreBar`)

Perceptually even: lightness stays ~0.56–0.72 (light) / 0.68–0.78 (dark) so no stop
"glows" louder than its meaning. **Low fit is neutral gray, not red** — a low score means
*generic*, not *broken*; red is reserved for real errors.

| Band | Score | Token | Light | Meaning |
|---|---|---|---|---|
| generic | 0–39 | `--fit-generic` | `oklch(0.60 0.02 75)` | Anonymous, model-default prose |
| weak | 40–54 | `--fit-weak` | `oklch(0.60 0.135 40)` | Faint voice (clay) |
| mid | 55–69 | `--fit-mid` | `oklch(0.72 0.13 85)` | Partial voice (amber) |
| good | 70–84 | `--fit-good` | `oklch(0.66 0.125 130)` | Clear voice (moss) |
| high | 85–100 | `--fit-high` | `oklch(0.56 0.135 152)` | Unmistakable voice (seal green) |

`--fit-track` is the empty-bar background. Band thresholds live in ONE place:
`getFitBand()` in `FitScoreBar.tsx` — import it, never re-implement.

**Text rule:** only `--fit-high` and `--fit-generic`/`muted-foreground` are approved as
*text* colors (they pass AA on parchment). `weak/mid/good` are fill-only — captions next
to them use `text-foreground`/`text-muted-foreground`.

### 2.4 Author signature palette

Each author has `--author-<id>` (solid), `--author-<id>-tint` (wash), `--author-<id>-on`
(text on solid). Light-mode solids are all L ≤ 0.52 so they pass AA as text on parchment.

| Author | Hue story | Solid (light) | Solid (dark) |
|---|---|---|---|
| Austen | Regency rose / claret | `oklch(0.52 0.13 10)` | `oklch(0.72 0.11 10)` |
| Dickens | Victorian deep teal | `oklch(0.45 0.085 200)` | `oklch(0.73 0.09 200)` |
| Poe | Gothic oxblood | `oklch(0.41 0.135 25)` | `oklch(0.68 0.13 25)` |

**The `--voice` indirection (how components stay author-agnostic):** components never name
an author. They use `bg-voice`, `bg-voice-tint`, `text-voice`, `text-voice-on`; an ancestor
sets `data-voice="dickens"` and CSS maps `--voice → --author-dickens` etc. No `data-voice`
(or an unknown/live-uploaded author) falls back to the brand signature — new authors work
instantly with zero component changes. **To add an author:** add three `--author-*` vars in
`:root` + `.dark` and one `[data-voice="<id>"]` block. Nothing else.

Recharts mapping: `--chart-1` = Austen, `--chart-2` = Dickens, `--chart-3` = Poe,
`--chart-4` = brand, `--chart-5` = neutral. Radar/scatter series colors come only from
these.

### 2.5 Contrast notes (AA)

- `foreground` on `background`: ~12:1 both modes — safe everywhere.
- `muted-foreground` on `background`: ≥ 6:1 — safe for captions.
- Author solids as text on parchment: ≥ 4.6:1 — safe (that's why L ≤ 0.52).
- `text-voice` on `bg-voice-tint`: ≥ 4.5:1 for all three authors — safe for chips/marks.
- **Borderline / forbidden:** `--warning` and `--fit-mid`/`--fit-good`/`--fit-weak` as
  text on parchment (≈ 2–3:1) — fills, borders, icons only. White text on `--warning` —
  never; use `--warning-foreground` on `--warning-tint`.

---

## 3. Typography

| Role | Font | Token / class | Usage |
|---|---|---|---|
| Editorial display | **Fraunces** (next/font, self-hosted) | `font-heading`, `font-display` | Author names, page titles, passport headings, verified banner title |
| Literary body | Fraunces | `font-serif` | Generated passages only |
| UI / body | Geist Sans | `font-sans` (default) | Everything else |
| Forensic | Geist Mono | `font-mono` | Scores, latency, hashes, JWS, JSON |

**Type scale** (Tailwind utilities; don't invent sizes):

| Step | Class recipe | Use |
|---|---|---|
| Display | `font-heading text-4xl font-semibold tracking-tight` | Studio hero (author name) |
| Title | `font-heading text-3xl font-semibold tracking-tight` | Page headings |
| Card title | `font-heading text-2xl font-semibold tracking-tight` | Author cards, panel titles |
| Section | `text-sm font-semibold uppercase tracking-wide text-muted-foreground` | Panel section labels |
| Body | `text-[0.9375rem] leading-relaxed` | UI copy |
| Literary | `font-serif text-[0.9375rem] leading-7 max-w-[66ch] whitespace-pre-line` | Generated text — measure ~66ch, generous leading |
| Caption | `text-xs text-muted-foreground` | Metadata, legends |
| Metric | `font-mono tabular-nums` | All numbers that can change |

Generated passages keep real quotation marks from the model output; do not strip or
re-typeset them.

---

## 4. Spacing, radius, elevation

- **Rhythm:** 4/8px grid. Card padding `p-5`/`p-6`; column gap `gap-6`; page sections
  `gap-8`/`gap-10`. Shell stays `max-w-5xl px-6`, designed at 1280–1440px (desktop-first;
  mobile out of scope, degrade gracefully with existing grid fallbacks).
- **Radius:** existing scale off `--radius: 0.625rem` (`rounded-lg` default, `rounded-xl`
  cards, `rounded-full` chips/bars). Don't add new radii.
- **Elevation ("paper-lift"), 3 steps:** `shadow-paper-sm` (resting card),
  `shadow-paper` (raised panel / output column), `shadow-paper-lg` (hover lift, popover).
  Warm-ink shadows at ≤ 14% alpha — never heavy drops.

---

## 5. Motion

Tokens in `globals.css`: `--duration-fast: 150ms`, `--duration-base: 250ms`,
`--duration-reveal: 600ms`, `--ease-out-soft: cubic-bezier(0.22, 1, 0.36, 1)`.

| Moment | Recipe |
|---|---|
| Hover / focus | `transition-*` at 150–200ms; cards lift `-translate-y-0.5` + `shadow-paper-lg` |
| Generate reveal | `.animate-fade-rise` on the passage (250ms fade + 8px rise) |
| Fit-bar fill | `.animate-fit-grow` — width grows 0 → score over 600ms; the two bars filling to very different lengths *is* the demo moment |
| Verified stamp | `.animate-stamp-in` — 400ms scale 1.08 → 1 with a settle, like a seal pressed onto paper |

`prefers-reduced-motion: reduce` disables all three keyframe classes (already in
`globals.css`). Never animate layout (width/height of containers) — only transform,
opacity, and the fit-bar fill.

---

## 6. Iconography

**lucide-react only** (already installed). Size `size-4` inline, `size-5` in banners.
Stroke width default. Icons always accompany, never replace, a label. Canonical picks:
`BadgeCheck` (verified), `ShieldAlert` (invalid), `Clock` (timeout), `TriangleAlert`
(error), `Feather` (authorial/voice), `Download` (passport), `Upload` (add author),
`ChevronDown` (collapsible).

---

## 7. Component inventory

| Component | Sprint | Screen(s) | States | Notes |
|---|---|---|---|---|
| AppShell / header | 1 | all | — | Sticky, `max-w-5xl`, brand serif + Art. 50 tag |
| `AuthorCard` | 1 | `/` | default, hover, focus | `data-voice` accent bar, serif name |
| `AuthorGrid` | 1 | `/` | populated, empty | 3-col desktop; last slot = `AddAuthorCard` |
| `AddAuthorCard` | 1 ✅ | `/` | idle, editing, submitting, success, error | Dashed card → inline name + .txt/.md upload form |
| `ThemeToggle` | 1 ✅ | all (header) | light, dark | CSS-only icon swap; pre-paint init script in layout |
| `StyleDnaPanel` | 1 ✅ | studio | loading, empty, error, ready, collapsed | Collapsible wrapper; owns fetch states |
| `StyleRadarChart` | 1 ✅ | studio | ready | Recharts radar, 6 axes normalized [0,1], series = `--chart-*` |
| `StyleScatter2D` | 1 ✅ | studio | ready | UMAP clusters; selected author's cluster in its voice color, others muted |
| `MetricChip` | 1 ✅ | studio | ready | `font-mono` value + sans label |
| `EmptyState` | 1 ✅ | all | — | Icon + one line + optional action |
| `LoadingSkeleton` | 1 | all | — | Pulsing muted bars; pattern shown in `AuthorColumn` |
| `PromptComposer` | 2 | studio | idle, submitting, disabled | Textarea + Generate (primary button) |
| `AuthorColumn` | 2 ✅ | studio | loading, success, error, timeout | Built — the reference implementation |
| `SideBySideOutput` | 2 ✅ | studio | delegates to columns | Built |
| `FitScoreBar` | 2 ✅ | studio, verify | pending, filled | Built — exemplary; copy its patterns |
| `DistinctiveVocabHighlight` | 2 ✅ | studio | — | Built — voice-tinted `<mark>` |
| `PassportCard` | 2 | studio, verify | ready | Mono JSON block + `Download` action |
| `VerifyForm` | 2 | `/verify` | idle, submitting, verified, invalid, error | Paste JWS / upload JSON |
| `VerifiedBanner` | 2 | `/verify` | verified | `success-tint` bg, `BadgeCheck`, `.animate-stamp-in` |
| `PassportErrorList` | 2 | `/verify` | invalid | Structured `VerifyError[]`, destructive styling |
| Cluster-landing reveal, polish | 3 | studio | — | Motion + state audit only, no new components |

### Rules for adding a component (keeps the system scalable)

1. **Placement & naming:** `frontend/src/components/PascalCase.tsx`, one component per
   file, < 500 lines. shadcn primitives stay in `components/ui/` (generated — don't hand-edit).
2. **Props from contracts:** consume types from `lib/types.ts` that mirror
   `docs/api_contract.yaml`. Missing field → flag it and add a typed fixture; never `as any`.
3. **Tokens only:** if you need a color that has no token, add the token to `globals.css`
   *and a row to §2* in the same PR. Author-specific styling goes through `data-voice`,
   never `if (author === "poe")` color logic in TSX.
4. **Three states minimum** for anything async: loading (skeleton + status text), error
   (message + retry), success. Timeouts get their own copy (`warning`, not `destructive`).
5. **Strings:** every visible string into `en.ts` first, grouped by screen; interpolations
   are typed functions.
6. **Discriminated-union props** for variant components (see `AuthorColumn`) so invalid
   combinations (an authorial column with no author) don't compile.
7. **A11y floor:** visible focus ring, AA text, `role`/`aria-*` on meters and status
   regions, color always paired with a word or icon.

---

## 8. The 5-second contrast playbook

The devices that make vanilla vs AutorIA legible without reading a word, in priority order:

1. **The fit-bar gap.** Two `FitScoreBar`s aligned in twin column footers: vanilla fills
   ~⅓ in neutral gray, AutorIA fills ~⅞ in seal green, both animating on reveal. The gap
   in *length* carries the message in grayscale; color and the big mono numbers amplify it.
2. **Named vs anonymous captions.** "34% generic" vs "87% Dickens-fit" — the words do the
   work for anyone who can't parse a chart.
3. **The voice-colored column.** The AutorIA column wears the author's signature: colored
   top rule, tinted label chip ("AutorIA · Dickens voice"). The vanilla column is
   deliberately beige/gray with a generic chip ("Llama 3.3 · vanilla") — visually anonymous
   *by design*.
4. **Highlighted signature vocabulary.** Distinctive terms glow in voice-tinted `<mark>`s
   only in the AutorIA column, with a one-line legend. The vanilla side has nothing to
   highlight — its blankness is the point.
5. **Cluster identity (Style DNA).** The author's UMAP cluster and radar series render in
   the same signature hue as their column, so the color = author association is learned
   before generation even runs. (Sprint 3: generated-output dot "lands" inside the cluster.)
6. **Honesty rule:** both columns use the same model and the real scores. The contrast is
   earned by design, never faked.

---

## 9. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-07-12 | Fraunces (variable, `opsz`) as the single editorial serif via next/font | Literary title-page feel; pairs with Geist; no CDN |
| 2026-07-12 | `--voice` indirection via `data-voice` attribute | Author theming with zero per-author component code; live-uploaded authors fall back to brand |
| 2026-07-12 | Low fit = neutral gray, not red | Low fit means *generic*, not *error*; red stays reserved for real failures |
| 2026-07-12 | Fixed `--font-sans` mapping (was circular `var(--font-sans)`) | Geist was never actually applied |
| 2026-07-12 | Micro-interactions in CSS/Tailwind only; no framer-motion | Motion needs are 4 small effects; revisit only if Sprint 3 demands orchestration |
| 2026-07-12 | Hand-rolled dark-mode toggle (no next-themes) | One class + localStorage + a 3-line pre-paint script; not worth a dependency |
| 2026-07-12 | Author list fetches `GET /api/authors` with seed fallback | Live-uploaded authors appear; selector never renders empty if the API is down |
| 2026-07-12 | **Contract gap flagged:** no create-author endpoint | Add-author flow posts to `/api/authors/{new-slug}/documents` and expects backend auto-create; contract's 404 contradicts this — resolve in contract pairing session |
| 2026-07-13 | **Radar axes + normalization domains (Style DNA panel):** 6 axes normalized to the *plausible literary range* of each metric (not theoretical bounds): vocab richness (MATTR-500 [0.4, 0.85]), rare words (hapax_ratio [0.05, 0.5]), word length ([3.5, 6] chars), sentence length ([8, 40] tokens), subordination ([0.1, 0.5]), dialogue ratio ([0, 0.5]). Radial axis pinned to `domain={[0,1]}`. Thresholds live only in `lib/style-dna.ts::RADAR_AXES`. | Six axes cover lexical richness, syntactic complexity, and stylistic register. Native-[0,1] fields (hapax, dialogue, subordination) never use their full theoretical range in real prose, so a [0,1] domain pinned every author near the centre ("radar too short"). Scaling to the observed literary spread fills the frame and makes authors visibly differ; the fixed radial axis keeps shapes comparable across authors. Honest presentation scalings, clamped not hidden. |
| 2026-07-13 | **Centroid-only scatter (contract limitation):** `GET /api/authors/{id}/style-profile` exposes only `embedding_umap_2d.centroid + spread` — no per-chunk points. The scatter plots one point per author with a dispersion ring. Per-chunk scatter flagged as contract gap; no data invented. | Honesty rule (§8.6): do not fabricate points the contract does not provide. Address when per-chunk embeddings are available from the backend. |
| 2026-07-13 | **StyleProfile fixture fallback:** On network failure only (not a real 404), `StyleDnaPanel` falls back to `lib/fixtures/style-profiles.ts` typed fixtures for the 3 seed authors. Fixtures are presentation seed data — not faked quality signals. Fallback logged to console. | API-with-seed-fallback pattern (mirrors `getAuthorCards`). Demo reliability without inventing API responses. |
