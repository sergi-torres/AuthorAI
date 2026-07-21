"use client";

import { useMemo } from "react";

import { en } from "@/lib/i18n/en";
import { measureText } from "@/lib/textMetrics";
import { cn } from "@/lib/utils";

interface ComparativeMetricsTableProps {
  vanillaText: string;
  authorText: string;
  authorName: string;
}

/**
 * Side-by-side descriptive statistics for one generation pair (#28).
 *
 * Both columns are measured from the actual output text — never invented or
 * hardcoded per author (design-system §8 / "never fake the contrast").
 *
 * The AutorIA column header uses `text-voice` so it inherits the author's
 * palette token set by the parent's `data-voice` attribute. Numbers use
 * `font-mono tabular-nums`; no hex/rgb colours are added.
 */
export function ComparativeMetricsTable({
  vanillaText,
  authorText,
  authorName,
}: ComparativeMetricsTableProps) {
  const vanilla = useMemo(() => measureText(vanillaText), [vanillaText]);
  const autoria = useMemo(() => measureText(authorText), [authorText]);

  const rows: Array<{ label: string; vanilla: string; autoria: string }> = [
    {
      label: en.studio.metricSentenceLength,
      vanilla: vanilla.avgSentenceLength.toFixed(1),
      autoria: autoria.avgSentenceLength.toFixed(1),
    },
    {
      label: en.studio.metricTtr,
      vanilla: vanilla.ttr.toFixed(2),
      autoria: autoria.ttr.toFixed(2),
    },
    {
      label: en.studio.metricWordCount,
      vanilla: vanilla.wordCount.toLocaleString("en-US"),
      autoria: autoria.wordCount.toLocaleString("en-US"),
    },
    {
      label: en.studio.metricTopWords,
      vanilla: vanilla.topWords.join(" · ") || "—",
      autoria: autoria.topWords.join(" · ") || "—",
    },
  ];

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {en.studio.metricsTitle}
      </h3>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          {/* Screen-reader caption — hidden visually */}
          <caption className="sr-only">{en.studio.metricsTitle}</caption>

          <thead>
            <tr className="border-b border-border bg-muted/40">
              {/* Metric label column — no header text needed visually */}
              <th
                scope="col"
                className="w-[40%] px-4 py-2 text-left text-xs font-medium text-muted-foreground"
              >
                {/* empty — label is conveyed by row headers */}
              </th>
              <th
                scope="col"
                className="px-4 py-2 text-right text-xs font-medium text-muted-foreground"
              >
                {en.studio.metricsColVanilla}
              </th>
              <th
                scope="col"
                className="px-4 py-2 text-right text-xs font-medium text-voice"
              >
                {en.studio.metricsColVoice(authorName)}
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr
                key={row.label}
                className={cn(
                  "border-b border-border/50 last:border-0",
                  i % 2 === 1 && "bg-muted/20",
                )}
              >
                <th
                  scope="row"
                  className="px-4 py-2 text-left text-xs font-medium text-muted-foreground"
                >
                  {row.label}
                </th>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-xs text-foreground/80">
                  {row.vanilla}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-xs text-foreground/80">
                  {row.autoria}
                </td>
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr>
              <td
                colSpan={3}
                className="px-4 py-2 text-left text-xs text-muted-foreground/70"
              >
                {en.studio.metricsCaption}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
