/**
 * Tests for the StyleProfile fixtures and the rule that decides when they may
 * be substituted for a real profile.
 *
 * Vitest, environment "node" — pure modules only, no component mounting
 * (frontend testing convention, decision_log 2026-07-21).
 *
 * Covers:
 *   1. Fixture-substitution policy (decision_log 2026-07-27, option A):
 *      NotFoundError → no fixture; NetworkError / 5xx ServerError → fixture.
 *   2. Every fixture metric falls inside the expected range for its author
 *      in docs/style_features.md §7.
 */

import { describe, it, expect } from "vitest";
import { NotFoundError, NetworkError, ServerError } from "@/lib/api";
import {
  FIXTURE_STYLE_PROFILES,
  fixtureProfileForError,
} from "@/lib/fixtures/style-profiles";
import type { StyleProfile } from "@/lib/types";

// ---------------------------------------------------------------------------
// 1. Fixture-substitution policy — option A
// ---------------------------------------------------------------------------

describe("fixtureProfileForError — option A substitution rule", () => {
  const label = "GET /api/authors/austen/style-profile";

  it("does NOT substitute a fixture on a real 404, even for a seed author", () => {
    // The load point must degrade to its neutral empty state (panel: EmptyState,
    // highlights: []). design-system.md §9:276 + §8.6.
    expect(
      fixtureProfileForError("austen", new NotFoundError(label)),
    ).toBeUndefined();
  });

  it("substitutes the fixture when the API was unreachable (network failure)", () => {
    const profile = fixtureProfileForError(
      "austen",
      new NetworkError(label, new TypeError("fetch failed")),
    );
    expect(profile).toBe(FIXTURE_STYLE_PROFILES.austen);
  });

  it("substitutes the fixture on a 5xx", () => {
    const profile = fixtureProfileForError(
      "dickens",
      new ServerError(label, 503),
    );
    expect(profile).toBe(FIXTURE_STYLE_PROFILES.dickens);
  });

  it("does NOT substitute on a non-404 4xx (a client bug is not a data gap)", () => {
    expect(
      fixtureProfileForError(
        "poe",
        new Error(`${label} failed with status 422`),
      ),
    ).toBeUndefined();
  });

  it("does NOT substitute for an author with no fixture, even on a network failure", () => {
    expect(
      fixtureProfileForError(
        "live-uploaded-author",
        new NetworkError(label, new TypeError("fetch failed")),
      ),
    ).toBeUndefined();
  });

  it("does NOT substitute for a non-Error rejection value", () => {
    expect(fixtureProfileForError("austen", "boom")).toBeUndefined();
    expect(fixtureProfileForError("austen", undefined)).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// 2. Fixture values vs docs/style_features.md §7 expected ranges
// ---------------------------------------------------------------------------

type Range = readonly [number, number];

/** Verbatim from docs/style_features.md §7 "Expected ranges per author". */
const EXPECTED_RANGES: Record<string, Record<string, Range>> = {
  austen: {
    mattr_500: [0.62, 0.68],
    avg_word_length: [4.0, 4.5],
    hapax_ratio: [0.38, 0.44],
    avg_sentence_length_tokens: [22, 28],
    std_sentence_length_tokens: [10, 14],
    subordination_ratio: [0.28, 0.36],
    noun_to_verb_ratio: [1.6, 2.0],
    passive_voice_ratio: [0.06, 0.12],
    dialogue_ratio: [0.28, 0.38],
    first_person_ratio: [0.5, 3.0],
  },
  dickens: {
    mattr_500: [0.58, 0.64],
    avg_word_length: [4.6, 5.1],
    hapax_ratio: [0.4, 0.46],
    avg_sentence_length_tokens: [25, 32],
    std_sentence_length_tokens: [13, 17],
    subordination_ratio: [0.34, 0.44],
    noun_to_verb_ratio: [1.7, 2.1],
    passive_voice_ratio: [0.08, 0.14],
    dialogue_ratio: [0.2, 0.28],
    first_person_ratio: [4.0, 9.0],
  },
  poe: {
    mattr_500: [0.66, 0.73],
    avg_word_length: [5.0, 5.6],
    hapax_ratio: [0.48, 0.56],
    avg_sentence_length_tokens: [24, 34],
    std_sentence_length_tokens: [14, 20],
    subordination_ratio: [0.22, 0.32],
    noun_to_verb_ratio: [1.2, 1.6],
    passive_voice_ratio: [0.18, 0.28],
    dialogue_ratio: [0.05, 0.14],
    first_person_ratio: [18.0, 30.0],
  },
};

/**
 * Flattens the metric blocks into the flat feature names §7 uses. Only the
 * numeric stylistic fields are lifted — punct/pos distributions have no §7 row.
 */
function measuredFeatures(profile: StyleProfile): Record<string, number> {
  return {
    ...profile.lexical,
    ...profile.syntactic,
    dialogue_ratio: profile.stylistic.dialogue_ratio,
    first_person_ratio: profile.stylistic.first_person_ratio,
  };
}

describe("FIXTURE_STYLE_PROFILES — values inside docs/style_features.md §7 ranges", () => {
  it("covers exactly the three seed authors named in §7", () => {
    expect(Object.keys(FIXTURE_STYLE_PROFILES).sort()).toEqual(
      Object.keys(EXPECTED_RANGES).sort(),
    );
  });

  for (const [authorId, ranges] of Object.entries(EXPECTED_RANGES)) {
    describe(authorId, () => {
      const values = measuredFeatures(FIXTURE_STYLE_PROFILES[authorId]);

      for (const [feature, [min, max]] of Object.entries(ranges)) {
        it(`${feature} is within ${min}–${max}`, () => {
          const value = values[feature];
          expect(value, `${feature} missing from fixture`).toBeTypeOf("number");
          expect(value).toBeGreaterThanOrEqual(min);
          expect(value).toBeLessThanOrEqual(max);
        });
      }
    });
  }
});
