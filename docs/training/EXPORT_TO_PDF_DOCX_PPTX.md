# Exporting training materials (PDF / DOCX / PPTX)

Sources live in `docs/training/` as Markdown.

## Requirements

- [Pandoc](https://pandoc.org/) 3.x (optional, on trainer laptop)
- For PPTX from presentations: pandoc with `--slide-level=2` or use [Marp](https://marp.app/) on `presentations/*.md`

## Examples (run from repo root)

```bash
# Single role guide → PDF
pandoc docs/training/roles/01-super-admin.md -o exports/super-admin-guide.pdf

# Role guide → DOCX
pandoc docs/training/roles/05-support-worker.md -o exports/support-worker-guide.docx

# Introduction slides → PPTX
pandoc docs/training/presentations/00-introduction.md -o exports/hmore-intro.pptx -t pptx
```

Create `exports/` locally; **do not commit** generated binaries with real screenshots unless approved.

## Branding

Use organisation letterhead for external PDFs. Colours in app: forest green `#0f3b32`, cream `#f6f3ee`, teal accents (see web Tailwind config).
