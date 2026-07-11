# InfraBench arXiv Draft

This directory contains a working arXiv-style draft for an InfraBench benchmark
paper.

## Files

- `main.tex`: paper source.
- `references.bib`: bibliography.

## Current Positioning

The draft frames InfraBench as a reproducible benchmark for AI agents on
infrastructure operations, with Kubernetes as the first dataset scope. It is
written as a benchmark/dataset paper rather than a model paper.

The author line currently uses:

```text
Thomas Chaigneau
Independent Researcher / Kubeply
```

Change this before submission if the preferred affiliation is different.

## Before arXiv Submission

- Tag an immutable dataset release, such as `kubeply/kubernetes-core v0.1`.
- Publish or attach immutable benchmark run artifacts for every result table.
- Re-run the selected model evaluations against the tagged dataset release.
- Decide whether to include local preliminary results or a smaller verified
  result set.
- Add a human or oracle sanity-check section if available.
- Confirm the exact arXiv category, likely `cs.SE` with `cs.AI` cross-listing.
- Obtain arXiv endorsement if the submitting account is not already endorsed in
  the selected category.

## Build

Requires a local TeX distribution with `pdflatex` and `bibtex`. From this
directory:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The source intentionally uses standard LaTeX packages only.
