import { describe, it, expect } from "vitest";
import { measureText } from "./textMetrics";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

/** Round a number to n decimal places — mirrors the .toFixed() display path. */
function r(n: number, places = 2): number {
  return Math.round(n * 10 ** places) / 10 ** places;
}

// ---------------------------------------------------------------------------
// Edge cases: empty / whitespace
// ---------------------------------------------------------------------------

describe("measureText — empty / whitespace input", () => {
  it("returns all-zero struct for empty string", () => {
    expect(measureText("")).toEqual({
      wordCount: 0,
      avgSentenceLength: 0,
      ttr: 0,
      topWords: [],
    });
  });

  it("returns all-zero struct for whitespace-only string", () => {
    expect(measureText("   \n\t  ")).toEqual({
      wordCount: 0,
      avgSentenceLength: 0,
      ttr: 0,
      topWords: [],
    });
  });

  it("returns all-zero struct for punctuation-only string (no word chars)", () => {
    const m = measureText("... ??? !!!");
    expect(m.wordCount).toBe(0);
    expect(m.ttr).toBe(0);
    expect(m.topWords).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// wordCount
// ---------------------------------------------------------------------------

describe("measureText — wordCount", () => {
  it("counts a simple sentence", () => {
    expect(measureText("The cat sat on the mat.").wordCount).toBe(6);
  });

  it("counts words separated by multiple spaces", () => {
    expect(measureText("one  two   three").wordCount).toBe(3);
  });

  it("counts hyphenated compound as one word", () => {
    // /\p{L}[\p{L}'-]*/ matches "well-known" as a single token
    expect(measureText("A well-known fact.").wordCount).toBe(3);
  });

  it("counts contraction as one word", () => {
    // "it's" → one token
    expect(measureText("It's raining.").wordCount).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// avgSentenceLength
// ---------------------------------------------------------------------------

describe("measureText — avgSentenceLength", () => {
  it("single sentence: avgSentenceLength equals wordCount", () => {
    // "The cat sat" — 1 sentence (no terminal punctuation → sentenceCount=1 after split)
    const m = measureText("The cat sat");
    expect(m.wordCount).toBe(3);
    expect(m.avgSentenceLength).toBe(3);
  });

  it("two equally-sized sentences produce the average", () => {
    // "One two. Three four." → 2 sentences, 4 words total → avg 2.0
    const m = measureText("One two. Three four.");
    expect(m.wordCount).toBe(4);
    expect(r(m.avgSentenceLength, 1)).toBe(2.0);
  });

  it("handles exclamation and question marks as sentence endings", () => {
    // "Run! Stop? Go." → 3 sentences, 3 words → avg 1.0
    const m = measureText("Run! Stop? Go.");
    expect(m.wordCount).toBe(3);
    expect(r(m.avgSentenceLength, 1)).toBe(1.0);
  });

  it("consecutive terminal punctuation counts as one sentence boundary", () => {
    // "Really?! Yes." → 2 sentences, 2 words → avg 1.0
    const m = measureText("Really?! Yes.");
    expect(m.wordCount).toBe(2);
    expect(r(m.avgSentenceLength, 1)).toBe(1.0);
  });
});

// ---------------------------------------------------------------------------
// TTR (type-token ratio)
// ---------------------------------------------------------------------------

describe("measureText — ttr", () => {
  it("all unique words → ttr = 1.0", () => {
    expect(measureText("cat dog bird fish").ttr).toBe(1.0);
  });

  it("all identical words → ttr = 1/n", () => {
    // "cat cat cat cat" → 1 unique / 4 total = 0.25
    expect(r(measureText("cat cat cat cat").ttr)).toBe(0.25);
  });

  it("mixed case is normalised before computing TTR", () => {
    // "Cat cat CAT" → 1 unique ("cat") / 3 total = 0.333…
    expect(r(measureText("Cat cat CAT").ttr)).toBe(0.33);
  });

  it("ttr is within [0, 1]", () => {
    const m = measureText("The quick brown fox jumps over the lazy dog.");
    expect(m.ttr).toBeGreaterThan(0);
    expect(m.ttr).toBeLessThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// topWords — stopword exclusion and frequency ranking
// ---------------------------------------------------------------------------

describe("measureText — topWords", () => {
  it("excludes all stopwords from the result", () => {
    // Every word in this sentence is a stopword → topWords must be empty
    const m = measureText("the and or but of to in on it is was");
    expect(m.topWords).toEqual([]);
  });

  it("returns top-3 content words sorted by descending frequency", () => {
    // "apple" × 3, "banana" × 2, "cherry" × 1
    const text = "apple banana apple cherry apple banana";
    const m = measureText(text);
    expect(m.topWords).toEqual(["apple", "banana", "cherry"]);
  });

  it("returns at most 3 words even when more are present", () => {
    const text = "alpha beta gamma delta epsilon zeta";
    expect(measureText(text).topWords).toHaveLength(3);
  });

  it("returns fewer than 3 words when fewer content words exist", () => {
    // Only 2 non-stopword tokens
    const m = measureText("the cat sat");
    expect(m.topWords).toHaveLength(2);
    expect(m.topWords).toContain("cat");
    expect(m.topWords).toContain("sat");
  });

  it("breaks frequency ties alphabetically (ascending)", () => {
    // "zebra" and "apple" both appear twice; "apple" < "zebra" alphabetically
    const m = measureText("zebra apple zebra apple");
    expect(m.topWords[0]).toBe("apple");
    expect(m.topWords[1]).toBe("zebra");
  });

  it("lowercases words before frequency counting", () => {
    // "Fox" and "fox" should merge into one token with count 2
    const m = measureText("Fox jumped fox jumped");
    expect(m.topWords[0]).toBe("fox");
  });
});

// ---------------------------------------------------------------------------
// Integration: a realistic prose passage
// ---------------------------------------------------------------------------

describe("measureText — realistic prose", () => {
  const prose =
    "It was the best of times, it was the worst of times. " +
    "It was the age of wisdom, it was the age of foolishness.";

  it("counts words correctly", () => {
    expect(measureText(prose).wordCount).toBe(24);
  });

  it("computes avgSentenceLength for two sentences", () => {
    // 24 words / 2 sentences = 12.0
    expect(r(measureText(prose).avgSentenceLength, 1)).toBe(12.0);
  });

  it("ttr is less than 1 due to repeated words", () => {
    expect(measureText(prose).ttr).toBeLessThan(1);
  });

  it("topWords excludes stopwords (the, of, it, was)", () => {
    const { topWords } = measureText(prose);
    const stopwordsInResults = topWords.filter((w) =>
      ["the", "of", "it", "was", "times"].includes(w),
    );
    // "times" is not in the stopword list — it CAN appear; but the four
    // function-words above must all be excluded
    const hardStops = topWords.filter((w) =>
      ["the", "of", "it", "was"].includes(w),
    );
    expect(hardStops).toHaveLength(0);
    void stopwordsInResults; // suppress unused-var warning
  });

  it("topWords contains 'times' (appears twice, not a stopword)", () => {
    expect(measureText(prose).topWords).toContain("times");
  });
});
