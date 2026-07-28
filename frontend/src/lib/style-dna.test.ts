import { describe, it, expect } from "vitest";

import {
  DISTINCTIVE_HIGHLIGHT_LIMIT,
  selectDistinctiveTerms,
} from "./style-dna";
import type { DistinctiveTerm } from "./types";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

/** Builds a `{term, score}` list (the api_contract DistinctiveTerm shape). */
function vocab(...pairs: [string, number][]): DistinctiveTerm[] {
  return pairs.map(([term, score]) => ({ term, score }));
}

// ---------------------------------------------------------------------------
// Degraded inputs — the column must never break (issue #93)
// ---------------------------------------------------------------------------

describe("selectDistinctiveTerms — degraded input", () => {
  it("returns [] for an empty vocab (profile not yet computed)", () => {
    expect(selectDistinctiveTerms([])).toEqual([]);
  });

  it("returns [] for undefined (no profile at all)", () => {
    expect(selectDistinctiveTerms(undefined)).toEqual([]);
  });

  it("returns [] for null", () => {
    expect(selectDistinctiveTerms(null)).toEqual([]);
  });

  it("drops empty and whitespace-only terms", () => {
    expect(
      selectDistinctiveTerms(vocab(["", 0.9], ["   ", 0.8], ["fog", 0.7])),
    ).toEqual(["fog"]);
  });

  it("returns [] when every term is blank", () => {
    expect(selectDistinctiveTerms(vocab(["", 0.9], ["\t", 0.8]))).toEqual([]);
  });

  it("returns [] for a non-positive limit", () => {
    expect(selectDistinctiveTerms(vocab(["fog", 0.9]), 0)).toEqual([]);
    expect(selectDistinctiveTerms(vocab(["fog", 0.9]), -3)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Ranking
// ---------------------------------------------------------------------------

describe("selectDistinctiveTerms — ranking", () => {
  it("sorts by score descending", () => {
    expect(
      selectDistinctiveTerms(
        vocab(["miserable", 0.8], ["countenance", 0.88], ["wretched", 0.84]),
      ),
    ).toEqual(["countenance", "wretched", "miserable"]);
  });

  it("keeps incoming order for ties (the API ranking)", () => {
    expect(
      selectDistinctiveTerms(vocab(["pallid", 0.5], ["phantasm", 0.5])),
    ).toEqual(["pallid", "phantasm"]);
  });

  it("handles negative scores without dropping them", () => {
    expect(
      selectDistinctiveTerms(vocab(["rare", -0.2], ["common", -0.9])),
    ).toEqual(["rare", "common"]);
  });

  it("trims surrounding whitespace off the returned terms", () => {
    expect(selectDistinctiveTerms(vocab(["  countenance  ", 0.9]))).toEqual([
      "countenance",
    ]);
  });
});

// ---------------------------------------------------------------------------
// De-duplication (the highlight matcher is case-insensitive)
// ---------------------------------------------------------------------------

describe("selectDistinctiveTerms — de-duplication", () => {
  it("keeps only the highest-scoring casing of a repeated term", () => {
    expect(
      selectDistinctiveTerms(
        vocab(["Fog", 0.9], ["fog", 0.7], ["FOG", 0.5], ["gloom", 0.6]),
      ),
    ).toEqual(["Fog", "gloom"]);
  });

  it("treats whitespace-padded duplicates as the same term", () => {
    expect(selectDistinctiveTerms(vocab(["fog", 0.9], [" fog ", 0.8]))).toEqual(
      ["fog"],
    );
  });
});

// ---------------------------------------------------------------------------
// Limit
// ---------------------------------------------------------------------------

describe("selectDistinctiveTerms — limit", () => {
  it("caps at DISTINCTIVE_HIGHLIGHT_LIMIT by default", () => {
    const many = vocab(
      ...Array.from(
        { length: 25 },
        (_, i) => [`term${i}`, 1 - i / 100] as [string, number],
      ),
    );
    const terms = selectDistinctiveTerms(many);
    expect(terms).toHaveLength(DISTINCTIVE_HIGHLIGHT_LIMIT);
    expect(terms[0]).toBe("term0");
    expect(terms.at(-1)).toBe(`term${DISTINCTIVE_HIGHLIGHT_LIMIT - 1}`);
  });

  it("honours an explicit smaller limit, taking the top scorers", () => {
    expect(
      selectDistinctiveTerms(
        vocab(["a", 0.1], ["b", 0.9], ["c", 0.5], ["d", 0.7]),
        2,
      ),
    ).toEqual(["b", "d"]);
  });

  it("returns everything when the vocab is shorter than the limit", () => {
    expect(selectDistinctiveTerms(vocab(["a", 0.1], ["b", 0.9]))).toEqual([
      "b",
      "a",
    ]);
  });

  it("does not mutate the input array", () => {
    const input = vocab(["a", 0.1], ["b", 0.9]);
    const snapshot = [...input];
    selectDistinctiveTerms(input);
    expect(input).toEqual(snapshot);
  });
});
