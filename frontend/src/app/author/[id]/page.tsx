import { notFound } from "next/navigation";
import Link from "next/link";

import { AUTHORS_BY_ID } from "@/lib/authors";
import { en } from "@/lib/i18n/en";

interface AuthorPageProps {
  params: Promise<{ id: string }>;
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { id } = await params;
  const author = AUTHORS_BY_ID[id];

  if (!author) {
    notFound();
  }

  return (
    <div className="flex flex-col gap-6">
      <Link
        href="/"
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        {en.authorDetail.backToAuthors}
      </Link>

      <h1 className="font-heading text-3xl font-semibold tracking-tight">
        {author.name}
      </h1>

      <p className="text-muted-foreground">{en.authorDetail.comingSoon}</p>
    </div>
  );
}
