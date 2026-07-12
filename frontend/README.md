# AutorIA — Frontend (Next.js)

> **Owner**: P1 (Frontend + Pitch + Bob Champion).

The Next.js app is **already scaffolded** (Sprint 1). Do not re-run `create-next-app`.

## Stack (as actually installed)

| Concern | Choice |
|---|---|
| Framework | **Next.js 16** (App Router) + **React 19** |
| Language | TypeScript, `src/` directory, import alias `@/*` → `src/*` |
| Styling | **Tailwind CSS v4** (`@import "tailwindcss"` in `src/app/globals.css`) |
| Components | **shadcn/ui** — `base-nova` style, `@base-ui/react` primitives (see `components.json`) |
| Icons | `lucide-react` |
| Charts | `recharts` (radar + bar) |

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

| Path | Purpose |
|---|---|
| `src/app/page.tsx` | Home — author selector (3 cards) |
| `src/app/author/[id]/page.tsx` | Author detail — Style DNA + side-by-side generation |
| `src/app/verify/page.tsx` | Authorship Passport verifier |
| `src/app/layout.tsx` | Base layout shell (header/wordmark, metadata) |
| `src/components/AuthorCard.tsx` | Author card on home |
| `src/components/StyleRadarChart.tsx` | Radar chart of StyleProfile metrics |
| `src/components/StyleScatter2D.tsx` | UMAP 2D scatter |
| `src/components/PromptBox.tsx` | Generation input |
| `src/components/SideBySideOutput.tsx` | Vanilla vs AutorIA columns |
| `src/components/FitScoreBar.tsx` | 0-100 fit score visualization |
| `src/components/PassportCard.tsx` | Formatted Passport viewer |
| `src/lib/api.ts` | Backend HTTP client |
| `src/lib/types.ts` | Types aligned with `docs/api_contract.yaml` |
| `src/lib/authors.ts` | Local seed author data (until the backend `GET /api/authors` is wired) |
| `src/lib/i18n/en.ts` | UI strings (English) — see `docs/ONBOARDING.md` §12 |

> The author detail route is **`/author/[id]`** per issue #9 — not `/studio/[author]`.

---

## Local run

```bash
npm install
npm run dev
# http://localhost:3000
```

---

## Conventions

- All UI strings via `src/lib/i18n/en.ts`. **No hardcoded text in components.** Everything is
  English (UI and generated text alike).
- Components in PascalCase. Hooks in camelCase prefixed with `use`.
- API responses typed via `src/lib/types.ts`, kept in sync with `docs/api_contract.yaml`.
- Use shadcn `base-nova` primitives and Tailwind tokens (`bg-card`, `text-muted-foreground`,
  `border`, …) — avoid one-off hardcoded colors.
- Desktop-first; mobile-responsive is out of scope for July (MVP §5).
