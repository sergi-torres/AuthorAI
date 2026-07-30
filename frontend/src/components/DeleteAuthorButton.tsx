"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { deleteAuthor } from "@/lib/api";
import { en } from "@/lib/i18n/en";

interface DeleteAuthorButtonProps {
  authorId: string;
  authorName: string;
}

/**
 * Removes a live-added author from the gallery. Sit outside the card Link so
 * the click does not navigate; confirm before calling DELETE.
 */
export function DeleteAuthorButton({
  authorId,
  authorName,
}: DeleteAuthorButtonProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  async function handleClick(event: React.MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
    if (busy) return;
    if (!window.confirm(en.authorSelector.deleteConfirm(authorName))) return;

    setBusy(true);
    setError(false);
    try {
      await deleteAuthor(authorId);
      router.refresh();
    } catch {
      setError(true);
      setBusy(false);
    }
  }

  return (
    <div className="absolute right-2 bottom-2 z-10 flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="destructive"
        size="icon-sm"
        onClick={handleClick}
        disabled={busy}
        aria-label={en.authorSelector.deleteAuthor}
        title={en.authorSelector.deleteAuthor}
      >
        <Trash2 aria-hidden="true" />
      </Button>
      {error && (
        <p className="max-w-[12rem] rounded-md bg-background/95 px-2 py-1 text-xs text-destructive shadow-sm">
          {en.authorSelector.deleteError}
        </p>
      )}
      {busy && (
        <span className="sr-only">{en.authorSelector.deleting}</span>
      )}
    </div>
  );
}
