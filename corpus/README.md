# Demo Corpus — AutorIA

Texts used to seed the 3 preloaded authors. **All public domain.**

> Downloaded and cleaned during Sprint 0. Re-downloadable via `scripts/download_corpus.py`.

---

## Authors

| Author | Slug | Folder | Approx. word count |
|---|---|---|---|
| Jane Austen (1775–1817) | `austen` | `austen/` | ~330,000 |
| Charles Dickens (1812–1870) | `dickens` | `dickens/` | ~440,000 |
| Edgar Allan Poe (1809–1849) | `poe` | `poe/` | ~150,000 |

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

## Re-downloading

```bash
python scripts/download_corpus.py --author all
# or for a single author:
python scripts/download_corpus.py --author dickens
```

The script fetches from the source URLs noted in each subfolder's `SOURCES.md` (added in Sprint 0).

---

## Validation

The corpus is "valid" if:

- Each author has ≥ 30,000 cleaned tokens
- No file has Gutenberg-style headers (`*** START OF THE PROJECT GUTENBERG EBOOK ***`)
- Encoding is UTF-8 (no Windows-1252 leftovers)
- `python scripts/seed_corpus.py --dry-run` runs without errors