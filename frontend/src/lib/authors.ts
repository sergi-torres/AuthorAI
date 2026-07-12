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
