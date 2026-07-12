import type { ReactNode } from "react";

interface DistinctiveVocabHighlightProps {
  /** Generated passage text. */
  text: string;
  /** Terms from StyleProfile.distinctive_vocab (already ranked by the API). */
  terms: readonly string[];
}

function escapeRegExp(term: string): string {
  return term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Marks the author's signature vocabulary inline using the ambient voice
 * palette — an ancestor's data-voice decides the color, so this component
 * stays author-agnostic. Matching is whole-word, case-insensitive.
 */
export function DistinctiveVocabHighlight({
  text,
  terms,
}: DistinctiveVocabHighlightProps): ReactNode {
  const patterns = terms.filter((t) => t.trim().length > 0).map(escapeRegExp);
  if (patterns.length === 0) {
    return text;
  }

  /* Capture group makes split() interleave: even indices = plain text,
     odd indices = matched terms. Unicode letter lookarounds instead of \b so
     accented terms ("corazón", "María") still match whole words. */
  const parts = text.split(
    new RegExp(`(?<!\\p{L})(${patterns.join("|")})(?!\\p{L})`, "giu"),
  );

  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <mark
        key={i}
        className="rounded-sm bg-voice-tint px-0.5 font-medium text-voice"
      >
        {part}
      </mark>
    ) : (
      part
    ),
  );
}
