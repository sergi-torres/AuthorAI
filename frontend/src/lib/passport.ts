/**
 * Passport download helper — issue #42.
 *
 * Extracted as a pure function so it can be unit-tested without mounting a
 * React component. GenerateStudio delegates to this function.
 *
 * Behaviour:
 *  - Serialises the FULL envelope (jws_token + json_payload) as pretty-printed
 *    JSON (indent 2). The signature is included on purpose so the downloaded
 *    file is verifiable offline via /verify (POST /api/passports/verify).
 *  - Creates a temporary anchor element, triggers a click, then cleans up.
 *  - Filename: passport-<author_id>.json  (author_id from json_payload.author_voice.id).
 */
import type { PassportEnvelope } from "@/lib/types";

/**
 * Triggers a browser download of the full Authorship Passport envelope
 * (`jws_token` + `json_payload`) as a formatted JSON file named
 * `passport-<author_id>.json`. Keeping the JWS in the file is what makes the
 * artifact tamper-evident and verifiable — a payload-only export could not be
 * checked against the JWKS.
 *
 * The caller is responsible for ensuring `passport` is non-null before calling.
 */
export function downloadPassport(passport: PassportEnvelope): void {
  const authorId = passport.json_payload.author_voice.id;
  const filename = `passport-${authorId}.json`;
  const json = JSON.stringify(passport, null, 2);

  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();

  URL.revokeObjectURL(url);
}

/**
 * Extract the compact JWS token from the text of an uploaded `.json`/`.jws`
 * file — the exact inverse of {@link downloadPassport}.
 *
 * This is the join between the two halves of the MVP §10 Definition of Done
 * ("Passport issued, downloaded, and verifies with a valid signature"): what
 * `downloadPassport` writes to disk must be what `/verify` can read back. It
 * lives here, next to its inverse, so that contract is covered by one
 * round-trip test instead of two inline copies that can drift apart.
 *
 * Accepts either shape:
 *  - a full `PassportEnvelope` JSON (what we download) → returns `jws_token`
 *  - a bare compact JWS token in a plain text file    → returned trimmed
 *
 * The token is returned **verbatim**. Nothing here re-serialises, re-indents or
 * otherwise normalises the signed material: the signature covers the compact
 * JSON embedded inside the JWS, not the pretty-printed `json_payload` copy that
 * sits beside it in the file for humans to read. Reformatting the token would
 * invalidate it.
 */
export function extractJwsToken(fileText: string): string {
  const trimmed = fileText.trim();

  // Try to parse as JSON with a jws_token field; fall back to a bare token.
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      "jws_token" in parsed &&
      typeof (parsed as { jws_token: unknown }).jws_token === "string"
    ) {
      return (parsed as { jws_token: string }).jws_token;
    }
  } catch {
    // Not JSON — treat the whole content as a bare token.
  }

  return trimmed;
}
