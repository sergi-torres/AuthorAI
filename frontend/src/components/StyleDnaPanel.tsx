"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Feather, TriangleAlert } from "lucide-react";

import { getStyleProfile, NotFoundError } from "@/lib/api";
import { listAuthors } from "@/lib/api";
import { FIXTURE_STYLE_PROFILES } from "@/lib/fixtures/style-profiles";
import { en } from "@/lib/i18n/en";
import type { StyleProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CorpusMetricChips } from "@/components/MetricChip";
import { EmptyState } from "@/components/EmptyState";
import { StyleRadarChart } from "@/components/StyleRadarChart";
import { StyleScatter2D } from "@/components/StyleScatter2D";
import type { ScatterAuthorPoint } from "@/components/StyleScatter2D";

// ---------------------------------------------------------------------------
// Timeout guard: after 10 s without a resolved profile → transition to error
// ---------------------------------------------------------------------------
const FETCH_TIMEOUT_MS = 10_000;

// ---------------------------------------------------------------------------
// Panel state (discriminated union — no infinite spinner possible)
// ---------------------------------------------------------------------------
type PanelState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      profile: StyleProfile;
      scatterPoints: ScatterAuthorPoint[];
    };

interface StyleDnaPanelProps {
  /** The author whose style profile to load and display as the selected point. */
  authorId: string;
  /** Display name — used only for the scatter label; fetch is by authorId. */
  authorName: string;
}

/**
 * The Style DNA panel: collapsible wrapper that owns all fetch states for the
 * selected author's StyleProfile and the comparison scatter set.
 *
 * States:
 *  • loading — pulsing skeleton + status text + 10 s timeout guard
 *  • empty   — 404 / has_style_profile:false → neutral EmptyState (not an error)
 *  • error   — network/5xx → message + Retry
 *  • ready   — MetricChips + Radar + Scatter, fade-rise reveal
 *
 * Design-system.md §7 inventory: StyleDnaPanel, Sprint 1.
 */
export function StyleDnaPanel({ authorId, authorName }: StyleDnaPanelProps) {
  const [panelState, setPanelState] = useState<PanelState>({
    status: "loading",
  });
  const [expanded, setExpanded] = useState(true);
  const contentId = `style-dna-content-${authorId}`;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // retryCounter lets the Retry button re-run the same effect
  const [retryCount, setRetryCount] = useState(0);
  const handleRetry = () => setRetryCount((c) => c + 1);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setPanelState({ status: "loading" });

      // Timeout guard: after FETCH_TIMEOUT_MS with no result, show error
      timeoutRef.current = setTimeout(() => {
        if (!cancelled) {
          setPanelState({ status: "error", message: en.styleDna.error });
        }
      }, FETCH_TIMEOUT_MS);

      try {
        const profile = await fetchProfileWithFallback(authorId);
        if (cancelled) return;
        if (timeoutRef.current) clearTimeout(timeoutRef.current);

        const scatterPoints = await buildScatterPoints(
          authorId,
          authorName,
          profile,
        );
        if (cancelled) return;

        setPanelState({ status: "ready", profile, scatterPoints });
      } catch (err) {
        if (cancelled) return;
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        if (err instanceof NotFoundError) {
          setPanelState({ status: "empty" });
        } else {
          setPanelState({ status: "error", message: en.styleDna.error });
        }
      }
    }

    void run();

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [authorId, authorName, retryCount]);

  return (
    <section
      aria-label={en.styleDna.sectionTitle}
      className="flex flex-col gap-3"
    >
      {/* Collapsible header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {en.styleDna.sectionTitle}
        </h2>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={contentId}
          aria-label={en.styleDna.collapseToggle}
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center justify-center rounded p-1 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronDown
            className={cn(
              "size-4 transition-transform duration-200",
              expanded ? "rotate-0" : "-rotate-90",
            )}
            aria-hidden="true"
          />
        </button>
      </div>

      {/* Panel content — conditionally hidden (design-system §5: no height animation) */}
      <div id={contentId} hidden={!expanded}>
        {panelState.status === "loading" && <LoadingSkeleton />}

        {panelState.status === "empty" && (
          <EmptyState
            icon={<Feather className="size-5" />}
            title={en.styleDna.empty}
            body={en.styleDna.emptyBody}
          />
        )}

        {panelState.status === "error" && (
          <ErrorNotice message={panelState.message} onRetry={handleRetry} />
        )}

        {panelState.status === "ready" && (
          <ReadyLayout
            profile={panelState.profile}
            authorId={authorId}
            scatterPoints={panelState.scatterPoints}
          />
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sub-components (internal only)
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">{en.styleDna.loading}</p>
      <div className="animate-pulse flex flex-col gap-2" aria-hidden="true">
        <div className="h-3 w-1/3 rounded bg-muted" />
        <div className="h-40 w-full rounded bg-muted" />
        <div className="h-3 w-1/4 rounded bg-muted" />
        <div className="h-40 w-full rounded bg-muted" />
      </div>
    </div>
  );
}

function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="status"
      aria-live="assertive"
      className="flex flex-col items-start gap-3"
    >
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <TriangleAlert className="size-4 text-destructive" aria-hidden="true" />
        {message}
      </p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        {en.styleDna.retry}
      </Button>
    </div>
  );
}

function ReadyLayout({
  profile,
  authorId,
  scatterPoints,
}: {
  profile: StyleProfile;
  authorId: string;
  scatterPoints: ScatterAuthorPoint[];
}) {
  const dateStr = new Date(profile.computed_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <Card className="shadow-paper animate-fade-rise">
      <CardContent className="flex flex-col gap-6 py-5">
        {/* Chips row + computed_at caption */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CorpusMetricChips {...profile.corpus_stats} />
          <span className="font-mono text-xs text-muted-foreground">
            {en.styleDna.computedAt(dateStr)}
          </span>
        </div>

        {/* Two-column grid: radar left, scatter right */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Radar */}
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {en.styleDna.radarSectionTitle}
            </h3>
            <StyleRadarChart profile={profile} authorId={authorId} />
            <p className="text-xs text-muted-foreground">
              {en.styleDna.radarCaption}
            </p>
          </div>

          {/* Scatter */}
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {en.styleDna.scatterSectionTitle}
            </h3>
            <StyleScatter2D points={scatterPoints} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Data-fetching helpers (pure async functions, not hooks — no lib layer exposure)
// ---------------------------------------------------------------------------

/**
 * Fetches a StyleProfile, falling back to the fixture on NETWORK failure only.
 * A real 404 (NotFoundError) is re-thrown so the panel can show the empty state.
 */
async function fetchProfileWithFallback(
  authorId: string,
): Promise<StyleProfile> {
  try {
    return await getStyleProfile(authorId);
  } catch (err) {
    // NotFoundError → empty state; re-throw
    if (err instanceof NotFoundError) throw err;
    // Network / 5xx → fall back to fixture if available; otherwise re-throw
    const fixture = FIXTURE_STYLE_PROFILES[authorId];
    if (fixture) {
      console.info(
        `[StyleDnaPanel] API unreachable — using fixture for "${authorId}" (demo-safe fallback)`,
      );
      return fixture;
    }
    throw err;
  }
}

/**
 * Builds the scatter point array: the selected author + all other authors
 * whose profiles are available (parallel fetch, silently skip failures).
 */
async function buildScatterPoints(
  selectedAuthorId: string,
  selectedAuthorName: string,
  selectedProfile: StyleProfile,
): Promise<ScatterAuthorPoint[]> {
  const points: ScatterAuthorPoint[] = [
    {
      authorId: selectedAuthorId,
      authorName: selectedAuthorName,
      point: selectedProfile.embedding_umap_2d.centroid,
      spread: selectedProfile.embedding_umap_2d.spread,
      selected: true,
    },
  ];

  // Fetch the author list to get other authors
  let authorSummaries: { id: string; name: string }[] = [];
  try {
    authorSummaries = await listAuthors();
  } catch {
    // If author list fails, use known fixture authors as fallback
    authorSummaries = Object.keys(FIXTURE_STYLE_PROFILES)
      .filter((id) => id !== selectedAuthorId)
      .map((id) => ({ id, name: id }));
  }

  const otherAuthors = authorSummaries.filter((a) => a.id !== selectedAuthorId);

  // Parallel fetch — silently skip any that fail (404 or network)
  const settled = await Promise.allSettled(
    otherAuthors.map(async (author) => {
      const profile = await fetchProfileWithFallback(author.id);
      return {
        authorId: author.id,
        authorName: author.name,
        point: profile.embedding_umap_2d.centroid,
        spread: profile.embedding_umap_2d.spread,
        selected: false,
      } satisfies ScatterAuthorPoint;
    }),
  );

  for (const result of settled) {
    if (result.status === "fulfilled") {
      points.push(result.value);
    }
  }

  return points;
}
