"use client";

/**
 * /verify — Public Authorship Passport verification screen.
 *
 * Accepts a compact JWS token (pasted or from a .jws/.json file), POSTs it to
 * POST /api/passports/verify, and renders a typed verdict. No client-side
 * crypto — all verification happens on the backend per StudioComposer rules.
 */

import { useRef, useState } from "react";
import { BadgeCheck, Clock, ShieldAlert } from "lucide-react";
import { verifyPassport } from "@/lib/api";
import { extractJwsToken } from "@/lib/passport";
import type { VerifyResponse, PassportPayload, VerifyError } from "@/lib/types";
import { en } from "@/lib/i18n/en";
import { FitScoreBar } from "@/components/FitScoreBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const t = en.verify;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PageState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | {
      kind: "valid";
      response: VerifyResponse & { valid: true; payload: PassportPayload };
    }
  | { kind: "invalid"; errors: VerifyError[] }
  | { kind: "network_error" };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Truncate a sha256:… hash to first 16 hex chars with copy affordance. */
function HashCell({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const display = value.startsWith("sha256:")
    ? `sha256:${value.slice(7, 23)}…`
    : value.length > 20
      ? `${value.slice(0, 16)}…`
      : value;

  function handleCopy() {
    void navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      <code className="font-mono text-xs">{display}</code>
      <button
        type="button"
        onClick={handleCopy}
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        title={t.copyHashTitle}
      >
        {copied ? t.copyHashDone : t.copyHashIcon}
      </button>
    </span>
  );
}

/** A two-column label / value row inside the payload table. */
function PayloadRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <tr className="border-b border-border last:border-0">
      <th className="py-2 pr-4 text-left text-xs font-medium text-muted-foreground whitespace-nowrap align-top w-44">
        {label}
      </th>
      <td className="py-2 text-sm break-all align-top">{children}</td>
    </tr>
  );
}

/** Decode an error code to its i18n copy, falling back to the backend message. */
function errorMessage(err: VerifyError): string {
  return t.errorMessages[err.code] ?? err.message;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PayloadTable({ payload }: { payload: PassportPayload }) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <tbody>
            <PayloadRow label={t.fieldPassportId}>
              <HashCell value={payload.passport_id} />
            </PayloadRow>
            <PayloadRow label={t.fieldSchemaVersion}>
              <code className="font-mono text-xs">
                {payload.schema_version}
              </code>
            </PayloadRow>
            <PayloadRow label={t.fieldGeneratedAt}>
              {new Date(payload.generated_at).toLocaleString("en-GB", {
                dateStyle: "medium",
                timeStyle: "short",
                timeZone: "UTC",
              })}{" "}
              UTC
            </PayloadRow>

            {/* Author voice */}
            <PayloadRow label={t.fieldAuthorVoice}>
              <span className="font-medium">{payload.author_voice.id}</span>
            </PayloadRow>
            <PayloadRow label={t.fieldStyleProfileHash}>
              <HashCell value={payload.author_voice.style_profile_hash} />
            </PayloadRow>
            <PayloadRow label={t.fieldStyleProfileVersion}>
              {payload.author_voice.style_profile_version}
            </PayloadRow>

            {/* Generation */}
            <PayloadRow label={t.fieldModelProvider}>
              {payload.generation.model_provider}
            </PayloadRow>
            <PayloadRow label={t.fieldModel}>
              <code className="font-mono text-xs">
                {payload.generation.model_id}
              </code>
            </PayloadRow>
            <PayloadRow label={t.fieldPromptHash}>
              <HashCell value={payload.generation.user_prompt_hash} />
            </PayloadRow>
            <PayloadRow label={t.fieldOutputHash}>
              <HashCell value={payload.generation.output_hash} />
            </PayloadRow>
            <PayloadRow label={t.fieldOutputLength}>
              {t.tokens(payload.generation.output_length_tokens)}
            </PayloadRow>

            {/* Fit score */}
            <PayloadRow label={t.fieldFitScore}>
              <div className="w-64">
                <FitScoreBar
                  variant="authorial"
                  score={payload.fit_score}
                  authorName={payload.author_voice.id}
                  animate={false}
                />
              </div>
            </PayloadRow>

            {/* RAG sources */}
            <PayloadRow label={t.fieldRagSources}>
              {payload.rag_sources.length === 0 ? (
                <span className="text-muted-foreground">
                  {t.ragSourcesEmpty}
                </span>
              ) : (
                <ul className="flex flex-col gap-2">
                  {payload.rag_sources.map((src, i) => (
                    <li
                      key={i}
                      className="flex flex-col gap-0.5 rounded border border-border px-2 py-1 text-xs"
                    >
                      <span>
                        <span className="text-muted-foreground">
                          {t.fieldRagDoc}:{" "}
                        </span>
                        <code className="font-mono">{src.doc_id}</code>
                      </span>
                      <span>
                        <span className="text-muted-foreground">
                          {t.fieldRagChunk}:{" "}
                        </span>
                        {src.chunk_id}
                      </span>
                      <span>
                        <span className="text-muted-foreground">
                          {t.fieldRagSnippetHash}:{" "}
                        </span>
                        <HashCell value={src.snippet_hash} />
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </PayloadRow>

            {/* Contribution */}
            <PayloadRow label={t.fieldContributionAi}>
              {t.percentage(payload.contribution.ai_pct)}
            </PayloadRow>
            <PayloadRow label={t.fieldContributionHuman}>
              {t.percentage(payload.contribution.human_pct)}
            </PayloadRow>

            {/* Verifier URL (optional) */}
            {payload.verifier_url && (
              <PayloadRow label={t.fieldVerifierUrl}>
                <a
                  href={payload.verifier_url}
                  className="text-primary underline-offset-4 hover:underline text-xs"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {payload.verifier_url}
                </a>
              </PayloadRow>
            )}
          </tbody>
        </table>
      </div>

      {/* Raw JSON toggle */}
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setShowRaw((v) => !v)}
          className="self-start text-xs text-muted-foreground hover:text-foreground transition-colors underline-offset-4 hover:underline"
        >
          {showRaw ? t.rawJsonToggleHide : t.rawJsonToggleShow}
        </button>
        {showRaw && (
          <pre className="overflow-x-auto rounded-lg border border-border bg-muted/50 p-4 font-mono text-xs leading-relaxed">
            {JSON.stringify(payload, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function VerifyPage() {
  const [inputMode, setInputMode] = useState<"paste" | "upload">("paste");
  const [token, setToken] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [state, setState] = useState<PageState>({ kind: "idle" });
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Extract a JWS token string from a .jws/.json file's text.
   *
   * Delegates to `lib/passport.extractJwsToken`, the inverse of the studio's
   * `downloadPassport`, so a passport downloaded from the studio is guaranteed
   * to be readable here (MVP §10 Definition of Done).
   */
  async function readFileToken(file: File): Promise<string> {
    return extractJwsToken(await file.text());
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    readFileToken(file)
      .then((t) => setToken(t))
      .catch(() => setToken(""));
  }

  function handleClear() {
    setToken("");
    setFileName(null);
    setState({ kind: "idle" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const jwsToken = token.trim();
    if (!jwsToken) return;

    setState({ kind: "submitting" });
    const response = await verifyPassport(jwsToken);

    if (response.valid && response.payload !== null) {
      setState({
        kind: "valid",
        response: response as VerifyResponse & {
          valid: true;
          payload: PassportPayload;
        },
      });
    } else if (
      !response.valid &&
      response.errors.some((e) => e.code === "jwks_unavailable") &&
      response.errors.length === 1 &&
      response.errors[0].message.startsWith("Network error:")
    ) {
      // Synthesised network error from the client wrapper
      setState({ kind: "network_error" });
    } else {
      setState({ kind: "invalid", errors: response.errors });
    }
  }

  const isSubmitting = state.kind === "submitting";

  return (
    <div className="flex flex-col gap-8 max-w-3xl">
      <div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          {t.pageTitle}
        </h1>
        <p className="mt-2 text-muted-foreground">{t.pageSubtitle}</p>
      </div>

      {/* Input card */}
      <Card>
        <CardHeader>
          {/* Mode tabs */}
          <div className="flex gap-1 self-start rounded-lg border border-border bg-muted/50 p-0.5">
            <button
              type="button"
              onClick={() => {
                setInputMode("paste");
                handleClear();
              }}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                inputMode === "paste"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.tabPaste}
            </button>
            <button
              type="button"
              onClick={() => {
                setInputMode("upload");
                handleClear();
              }}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                inputMode === "upload"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.tabUpload}
            </button>
          </div>
        </CardHeader>

        <CardContent>
          <form
            onSubmit={(e) => void handleSubmit(e)}
            className="flex flex-col gap-4"
          >
            {inputMode === "paste" ? (
              <div className="flex flex-col gap-1.5">
                <label htmlFor="jws-token" className="text-sm font-medium">
                  {t.tokenLabel}
                </label>
                <textarea
                  id="jws-token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder={t.tokenPlaceholder}
                  rows={4}
                  spellCheck={false}
                  className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                  disabled={isSubmitting}
                />
              </div>
            ) : (
              <div className="flex flex-col gap-1.5">
                <span className="text-sm font-medium">{t.fileLabel}</span>
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isSubmitting}
                  >
                    {t.fileButton}
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {fileName ?? t.fileEmpty}
                  </span>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".jws,.json"
                  className="sr-only"
                  onChange={handleFileChange}
                />
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={isSubmitting || !token.trim()}>
                {isSubmitting ? t.verifyingButton : t.verifyButton}
              </Button>
              {token && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleClear}
                  disabled={isSubmitting}
                >
                  {t.clearButton}
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Result area */}
      {state.kind === "idle" && (
        <div className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
          <p className="text-base font-medium">{t.idleHeading}</p>
          <p className="text-sm">{t.idleBody}</p>
        </div>
      )}

      {state.kind === "submitting" && (
        <div className="flex items-center justify-center py-12">
          <span className="text-sm text-muted-foreground animate-pulse">
            {t.verifyingButton}
          </span>
        </div>
      )}

      {state.kind === "valid" && (
        <div className="flex flex-col gap-4">
          {/* Seal-green verdict banner — design-system §5 stamp motion, §7 VerifiedBanner */}
          <div className="animate-stamp-in flex items-start gap-3 rounded-xl border border-success/40 bg-success-tint px-4 py-3">
            <BadgeCheck
              className="mt-1 size-5 shrink-0 text-success"
              aria-hidden="true"
            />
            <div>
              <p className="font-heading text-lg font-semibold text-success">
                {t.verifiedTitle}
              </p>
              <p className="text-sm text-muted-foreground">
                {t.verifiedSubtitle}
              </p>
            </div>
          </div>

          {/* Decoded payload */}
          <Card>
            <CardContent className="pt-4">
              <PayloadTable payload={state.response.payload} />
            </CardContent>
          </Card>
        </div>
      )}

      {state.kind === "invalid" && (
        <div className="flex flex-col gap-4">
          {/* Destructive verdict banner — design-system §6 ShieldAlert = invalid */}
          <div className="bg-destructive-tint flex items-center gap-3 rounded-xl border border-destructive/40 px-4 py-3">
            <ShieldAlert
              className="text-destructive-foreground size-5 shrink-0"
              aria-hidden="true"
            />
            <p className="text-destructive-foreground font-heading text-lg font-semibold">
              {t.invalidTitle}
            </p>
          </div>

          {/* Error list */}
          <Card>
            <CardContent className="pt-4">
              <ul className="flex flex-col gap-2">
                {state.errors.map((err, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
                  >
                    <code className="shrink-0 font-mono text-xs text-muted-foreground mt-0.5">
                      {err.code}
                    </code>
                    <span>{errorMessage(err)}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}

      {state.kind === "network_error" && (
        <div className="flex flex-col gap-4">
          {/* Warning banner — design-system §2.2: --warning-foreground on --warning-tint */}
          <div className="flex items-start gap-3 rounded-xl border border-warning/40 bg-warning-tint px-4 py-3">
            <Clock
              className="mt-1 size-5 shrink-0 text-warning-foreground"
              aria-hidden="true"
            />
            <div>
              <p className="font-heading text-lg font-semibold text-warning-foreground">
                {t.networkErrorTitle}
              </p>
              <p className="text-sm text-muted-foreground">
                {t.networkErrorBody}
              </p>
            </div>
          </div>
          <div>
            <Button
              type="button"
              variant="outline"
              onClick={() => setState({ kind: "idle" })}
            >
              {t.retryButton}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
