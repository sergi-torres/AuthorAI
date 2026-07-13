/**
 * Pure logic for the Style DNA panel — no JSX.
 * This is the single source of truth for radar axes, normalization domains,
 * and chart color assignment (design-system.md §2.4).
 */
import type { StyleProfile } from "@/lib/types";

// ---------------------------------------------------------------------------
// Radar axis definitions
// ---------------------------------------------------------------------------

export interface RadarAxisDef {
  /** Unique key used as dataKey in Recharts. */
  key: string;
  /** Key into en.styleDna.radarAxes for the axis label. */
  labelKey: string;
  /**
   * The [min, max] domain used for normalization.
   * Native [0,1] ranges need no comment; non-native ranges are annotated.
   */
  domain: [number, number];
  /** Extracts the raw value from a StyleProfile. */
  select: (p: StyleProfile) => number;
}

/**
 * The six radar axes for the Style DNA panel.
 *
 * Domains are the *plausible range of each metric across literary prose*, NOT the
 * metric's theoretical bounds. Several of these fields are natively [0, 1] but no
 * real author uses the full range (e.g. dialogue_ratio never approaches 1.0), so a
 * [0, 1] domain would pin every author near the centre and waste the chart. Scaling
 * to the observed literary spread makes the radar fill the frame and, crucially, makes
 * authors visibly *differ*. These are honest presentation scalings (like getFitBand
 * thresholds), not data changes — values outside a domain are clamped, not hidden.
 * Thresholds live here and only here.
 */
export const RADAR_AXES: ReadonlyArray<RadarAxisDef> = [
  {
    key: "vocab_richness",
    labelKey: "vocabRichness",
    // MATTR-500 for literary prose sits ~0.4 (repetitive) to ~0.85 (highly varied).
    domain: [0.4, 0.85],
    select: (p) => p.lexical.mattr_500,
  },
  {
    key: "rare_words",
    labelKey: "rareWords",
    // hapax_ratio spans ~0.05 (formulaic) to ~0.5 (idiosyncratic coinages).
    domain: [0.05, 0.5],
    select: (p) => p.lexical.hapax_ratio,
  },
  {
    key: "word_length",
    labelKey: "wordLength",
    // Avg word length in chars: ~3.5 (plain Anglo-Saxon) to ~6 (Latinate/Gothic).
    domain: [3.5, 6],
    select: (p) => p.lexical.avg_word_length,
  },
  {
    key: "sentence_length",
    labelKey: "sentenceLength",
    // Avg sentence length in tokens: ~8 (punchy / dialogue) to ~40 (sweeping prose).
    domain: [8, 40],
    select: (p) => p.syntactic.avg_sentence_length_tokens,
  },
  {
    key: "subordination",
    labelKey: "subordination",
    // subordination_ratio spans ~0.1 (direct) to ~0.5 (deeply nested clauses).
    domain: [0.1, 0.5],
    select: (p) => p.syntactic.subordination_ratio,
  },
  {
    key: "dialogue",
    labelKey: "dialogue",
    // dialogue_ratio spans ~0 (pure narration) to ~0.5 (dialogue-heavy).
    domain: [0, 0.5],
    select: (p) => p.stylistic.dialogue_ratio,
  },
] as const;

/**
 * Linear normalization: maps `value` from `domain` to [0, 1], clamped.
 * Used to prepare data for Recharts RadarChart with domain={[0, 1]}.
 */
export function normalizeAxis(value: number, domain: [number, number]): number {
  const [min, max] = domain;
  if (max === min) return 0;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

// ---------------------------------------------------------------------------
// Chart color assignment (design-system.md §2.4 Recharts mapping)
// ---------------------------------------------------------------------------

/**
 * Returns the CSS custom-property string for the Recharts series color of a given authorId.
 * Recharts accepts CSS variables as `stroke`/`fill` strings and they resolve correctly in SVG.
 *
 * chart-1 = Austen · chart-2 = Dickens · chart-3 = Poe
 * chart-4 = brand (unknown / live-uploaded author)
 * chart-5 = neutral muted (all other / comparison authors)
 *
 * NEVER use if-author logic in components — call this function from lib only.
 */
export function chartColorForAuthor(
  authorId: string,
  role: "selected" | "other" = "other",
): string {
  if (role === "other") return "var(--chart-5)";
  switch (authorId) {
    case "austen":
      return "var(--chart-1)";
    case "dickens":
      return "var(--chart-2)";
    case "poe":
      return "var(--chart-3)";
    default:
      return "var(--chart-4)";
  }
}
