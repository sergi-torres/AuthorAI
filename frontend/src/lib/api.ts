/**
 * Typed client for the AutorIA REST API (docs/api_contract.yaml).
 * All response shapes mirror the contract via lib/types.ts — never invent fields here.
 */
import type {
  AuthorSummary,
  DocumentUploadAccepted,
  StyleProfile,
} from "@/lib/types";

/**
 * Thrown when a style-profile request returns HTTP 404.
 * Per contract: 404 means "author unknown OR StyleProfile not yet computed"
 * — this is an EMPTY state, not a server error. Callers must distinguish it
 * from NetworkError / 5xx (which are error states with retry).
 */
export class NotFoundError extends Error {
  readonly status = 404 as const;
  constructor(label: string) {
    super(`${label} returned 404 (not found or not yet computed)`);
    this.name = "NotFoundError";
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    throw new Error(`${label} failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** GET /api/authors — preloaded authors plus any added via document upload. */
export async function listAuthors(): Promise<AuthorSummary[]> {
  const res = await fetch(`${API_BASE}/api/authors`, { cache: "no-store" });
  return parseOrThrow<AuthorSummary[]>(res, "GET /api/authors");
}

/**
 * POST /api/authors/{author_id}/documents — multipart .txt/.md upload (202 async).
 *
 * CONTRACT GAP: the API has no create-author endpoint, yet listAuthors is
 * documented as returning authors "added via document upload". The add-author
 * flow therefore posts to a fresh slug and expects the backend to auto-create
 * it; the contract's 404 for unknown author_id contradicts this. Flagged for
 * the Sprint 1 contract pairing session.
 */
export async function uploadAuthorDocument(
  authorId: string,
  file: File,
  title?: string,
): Promise<DocumentUploadAccepted> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  const res = await fetch(
    `${API_BASE}/api/authors/${encodeURIComponent(authorId)}/documents`,
    { method: "POST", body: form },
  );
  return parseOrThrow<DocumentUploadAccepted>(
    res,
    "POST /api/authors/{id}/documents",
  );
}

/**
 * GET /api/authors/{author_id}/style-profile — Style DNA fingerprint v1.0.
 *
 * Throws NotFoundError for HTTP 404 (author unknown or profile not yet computed).
 * Throws a plain Error for any other non-ok status (5xx, network failure, etc.).
 */
export async function getStyleProfile(authorId: string): Promise<StyleProfile> {
  const res = await fetch(
    `${API_BASE}/api/authors/${encodeURIComponent(authorId)}/style-profile`,
    { cache: "no-store" },
  );
  if (res.status === 404) {
    throw new NotFoundError(`GET /api/authors/${authorId}/style-profile`);
  }
  return parseOrThrow<StyleProfile>(
    res,
    `GET /api/authors/${authorId}/style-profile`,
  );
}

/** Derives a URL-safe author slug from a display name (client-side id proposal). */
export function slugifyAuthorName(name: string): string {
  return name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
