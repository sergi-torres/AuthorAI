# Demo Corpus — AutorIA

Texts used to seed the 3 preloaded authors. **All public domain.**

> Downloaded and cleaned during Sprint 0. Re-downloadable via `scripts/download_corpus.py`.

---

## Authors

| Author | Slug | Folder | Approx. word count |
|---|---|---|---|
| Jane Austen (1775–1817) | `austen` | `austen/` | ~330,000 |
| Charles Dickens (1812–1870) | `dickens` | `dickens/` | ~300,000 |
| Edgar Allan Poe (1809–1849) | `poe` | `poe/` | ~70,000 |

All 3 died **well over 70 years ago**, so their works are unambiguously public domain worldwide (US, EU, and Spain). They were chosen as **maximally distinct, instantly recognizable English voices** — Regency social irony · Victorian maximalism · Gothic first-person intensity.

---

## Sources

### Austen
| Title | Source | Cleaning notes |
|---|---|---|
| *Pride and Prejudice* | Project Gutenberg | Remove Gutenberg header/footer, normalize quotes |
| *Emma* | Project Gutenberg | Remove Gutenberg header/footer |
| *Sense and Sensibility* | Project Gutenberg | Remove Gutenberg header/footer |

### Dickens
| Title | Source | Cleaning notes |
|---|---|---|
| *Great Expectations* | Project Gutenberg | Remove Gutenberg header/footer |
| *A Tale of Two Cities* | Project Gutenberg | Remove Gutenberg header/footer |
| *Oliver Twist* | Project Gutenberg | Remove Gutenberg header/footer |

### Poe
| Title | Source | Cleaning notes |
|---|---|---|
| *The Fall of the House of Usher* | Project Gutenberg | Remove Gutenberg header/footer |
| *The Tell-Tale Heart* | Project Gutenberg | Remove Gutenberg header/footer |
| ~13 more selected tales | Project Gutenberg | From *The Works of E. A. Poe*; sources annotated in `poe/SOURCES.md` |

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
