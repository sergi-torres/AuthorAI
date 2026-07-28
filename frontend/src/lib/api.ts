/**
 * Typed client for the AutorIA REST API (docs/api_contract.yaml).
 * All response shapes mirror the contract via lib/types.ts — never invent fields here.
 */
import type {
  AuthorSummary,
  DocumentUploadAccepted,
  GenerateRequest,
  GenerateResponse,
  StyleProfile,
  VerifyRequest,
  VerifyResponse,
  VerifyErrorCode,
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

/**
 * Thrown when the request never reached the backend (fetch itself rejected:
 * DNS failure, connection refused, TLS error, offline browser).
 * The backend gave NO answer, so the client knows nothing about the resource.
 */
export class NetworkError extends Error {
  readonly status = null;
  constructor(label: string, cause: unknown) {
    super(
      `${label} failed to reach the API: ${
        cause instanceof Error ? cause.message : String(cause)
      }`,
      { cause },
    );
    this.name = "NetworkError";
  }
}

/**
 * Thrown for HTTP 5xx — the backend was reached but failed to answer the
 * question. Like NetworkError (and unlike a 404) this leaves the state of the
 * resource unknown.
 */
export class ServerError extends Error {
  readonly status: number;
  constructor(label: string, status: number) {
    super(`${label} failed with status ${status}`);
    this.name = "ServerError";
    this.status = status;
  }
}

/**
 * The single predicate behind the fixture-substitution policy
 * (decision_log 2026-07-27 · option A · design-system.md §8.6 + §9:276).
 *
 * True ONLY for failures that leave the real answer unknown — a transport
 * failure or a 5xx. Those are the only cases in which demo fixtures may stand
 * in for a real StyleProfile.
 *
 * A 404 is a definitive answer ("this author has no computed profile") and is
 * therefore NOT eligible: it must degrade to the neutral empty state. Any other
 * 4xx is a client-side bug and is not eligible either.
 */
export function isFixtureEligibleError(err: unknown): boolean {
  return err instanceof NetworkError || err instanceof ServerError;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * fetch() wrapper that turns a rejected fetch into a typed NetworkError so
 * callers can tell "never reached the backend" from "the backend said no".
 * AbortError is re-thrown untouched — generateText's timeout contract depends
 * on its `name`.
 */
async function fetchOrThrow(
  url: string,
  init: RequestInit | undefined,
  label: string,
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") throw err;
    throw new NetworkError(label, err);
  }
}

async function parseOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    if (res.status >= 500) {
      throw new ServerError(label, res.status);
    }
    throw new Error(`${label} failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** GET /api/authors — preloaded authors plus any added via document upload. */
export async function listAuthors(): Promise<AuthorSummary[]> {
  const label = "GET /api/authors";
  const res = await fetchOrThrow(
    `${API_BASE}/api/authors`,
    { cache: "no-store" },
    label,
  );
  return parseOrThrow<AuthorSummary[]>(res, label);
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
  const label = "POST /api/authors/{id}/documents";
  const res = await fetchOrThrow(
    `${API_BASE}/api/authors/${encodeURIComponent(authorId)}/documents`,
    { method: "POST", body: form },
    label,
  );
  return parseOrThrow<DocumentUploadAccepted>(res, label);
}

/**
 * GET /api/authors/{author_id}/style-profile — Style DNA fingerprint v1.0.
 *
 * Error taxonomy — callers MUST branch on it (see isFixtureEligibleError):
 *   404          → NotFoundError  (definitive: no profile → neutral empty state)
 *   5xx          → ServerError    (unknown: error state, fixture-eligible)
 *   fetch throws → NetworkError   (unknown: error state, fixture-eligible)
 *   other 4xx    → plain Error    (client bug: error state, NOT fixture-eligible)
 */
export async function getStyleProfile(authorId: string): Promise<StyleProfile> {
  const label = `GET /api/authors/${authorId}/style-profile`;
  const res = await fetchOrThrow(
    `${API_BASE}/api/authors/${encodeURIComponent(authorId)}/style-profile`,
    { cache: "no-store" },
    label,
  );
  if (res.status === 404) {
    throw new NotFoundError(label);
  }
  return parseOrThrow<StyleProfile>(res, label);
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

/**
 * POST /api/generate — run vanilla + AutorIA generation in parallel on the backend.
 *
 * Uses AbortController with a 10 s timeout so a hanging Watsonx call resolves
 * to a timeout state rather than an infinite spinner (design-system §1 / §7.4).
 *
 * Return contract:
 *   200       → resolves with GenerateResponse
 *   AbortError → throws with name "AbortError" (timeout path)
 *   other      → throws a plain Error (error path)
 */
export async function generateText(
  authorId: string,
  prompt: string,
): Promise<GenerateResponse> {
  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), 10_000);

  try {
    const body: GenerateRequest = { author_id: authorId, prompt };
    const label = "POST /api/generate";
    const res = await fetchOrThrow(
      `${API_BASE}/api/generate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      },
      label,
    );
    return parseOrThrow<GenerateResponse>(res, label);
  } finally {
    clearTimeout(timerId);
  }
}

/**
 * POST /api/passports/verify — verify a compact JWS Authorship Passport.
 *
 * Per contract: verification always returns HTTP 200 (valid or invalid).
 * Non-200 responses (5xx, network failure) are caught and synthesised into
 * a VerifyResponse with valid=false and a jwks_unavailable error so the
 * caller always gets a typed result — never a thrown exception.
 *
 * The UI MUST NOT parse the JWS itself — only call this function.
 */
export async function verifyPassport(
  jwsToken: string,
): Promise<VerifyResponse> {
  const unreachable = (detail: string): VerifyResponse => ({
    valid: false,
    payload: null,
    errors: [
      {
        code: "jwks_unavailable" satisfies VerifyErrorCode,
        message: `Network error: ${detail}`,
      },
    ],
  });

  try {
    const body: VerifyRequest = { jws_token: jwsToken };
    const res = await fetch(`${API_BASE}/api/passports/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      return unreachable(`HTTP ${res.status}`);
    }
    return res.json() as Promise<VerifyResponse>;
  } catch (err) {
    const detail = err instanceof Error ? err.message : "unknown";
    return unreachable(detail);
  }
}
