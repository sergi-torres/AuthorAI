/**
 * Unit tests for `fetchProfileWithFallback` — the Style DNA panel's loader.
 *
 * Vitest, environment "node". This imports the module and calls one exported
 * async function with `getStyleProfile` mocked; nothing is rendered, so the
 * "pure-function unit tests only" convention (decision_log 2026-07-21) holds.
 *
 * The rule under test (decision_log 2026-07-27, option A):
 *   404          → re-throw  → panel shows the neutral EMPTY state
 *   network/5xx  → fixture   → panel stays populated during an outage
 *   other 4xx    → re-throw  → panel shows the ERROR state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getStyleProfile,
  isFixtureEligibleError,
  NetworkError,
  NotFoundError,
  ServerError,
} from "@/lib/api";
import { fetchProfileWithFallback } from "@/components/StyleDnaPanel";
import { FIXTURE_STYLE_PROFILES } from "@/lib/fixtures/style-profiles";

// Only the network calls are stubbed; the error classes and the eligibility
// predicate stay real, so the test exercises the actual decision.
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, getStyleProfile: vi.fn(), listAuthors: vi.fn() };
});

const LABEL = "GET /api/authors/austen/style-profile";
const mockedGetStyleProfile = vi.mocked(getStyleProfile);

beforeEach(() => {
  vi.spyOn(console, "info").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  mockedGetStyleProfile.mockReset();
});

describe("fetchProfileWithFallback", () => {
  it("returns the live profile when the API answers", async () => {
    const live = {
      ...FIXTURE_STYLE_PROFILES.austen,
      computed_at: "2026-07-27T00:00:00Z",
    };
    mockedGetStyleProfile.mockResolvedValue(live);

    await expect(fetchProfileWithFallback("austen")).resolves.toBe(live);
  });

  it("re-throws a NotFoundError for a seed author instead of serving the fixture", async () => {
    // Option A: a real 404 is a definitive answer. The panel maps the rethrown
    // NotFoundError to its empty state — an unseeded DB shows nothing, not
    // hand-written numbers dressed as measurements (design-system.md §8.6).
    mockedGetStyleProfile.mockRejectedValue(new NotFoundError(LABEL));

    await expect(fetchProfileWithFallback("austen")).rejects.toBeInstanceOf(
      NotFoundError,
    );
  });

  it("serves the fixture when the API is unreachable (network failure)", async () => {
    mockedGetStyleProfile.mockRejectedValue(
      new NetworkError(LABEL, new TypeError("fetch failed")),
    );

    await expect(fetchProfileWithFallback("austen")).resolves.toBe(
      FIXTURE_STYLE_PROFILES.austen,
    );
  });

  it("serves the fixture on a 5xx", async () => {
    mockedGetStyleProfile.mockRejectedValue(new ServerError(LABEL, 500));

    await expect(fetchProfileWithFallback("poe")).resolves.toBe(
      FIXTURE_STYLE_PROFILES.poe,
    );
  });

  it("re-throws a non-404 4xx (not fixture-eligible)", async () => {
    const clientError = new Error(`${LABEL} failed with status 422`);
    mockedGetStyleProfile.mockRejectedValue(clientError);

    await expect(fetchProfileWithFallback("austen")).rejects.toBe(clientError);
  });

  it("re-throws for an author with no fixture, whatever the failure", async () => {
    const outage = new NetworkError(LABEL, new TypeError("fetch failed"));
    mockedGetStyleProfile.mockRejectedValue(outage);

    await expect(fetchProfileWithFallback("live-author")).rejects.toBe(outage);
  });
});

describe("isFixtureEligibleError", () => {
  it("is true only for NetworkError and ServerError", () => {
    expect(
      isFixtureEligibleError(new NetworkError(LABEL, new Error("boom"))),
    ).toBe(true);
    expect(isFixtureEligibleError(new ServerError(LABEL, 502))).toBe(true);
    expect(isFixtureEligibleError(new NotFoundError(LABEL))).toBe(false);
    expect(isFixtureEligibleError(new Error("plain"))).toBe(false);
    expect(isFixtureEligibleError("not an error")).toBe(false);
  });
});
