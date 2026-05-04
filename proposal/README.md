# Proposal Build Notes

The main proposal draft is in [`main.tex`](main.tex).

## Build

If `latexmk` is available:

```bash
latexmk -pdf main.tex
```

If `pdflatex` and `bibtex` are available:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Output

Expected output:

- `main.pdf`

## Notes

The proposal is written as a thesis-ready draft and can be adapted into a conference-style position paper later.
