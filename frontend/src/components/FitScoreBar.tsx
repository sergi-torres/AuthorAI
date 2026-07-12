import { en } from "@/lib/i18n/en";
import { cn } from "@/lib/utils";

/**
 * Fit-score bands — the ONLY place score thresholds live.
 * Import getFitBand() wherever a band is needed; never re-implement.
 * Color mapping follows docs/design-system.md §2.3: low fit is neutral
 * "generic" gray, not red — red is reserved for real errors.
 */
export type FitBand = "generic" | "weak" | "mid" | "good" | "high";

export function getFitBand(score: number): FitBand {
  if (score >= 85) return "high";
  if (score >= 70) return "good";
  if (score >= 55) return "mid";
  if (score >= 40) return "weak";
  return "generic";
}

const BAND_FILL: Record<FitBand, string> = {
  generic: "bg-fit-generic",
  weak: "bg-fit-weak",
  mid: "bg-fit-mid",
  good: "bg-fit-good",
  high: "bg-fit-high",
};

/* weak/mid/good fail AA as text on parchment — fill-only (design-system.md §2.5). */
const BAND_SCORE_TEXT: Record<FitBand, string> = {
  generic: "text-muted-foreground",
  weak: "text-foreground",
  mid: "text-foreground",
  good: "text-foreground",
  high: "text-fit-high",
};

type FitScoreBarProps = {
  /** Integer 0–100 from GenerationOutput.fit_score. */
  score: number;
  /** Animate the fill on mount (the generate-reveal moment). */
  animate?: boolean;
} & ({ variant: "vanilla" } | { variant: "authorial"; authorName: string });

/**
 * The hero metric of the app: a horizontal fill whose LENGTH carries the
 * vanilla-vs-AutorIA contrast even in grayscale. Caption text ("34% generic"
 * vs "87% Dickens-fit") makes the meaning explicit without color.
 */
export function FitScoreBar(props: FitScoreBarProps) {
  const score = Math.max(0, Math.min(100, Math.round(props.score)));
  const band = getFitBand(score);
  const caption =
    props.variant === "authorial"
      ? en.studio.fitCaptionVoice(score, props.authorName)
      : en.studio.fitCaptionGeneric(score);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          {caption}
        </span>
        <span
          className={cn(
            "font-mono text-2xl font-semibold tabular-nums leading-none",
            BAND_SCORE_TEXT[band],
          )}
        >
          {score}
        </span>
      </div>
      <div
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score}
        aria-label={caption}
        className="h-2 overflow-hidden rounded-full bg-fit-track"
      >
        <div
          className={cn(
            "h-full rounded-full",
            BAND_FILL[band],
            props.animate !== false && "animate-fit-grow",
          )}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

/** Empty-track placeholder shown while generation is pending or failed. */
export function FitScoreBarPending() {
  return (
    <div className="flex flex-col gap-1.5" aria-hidden="true">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          {en.studio.fitPending}
        </span>
        <span className="font-mono text-2xl font-semibold tabular-nums leading-none text-muted-foreground">
          —
        </span>
      </div>
      <div className="h-2 rounded-full bg-fit-track" />
    </div>
  );
}
