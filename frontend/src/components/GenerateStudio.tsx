"use client";

import { useCallback, useRef, useState } from "react";

import { PromptComposer } from "@/components/PromptComposer";
import { SideBySideOutput } from "@/components/SideBySideOutput";
import type { GenerationState } from "@/components/AuthorColumn";
import { Button } from "@/components/ui/button";
import { generateText } from "@/lib/api";
import { en } from "@/lib/i18n/en";
import type { AuthorCardData } from "@/lib/types";

interface GenerateStudioProps {
  author: AuthorCardData;
}

/**
 * Generation studio client component — owns prompt state and both column
 * GenerationStates. Passes real response data to SideBySideOutput; never
 * fakes the contrast (design-system §8).
 *
 * The parent page (server component) owns the page header and data-voice.
 * This component starts in an "idle" visual state before the first generation.
 */
export function GenerateStudio({ author }: GenerateStudioProps) {
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [vanillaState, setVanillaState] = useState<GenerationState>({
    status: "loading",
  });
  const [autoriaState, setAutoriaState] = useState<GenerationState>({
    status: "loading",
  });
  const [hasGenerated, setHasGenerated] = useState(false);

  /**
   * Passport from the most recent GenerateResponse.
   * Remains `null` until the backend returns a non-null passport.
   * Full handling (download / verify) deferred to #42 / #29.
   */
  const [passport, setPassport] = useState<unknown>(null);

  /**
   * Distinctive terms from the StyleProfile — optional enhancement.
   * Not fetched here; could be passed in from a parent that already has
   * the StyleProfile loaded. Kept as a future prop without blocking
   * generation (design-system §7, Deliverable 6).
   */
  const [distinctiveTerms] = useState<readonly string[]>([]);

  // Keep last prompt so onRetry can re-run it without re-reading stale state.
  const lastPromptRef = useRef<string>("");

  const runGeneration = useCallback(
    async (promptText: string) => {
      lastPromptRef.current = promptText;
      setIsSubmitting(true);
      setHasGenerated(true);
      setVanillaState({ status: "loading" });
      setAutoriaState({ status: "loading" });

      try {
        const response = await generateText(author.id, promptText);
        setVanillaState({ status: "success", output: response.vanilla });
        setAutoriaState({ status: "success", output: response.autoria });
        // Store the passport from this generation; may be null if backend
        // hasn't implemented signing yet (see backend #26).
        setPassport(response.passport ?? null);
      } catch (err: unknown) {
        const isAbort = err instanceof Error && err.name === "AbortError";
        const nextState: GenerationState = isAbort
          ? { status: "timeout" }
          : { status: "error" };
        setVanillaState(nextState);
        setAutoriaState(nextState);
      } finally {
        setIsSubmitting(false);
      }
    },
    [author.id],
  );

  const handleSubmit = useCallback(() => {
    if (prompt.trim().length === 0 || isSubmitting) return;
    void runGeneration(prompt);
  }, [prompt, isSubmitting, runGeneration]);

  const handleRetry = useCallback(() => {
    if (isSubmitting) return;
    void runGeneration(lastPromptRef.current);
  }, [isSubmitting, runGeneration]);

  const bothSucceeded =
    vanillaState.status === "success" && autoriaState.status === "success";

  const handleGeneratePassport = useCallback(() => {
    // TODO(#42): download formatted passport JSON
  }, []);

  return (
    <div className="flex flex-col gap-8">
      {/* ── Section label ── */}
      <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {en.generate.sectionTitle}
      </p>

      {/* ── Prompt composer ── */}
      <section aria-label={en.generate.promptLabel}>
        <PromptComposer
          prompt={prompt}
          isSubmitting={isSubmitting}
          onPromptChange={setPrompt}
          onSubmit={handleSubmit}
        />
      </section>

      {/* ── Side-by-side output ── */}
      <section aria-label={en.generate.outputSectionLabel}>
        {hasGenerated ? (
          <SideBySideOutput
            authorId={author.id}
            authorName={author.name}
            vanilla={vanillaState}
            autoria={autoriaState}
            distinctiveTerms={distinctiveTerms}
            onRetry={handleRetry}
          />
        ) : (
          <IdleState />
        )}
      </section>

      {/* ── Generate Passport button — only after first successful generation ── */}
      {bothSucceeded && (
        <div className="flex flex-col items-start gap-2">
          <Button
            variant="outline"
            disabled={passport === null}
            onClick={handleGeneratePassport}
          >
            {en.studio.passportButton}
          </Button>
          {passport === null && (
            <p className="text-xs text-muted-foreground">
              {en.studio.passportUnavailable}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Placeholder shown before the first generation. Replaced by SideBySideOutput
 * as soon as Generate is pressed for the first time.
 */
function IdleState() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {/* Instruction exposed once to assistive tech; the two cards below are
          decorative placeholders (aria-hidden) to avoid a double announcement. */}
      <p className="sr-only">{en.generate.idleBody}</p>
      <IdleColumn />
      <IdleColumn />
    </div>
  );
}

function IdleColumn() {
  return (
    <div
      className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center shadow-paper-sm"
      aria-hidden="true"
    >
      <p className="text-sm font-medium text-muted-foreground">
        {en.generate.idleHeading}
      </p>
      <p className="max-w-[36ch] text-xs text-muted-foreground/70">
        {en.generate.idleBody}
      </p>
    </div>
  );
}
