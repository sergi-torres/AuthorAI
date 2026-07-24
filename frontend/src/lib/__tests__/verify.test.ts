/**
 * Happy-path tests for the /verify feature.
 * Uses Vitest with environment: "node" (no jsdom) — pure module tests only.
 * Covers:
 *   1. verifyPassport() api client — valid, invalid, and network-error paths.
 *   2. Error-code → i18n message mapping.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { verifyPassport } from "@/lib/api";
import { en } from "@/lib/i18n/en";
import type {
  VerifyResponse,
  PassportPayload,
  VerifyErrorCode,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const VALID_PAYLOAD: PassportPayload = {
  schema_version: "1.0",
  passport_id: "550e8400-e29b-41d4-a716-446655440000",
  generated_at: "2026-07-15T10:32:11Z",
  author_voice: {
    id: "dickens",
    style_profile_hash:
      "sha256:9f2c1b0000000000000000000000000000000000000000000000000000000000",
    style_profile_version: "1.0",
  },
  generation: {
    model_provider: "ibm/watsonx",
    model_id: "meta-llama/llama-3-3-70b-instruct",
    user_prompt_hash:
      "sha256:1a3b000000000000000000000000000000000000000000000000000000000000",
    output_hash:
      "sha256:c7d9000000000000000000000000000000000000000000000000000000000000",
    output_length_tokens: 312,
  },
  rag_sources: [
    {
      doc_id: "great_expectations",
      chunk_id: 42,
      snippet_hash:
        "sha256:4e5f000000000000000000000000000000000000000000000000000000000000",
    },
  ],
  contribution: { human_pct: 0, ai_pct: 100, note: "v1: 100% AI-assisted." },
  fit_score: 87,
  verifier_url: "https://autoria.vercel.app/verify",
};

const VALID_RESPONSE: VerifyResponse = {
  valid: true,
  payload: VALID_PAYLOAD,
  errors: [],
};

const INVALID_RESPONSE: VerifyResponse = {
  valid: false,
  payload: null,
  errors: [
    {
      code: "invalid_signature",
      message: "Signature check failed",
    },
  ],
};

const MULTI_ERROR_RESPONSE: VerifyResponse = {
  valid: false,
  payload: null,
  errors: [
    { code: "invalid_token", message: "Malformed compact JWS" },
    { code: "schema_mismatch", message: "Schema validation failed" },
  ],
};

// ---------------------------------------------------------------------------
// Helper: mock global fetch
// ---------------------------------------------------------------------------

function mockFetch(response: VerifyResponse, status = 200) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(response),
  } as Response);
}

// ---------------------------------------------------------------------------
// 1. verifyPassport — api client
// ---------------------------------------------------------------------------

describe("verifyPassport()", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns a valid VerifyResponse on HTTP 200 valid", async () => {
    mockFetch(VALID_RESPONSE);
    const result = await verifyPassport("eyJhbGci.payload.sig");
    expect(result.valid).toBe(true);
    expect(result.payload).toMatchObject({
      passport_id: VALID_PAYLOAD.passport_id,
    });
    expect(result.errors).toHaveLength(0);
  });

  it("returns valid=false with errors on HTTP 200 invalid signature", async () => {
    mockFetch(INVALID_RESPONSE);
    const result = await verifyPassport("eyJhbGci.tampered.sig");
    expect(result.valid).toBe(false);
    expect(result.payload).toBeNull();
    expect(result.errors[0].code).toBe("invalid_signature");
  });

  it("returns multiple errors from the backend unchanged", async () => {
    mockFetch(MULTI_ERROR_RESPONSE);
    const result = await verifyPassport("eyJhbGci.bad.token");
    expect(result.errors).toHaveLength(2);
    expect(result.errors.map((e) => e.code)).toEqual([
      "invalid_token",
      "schema_mismatch",
    ]);
  });

  it("maps a non-200 HTTP response to jwks_unavailable without throwing", async () => {
    mockFetch(INVALID_RESPONSE, 503);
    const result = await verifyPassport("eyJhbGci.payload.sig");
    expect(result.valid).toBe(false);
    expect(result.payload).toBeNull();
    expect(result.errors[0].code).toBe("jwks_unavailable");
    expect(result.errors[0].message).toContain("HTTP 503");
  });

  it("maps a network fetch failure to jwks_unavailable without throwing", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new Error("Failed to fetch"),
    );
    const result = await verifyPassport("eyJhbGci.payload.sig");
    expect(result.valid).toBe(false);
    expect(result.errors[0].code).toBe("jwks_unavailable");
    expect(result.errors[0].message).toContain("Failed to fetch");
  });

  it("sends the correct JSON body to POST /api/passports/verify", async () => {
    const spy = mockFetch(VALID_RESPONSE);
    const token = "eyJhbGci.payload.sig";
    await verifyPassport(token);

    expect(spy).toHaveBeenCalledOnce();
    const [url, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/passports/verify");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string) as { jws_token: string };
    expect(body.jws_token).toBe(token);
  });
});

// ---------------------------------------------------------------------------
// 2. i18n — error code message map
// ---------------------------------------------------------------------------

describe("en.verify.errorMessages", () => {
  const allContractCodes: VerifyErrorCode[] = [
    "invalid_token",
    "invalid_signature",
    "unknown_kid",
    "unsupported_algorithm",
    "schema_mismatch",
    "jwks_unavailable",
  ];

  it("has a non-empty user-facing message for every VerifyErrorCode", () => {
    for (const code of allContractCodes) {
      const msg = en.verify.errorMessages[code];
      expect(msg, `missing message for code "${code}"`).toBeTruthy();
      // Must be a real sentence (starts with capital letter)
      expect(msg[0]).toMatch(/[A-Z]/);
    }
  });

  it("uses the verbatim §8.2 copy for invalid_signature", () => {
    expect(en.verify.errorMessages["invalid_signature"]).toBe(
      "Signature invalid — this Passport may have been altered.",
    );
  });

  it("uses the verbatim §8.2 copy for jwks_unavailable", () => {
    expect(en.verify.errorMessages["jwks_unavailable"]).toBe(
      "Couldn't reach the key directory. Try again shortly.",
    );
  });
});

// ---------------------------------------------------------------------------
// 3. Payload fixture type-narrowing sanity check
// ---------------------------------------------------------------------------

describe("PassportPayload fixture", () => {
  it("has required fields per contract schema", () => {
    expect(VALID_PAYLOAD.schema_version).toBe("1.0");
    expect(VALID_PAYLOAD.fit_score).toBeGreaterThanOrEqual(0);
    expect(VALID_PAYLOAD.fit_score).toBeLessThanOrEqual(100);
    expect(
      VALID_PAYLOAD.contribution.human_pct + VALID_PAYLOAD.contribution.ai_pct,
    ).toBe(100);
    expect(VALID_PAYLOAD.rag_sources[0].snippet_hash).toMatch(
      /^sha256:[0-9a-f]{64}$/,
    );
  });
});
