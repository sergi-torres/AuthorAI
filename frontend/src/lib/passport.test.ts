import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { downloadPassport } from "./passport";
import type { PassportEnvelope } from "./types";

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
