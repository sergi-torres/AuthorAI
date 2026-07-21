import { notFound } from "next/navigation";

import { getAuthorCards } from "@/lib/authors";
import type { AuthorCardData } from "@/lib/types";
import { GenerateStudio } from "./GenerateStudio";

interface GeneratePageProps {
  params: Promise<{ id: string }>;
}

/**
 * Server component: resolves the author, 404s if missing, then delegates
 * all interactive state to the GenerateStudio client component.
 */
export default async function GeneratePage({ params }: GeneratePageProps) {
  const { id } = await params;
  const authors = await getAuthorCards();
  const author = authors.find(
    (a: AuthorCardData) => a.id === id || a.slug === id,
  );

  if (!author) {
    notFound();
  }

  return <GenerateStudio author={author} />;
}
