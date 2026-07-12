import Link from "next/link";

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { en } from "@/lib/i18n/en";
import type { AuthorCardData } from "@/lib/types";

interface AuthorCardProps {
  author: AuthorCardData;
}

export function AuthorCard({ author }: AuthorCardProps) {
  return (
    <Link
      href={`/author/${author.slug}`}
      className="group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
    >
      <Card className="h-full transition-shadow duration-200 group-hover:shadow-md group-focus-visible:shadow-md cursor-pointer">
        <CardHeader>
          <CardTitle className="text-lg">{author.name}</CardTitle>
          {author.has_style_profile && (
            <div data-slot="card-action">
              <Badge variant="secondary" className="shrink-0">
                {en.badge.styleProfileReady}
              </Badge>
            </div>
          )}
        </CardHeader>

        <CardContent>
          <p className="text-muted-foreground leading-relaxed">{author.bio}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            {en.authorSelector.documentCount(author.n_documents)}
          </p>
        </CardContent>

        <CardFooter>
          <span className="text-sm font-medium text-primary">
            {en.authorSelector.cardCta}
          </span>
        </CardFooter>
      </Card>
    </Link>
  );
}
