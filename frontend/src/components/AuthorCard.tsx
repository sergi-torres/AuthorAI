import Link from "next/link";

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { en } from "@/lib/i18n/en";
import type { AuthorCardData } from "@/lib/types";

interface AuthorCardProps {
  author: AuthorCardData;
}

/** Monogram initial: surname first letter ("Edgar Allan Poe" -> "P"). */
function monogramOf(name: string): string {
  return name.trim().split(/\s+/).at(-1)?.charAt(0).toUpperCase() ?? "?";
}

export function AuthorCard({ author }: AuthorCardProps) {
  return (
    <Link
      href={`/author/${author.slug}`}
      data-voice={author.id}
      className="group block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Card className="relative h-full cursor-pointer overflow-hidden shadow-paper-sm transition-all duration-200 group-hover:-translate-y-0.5 group-hover:shadow-paper-lg group-focus-visible:shadow-paper-lg">
        <div
          className="absolute inset-x-0 top-0 h-1 bg-voice"
          aria-hidden="true"
        />
        <CardHeader>
          <div className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-voice-tint font-heading text-2xl font-semibold text-voice"
            >
              {monogramOf(author.name)}
            </span>
            <CardTitle className="font-heading text-2xl font-semibold tracking-tight">
              {author.name}
            </CardTitle>
          </div>
          {author.has_style_profile && (
            <div data-slot="card-action">
              <Badge
                variant="secondary"
                className="shrink-0 bg-voice-tint text-voice"
              >
                {en.badge.styleProfileReady}
              </Badge>
            </div>
          )}
        </CardHeader>

        <CardContent>
          <p className="text-muted-foreground leading-relaxed">{author.bio}</p>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {en.authorSelector.documentCount(author.n_documents)}
          </p>
        </CardContent>

        <CardFooter className="mt-auto">
          <span className="text-sm font-medium text-voice">
            {en.authorSelector.cardCta}
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}
