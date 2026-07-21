/**
 * Pure, deterministic text-measurement utilities for the comparative metrics
 * table (#28). No I/O, no side-effects — unit-testable in isolation.
 *
 * All returned numeric values are unrounded raw measurements; callers should
 * apply toFixed(n) or toLocaleString for display.
 */

/** Stopwords excluded from topWords frequency ranking. */
const STOPWORDS = new Set([
  "the",
  "a",
  "an",
  "and",
  "or",
  "but",
  "of",
  "to",
  "in",
  "on",
  "it",
  "is",
  "was",
  "that",
  "this",
  "with",
  "as",
  "for",
  "he",
  "she",
  "they",
  "his",
  "her",
]);

export interface TextMetrics {
  wordCount: number;
  /** Mean tokens per sentence. */
  avgSentenceLength: number;
  /** Type-token ratio: unique words / total words. Range [0, 1]. */
  ttr: number;
  /** Top 3 content words by frequency, lowercased. Ties broken alphabetically. */
  topWords: string[];
}

/**
 * Measure a generated text string.
 *
 * - Sentences: split on /[.!?]+(\s|$)/, drop empties.
 * - Words: match Unicode letters including hyphens and apostrophes, lowercased.
 * - TTR: uniqueWords / totalWords (0 when no words).
 * - topWords: top 3 content words, stopwords excluded.
 * - Empty / whitespace input returns zeros / empty array. Never throws.
 */
export function measureText(text: string): TextMetrics {
  const trimmed = text.trim();
  if (trimmed.length === 0) {
    return { wordCount: 0, avgSentenceLength: 0, ttr: 0, topWords: [] };
  }

  // Sentences: split on sentence-ending punctuation
  const rawSentences = trimmed.split(/[.!?]+(?:\s|$)/);
  const sentences = rawSentences.filter((s) => s.trim().length > 0);
  const sentenceCount = sentences.length;

  // Words: Unicode-aware letter sequences including hyphens and apostrophes
  const wordMatches = trimmed.match(/\p{L}[\p{L}'-]*/gu);
  const words: string[] = wordMatches
    ? wordMatches.map((w) => w.toLowerCase())
    : [];
  const wordCount = words.length;

  if (wordCount === 0) {
    return { wordCount: 0, avgSentenceLength: 0, ttr: 0, topWords: [] };
  }

  // Avg sentence length: total words / sentence count
  const avgSentenceLength =
    sentenceCount > 0 ? wordCount / sentenceCount : wordCount;

  // TTR: unique word types / total word tokens
  const uniqueWords = new Set(words);
  const ttr = uniqueWords.size / wordCount;

  // Top content words: frequency map excluding stopwords
  const freq = new Map<string, number>();
  for (const w of words) {
    if (!STOPWORDS.has(w)) {
      freq.set(w, (freq.get(w) ?? 0) + 1);
    }
  }

  const topWords = [...freq.entries()]
    .sort(([aWord, aCount], [bWord, bCount]) => {
      if (bCount !== aCount) return bCount - aCount; // desc by frequency
      return aWord.localeCompare(bWord); // asc alphabetically on tie
    })
    .slice(0, 3)
    .map(([w]) => w);

  return { wordCount, avgSentenceLength, ttr, topWords };
}
