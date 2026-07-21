import { AuthorColumn, type GenerationState } from "@/components/AuthorColumn";
import { ComparativeMetricsTable } from "@/components/ComparativeMetricsTable";

interface SideBySideOutputProps {
  /** Author slug, e.g. "dickens" — drives the voice palette via data-voice. */
  authorId: string;
  /** Display name for labels and captions, e.g. "Dickens". */
  authorName: string;
  /** State of the vanilla Llama branch (GenerateResponse.vanilla). */
  vanilla: GenerationState;
  /** State of the in-voice branch (GenerateResponse.autoria). */
  autoria: GenerationState;
  /** Terms from StyleProfile.distinctive_vocab to highlight in the voice column. */
  distinctiveTerms?: readonly string[];
  onRetry?: () => void;
}

/**
 * The hero comparison: vanilla on the left, AutorIA in-voice on the right.
 * Both branches come from the same POST /generate call, so their states
 * usually move together — but each column owns its own state so a single
 * branch can fail or lag without hiding the other.
 *
 * When BOTH columns reach `success`, the ComparativeMetricsTable is rendered
 * below the grid with real measurements from the output text (#28).
 */
export function SideBySideOutput({
  authorId,
  authorName,
  vanilla,
  autoria,
  distinctiveTerms,
  onRetry,
}: SideBySideOutputProps) {
  const bothSucceeded =
    vanilla.status === "success" && autoria.status === "success";

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 items-stretch gap-6 md:grid-cols-2">
        <AuthorColumn variant="vanilla" state={vanilla} onRetry={onRetry} />
        <AuthorColumn
          variant="authorial"
          authorId={authorId}
          authorName={authorName}
          state={autoria}
          distinctiveTerms={distinctiveTerms}
          onRetry={onRetry}
        />
      </div>

      {bothSucceeded && (
        <ComparativeMetricsTable
          vanillaText={vanilla.output.text}
          authorText={autoria.output.text}
          authorName={authorName}
        />
      )}
    </div>
  );
}
