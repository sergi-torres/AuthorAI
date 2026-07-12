import { listAuthors } from "@/lib/api";
import { en } from "@/lib/i18n/en";
import type { AuthorCardData } from "@/lib/types";

/**
 * Seeded author data used until GET /api/authors is available.
 * Replace this constant with a lib/api.ts call; components receive AuthorCardData via props.
 */
export const AUTHORS: AuthorCardData[] = [
  {
    id: "austen",
    name: "Jane Austen",
    slug: "austen",
    has_style_profile: true,
    n_documents: 3,
    bio: "English novelist known for sharp social observation and irony, author of Pride and Prejudice and Sense and Sensibility.",
  },
  {
    id: "dickens",
    name: "Charles Dickens",
    slug: "dickens",
    has_style_profile: true,
    n_documents: 3,
    bio: "Victorian novelist who chronicled London's poor with unforgettable characters, from Oliver Twist to Ebenezer Scrooge.",
  },
  {
    id: "poe",
    name: "Edgar Allan Poe",
    slug: "poe",
    has_style_profile: true,
    n_documents: 15,
    bio: "American master of the macabre and detective fiction, pioneer of the short story form and author of The Raven.",
  },
];

/** Indexed by id for fast lookup in dynamic route pages. */
export const AUTHORS_BY_ID: Readonly<Record<string, AuthorCardData>> =
  Object.fromEntries(AUTHORS.map((a) => [a.id, a]));

/**
 * Live author list: GET /api/authors merged with seed bios, falling back to
 * the seed constant when the API is unreachable (demo-safe — the selector
 * must never render empty because the backend is down).
 */
export async function getAuthorCards(): Promise<AuthorCardData[]> {
  try {
    const summaries = await listAuthors();
    return summaries.map((summary) => ({
      ...summary,
      bio: AUTHORS_BY_ID[summary.id]?.bio ?? en.addAuthor.customBio,
    }));
  } catch {
    return AUTHORS;
  }
}
