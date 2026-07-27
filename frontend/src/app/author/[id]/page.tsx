import { notFound } from "next/navigation";
import Link from "next/link";

import { StyleDnaPanel } from "@/components/StyleDnaPanel";
import { GenerateStudio } from "@/components/GenerateStudio";
import { getStyleProfile } from "@/lib/api";
import { getAuthorCards } from "@/lib/authors";
import { FIXTURE_STYLE_PROFILES } from "@/lib/fixtures/style-profiles";
import { en } from "@/lib/i18n/en";
import { selectDistinctiveTerms } from "@/lib/style-dna";

interface AuthorPageProps {
  params: Promise<{ id: string }>;
}

/**
 * Server-render budget for the optional style-profile fetch. The highlight is
 * an enhancement, never a blocker: if the backend is slow we give up and render
 * the studio without marks rather than hold the whole page hostage.
 */
const PROFILE_FETCH_BUDGET_MS = 5_000;

/**
 * Distinctive vocabulary for the AutorIA column (design-system §8.4).
 *
 * Loaded here, in the common parent, so `GenerateStudio` stays a pure client
 * component with no fetch of its own. Falls back to the seeded fixture for the
 * preloaded authors — the same demo-safe substitution `StyleDnaPanel` makes —
 * so the highlighted terms always match the vocab table shown above them.
 * Any failure without a fixture degrades to `[]` (no marks, no legend, no throw).
 */
async function loadDistinctiveTerms(authorId: string): Promise<string[]> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const profile = await Promise.race([
      getStyleProfile(authorId).catch(() => FIXTURE_STYLE_PROFILES[authorId]),
      new Promise<undefined>((resolve) => {
        timer = setTimeout(() => resolve(undefined), PROFILE_FETCH_BUDGET_MS);
      }),
    ]);
    return selectDistinctiveTerms(profile?.distinctive_vocab);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { id } = await params;
  const authors = await getAuthorCards();
  const author = authors.find((a) => a.id === id || a.slug === id);

  if (!author) {
    notFound();
  }

  const distinctiveTerms = await loadDistinctiveTerms(author.id);

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

      <GenerateStudio author={author} distinctiveTerms={distinctiveTerms} />
    </div>
  );
}
