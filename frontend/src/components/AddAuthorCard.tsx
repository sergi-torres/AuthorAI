"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BadgeCheck, Hourglass, TriangleAlert, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  listAuthors,
  slugifyAuthorName,
  uploadAuthorDocument,
} from "@/lib/api";
import { en } from "@/lib/i18n/en";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 4_000;
const POLL_DEADLINE_MS = 90_000;

type UploadState =
  | { status: "idle" }
  | { status: "editing" }
  | { status: "submitting" }
  /** Corpus accepted (202); polling until the StyleProfile shows up. `stalled`
      means the poll deadline passed — we stop polling but stay honest about it. */
  | { status: "success"; slug: string; name: string; stalled: boolean }
  | { status: "ready"; name: string }
  | { status: "error"; message: string };

/**
 * The "add your voice" slot in the author grid: expands in place into a
 * name + corpus-file form and posts to the documents endpoint (202 async).
 * After the upload it polls GET /api/authors until the new author reports
 * has_style_profile, refreshing the server-fetched grid so the card appears
 * without a manual reload.
 */
export function AddAuthorCard() {
  const router = useRouter();
  const [state, setState] = useState<UploadState>({ status: "idle" });
  const [name, setName] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const isPolling = state.status === "success" && !state.stalled;
  const pollSlug = state.status === "success" ? state.slug : null;
  const pollName = state.status === "success" ? state.name : "";

  useEffect(() => {
    if (!isPolling || !pollSlug) return;
    const slug = pollSlug;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const deadline = Date.now() + POLL_DEADLINE_MS;

    async function tick() {
      try {
        const authors = await listAuthors();
        if (cancelled) return;
        const ready = authors.some(
          (a) => a.slug === slug && a.has_style_profile,
        );
        if (ready) {
          router.refresh();
          setState({ status: "ready", name: pollName });
          return;
        }
      } catch {
        /* transient API error — keep polling until the deadline */
      }
      if (cancelled) return;
      if (Date.now() >= deadline) {
        router.refresh();
        setState({ status: "success", slug, name: pollName, stalled: true });
        return;
      }
      timer = setTimeout(tick, POLL_INTERVAL_MS);
    }

    timer = setTimeout(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [isPolling, pollSlug, pollName, router]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    const trimmedName = name.trim();
    const slug = slugifyAuthorName(trimmedName);
    if (!slug || !file) {
      setState({ status: "error", message: en.addAuthor.validationError });
      return;
    }
    setState({ status: "submitting" });
    try {
      await uploadAuthorDocument(slug, file, trimmedName);
      setState({ status: "success", slug, name: trimmedName, stalled: false });
      router.refresh();
    } catch {
      setState({ status: "error", message: en.addAuthor.error });
    }
  }

  function resetToIdle() {
    setName("");
    setFileName(null);
    if (fileRef.current) fileRef.current.value = "";
    setState({ status: "idle" });
  }

  const isForm =
    state.status === "editing" ||
    state.status === "submitting" ||
    state.status === "error";

  return (
    <div className="flex h-full flex-col rounded-xl border border-dashed border-border bg-card/50 p-4 transition-colors hover:border-ring/60">
      {state.status === "idle" && (
        <button
          type="button"
          onClick={() => setState({ status: "editing" })}
          className="flex flex-1 cursor-pointer flex-col items-center justify-center gap-3 rounded-lg py-8 text-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex size-10 items-center justify-center rounded-full bg-secondary text-primary">
            <Upload className="size-5" aria-hidden="true" />
          </span>
          <span className="font-heading text-xl font-semibold tracking-tight">
            {en.addAuthor.cta}
          </span>
          <span className="text-sm text-muted-foreground">
            {en.addAuthor.subtitle}
          </span>
        </button>
      )}

      {isForm && (
        <form
          onSubmit={handleSubmit}
          className="flex flex-1 flex-col gap-3"
          aria-busy={state.status === "submitting"}
        >
          <p className="font-heading text-xl font-semibold tracking-tight">
            {en.addAuthor.cta}
          </p>

          <label className="flex flex-col gap-1 text-sm font-medium">
            {en.addAuthor.nameLabel}
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={en.addAuthor.namePlaceholder}
              disabled={state.status === "submitting"}
              className="h-9 rounded-lg border border-input bg-background px-3 text-sm font-normal placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            />
          </label>

          {/* Native file inputs render browser-localized text ("Ningún archivo
              seleccionado"), clashing with the English UI — so the real input is
              visually hidden and a styled twin shows i18n strings instead. */}
          <label className="flex flex-col gap-1 text-sm font-medium">
            {en.addAuthor.fileLabel}
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md"
              disabled={state.status === "submitting"}
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
              className="peer sr-only"
            />
            <span className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-input bg-background px-1.5 text-sm font-normal peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:cursor-not-allowed peer-disabled:opacity-50">
              <span className="shrink-0 rounded-md bg-secondary px-2.5 py-1 text-sm font-medium text-secondary-foreground">
                {en.addAuthor.fileButton}
              </span>
              <span
                className={cn(
                  "min-w-0 truncate",
                  fileName ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {fileName ?? en.addAuthor.fileEmpty}
              </span>
            </span>
          </label>

          {state.status === "error" && (
            <p
              role="alert"
              className="flex items-center gap-2 text-sm text-destructive"
            >
              <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
              {state.message}
            </p>
          )}

          <div className="mt-auto flex items-center gap-2 pt-2">
            <Button type="submit" disabled={state.status === "submitting"}>
              {state.status === "submitting"
                ? en.addAuthor.submitting
                : en.addAuthor.submit}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={state.status === "submitting"}
              onClick={resetToIdle}
            >
              {en.addAuthor.cancel}
            </Button>
          </div>
        </form>
      )}

      {state.status === "success" && (
        <div
          role="status"
          className="animate-fade-rise flex flex-1 flex-col items-center justify-center gap-2 py-8 text-center"
        >
          {state.stalled ? (
            <Hourglass className="size-6 text-warning" aria-hidden="true" />
          ) : (
            <Hourglass
              className="size-6 animate-pulse text-muted-foreground"
              aria-hidden="true"
            />
          )}
          <p className="font-heading text-xl font-semibold tracking-tight">
            {en.addAuthor.successTitle}
          </p>
          <p className="max-w-[28ch] text-sm text-muted-foreground">
            {state.stalled
              ? en.addAuthor.stillProcessing
              : en.addAuthor.successNote}
          </p>
        </div>
      )}

      {state.status === "ready" && (
        <div
          role="status"
          className="animate-fade-rise flex flex-1 flex-col items-center justify-center gap-2 py-8 text-center"
        >
          <BadgeCheck className="size-6 text-success" aria-hidden="true" />
          <p className="font-heading text-xl font-semibold tracking-tight">
            {en.addAuthor.readyTitle}
          </p>
          <p className="max-w-[28ch] text-sm text-muted-foreground">
            {en.addAuthor.readyNote(state.name)}
          </p>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="mt-1"
            onClick={resetToIdle}
          >
            {en.addAuthor.addAnother}
          </Button>
        </div>
      )}
    </div>
  );
}
