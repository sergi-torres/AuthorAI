/**
 * Types derived from docs/api_contract.yaml.
 * AuthorSummary mirrors the GET /api/authors list item exactly.
 * AuthorCardData extends it with presentation-only fields that are NOT in the API response.
 */

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
