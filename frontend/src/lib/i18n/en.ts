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

    // Comparative metrics table (#28)
    metricsTitle: "Measured on this generation",
    metricSentenceLength: "Avg. sentence length",
    metricTtr: "Type–token ratio",
    metricWordCount: "Word count",
    metricTopWords: "Top words",
    metricsColVanilla: "Vanilla",
    metricsColVoice: (author: string) => `AutorIA · ${author}`,
    metricsCaption:
      "Descriptive statistics computed from the text above — not the training corpus.",

    // Generate Passport button (#28)
    passportButton: "Generate Passport",
    passportUnavailable:
      "A signed Authorship Passport will appear here once generation returns one.",
  },

  generate: {
    sectionTitle: "Generate in this voice",
    promptLabel: "Your prompt",
    promptPlaceholder: "Write a paragraph about a foggy London morning…",
    promptHint: (max: number) => `Up to ${max} characters`,
    generateButton: "Generate",
    generatingButton: "Generating…",
    outputSectionLabel: "Generation output",
    idleHeading: "Ready to generate",
    idleBody:
      "Enter a prompt above and press Generate to see the vanilla model alongside AutorIA's voice-conditioned output.",
  },

  styleDna: {
    sectionTitle: "Style DNA",
    collapseToggle: "Toggle Style DNA panel",
    computedAt: (date: string) => `Computed ${date}`,

    // MetricChip labels
    metricDocuments: "documents",
    metricTokens: "tokens",
    metricSentences: "sentences",

    // Radar chart
    radarSectionTitle: "Style signature",
    radarCaption:
      "Normalized to [0–1]; axis ends represent the extremes of the training corpus range.",
    radarAriaLabel:
      "Radar chart showing six normalized style metrics for this author.",
    radarAxes: {
      vocabRichness: "Vocab richness",
      rareWords: "Rare words",
      wordLength: "Word length",
      sentenceLength: "Sentence length",
      subordination: "Subordination",
      dialogue: "Dialogue",
    },

    // Scatter chart
    scatterSectionTitle: "Semantic map",
    scatterCaption:
      "Each point is an author's corpus centroid in UMAP space. The ring shows cluster spread.",

    // Async states
    loading: "Loading Style DNA…",
    empty: "Style DNA not yet computed",
    emptyBody:
      "Upload corpus documents to start the analysis pipeline. This panel will populate automatically once the profile is ready.",
    error: "Could not load Style DNA — check the API and try again.",
    retry: "Retry",

    // Distinctive vocabulary table (#41)
    vocabSectionTitle: "Distinctive vocabulary",
    vocabCaption: "Top terms ranked by TF-IDF against the reference corpus.",
    vocabTermHeader: "Term",
    vocabScoreHeader: "TF-IDF",
    vocabEmpty: "Distinctive vocabulary not yet computed.",
  },

  verify: {
    verifiedTitle: "Verified",
    verifiedSubtitle: "This Authorship Passport is authentic and untampered.",
    invalidTitle: "Verification failed",
  },
} as const;

export type EN = typeof en;
