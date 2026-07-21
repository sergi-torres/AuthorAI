"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { Feather } from "lucide-react";

import { PromptComposer } from "@/components/PromptComposer";
import { SideBySideOutput } from "@/components/SideBySideOutput";
import type { GenerationState } from "@/components/AuthorColumn";
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
 * The component starts in an "idle" visual state (both columns show loading
 * skeletons) before the first generation. Once Generate is pressed the
 * loading state is real.
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

  return (
    <div className="flex flex-col gap-8" data-voice={author.id}>
      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <Link
          href={`/author/${author.id}`}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {en.generate.backToProfile}
        </Link>
      </div>

      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Feather className="size-5 text-voice" aria-hidden="true" />
          <h1 className="font-heading text-4xl font-semibold tracking-tight">
            {author.name}
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          {en.generate.pageTitle(author.name)}
        </p>
      </header>

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
