# AutorIA — Frontend (Next.js)

> **Owner**: P1 (Frontend + Pitch + Bob Champion).

The Next.js app is **already scaffolded** (Sprint 1). Do not re-run `create-next-app`.

## Stack (as actually installed)

| Concern    | Choice                                                                                 |
| ---------- | -------------------------------------------------------------------------------------- |
| Framework  | **Next.js 16** (App Router) + **React 19**                                             |
| Language   | TypeScript, `src/` directory, import alias `@/*` → `src/*`                             |
| Styling    | **Tailwind CSS v4** (`@import "tailwindcss"` in `src/app/globals.css`)                 |
| Components | **shadcn/ui** — `base-nova` style, `@base-ui/react` primitives (see `components.json`) |
| Icons      | `lucide-react`                                                                         |
| Charts     | `recharts` (radar + bar)                                                               |

> ⚠️ Earlier drafts of this file described Next.js 14 with `--src-dir=false` and a
> `create-next-app` bootstrap. That is outdated — trust this file and the repo, not old notes.

Add new shadcn primitives via the CLI so they match the configured style:

```bash
cd frontend
npx shadcn@latest add card badge
```

---

## What we build here

Paths are under `src/`. **Routes follow the GitHub issues as source of truth.**

### Routes

| Path                           | Purpose                                                      |
| ------------------------------ | ------------------------------------------------------------ |
| `src/app/page.tsx`             | Home — author gallery                                        |
| `src/app/author/[id]/page.tsx` | **The studio**: Style DNA panel + prompt + side-by-side       |
| `src/app/verify/page.tsx`      | Public Authorship Passport verifier                          |
| `src/app/layout.tsx`           | Layout shell (wordmark, theme, metadata)                     |

> The author detail route is **`/author/[id]`** per issue #9 — not `/studio/[author]`.
> Style DNA and generation live on **one** screen: the earlier two-route split was
> merged on 2026-07-21 because the "Generate in this voice" hop was easy to miss
> (Decision Log).

### Components

| File | Purpose |
| --- | --- |
| `AuthorGrid.tsx` · `AuthorCard.tsx` · `AddAuthorCard.tsx` · `DeleteAuthorButton.tsx` | Gallery, live author upload, and removal (shown **only** for live-added authors — the 3 demo voices have no button, and the API returns 403 for them anyway) |
| `StyleDnaPanel.tsx` | Style DNA container: corpus stats, loading / error / empty states, fixture policy |
| `StyleRadarChart.tsx` · `StyleScatter2D.tsx` | 6-axis radar; UMAP 2D semantic map with centroid + spread ring |
| `PromptComposer.tsx` | Generation input (4 000-char cap) |
| `SideBySideOutput.tsx` · `AuthorColumn.tsx` | Vanilla vs AutorIA columns |
| `FitScoreBar.tsx` · `MetricChip.tsx` · `ComparativeMetricsTable.tsx` | 0–100 fit score, metric chips, client-side comparative metrics |
| `DistinctiveVocabHighlight.tsx` | `<mark>`s signature vocabulary inside the AutorIA output |
| `PassportCard.tsx` | Decoded Passport on screen + download action |
| `EmptyState.tsx` · `ThemeToggle.tsx` · `ui/{button,card,badge}.tsx` | Shared primitives |

### Lib

| File | Purpose |
| --- | --- |
| `src/lib/api.ts` | Backend HTTP client. Reads **`NEXT_PUBLIC_API_BASE_URL`** (not `NEXT_PUBLIC_API_URL` — that mismatch was issue #82) and exports typed `NetworkError` / `ServerError` |
| `src/lib/types.ts` | Types aligned with `docs/api_contract.yaml` |
| `src/lib/authors.ts` | Author list from `GET /api/authors`, with a declared fallback |
| `src/lib/style-dna.ts` | Radar axis normalization — domains derived from the **measured** ranges in `docs/style_features.md` §7 |
| `src/lib/textMetrics.ts` | Client-side comparative metrics (sentence length, TTR, word count) |
| `src/lib/passport.ts` | Passport download (JWS + decoded payload) |
| `src/lib/fixtures/style-profiles.ts` | Demo-safe fixtures — see the rule below |
| `src/lib/i18n/en.ts` | All UI strings (English) |

> **Fixture policy — do not loosen this.** Fixtures substitute **only** when the
> backend gave no answer: a `NetworkError` or a 5xx. A real **404 is a definitive
> answer** ("this author has no computed profile") and must render the empty state,
> never invented metrics. Any other 4xx is an error, never a fixture. Enforced by
> `StyleDnaPanel.test.ts` and `fixtures/style-profiles.test.ts`; rationale in the
> Decision Log, 2026-07-27.

### Tests

Vitest, pure-function and policy tests (no jsdom):

```bash
npm run test          # 78 cases
npx tsc --noEmit
npm run lint
```

---

## Local run

```bash
cp .env.local.example .env.local   # sets NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
# http://localhost:3000
```

Next.js reads env from `frontend/`, **not** the repo root, so the root `.env` alone is
not enough. Production: <https://quebasto.com> (Vercel).

---

## Conventions

- All UI strings via `src/lib/i18n/en.ts`. **No hardcoded text in components.** Everything is
  English (UI and generated text alike).
- Components in PascalCase. Hooks in camelCase prefixed with `use`.
- API responses typed via `src/lib/types.ts`, kept in sync with `docs/api_contract.yaml`.
- Use shadcn `base-nova` primitives and Tailwind tokens (`bg-card`, `text-muted-foreground`,
  `border`, …) — avoid one-off hardcoded colors.
- Desktop-first; mobile-responsive is out of scope for July (MVP §5).
