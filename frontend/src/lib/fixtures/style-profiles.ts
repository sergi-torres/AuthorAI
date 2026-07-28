/**
 * Typed StyleProfile fixtures for the three seed authors.
 *
 * WHEN THEY ARE USED (decision_log 2026-07-27 · option A — this header describes
 * the behaviour the code actually implements; do not edit one without the other):
 * - ONLY when the backend never gave an answer: a transport failure
 *   (`NetworkError`) or an HTTP 5xx (`ServerError`). See `isFixtureEligibleError`
 *   in `lib/api.ts`, which is the single gate — every caller goes through
 *   `fixtureProfileForError` below.
 * - NOT on a real 404. A 404 means "this author has no computed StyleProfile",
 *   which is a definitive answer and must degrade to the neutral empty state
 *   (design-system.md §9:276 and the §8.6 honesty rule). If the DB is unseeded
 *   the Style DNA panel renders EMPTY — that is the intended, accepted outcome;
 *   seeding is what fixes it, not a fixture.
 * - NOT on any other 4xx (a client bug must surface as an error, not as data).
 *
 * WHAT THEY ARE: presentation seed data for development and demos — hand-written
 * plausible values, never measurements. Every metric listed in
 * `docs/style_features.md` §7 is kept inside that document's expected range for
 * its author, so a fixture that does reach the screen is at least stylometrically
 * plausible; `style-profiles.test.ts` enforces this. Comments below explain each
 * value in the terms of that document, which is the governing source — where the
 * literary intuition and the table disagreed, the table won.
 *
 * Units follow the contract and `docs/style_features.md`:
 * `first_person_ratio` is per 1,000 tokens (§3.4), not a [0,1] fraction.
 *
 * Centroids are spaced apart in UMAP space so the scatter plot is readable:
 *   Austen → upper-right quadrant
 *   Dickens → lower-left quadrant
 *   Poe → lower-right quadrant (more solitary, high spread)
 */
import { isFixtureEligibleError } from "@/lib/api";
import type { StyleProfile } from "@/lib/types";

export const FIXTURE_STYLE_PROFILES: Readonly<Record<string, StyleProfile>> = {
  austen: {
    schema_version: "1.0",
    author_id: "austen",
    computed_at: "2026-07-12T10:00:00Z",
    corpus_stats: {
      n_documents: 3,
      n_tokens: 412_000,
      n_sentences: 21_800,
    },
    lexical: {
      // Mid MATTR — controlled, precise diction rather than a broad vocabulary
      mattr_500: 0.65,
      // Shortest of the three — plain Anglo-Saxon register, not Latinate
      avg_word_length: 4.25,
      // Lowest hapax of the three — signature words recur across novels
      hapax_ratio: 0.41,
    },
    syntactic: {
      // Balanced, well-constructed sentences
      avg_sentence_length_tokens: 25.0,
      // Least variable of the three — even, measured rhythm
      std_sentence_length_tokens: 12.0,
      subordination_ratio: 0.32,
      passive_voice_ratio: 0.09,
      noun_to_verb_ratio: 1.8,
    },
    stylistic: {
      punct_distribution: {
        ",": 0.48,
        ".": 0.22,
        ";": 0.14,
        ":": 0.06,
        "?": 0.08,
        "!": 0.02,
      },
      pos_distribution: {
        NOUN: 0.22,
        VERB: 0.14,
        ADJ: 0.12,
        ADV: 0.08,
        PUNCT: 0.18,
      },
      // Highest dialogue of the three — social sparring drives the novels (§3.3)
      dialogue_ratio: 0.33,
      // Near-zero first person — third-person omniscient narration (per 1k tokens)
      first_person_ratio: 1.8,
    },
    distinctive_vocab: [
      { term: "elegance", score: 0.85 },
      { term: "propriety", score: 0.82 },
      { term: "sensibility", score: 0.79 },
    ],
    // 768 floats — not used in UI; placeholder filled with zeros
    semantic_centroid: Array(768).fill(0),
    embedding_umap_2d: {
      // Upper-right: social, ordered, restrained
      centroid: [2.8, 3.4],
      spread: 0.6,
    },
  },

  dickens: {
    schema_version: "1.0",
    author_id: "dickens",
    computed_at: "2026-07-12T10:00:00Z",
    corpus_stats: {
      n_documents: 3,
      n_tokens: 630_000,
      n_sentences: 28_500,
    },
    lexical: {
      // Lowest MATTR — sprawling serial prose reuses its own idiom heavily
      mattr_500: 0.61,
      // Slightly elevated — vivid, specific nouns
      avg_word_length: 4.85,
      // Mid hapax — inventive coinages and character names
      hapax_ratio: 0.43,
    },
    syntactic: {
      // Longer sentences — sweeping Victorian prose
      avg_sentence_length_tokens: 28.5,
      std_sentence_length_tokens: 15.0,
      // Highest subordination — piled-up clauses and asides
      subordination_ratio: 0.39,
      passive_voice_ratio: 0.11,
      noun_to_verb_ratio: 1.9,
    },
    stylistic: {
      punct_distribution: {
        ",": 0.42,
        ".": 0.24,
        ";": 0.1,
        ":": 0.08,
        "?": 0.06,
        "!": 0.1,
      },
      pos_distribution: {
        NOUN: 0.24,
        VERB: 0.12,
        ADJ: 0.15,
        ADV: 0.1,
        PUNCT: 0.16,
      },
      // Memorable character voices, but less dialogue-driven than Austen (§3.3)
      dialogue_ratio: 0.24,
      // Some first person — satirical narrator intrusions (per 1k tokens)
      first_person_ratio: 6.5,
    },
    distinctive_vocab: [
      { term: "countenance", score: 0.88 },
      { term: "wretched", score: 0.84 },
      { term: "miserable", score: 0.8 },
    ],
    semantic_centroid: Array(768).fill(0),
    embedding_umap_2d: {
      // Lower-left: social, expansive, energetic
      centroid: [-2.1, -2.6],
      spread: 0.9,
    },
  },

  poe: {
    schema_version: "1.0",
    author_id: "poe",
    computed_at: "2026-07-12T10:00:00Z",
    corpus_stats: {
      n_documents: 15,
      n_tokens: 185_000,
      n_sentences: 7_200,
    },
    lexical: {
      // Highest MATTR — short tales, each with its own dense lexicon
      mattr_500: 0.7,
      // Longest words — Gothic Latinate vocabulary
      avg_word_length: 5.3,
      // Highest hapax — idiosyncratic, rare word choices
      hapax_ratio: 0.52,
    },
    syntactic: {
      // Long, unspooling sentences with the widest variance of the three
      avg_sentence_length_tokens: 29.0,
      std_sentence_length_tokens: 17.0,
      // Lowest subordination — direct, percussive rhythm
      subordination_ratio: 0.27,
      // Highest passive voice — the narrator as the thing acted upon
      passive_voice_ratio: 0.23,
      noun_to_verb_ratio: 1.4,
    },
    stylistic: {
      punct_distribution: {
        ",": 0.38,
        ".": 0.28,
        ";": 0.08,
        ":": 0.06,
        "?": 0.06,
        "!": 0.14,
      },
      pos_distribution: {
        NOUN: 0.2,
        VERB: 0.16,
        ADJ: 0.14,
        ADV: 0.12,
        PUNCT: 0.17,
      },
      // Very low dialogue — interior monologue and narration dominate
      dialogue_ratio: 0.1,
      // Sharpest Poe discriminator — confessional narrator (per 1k tokens, §3.4)
      first_person_ratio: 24.0,
    },
    distinctive_vocab: [
      { term: "phantasm", score: 0.92 },
      { term: "melancholy", score: 0.89 },
      { term: "pallid", score: 0.87 },
    ],
    semantic_centroid: Array(768).fill(0),
    embedding_umap_2d: {
      // Lower-right: solitary, dark, intense
      centroid: [3.1, -3.2],
      spread: 1.2,
    },
  },
};

/**
 * The one place where a fixture may be substituted for a real StyleProfile.
 *
 * Returns the fixture for `authorId` ONLY when `err` is fixture-eligible —
 * a NetworkError or a 5xx ServerError (`lib/api.ts::isFixtureEligibleError`).
 * Returns `undefined` for a NotFoundError (real 404), for any other 4xx, and
 * for authors with no fixture; callers turn that `undefined` into their own
 * neutral empty state (an EmptyState in the panel, `[]` for the highlights).
 *
 * Pure and total — no throwing, no I/O — so the decision itself is unit-tested
 * without mounting a component (see `style-profiles.test.ts`).
 */
export function fixtureProfileForError(
  authorId: string,
  err: unknown,
): StyleProfile | undefined {
  if (!isFixtureEligibleError(err)) return undefined;
  return FIXTURE_STYLE_PROFILES[authorId];
}
