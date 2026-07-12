import { AuthorGrid } from "@/components/AuthorGrid";
import { getAuthorCards } from "@/lib/authors";
import { en } from "@/lib/i18n/en";

export default async function HomePage() {
  const authors = await getAuthorCards();

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-4">
        <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
          {en.hero.title}
        </h1>
        <p className="max-w-[58ch] text-lg leading-relaxed text-muted-foreground">
          {en.hero.lead}
        </p>
      </section>

      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h2 className="font-heading text-2xl font-semibold tracking-tight">
            {en.authorSelector.heading}
          </h2>
          <p className="text-muted-foreground">
            {en.authorSelector.subheading}
          </p>
        </div>

        <AuthorGrid authors={authors} />
      </section>
    </div>
  );
}
