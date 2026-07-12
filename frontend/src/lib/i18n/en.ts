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
    compliance: "EU AI Act · Art. 50",
    complianceNote:
      "AI-generated content is labelled and verifiable, in line with Article 50 of the EU AI Act.",
  },

  hero: {
    title: "Every voice leaves a signature.",
    lead: "AutorIA learns an author's Style DNA from their texts and writes new passages in that voice — side by side with a vanilla model, so the difference is plain to see.",
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
    styleProfileReady: "Voice ready",
  },

  addAuthor: {
    cta: "Add your voice",
    subtitle: "Upload your texts to extract your Style DNA",
    nameLabel: "Author name",
    namePlaceholder: "e.g. María García",
    fileLabel: "Corpus file (.txt or .md)",
    fileButton: "Choose file",
    fileEmpty: "No file selected",
    submit: "Upload & analyze",
    cancel: "Cancel",
    submitting: "Uploading corpus…",
    successTitle: "Corpus received",
    successNote:
      "Style DNA is being computed — your author card will be ready shortly.",
    stillProcessing:
      "Still processing — your card will appear once the analysis finishes.",
    readyTitle: "Voice ready",
    readyNote: (name: string) => `${name} is now in the author gallery.`,
    addAnother: "Add another voice",
    error: "Upload failed — check that the API is running and try again.",
    validationError: "Enter a name and choose a .txt or .md file.",
    customBio: "Custom voice — Style DNA extracted from your uploaded corpus.",
  },

  theme: {
    toggle: "Toggle dark mode",
  },

  studio: {
    vanillaLabel: "Llama 3.3 · vanilla",
    voiceLabel: (author: string) => `AutorIA · ${author} voice`,
    fitCaptionGeneric: (score: number) => `${score}% generic`,
    fitCaptionVoice: (score: number, author: string) =>
      `${score}% ${author}-fit`,
    fitPending: "Style fit — pending",
    generating: "Generating baseline…",
    generatingVoice: (author: string) => `Writing in ${author}'s voice…`,
    generationError: "Generation failed — the model may be unavailable.",
    generationTimeout: "The model is taking longer than expected.",
    retry: "Retry",
    latency: (ms: number) => `${(ms / 1000).toFixed(1)} s`,
    vocabLegend: (author: string) =>
      `Highlights mark ${author}'s signature vocabulary`,
  },

  verify: {
    verifiedTitle: "Verified",
    verifiedSubtitle: "This Authorship Passport is authentic and untampered.",
    invalidTitle: "Verification failed",
  },
} as const;

export type EN = typeof en;
