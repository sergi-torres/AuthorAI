import { notFound } from "next/navigation";
import Link from "next/link";
import { Feather } from "lucide-react";

import { StyleDnaPanel } from "@/components/StyleDnaPanel";
import { getAuthorCards } from "@/lib/authors";
import { en } from "@/lib/i18n/en";

interface AuthorPageProps {
  params: Promise<{ id: string }>;
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { id } = await params;
  const authors = await getAuthorCards();
  const author = authors.find((a) => a.id === id || a.slug === id);

  if (!author) {
    notFound();
  }

  return (
    <div className="flex flex-col gap-6" data-voice={author.id}>
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {en.authorDetail.backToAuthors}
        </Link>

        <Link
          href={`/author/${author.id}/generate`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Feather className="size-4" aria-hidden="true" />
          {en.authorDetail.generateCta}
        </Link>
      </div>

      <h1 className="font-heading text-4xl font-semibold tracking-tight">
        {author.name}
      </h1>

      <StyleDnaPanel authorId={author.id} authorName={author.name} />
    </div>
  );
}
