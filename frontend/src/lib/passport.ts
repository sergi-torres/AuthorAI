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
