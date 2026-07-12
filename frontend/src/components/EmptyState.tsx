import type { ReactNode } from "react";

interface EmptyStateProps {
  /** lucide-react icon element to display above the message. */
  icon: ReactNode;
  /** Primary one-line message. */
  title: string;
  /** Optional descriptive body text. */
  body?: string;
  /** Optional action (e.g., a Button). Rendered below the message. */
  action?: ReactNode;
}

/**
 * Generic empty-state surface: icon + title + optional body + optional action.
 * Used across all screens where content is absent (not an error — neutral tone).
 * Design-system.md §7 inventory: Sprint 1, all screens.
 */
export function EmptyState({ icon, title, body, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <span className="text-muted-foreground" aria-hidden="true">
        {icon}
      </span>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {body && <p className="max-w-sm text-xs text-muted-foreground">{body}</p>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
