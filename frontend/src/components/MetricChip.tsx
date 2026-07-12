import { en } from "@/lib/i18n/en";

interface MetricChipProps {
  /** Numeric value to display (formatted as integer). */
  value: number;
  /** Label key within en.styleDna — "metricDocuments" | "metricTokens" | "metricSentences". */
  label: string;
}

/**
 * A small forensic metric display: `font-mono tabular-nums` value atop a
 * `text-xs text-muted-foreground` label. Matches design-system.md §3 "Metric"
 * + "Caption" recipes. Used for corpus_stats counts in the Style DNA panel header.
 */
export function MetricChip({ value, label }: MetricChipProps) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="font-mono tabular-nums text-sm font-semibold text-foreground">
        {value.toLocaleString("en-US")}
      </span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  );
}

/** Convenience: render all three corpus-stat chips from a corpus_stats object. */
export function CorpusMetricChips({
  n_documents,
  n_tokens,
  n_sentences,
}: {
  n_documents: number;
  n_tokens: number;
  n_sentences: number;
}) {
  return (
    <div className="flex items-center gap-6">
      <MetricChip value={n_documents} label={en.styleDna.metricDocuments} />
      <MetricChip value={n_tokens} label={en.styleDna.metricTokens} />
      <MetricChip value={n_sentences} label={en.styleDna.metricSentences} />
    </div>
  );
}
