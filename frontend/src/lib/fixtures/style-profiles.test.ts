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

/**
 * Measured from the seeded corpus on 2026-07-29 (the profiles then in the
 * database), NOT the estimates in docs/style_features.md §7.
 *
 * Those estimates were never checked against the extractors and are wrong on
 * almost every metric — §7 predicts hapax_ratio 0.38-0.44 for Austen where the
 * pipeline measures 0.695, and first_person_ratio 0.5-3.0 where it measures
 * 20.9. Fixtures built to match the estimates therefore rendered a radar no
 * real author could produce. Correcting §7 itself needs a decision_log entry
 * (it is a governing document) and is tracked separately.
 *
 * Bands are the measured value +/-8% (or +/-0.04 for sub-unit ratios): wide
 * enough to survive a recompute, tight enough to catch a regression.
 */
const EXPECTED_RANGES: Record<string, Record<string, Range>> = {
  austen: {
    mattr_500: [0.494, 0.574],
    avg_word_length: [3.995, 4.689],
    hapax_ratio: [0.655, 0.735],
    avg_sentence_length_tokens: [27.587, 32.385],
    std_sentence_length_tokens: [20.529, 24.099],
    subordination_ratio: [1.669, 1.959],
    noun_to_verb_ratio: [1.059, 1.243],
    passive_voice_ratio: [0.126, 0.206],
    dialogue_ratio: [0.269, 0.349],
    first_person_ratio: [19.257, 22.605],
  },
  dickens: {
    mattr_500: [0.489, 0.569],
    avg_word_length: [3.856, 4.526],
    hapax_ratio: [0.654, 0.734],
    avg_sentence_length_tokens: [24.839, 29.159],
    std_sentence_length_tokens: [17.855, 20.961],
    subordination_ratio: [1.424, 1.672],
    noun_to_verb_ratio: [1.092, 1.282],
    passive_voice_ratio: [0.075, 0.155],
    dialogue_ratio: [0.31, 0.39],
    first_person_ratio: [27.482, 32.262],
  },
  poe: {
    mattr_500: [0.52, 0.6],
    avg_word_length: [4.122, 4.838],
    hapax_ratio: [0.708, 0.788],
    avg_sentence_length_tokens: [28.41, 33.35],
    std_sentence_length_tokens: [19.24, 22.586],
    subordination_ratio: [1.273, 1.495],
    noun_to_verb_ratio: [1.713, 2.011],
    passive_voice_ratio: [0.148, 0.228],
    dialogue_ratio: [0.205, 0.285],
    first_person_ratio: [22.779, 26.741],
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
