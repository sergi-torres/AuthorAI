"use client";

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  LabelList,
} from "recharts";

import { chartColorForAuthor } from "@/lib/style-dna";
import { en } from "@/lib/i18n/en";

export interface ScatterAuthorPoint {
  /** Stable author id (maps to chart color token). */
  authorId: string;
  /** Display name used as a point label. */
  authorName: string;
  /** UMAP 2D centroid coordinates. */
  point: [number, number];
  /** UMAP cluster spread radius (used to size the dispersion ring). */
  spread: number;
  /** True for the author whose page is open — rendered in their voice chart token. */
  selected: boolean;
}

interface StyleScatter2DProps {
  points: ScatterAuthorPoint[];
}

/**
 * 2D scatter of UMAP author cluster centroids.
 *
 * CONTRACT LIMITATION (see docs/design-system.md Decision Log): the API exposes
 * only one centroid + spread per author — there are no per-chunk points. Each
 * Scatter series is therefore a single point. Per-chunk scatter is flagged as a
 * contract gap (docs/design-system.md §9) — not faked here.
 *
 * Selected author: rendered in their voice chart color (chart-1…chart-4) with a
 * translucent SVG dispersion ring scaled by `spread`. Others: chart-5 muted dots.
 * Both X and Y axes are hidden (UMAP axes are dimensionless user-unreadable coords).
 * Every point carries a text label — color is never the only signal (a11y, §7 rule 7).
 *
 * Design-system.md §7: StyleScatter2D, Sprint 1.
 */
export function StyleScatter2D({ points }: StyleScatter2DProps) {
  // Split into selected vs. others so selected renders on top via separate Scatter series
  const selected = points.filter((p) => p.selected);
  const others = points.filter((p) => !p.selected);

  // Build flat arrays Recharts expects: { x, y, authorName, spread, authorId }
  type Row = {
    x: number;
    y: number;
    authorName: string;
    spread: number;
    authorId: string;
    selected: boolean;
  };
  const toRow = (p: ScatterAuthorPoint): Row => ({
    x: p.point[0],
    y: p.point[1],
    authorName: p.authorName,
    spread: p.spread,
    authorId: p.authorId,
    selected: p.selected,
  });

  const selectedRows = selected.map(toRow);
  const otherRows = others.map(toRow);

  return (
    <div className="flex flex-col gap-2">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 32, bottom: 12, left: 8 }}>
            {/* X and Y axes hidden — UMAP coordinates are meaningless to users */}
            <XAxis type="number" dataKey="x" hide />
            <YAxis type="number" dataKey="y" hide />

            {/* Other / comparison authors: muted chart-5 dots */}
            <Scatter
              name="others"
              data={otherRows}
              fill="var(--chart-5)"
              fillOpacity={0.7}
              stroke="none"
            >
              <LabelList
                dataKey="authorName"
                position="top"
                style={{
                  fill: "var(--muted-foreground)",
                  fontSize: 10,
                  fontFamily: "var(--font-sans)",
                }}
              />
            </Scatter>

            {/* Selected author: voice chart token + dispersion ring */}
            <Scatter
              name="selected"
              data={selectedRows}
              fill={
                selectedRows[0]
                  ? chartColorForAuthor(selectedRows[0].authorId, "selected")
                  : "var(--chart-4)"
              }
              stroke="none"
              shape={(shapeProps: {
                cx?: number;
                cy?: number;
                payload?: Row;
              }) => {
                const { cx = 0, cy = 0, payload } = shapeProps;
                if (!payload) return <circle cx={cx} cy={cy} r={6} />;
                const color = chartColorForAuthor(payload.authorId, "selected");
                // Spread ring: 1 UMAP unit ≈ 20px at typical viewport (heuristic scale factor)
                const ringR = Math.max(10, payload.spread * 20);
                return (
                  <g>
                    <circle
                      cx={cx}
                      cy={cy}
                      r={ringR}
                      fill={color}
                      fillOpacity={0.12}
                      stroke={color}
                      strokeOpacity={0.35}
                      strokeWidth={1}
                    />
                    <circle cx={cx} cy={cy} r={7} fill={color} />
                  </g>
                );
              }}
            >
              <LabelList
                dataKey="authorName"
                position="top"
                style={{
                  fill: "var(--foreground)",
                  fontSize: 11,
                  fontFamily: "var(--font-sans)",
                  fontWeight: 600,
                }}
              />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Caption explaining the map — required by design-system §7 rule 7 */}
      <p className="text-xs text-muted-foreground">
        {en.styleDna.scatterCaption}
      </p>
    </div>
  );
}
