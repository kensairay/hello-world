# CLAUDE.md

## Project Overview

This is a personal GitHub Pages site using Jekyll with the Cayman theme. It serves as a static landing page hosted via GitHub Pages. There is no application source code, build pipeline, or test suite.

## Repository Structure

```
/
├── README.md      # Site content rendered by GitHub Pages
├── _config.yml    # Jekyll configuration (theme: jekyll-theme-cayman)
└── CLAUDE.md      # This file
```

## Tech Stack

- **Static site generator:** Jekyll (GitHub Pages default)
- **Theme:** jekyll-theme-cayman (configured in `_config.yml`)
- **Hosting:** GitHub Pages

## Development Workflow

- There is no build step, test suite, linter, or CI/CD pipeline.
- Changes to `README.md` are rendered directly by GitHub Pages via Jekyll.
- The `_config.yml` file controls the Jekyll theme; no other Jekyll configuration or custom layouts exist.

## Branching

- `master` is the default/primary branch.
- GitHub Pages serves from the `master` branch.

## Key Conventions

- Commit messages are short and informal.
- No `.gitignore`, no license file, and no contributing guidelines beyond this document.
