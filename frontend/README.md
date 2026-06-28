# AutorIA — Frontend (Next.js 14)

> **Owner**: P1 (Frontend + Pitch + Bob Champion).

This directory is intentionally empty until **Sprint 1, Day 1 (July 1)**, when P1 initializes the Next.js project with:

```bash
cd frontend
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --app \
  --src-dir=false \
  --import-alias="@/*"

# shadcn/ui
npx shadcn-ui@latest init

# Visualization deps
npm install recharts d3 umap-js react-scatter-plot
```

---

## What we build here

| Path | Purpose |
|---|---|
| `app/page.tsx` | Home — author selector (3 cards) |
| `app/studio/[author]/page.tsx` | Main screen — side-by-side generation |
| `app/verify/page.tsx` | Authorship Passport verifier |
| `components/AuthorCard.tsx` | Author card on home |
| `components/StyleRadarChart.tsx` | Radar chart of StyleProfile metrics |
| `components/StyleScatter2D.tsx` | UMAP 2D scatter |
| `components/PromptBox.tsx` | Generation input |
| `components/SideBySideOutput.tsx` | Vanilla vs AutorIA columns |
| `components/FitScoreBar.tsx` | 0-100 fit score visualization |
| `components/PassportCard.tsx` | Formatted Passport viewer |
| `lib/api.ts` | Backend HTTP client |
| `lib/types.ts` | Types generated from `docs/api_contract.yaml` |
| `lib/i18n/en.ts` | UI strings (English) — see `docs/ONBOARDING.md` §12 |

---

## Local run

```bash
npm install
npm run dev
# http://localhost:3000
```

---

## Conventions

- All UI strings via `lib/i18n/en.ts`. **No hardcoded text in components.** Everything is English (UI and generated text alike).
- Components in PascalCase. Hooks in camelCase prefixed with `use`.
- API responses typed via the generated `lib/types.ts` (regen on `api_contract.yaml` changes).
