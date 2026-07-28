import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { downloadPassport, extractJwsToken } from "./passport";
import type { PassportEnvelope, PassportPayload } from "./types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const MOCK_PASSPORT: PassportEnvelope = {
  jws_token: "eyJhbGciOiJFUzI1NiIsImtpZCI6ImF1dG9yaWEtMSJ9.fake.sig",
  json_payload: {
    schema_version: "1.0",
    passport_id: "00000000-0000-0000-0000-000000000001",
    generated_at: "2025-01-01T00:00:00Z",
    author_voice: {
      id: "dickens",
      style_profile_hash: "sha256:" + "a".repeat(64),
      style_profile_version: "1.0",
    },
    generation: {
      model_provider: "ibm/watsonx",
      model_id: "meta-llama/llama-3-3-70b-instruct",
      user_prompt_hash: "sha256:" + "b".repeat(64),
      output_hash: "sha256:" + "c".repeat(64),
      output_length_tokens: 120,
    },
    rag_sources: [
      {
        doc_id: "doc-1",
        chunk_id: 3,
        snippet_hash: "sha256:" + "d".repeat(64),
      },
    ],
    contribution: {
      human_pct: 10,
      ai_pct: 90,
      note: "Prompt by human; text by AutorIA",
    },
    fit_score: 87,
    verifier_url: "https://autoria.app/verify",
  },
};

// ---------------------------------------------------------------------------
// DOM mocks — Blob, URL, anchor
// ---------------------------------------------------------------------------

/**
 * Vitest runs in "node" environment by default (see vitest.config.ts).
 * We stub just the four browser APIs that downloadPassport touches:
 *   - Blob constructor
 *   - URL.createObjectURL
 *   - URL.revokeObjectURL
 *   - document.createElement (only for tag "a")
 */

let anchorClickSpy: ReturnType<typeof vi.fn>;
let anchorDownloadAttr: string;
let anchorHrefAttr: string;

beforeEach(() => {
  anchorClickSpy = vi.fn();
  anchorDownloadAttr = "";
  anchorHrefAttr = "";

  // Stub the anchor element returned by createElement("a")
  vi.stubGlobal("document", {
    createElement: (tag: string) => {
      if (tag !== "a") throw new Error(`Unexpected createElement("${tag}")`);
      const el = {
        get href() {
          return anchorHrefAttr;
        },
        set href(v: string) {
          anchorHrefAttr = v;
        },
        get download() {
          return anchorDownloadAttr;
        },
        set download(v: string) {
          anchorDownloadAttr = v;
        },
        click: anchorClickSpy,
      };
      return el;
    },
  });

  vi.stubGlobal(
    "Blob",
    class MockBlob {
      public readonly parts: BlobPart[];
      public readonly options: BlobPropertyBag | undefined;
      constructor(parts: BlobPart[], options?: BlobPropertyBag) {
        this.parts = parts;
        this.options = options;
      }
    },
  );

  vi.stubGlobal("URL", {
    createObjectURL: vi.fn(() => "blob:mock-url"),
    revokeObjectURL: vi.fn(),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("downloadPassport — happy path", () => {
  it("derives the correct filename from author_voice.id", () => {
    downloadPassport(MOCK_PASSPORT);
    expect(anchorDownloadAttr).toBe("passport-dickens.json");
  });

  it("sets anchor.href to the object URL returned by createObjectURL", () => {
    downloadPassport(MOCK_PASSPORT);
    expect(anchorHrefAttr).toBe("blob:mock-url");
  });

  it("calls anchor.click() exactly once", () => {
    downloadPassport(MOCK_PASSPORT);
    expect(anchorClickSpy).toHaveBeenCalledTimes(1);
  });

  it("revokes the object URL after clicking", () => {
    downloadPassport(MOCK_PASSPORT);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("creates a Blob with application/json MIME type", () => {
    downloadPassport(MOCK_PASSPORT);
    expect(URL.createObjectURL).toHaveBeenCalledWith(
      expect.objectContaining({ options: { type: "application/json" } }),
    );
  });

  it("serialises the full envelope as pretty-printed JSON (indent 2)", () => {
    downloadPassport(MOCK_PASSPORT);

    // Retrieve the Blob that was passed to createObjectURL
    const blobArg = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as { parts: BlobPart[] };
    const serialised = blobArg.parts[0] as string;

    // Must be valid JSON matching the full envelope (jws_token + json_payload)
    const parsed = JSON.parse(serialised) as typeof MOCK_PASSPORT;
    expect(parsed).toEqual(MOCK_PASSPORT);

    // Must be pretty-printed (contains a newline + two-space indent)
    expect(serialised).toContain("\n  ");
  });

  it("includes jws_token so the file is verifiable offline", () => {
    downloadPassport(MOCK_PASSPORT);

    const blobArg = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as { parts: BlobPart[] };
    const serialised = blobArg.parts[0] as string;

    const parsed = JSON.parse(serialised) as typeof MOCK_PASSPORT;
    expect(parsed.jws_token).toBe(MOCK_PASSPORT.jws_token);
  });
});

// ---------------------------------------------------------------------------
// Round trip: downloadPassport → file bytes → extractJwsToken
// ---------------------------------------------------------------------------

/**
 * A REAL Authorship Passport, signed with a genuine ephemeral ES256 key by
 * `autoria_ai.passport.signer.sign_passport` (the same code path the backend
 * uses). It is checked in as a fixed artifact so this test proves the property
 * that MVP §10 makes a Definition of Done criterion:
 *
 *   "Authorship Passport issued, downloaded, and verifies with a valid
 *    signature"
 *
 * The signature covers the compact JSON *inside* the JWS, so the only thing
 * that must survive the download → upload round trip is `jws_token`, byte for
 * byte. The pretty-printed `json_payload` beside it is a human-readable copy
 * that verification never consults.
 *
 * The extracted token was verified back to `valid: true` by the real
 * `autoria_ai.passport.verifier.verify_passport` against the matching public
 * key — that is the half of the loop TypeScript cannot assert on its own,
 * since the frontend deliberately does no JWS parsing in the browser.
 */
const SIGNED_PASSPORT: PassportEnvelope = {
  jws_token:
    "eyJhbGciOiJFUzI1NiIsImtpZCI6ImF1dG9yaWEtcm91bmR0cmlwLXRlc3QiLCJ0eXAiOiJwYXNzcG9ydCtqd3MifQ.eyJzY2hlbWFfdmVyc2lvbiI6IjEuMCIsInBhc3Nwb3J0X2lkIjoiNjNhYWEyNGYtODI5NC00Y2ViLTlmNTEtYTU4ODQyN2RjNTAwIiwiZ2VuZXJhdGVkX2F0IjoiMjAyNi0wNy0yOFQxNzoxMjo0OFoiLCJhdXRob3Jfdm9pY2UiOnsiaWQiOiJkaWNrZW5zIiwic3R5bGVfcHJvZmlsZV9oYXNoIjoic2hhMjU2OjE1YmJkMWJmYjFmYTUwMmQzZmU3YjAzNmI1YjQ5NzYzYTU1M2YyMzU2NmUyNzJkZDE0YWQxNGQzOWM4MWI3MzgiLCJzdHlsZV9wcm9maWxlX3ZlcnNpb24iOiIxLjAifSwiZ2VuZXJhdGlvbiI6eyJtb2RlbF9wcm92aWRlciI6ImlibS93YXRzb254IiwibW9kZWxfaWQiOiJtZXRhLWxsYW1hL2xsYW1hLTMtMy03MGItaW5zdHJ1Y3QiLCJ1c2VyX3Byb21wdF9oYXNoIjoic2hhMjU2OjFmMDE3NTIzMTZkMDljMjUzYTM3ZThiZTI2OGFlMTg2YWI3MzcwYjIwMGVjYWFlODM1MjQ2ZDllZWU1MGM2YzMiLCJvdXRwdXRfaGFzaCI6InNoYTI1NjowNDkwMmJkYjc0YmEzOTViOTMwODZlOWEzM2ZiOWMwZjg3ODcyZmY0ZThlMzE5N2Y3MTBjNTM3N2UzNDQ4MjBiIiwib3V0cHV0X2xlbmd0aF90b2tlbnMiOjEyMH0sInJhZ19zb3VyY2VzIjpbeyJkb2NfaWQiOiJibGVhay1ob3VzZSIsImNodW5rX2lkIjozLCJzbmlwcGV0X2hhc2giOiJzaGEyNTY6MDFjYjJiN2FhYjJlM2M4ZWM5OTAwZWQ5ZDI1MDdlOGFhMWE0YWJjOTQzYjVhMzZmNGNkYzIxODQ1YjYyMWFlOCJ9XSwiY29udHJpYnV0aW9uIjp7Imh1bWFuX3BjdCI6MCwiYWlfcGN0IjoxMDB9LCJmaXRfc2NvcmUiOjg3LCJ2ZXJpZmllcl91cmwiOiJodHRwczovL2F1dG9yaWEuYXBwL3ZlcmlmeSJ9.T58cOpv4sHwm_jDsG2-EbEXLPV2ip2_F21t0tIDRgaI5CVgVeEGY_Uwb7mGQEJIoyd4xutWYJbAEV68PQggB9w",
  json_payload: {
    schema_version: "1.0",
    passport_id: "63aaa24f-8294-4ceb-9f51-a588427dc500",
    generated_at: "2026-07-28T17:12:48Z",
    author_voice: {
      id: "dickens",
      style_profile_hash:
        "sha256:15bbd1bfb1fa502d3fe7b036b5b49763a553f23566e272dd14ad14d39c81b738",
      style_profile_version: "1.0",
    },
    generation: {
      model_provider: "ibm/watsonx",
      model_id: "meta-llama/llama-3-3-70b-instruct",
      user_prompt_hash:
        "sha256:1f01752316d09c253a37e8be268ae186ab7370b200ecaae835246d9eee50c6c3",
      output_hash:
        "sha256:04902bdb74ba395b93086e9a33fb9c0f87872ff4e8e3197f710c5377e344820b",
      output_length_tokens: 120,
    },
    rag_sources: [
      {
        doc_id: "bleak-house",
        chunk_id: 3,
        snippet_hash:
          "sha256:01cb2b7aab2e3c8ec9900ed9d2507e8aa1a4abc943b5a36f4cdc21845b621ae8",
      },
    ],
    contribution: {
      human_pct: 0,
      ai_pct: 100,
    },
    fit_score: 87,
    verifier_url: "https://autoria.app/verify",
  } as PassportPayload,
};

/** Capture exactly the bytes `downloadPassport` hands to the Blob. */
function capturedDownloadBytes(envelope: PassportEnvelope): string {
  downloadPassport(envelope);
  const blobArg = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock
    .calls[0][0] as { parts: BlobPart[] };
  return blobArg.parts[0] as string;
}

describe("downloadPassport → extractJwsToken round trip", () => {
  it("recovers the JWS token byte-for-byte from a downloaded passport file", () => {
    const fileContents = capturedDownloadBytes(SIGNED_PASSPORT);

    // This is precisely what /verify does with an uploaded .json file.
    expect(extractJwsToken(fileContents)).toBe(SIGNED_PASSPORT.jws_token);
  });

  it("does not reformat the signed material even though the file is pretty-printed", () => {
    const fileContents = capturedDownloadBytes(SIGNED_PASSPORT);

    // The file is indented for humans...
    expect(fileContents).toContain("\n  ");
    // ...but the token itself is never re-wrapped, re-indented or re-encoded.
    expect(fileContents).toContain(SIGNED_PASSPORT.jws_token);
    expect(extractJwsToken(fileContents).split(".")).toHaveLength(3);
  });

  it("survives a trailing newline, as added by editors and some downloads", () => {
    const fileContents = capturedDownloadBytes(SIGNED_PASSPORT);

    expect(extractJwsToken(`${fileContents}\n`)).toBe(
      SIGNED_PASSPORT.jws_token,
    );
  });

  it("accepts a bare compact JWS token pasted into a plain file", () => {
    expect(extractJwsToken(`  ${SIGNED_PASSPORT.jws_token}  `)).toBe(
      SIGNED_PASSPORT.jws_token,
    );
  });
});
