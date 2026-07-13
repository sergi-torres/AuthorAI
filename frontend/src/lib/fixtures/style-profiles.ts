/**
 * Typed StyleProfile fixtures for the three seed authors.
 * Used as a demo-safe fallback when the backend style-profile endpoint is
 * unavailable (network error / not yet implemented). This mirrors the
 * API-with-seed-fallback pattern in lib/authors.ts.
 *
 * IMPORTANT: These are presentation seed data for development and demos only.
 * - They are NOT used when the live API returns a real 404 (not-computed state).
 * - They are ONLY substituted on network failure (fetch throws / non-404 HTTP error).
 * - Values are plausible but representative of each author's style — they are
 *   intentionally distinct so the radar chart reads clearly.
 * - The §8.6 honesty rule does not apply here (this is not a fit score).
 *
 * Centroids are spaced apart in UMAP space so the scatter plot is readable:
 *   Austen → upper-right quadrant
 *   Dickens → lower-left quadrant
 *   Poe → lower-right quadrant (more solitary, high spread)
 */
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
      // High vocabulary richness — Austen's controlled irony uses varied word choice
      mattr_500: 0.72,
      // Moderate word length — elegant but not Latinate
      avg_word_length: 4.6,
      // Low hapax ratio — she repeats signature words across novels
      hapax_ratio: 0.18,
    },
    syntactic: {
      // Moderate sentence length — balanced, well-constructed sentences
      avg_sentence_length_tokens: 22.0,
      std_sentence_length_tokens: 9.5,
      // High subordination — complex nested clauses
      subordination_ratio: 0.41,
      passive_voice_ratio: 0.08,
      noun_to_verb_ratio: 1.6,
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
      // Low dialogue ratio — social drama told through narration
      dialogue_ratio: 0.22,
      // Low first-person ratio — third-person narration
      first_person_ratio: 0.04,
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
      // Moderate-high vocabulary richness — broad range of registers
      mattr_500: 0.68,
      // Slightly elevated — vivid, specific nouns
      avg_word_length: 4.9,
      // Higher hapax ratio — inventive coinages and character names
      hapax_ratio: 0.31,
    },
    syntactic: {
      // Longer sentences — sweeping Victorian prose
      avg_sentence_length_tokens: 31.0,
      std_sentence_length_tokens: 14.2,
      // Moderate subordination
      subordination_ratio: 0.35,
      passive_voice_ratio: 0.12,
      noun_to_verb_ratio: 1.8,
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
      // Higher dialogue ratio — memorable character voices
      dialogue_ratio: 0.38,
      // Low — third-person omniscient with satirical intrusions
      first_person_ratio: 0.06,
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
      // Lower richness per window — intense, obsessive repetition
      mattr_500: 0.58,
      // Longer words — Gothic Latinate vocabulary
      avg_word_length: 5.3,
      // High hapax ratio — idiosyncratic, rare word choices
      hapax_ratio: 0.44,
    },
    syntactic: {
      // Shorter, punchy sentences — dread through brevity
      avg_sentence_length_tokens: 17.0,
      std_sentence_length_tokens: 10.8,
      // Lower subordination — direct, percussive rhythm
      subordination_ratio: 0.24,
      passive_voice_ratio: 0.15,
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
      dialogue_ratio: 0.09,
      // High first-person — unreliable narrator confessional style
      first_person_ratio: 0.52,
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
