# Demo Corpus — AutorIA

Texts used to seed the 3 preloaded authors. **All public domain.**

> Downloaded from Project Gutenberg and manually pre-cleaned during Sprint 0. The
> files are committed to the repo, so no download step is needed to run AutorIA.

---

## Authors

| Author | Slug | Folder | Files | Cleaned tokens (measured) |
|---|---|---|---|---|
| Jane Austen (1775–1817) | `austen` | `austen/` | 4 | **643,533** |
| Charles Dickens (1812–1870) | `dickens` | `dickens/` | 4 | **1,147,910** |
| Edgar Allan Poe (1809–1849) | `poe` | `poe/` | 2 | **259,034** |

> Token counts are `cl100k_base` tokens after cleaning, as reported by
> `python scripts/seed_corpus.py --dry-run` on 2026-07-27. They are larger than a word
> count — roughly 1.3–1.5 tokens per word.

All 3 died **well over 70 years ago**, so their works are unambiguously public domain worldwide (US, EU, and Spain). They were chosen as **maximally distinct, instantly recognizable English voices** — Regency social irony · Victorian maximalism · Gothic first-person intensity.

---

## Sources

### Austen
| Title | Source | Cleaning notes |
|---|---|---|
| *Pride and Prejudice* | Project Gutenberg | Remove Saintsbury preface + illustration list (pre-novel content); normalize quotes |
| *Emma* | Project Gutenberg | Clean as downloaded |
| *Sense and Sensibility* | Project Gutenberg | Clean as downloaded |
| *Northanger Abbey* | Project Gutenberg | Clean as downloaded |

### Dickens
| Title | Source | Cleaning notes |
|---|---|---|
| *Great Expectations* | Project Gutenberg | Clean as downloaded |
| *A Tale of Two Cities* | Project Gutenberg | Clean as downloaded |
| *Oliver Twist* | Project Gutenberg | Clean as downloaded |
| *Bleak House* | Project Gutenberg | Clean as downloaded |

### Poe
| Title | Source | Cleaning notes |
|---|---|---|
| *The Works of Edgar Allan Poe, Vol. 1* | Project Gutenberg | Remove opening biographical texts (Lowell + Willis); corpus starts at *Hans Pfaal* |
| *The Works of Edgar Allan Poe, Vol. 2* | Project Gutenberg | Clean as downloaded; end footnotes are Poe's own, retain |

**Vol. 1 contains**: The Unparalleled Adventures of One Hans Pfaal · The Gold-Bug · Four Beasts in One · The Murders in the Rue Morgue · The Mystery of Marie Rogêt · The Balloon Hoax · MS. Found in a Bottle · The Oval Portrait

**Vol. 2 contains**: The Purloined Letter · The Thousand-and-Second Tale of Scheherezade · A Descent into the Maelström · Von Kempelen and His Discovery · Mesmeric Revelation · The Facts in the Case of M. Valdemar · The Black Cat · The Fall of the House of Usher · Silence: A Fable · The Masque of the Red Death · The Cask of Amontillado · The Imp of the Perverse · The Island of the Fay · The Assignation · The Pit and the Pendulum · The Premature Burial · The Domain of Arnheim · Landor's Cottage · William Wilson · The Tell-Tale Heart · Berenice · Eleonora

---

## File format

- UTF-8 encoded `.txt` files
- One file per work
- Original orthography preserved (do NOT modernize; the style is what we measure)
- Gutenberg headers/footers stripped
- Multiple consecutive blank lines collapsed to one

---

## Cleaning, and where it happens

Two stages, deliberately separated:

1. **Manual pre-cleaning (Sprint 0, already applied to the committed files).** Only the
   two cases in the tables above: the Saintsbury preface and illustration list removed
   from *Pride and Prejudice*, and the Lowell/Willis biographical texts removed from
   Poe Vol. 1. Recorded in [`docs/decision_log.md`](../docs/decision_log.md), 2026-06-29.

2. **Automatic cleaning at ingest**, by
   [`ai_pipeline/autoria_ai/extractor/cleaner.py`](../ai_pipeline/autoria_ai/extractor/cleaner.py):
   Gutenberg header/footer stripping, quote and whitespace normalization, and removal of
   `[Illustration]` / `[Illustration: caption]` markup. That last rule was added on
   2026-07-30 after `illustration` ranked into Austen's top-10 signature vocabulary —
   193 raw occurrences across *Pride and Prejudice* and *Sense and Sensibility*.

> There is no `download_corpus.py`. Earlier drafts of this file described one; the
> texts are committed instead, which keeps the seed reproducible without depending on
> Gutenberg being reachable or its files being byte-stable.

---

## Validation

The corpus is "valid" if:

- Each author has ≥ 30,000 cleaned tokens (all three exceed it by two orders of magnitude)
- No file retains Gutenberg-style headers (`*** START OF THE PROJECT GUTENBERG EBOOK ***`)
- Encoding is UTF-8 (no Windows-1252 leftovers)
- `python scripts/seed_corpus.py --dry-run` exits 0 and prints the per-author manifest

```bash
python scripts/seed_corpus.py --dry-run     # validate only, never touches the DB
make seed-full                              # ingest + embeddings + StyleProfiles
```

Chunking is 500 tokens with 50 overlap, byte-identical to the path used by
`POST /api/authors/{id}/documents`, so a live-uploaded author is processed exactly like
a seeded one. Re-seeding is idempotent by `content_hash`.
