"use client";

import { useId, useMemo, useState } from "react";
import { ChevronDown, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { en } from "@/lib/i18n/en";
import type { PassportEnvelope } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Props are a discriminated union (design-system §7 rule 6) so the invalid
 * combination "ready without a passport" cannot compile:
 *
 *  • ready       — the backend returned a signed PassportEnvelope
 *  • unavailable — `GenerateResponse.passport` was null (contract allows it;
 *                  backend signing is #26). Download is disabled with copy.
 *
 * §7 inventories PassportCard with a single "ready" state; "unavailable" is the
 * honest rendering of the contract's nullable `passport` field rather than a
 * fourth async state — this component never fetches, the studio owns that.
 */
type PassportCardProps =
  | {
      status: "ready";
      passport: PassportEnvelope;
      /** Triggers the file download; wired to `lib/passport.downloadPassport`. */
      onDownload: () => void;
    }
  | { status: "unavailable" };

/**
 * PassportCard — design-system §7 inventory (Sprint 2, screens: studio, verify).
 * "Mono JSON block + Download action".
 *
 * Renders the decoded Authorship Passport payload as a collapsible `font-mono`
 * block next to the existing Download action, so the demo beat "Generate
 * Passport → the JSON appears" (docs/MVP.md, 01:40) happens on screen and not
 * only on disk.
 *
 * **Starts collapsed on purpose.** A full `json_payload` is ~40 lines; expanded
 * by default it pushes the rest of the studio out of the viewport and breaks
 * the demo framing (issue #94, regression risk).
 *
 * Forensic surfaces use `font-mono` (§3, "Forensic" row: hashes, JWS, JSON) and
 * only existing tokens (`rounded-lg`, `border-border`, `bg-card`,
 * `shadow-paper-sm`, `bg-muted/50`) — no raw Tailwind colors (§7 rule 3). The
 * JSON block keeps `bg-muted/50` so it reads as a quiet inset against the card.
 *
 * NOTE ON DUPLICATION (deliberate): `app/verify/page.tsx` has an equivalent raw
 * JSON toggle. It is NOT factored out here because `verify/page.tsx` is outside
 * the files this work order may touch (#94 "Ficheros a tocar"), and the two
 * blocks differ in framing: verify renders a *verified* payload as a secondary
 * detail under its table, while the studio renders a *freshly issued* envelope
 * as the primary artifact with the Download action attached. Extracting a
 * shared `<RawJsonDisclosure>` is a clean follow-up once both screens are in
 * scope of the same change.
 */
export function PassportCard(props: PassportCardProps) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();

  const isReady = props.status === "ready";
  const payload = isReady ? props.passport.json_payload : null;

  // Stringify once per payload, not on every expand/collapse re-render.
  const json = useMemo(
    () => (payload === null ? "" : JSON.stringify(payload, null, 2)),
    [payload],
  );

  return (
    <section
      aria-label={en.studio.passportCardTitle}
      className="flex flex-col gap-3 rounded-lg border border-border bg-card p-5 shadow-paper-sm"
    >
      {/* ── Header: label + Download action ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {en.studio.passportCardTitle}
        </h2>

        <Button
          variant="outline"
          size="sm"
          disabled={!isReady}
          onClick={isReady ? props.onDownload : undefined}
          aria-label={en.studio.passportDownloadAriaLabel}
        >
          <Download className="size-4" aria-hidden="true" />
          {en.studio.passportButton}
        </Button>
      </div>

      {!isReady && (
        <p className="text-xs text-muted-foreground">
          {en.studio.passportUnavailable}
        </p>
      )}

      {isReady && (
        <>
          <p className="text-xs text-muted-foreground">
            {en.studio.passportCardCaption}
          </p>

          {/* ── Collapsible mono JSON block — collapsed on first render ── */}
          <div className="flex flex-col gap-2">
            <button
              type="button"
              aria-expanded={expanded}
              aria-controls={contentId}
              onClick={() => setExpanded((v) => !v)}
              className="inline-flex items-center gap-1.5 self-start rounded text-xs text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ChevronDown
                className={cn(
                  "size-4 transition-transform duration-200",
                  expanded ? "rotate-0" : "-rotate-90",
                )}
                aria-hidden="true"
              />
              {expanded
                ? en.studio.passportJsonToggleHide
                : en.studio.passportJsonToggleShow}
            </button>

            {/* The wrapper stays mounted so aria-controls always resolves. */}
            <div id={contentId} hidden={!expanded}>
              {expanded && (
                <pre
                  tabIndex={0}
                  role="region"
                  aria-label={en.studio.passportJsonAriaLabel}
                  className="max-h-96 overflow-auto rounded-lg border border-border bg-muted/50 p-4 font-mono text-xs leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {json}
                </pre>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
