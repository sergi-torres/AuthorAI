import { notFound } from "next/navigation";
import Link from "next/link";

import { StyleDnaPanel } from "@/components/StyleDnaPanel";
import { GenerateStudio } from "@/components/GenerateStudio";
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
    <div className="flex flex-col gap-8" data-voice={author.id}>
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {en.authorDetail.backToAuthors}
        </Link>
      </div>

      <h1 className="font-heading text-4xl font-semibold tracking-tight">
        {author.name}
      </h1>

      <StyleDnaPanel authorId={author.id} authorName={author.name} />

      <GenerateStudio author={author} />
    </div>
  );
}
