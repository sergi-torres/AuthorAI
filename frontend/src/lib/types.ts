/**
 * Types derived from docs/api_contract.yaml.
 * AuthorSummary mirrors the GET /api/authors list item exactly.
 * AuthorCardData extends it with presentation-only fields that are NOT in the API response.
 */

/** Mirrors CorpusStats in api_contract.yaml — StyleProfile.corpus_stats. */
export interface CorpusStats {
  /** Number of documents in the corpus. */
  n_documents: number;
  /** Total token count across all documents. */
  n_tokens: number;
  /** Total sentence count across all documents. */
  n_sentences: number;
}

/** Mirrors LexicalFeatures in api_contract.yaml — StyleProfile.lexical. */
export interface LexicalFeatures {
  /** Moving Average TTR (window 500). Native range [0, 1]. */
  mattr_500: number;
  /** Mean character count per word. */
  avg_word_length: number;
  /** Fraction of word types that appear only once (hapax legomena). Native range [0, 1]. */
  hapax_ratio: number;
}

/** Mirrors SyntacticFeatures in api_contract.yaml — StyleProfile.syntactic. */
export interface SyntacticFeatures {
  /** Mean number of tokens per sentence. */
  avg_sentence_length_tokens: number;
  /** Standard deviation of sentence length in tokens. */
  std_sentence_length_tokens: number;
  /** Fraction of clauses that are subordinate. Native range [0, 1]. */
  subordination_ratio: number;
  /** Fraction of verb phrases in passive voice. Native range [0, 1]. */
  passive_voice_ratio: number;
  /** Ratio of nouns to verbs. */
  noun_to_verb_ratio: number;
}

/** Mirrors StylisticFeatures in api_contract.yaml — StyleProfile.stylistic. */
export interface StylisticFeatures {
  /** Relative frequency per punctuation mark. */
  punct_distribution: Record<string, number>;
  /** Relative frequency per POS tag (spaCy labels). */
  pos_distribution: Record<string, number>;
  /** Fraction of sentences that are dialogue (heuristic). Native range [0, 1]. */
  dialogue_ratio: number;
  /** Fraction of sentences with first-person pronouns (heuristic). Native range [0, 1]. */
  first_person_ratio: number;
}

/** Mirrors EmbeddingUmap2d in api_contract.yaml — StyleProfile.embedding_umap_2d. */
export interface EmbeddingUmap2d {
  /** UMAP 2D coordinates for the author cluster center: [x, y]. */
  centroid: [number, number];
  /** Spread radius of the cluster in UMAP space. */
  spread: number;
}

/**
 * Mirrors StyleProfile v1.0 in api_contract.yaml.
 * GET /api/authors/{author_id}/style-profile
 */
export interface StyleProfile {
  /** Always "1.0" for this version of the schema. */
  schema_version: "1.0";
  /** Stable author identifier matching AuthorSummary.id. */
  author_id: string;
  /** ISO 8601 date-time when this profile was last computed. */
  computed_at: string;
  /** Corpus size statistics. */
  corpus_stats: CorpusStats;
  /** Lexical richness features. */
  lexical: LexicalFeatures;
  /** Syntactic complexity features. */
  syntactic: SyntacticFeatures;
  /** Stylistic / rhetorical features. */
  stylistic: StylisticFeatures;
  /** Top distinctive vocabulary items (TF-IDF ranked). Rendered as a top-10 table in the Style DNA panel. */
  distinctive_vocab: DistinctiveTerm[];
  /**
   * 768-dimensional mean embedding vector.
   * CONTRACT: Never send this array to any chart or client-rendered list —
   * it is 768 floats and is not user-meaningful at the UI layer.
   */
  semantic_centroid: number[];
  /** 2D UMAP projection of the cluster centroid and spread radius. */
  embedding_umap_2d: EmbeddingUmap2d;
}

/** Mirrors AuthorSummary in api_contract.yaml — do not add fields here. */
export interface AuthorSummary {
  id: string;
  name: string;
  slug: string;
  has_style_profile: boolean;
  n_documents: number;
}

/** Adds presentation-only seed data (bio) that is not part of the API response. */
export interface AuthorCardData extends AuthorSummary {
  /** Short public-domain bio snippet shown on the selector card. */
  bio: string;
}

/** Mirrors DocumentUploadAccepted in api_contract.yaml — 202 from document upload. */
export interface DocumentUploadAccepted {
  document_id: string;
  /** Async pipeline state; poll style-profile until recomputed. */
  status: "processing";
}

/** Mirrors GenerationOutput in api_contract.yaml — one branch of POST /generate. */
export interface GenerationOutput {
  text: string;
  /** Style fit vs target StyleProfile, integer 0–100. */
  fit_score: number;
  latency_ms: number;
}

/** Mirrors DistinctiveTerm in api_contract.yaml (StyleProfile.distinctive_vocab items). */
export interface DistinctiveTerm {
  term: string;
  /** TF-IDF score vs reference corpus. */
  score: number;
}

/** Mirrors StyleProfileRecomputeAccepted in api_contract.yaml — 202 from POST recompute. */
export interface StyleProfileRecomputeAccepted {
  /** Always "computing" — recompute is async; poll GET style-profile for completion. */
  status: "computing";
  /** Rough wall-clock estimate in seconds: max(30, n_tokens // 2000). */
  estimated_seconds: number;
}

/** Mirrors GenerateRequest in api_contract.yaml — body for POST /api/generate. */
export interface GenerateRequest {
  /** Target author voice (slug). */
  author_id: string;
  /** User creative prompt (English). Max 4000 chars per contract. */
  prompt: string;
}

// ---------------------------------------------------------------------------
// Authorship Passport types — mirrors PassportPayload and related schemas
// in api_contract.yaml (PassportEnvelope, AuthorVoiceRef, GenerationMetadata,
// RagSourceRef, ContributionBreakdown) plus the verify endpoint types.
// ---------------------------------------------------------------------------

/** Mirrors AuthorVoiceRef in api_contract.yaml. */
export interface AuthorVoiceRef {
  /** Author slug (e.g. "dickens") — matches authors.slug. */
  id: string;
  /** SHA-256 hash of the StyleProfile used (format: sha256:<64 hex chars>). */
  style_profile_hash: string;
  /** StyleProfile schema version (e.g. "1.0"). */
  style_profile_version: string;
}

/** Mirrors GenerationMetadata in api_contract.yaml. */
export interface GenerationMetadata {
  /** e.g. "ibm/watsonx" */
  model_provider: string;
  /** e.g. "meta-llama/llama-3-3-70b-instruct" */
  model_id: string;
  /** SHA-256 of the user prompt — privacy-preserving, never raw text. */
  user_prompt_hash: string;
  /** SHA-256 of the AutorIA output text — tamper-evidence. */
  output_hash: string;
  /** Token count of the generated output. */
  output_length_tokens: number;
}

/** Mirrors RagSourceRef in api_contract.yaml. */
export interface RagSourceRef {
  /** Source document identifier / slug. */
  doc_id: string;
  /** Ordinal chunk index within the document. */
  chunk_id: number;
  /** SHA-256 of the retrieved chunk text. */
  snippet_hash: string;
}

/** Mirrors ContributionBreakdown in api_contract.yaml. */
export interface ContributionBreakdown {
  /** Percentage of human contribution (0–100). v1 always 0. */
  human_pct: number;
  /** Percentage of AI contribution (0–100). v1 always 100. */
  ai_pct: number;
  /** Optional free-text clarification. */
  note?: string;
}

/** Mirrors PassportPayload in api_contract.yaml — the decoded JWS body v1.0. */
export interface PassportPayload {
  schema_version: "1.0";
  /** UUID v4 uniquely identifying this passport. */
  passport_id: string;
  /** ISO-8601 UTC issuance timestamp. */
  generated_at: string;
  author_voice: AuthorVoiceRef;
  generation: GenerationMetadata;
  /** Retrieved passages that conditioned the generation; may be empty. */
  rag_sources: RagSourceRef[];
  contribution: ContributionBreakdown;
  /** Style-fit integer 0–100 vs the target StyleProfile. */
  fit_score: number;
  /** URL of the /verify page. Optional per passport_schema.md §4.1. */
  verifier_url?: string;
}

/** Mirrors PassportEnvelope in api_contract.yaml — field inside GenerateResponse. */
export interface PassportEnvelope {
  /** Compact JWS (ES256) — three base64url segments joined by dots. */
  jws_token: string;
  json_payload: PassportPayload;
}

// ---------------------------------------------------------------------------
// Verify endpoint types (POST /api/passports/verify)
// ---------------------------------------------------------------------------

/**
 * Union of all error codes returned by the verify endpoint.
 * Mirrors VerifyError.code enum in api_contract.yaml.
 */
export type VerifyErrorCode =
  | "invalid_token"
  | "invalid_signature"
  | "unknown_kid"
  | "unsupported_algorithm"
  | "schema_mismatch"
  | "jwks_unavailable";

/** Mirrors VerifyError in api_contract.yaml. */
export interface VerifyError {
  code: VerifyErrorCode;
  /** Backend-provided human-readable message (may differ from UI copy). */
  message: string;
}

/**
 * Mirrors VerifyResponse in api_contract.yaml.
 * Always HTTP 200; valid=false means a crypto/schema failure, not a server error.
 */
export interface VerifyResponse {
  valid: boolean;
  /** Decoded payload when valid; null when signature/schema check failed. */
  payload: PassportPayload | null;
  errors: VerifyError[];
}

/** Mirrors VerifyRequest in api_contract.yaml — body for POST /api/passports/verify. */
export interface VerifyRequest {
  /** Compact serialized JWS from passport.jws_token. */
  jws_token: string;
}

/**
 * Mirrors GenerateResponse in api_contract.yaml — 200 from POST /api/generate.
 * `passport` is now fully typed as PassportEnvelope (narrowed from `unknown` in #19).
 */
export interface GenerateResponse {
  vanilla: GenerationOutput;
  autoria: GenerationOutput;
  passport: PassportEnvelope;
}
