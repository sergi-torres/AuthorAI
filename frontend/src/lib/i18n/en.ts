/**
 * English UI strings for AutorIA.
 * All user-visible text must be sourced from this file — no hardcoded literals in components.
 * Bios live in src/lib/authors.ts seed data, not here.
 */
export const en = {
  app: {
    title: "AutorIA",
    tagline:
      "AI-powered authorship studio — generate text in the voice of great authors.",
  },

  nav: {
    home: "Authors",
  },

  authorSelector: {
    heading: "Choose an author",
    subheading:
      "Select a literary voice to explore its Style DNA or generate new text.",
    cardCta: "Explore →",
    documentCount: (n: number) => `${n} ${n === 1 ? "document" : "documents"}`,
  },

  authorDetail: {
    comingSoon: "Full studio coming soon.",
    backToAuthors: "← Back to authors",
  },

  badge: {
    styleProfileReady: "StyleProfile ready",
  },
} as const;

export type EN = typeof en;
