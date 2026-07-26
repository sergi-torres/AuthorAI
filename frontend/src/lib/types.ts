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

/** Mirrors AuthorVoiceRef in api_contract.yaml — PassportPayload.author_voice. */
export interface AuthorVoiceRef {
  id: string;
  /** SHA-256 hash of the style profile used. Pattern: ^sha256:[a-f0-9]{64}$ */
  style_profile_hash: string;
  style_profile_version: string;
}

/** Mirrors GenerationMetadata in api_contract.yaml — PassportPayload.generation. */
export interface GenerationMetadata {
  model_provider: string;
  model_id: string;
  /** SHA-256 of user prompt (privacy-preserving). Pattern: ^sha256:[a-f0-9]{64}$ */
  user_prompt_hash: string;
  /** SHA-256 of AutorIA output text. Pattern: ^sha256:[a-f0-9]{64}$ */
  output_hash: string;
  output_length_tokens: number;
}

/** Mirrors RagSourceRef in api_contract.yaml — PassportPayload.rag_sources items. */
export interface RagSourceRef {
  doc_id: string;
  chunk_id: number;
  /** SHA-256 of the retrieved chunk. Pattern: ^sha256:[a-f0-9]{64}$ */
  snippet_hash: string;
}

/** Mirrors ContributionBreakdown in api_contract.yaml — PassportPayload.contribution. */
export interface ContributionBreakdown {
  human_pct: number;
  ai_pct: number;
  note: string;
}

/**
 * Mirrors PassportPayload v1.0 in api_contract.yaml — the unsigned body inside
 * PassportEnvelope.json_payload. See docs/MVP.md §4.4.
 */
export interface PassportPayload {
  /** Always "1.0" for this version of the schema. */
  schema_version: "1.0";
  /** UUID identifying this specific passport. */
  passport_id: string;
  /** ISO 8601 date-time of generation. */
  generated_at: string;
  /** Reference to the author voice used. */
  author_voice: AuthorVoiceRef;
  /** Metadata about the generation run. */
  generation: GenerationMetadata;
  /** RAG chunks that influenced the output. */
  rag_sources: RagSourceRef[];
  /** Human vs AI contribution breakdown. */
  contribution: ContributionBreakdown;
  /** Style fit vs target StyleProfile, integer 0–100. */
  fit_score: number;
  /** URL for verifying this passport. */
  verifier_url: string;
}

/**
 * Mirrors PassportEnvelope in api_contract.yaml — the wrapper returned by
 * POST /api/generate inside GenerateResponse.passport.
 */
export interface PassportEnvelope {
  /** Compact JWS (ES256) over json_payload. */
  jws_token: string;
  json_payload: PassportPayload;
}

/**
 * Mirrors GenerateResponse in api_contract.yaml — 200 from POST /api/generate.
 */
export interface GenerateResponse {
  vanilla: GenerationOutput;
  autoria: GenerationOutput;
  /** Null when the backend hasn't implemented signing yet (see backend #26). */
  passport: PassportEnvelope | null;
}
