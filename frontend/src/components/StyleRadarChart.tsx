"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import {
  RADAR_AXES,
  normalizeAxis,
  chartColorForAuthor,
} from "@/lib/style-dna";
import { en } from "@/lib/i18n/en";
import type { StyleProfile } from "@/lib/types";

interface StyleRadarChartProps {
  profile: StyleProfile;
  /** Author id used to pick the series chart token (chart-1…chart-4). */
  authorId: string;
}

/**
 * Recharts RadarChart of the six Style DNA axes, pre-normalized to [0, 1].
 * Series color comes from chartColorForAuthor() — chart-* CSS variable, never raw hex.
 * Axis labels are sourced from en.styleDna.radarAxes (zero hardcoded strings).
 * Design-system.md §7: StyleRadarChart, Sprint 1.
 */
export function StyleRadarChart({ profile, authorId }: StyleRadarChartProps) {
  const color = chartColorForAuthor(authorId, "selected");

  const data = RADAR_AXES.map((axis) => ({
    subject:
      en.styleDna.radarAxes[
        axis.labelKey as keyof typeof en.styleDna.radarAxes
      ],
    value: normalizeAxis(axis.select(profile), axis.domain),
  }));

  return (
    <div
      role="img"
      aria-label={en.styleDna.radarAriaLabel}
      className="h-72 w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart
          data={data}
          margin={{ top: 8, right: 24, bottom: 8, left: 24 }}
        >
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{
              fill: "var(--muted-foreground)",
              fontSize: 11,
              fontFamily: "var(--font-sans)",
            }}
          />
          {/*
            Pin the radial scale to [0, 1] so the chart never auto-scales to the
            per-author data max — that would rescale every author differently and
            make the shapes non-comparable. Ticks hidden (values are dimensionless).
          */}
          <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
          <Radar
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.25}
            dot={false}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Accessible text table — color is never the only signal (design-system §7 rule 7) */}
      <table className="sr-only">
        <caption>{en.styleDna.radarAriaLabel}</caption>
        <tbody>
          {data.map((d) => (
            <tr key={d.subject}>
              <th scope="row">{d.subject}</th>
              <td>{(d.value * 100).toFixed(0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
