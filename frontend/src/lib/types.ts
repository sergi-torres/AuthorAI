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
