import { AuthorCard } from "@/components/AuthorCard";
import type { AuthorCardData } from "@/lib/types";

interface AuthorGridProps {
  authors: AuthorCardData[];
}

export function AuthorGrid({ authors }: AuthorGridProps) {
  return (
    <ul
      className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3"
      role="list"
    >
      {authors.map((author) => (
        <li key={author.id}>
          <AuthorCard author={author} />
        </li>
      ))}
    </ul>
  );
}
