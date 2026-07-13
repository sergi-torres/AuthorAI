import { Clock, TriangleAlert } from "lucide-react";

import { DistinctiveVocabHighlight } from "@/components/DistinctiveVocabHighlight";
import { FitScoreBar, FitScoreBarPending } from "@/components/FitScoreBar";
import { Button } from "@/components/ui/button";
import { en } from "@/lib/i18n/en";
import type { GenerationOutput } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Async state for one generation branch. Every column renders exactly one of
 * these — there is no path that shows a spinner forever (timeout is a state).
 */
export type GenerationState =
  | { status: "loading" }
  | { status: "timeout" }
  | { status: "error" }
  | { status: "success"; output: GenerationOutput };

type AuthorColumnProps = {
  state: GenerationState;
  onRetry?: () => void;
} & (
  | { variant: "vanilla" }
  | {
      variant: "authorial";
      authorId: string;
      authorName: string;
      distinctiveTerms?: readonly string[];
    }
);

/**
 * One side of the vanilla-vs-AutorIA comparison. The authorial column wears
 * the author's signature palette (via data-voice); the vanilla column stays
 * deliberately anonymous — that asymmetry is the 5-second contrast device.
 */
export function AuthorColumn(props: AuthorColumnProps) {
  const isVoice = props.variant === "authorial";
  const { state } = props;

  return (
    <section
      data-voice={isVoice ? props.authorId : undefined}
      className={cn(
        "flex flex-col overflow-hidden rounded-xl border bg-card shadow-paper",
        isVoice && "border-voice/30",
      )}
    >
      <div className={cn("h-1 shrink-0", isVoice ? "bg-voice" : "bg-border")} />

      <header className="flex items-center justify-between gap-3 px-5 pt-4">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
            isVoice
              ? "bg-voice-tint text-voice"
              : "bg-muted text-muted-foreground",
          )}
        >
          {isVoice
            ? en.studio.voiceLabel(props.authorName)
            : en.studio.vanillaLabel}
        </span>
        {state.status === "success" && (
          <span className="font-mono text-xs tabular-nums text-muted-foreground">
            {en.studio.latency(state.output.latency_ms)}
          </span>
        )}
      </header>

      <div className="flex-1 px-5 py-4">
        {state.status === "loading" && (
          <div role="status" className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              {isVoice
                ? en.studio.generatingVoice(props.authorName)
                : en.studio.generating}
            </p>
            <div
              className="flex animate-pulse flex-col gap-2"
              aria-hidden="true"
            >
              <div className="h-3 w-full rounded bg-muted" />
              <div className="h-3 w-11/12 rounded bg-muted" />
              <div className="h-3 w-full rounded bg-muted" />
              <div className="h-3 w-3/4 rounded bg-muted" />
            </div>
          </div>
        )}

        {state.status === "timeout" && (
          <StateNotice
            icon={<Clock className="size-4 text-warning" aria-hidden="true" />}
            message={en.studio.generationTimeout}
            onRetry={props.onRetry}
          />
        )}

        {state.status === "error" && (
          <StateNotice
            icon={
              <TriangleAlert
                className="size-4 text-destructive"
                aria-hidden="true"
              />
            }
            message={en.studio.generationError}
            onRetry={props.onRetry}
          />
        )}

        {state.status === "success" && (
          <div className="animate-fade-rise flex flex-col gap-3">
            <p className="max-w-[66ch] whitespace-pre-line font-serif text-[0.9375rem] leading-7 text-foreground/90">
              {isVoice ? (
                <DistinctiveVocabHighlight
                  text={state.output.text}
                  terms={props.distinctiveTerms ?? []}
                />
              ) : (
                state.output.text
              )}
            </p>
            {isVoice && (props.distinctiveTerms?.length ?? 0) > 0 && (
              <p className="text-xs text-muted-foreground">
                {en.studio.vocabLegend(props.authorName)}
              </p>
            )}
          </div>
        )}
      </div>

      <footer className="border-t border-border/60 px-5 py-4">
        {state.status === "success" ? (
          isVoice ? (
            <FitScoreBar
              variant="authorial"
              authorName={props.authorName}
              score={state.output.fit_score}
            />
          ) : (
            <FitScoreBar variant="vanilla" score={state.output.fit_score} />
          )
        ) : (
          <FitScoreBarPending />
        )}
      </footer>
    </section>
  );
}

function StateNotice({
  icon,
  message,
  onRetry,
}: {
  icon: React.ReactNode;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div role="status" className="flex flex-col items-start gap-3">
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        {message}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {en.studio.retry}
        </Button>
      )}
    </div>
  );
}
