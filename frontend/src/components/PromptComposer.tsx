"use client";

import { Feather } from "lucide-react";

import { Button } from "@/components/ui/button";
import { en } from "@/lib/i18n/en";

const PROMPT_MAX_LENGTH = 4000; // contract: GenerateRequest.prompt maxLength

interface PromptComposerProps {
  prompt: string;
  isSubmitting: boolean;
  onPromptChange: (value: string) => void;
  onSubmit: () => void;
}

/**
 * Prompt input area for the generation studio (design-system §7).
 * States: idle (enabled), submitting (button disabled + submitting label),
 * disabled (empty/whitespace prompt).
 *
 * The `aria-live` region on the form is announced when generation starts,
 * letting screen-reader users know the request is in flight.
 */
export function PromptComposer({
  prompt,
  isSubmitting,
  onPromptChange,
  onSubmit,
}: PromptComposerProps) {
  const trimmed = prompt.trim();
  const isDisabled = isSubmitting || trimmed.length === 0;

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Cmd/Ctrl+Enter submits without consuming the Enter key in normal typing.
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !isDisabled) {
      e.preventDefault();
      onSubmit();
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <label
        htmlFor="prompt-input"
        className="text-sm font-semibold text-foreground"
      >
        {en.generate.promptLabel}
      </label>

      <textarea
        id="prompt-input"
        value={prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isSubmitting}
        maxLength={PROMPT_MAX_LENGTH}
        placeholder={en.generate.promptPlaceholder}
        rows={4}
        aria-describedby="prompt-hint prompt-status"
        className="w-full resize-y rounded-lg border border-input bg-card px-4 py-3 text-[0.9375rem] leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
      />

      <div className="flex items-center justify-between gap-4">
        <span id="prompt-hint" className="text-xs text-muted-foreground">
          {en.generate.promptHint(PROMPT_MAX_LENGTH)}
        </span>

        <Button
          onClick={onSubmit}
          disabled={isDisabled}
          size="lg"
          aria-busy={isSubmitting}
        >
          <Feather className="size-4" aria-hidden="true" />
          {isSubmitting
            ? en.generate.generatingButton
            : en.generate.generateButton}
        </Button>
      </div>

      {/* Live region — announced when generation starts or succeeds */}
      <span
        id="prompt-status"
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {isSubmitting ? en.generate.generatingButton : ""}
      </span>
    </div>
  );
}
