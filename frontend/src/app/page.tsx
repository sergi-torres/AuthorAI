import { AuthorGrid } from "@/components/AuthorGrid";
import { AUTHORS } from "@/lib/authors";
import { en } from "@/lib/i18n/en";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          {en.authorSelector.heading}
        </h1>
        <p className="text-muted-foreground">{en.authorSelector.subheading}</p>
      </div>

      <AuthorGrid authors={AUTHORS} />
    </div>
  );
}
