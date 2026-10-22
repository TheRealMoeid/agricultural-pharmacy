# Changelog

What changed in each merged task, newest first.

## Unreleased

### 2026-10-22 — Phase 1, task 3: dev database

- Added `compose.yml` with PostgreSQL 17 for local development (bound to localhost, with a health check and a named volume).
- Added the local run steps to `README.md`.
- Checked the settings against a real PostgreSQL: `migrate` runs and the admin login page renders in Persian and RTL.
- Recorded D25 as approved and proposed D26 (PostgreSQL 17).

### 2026-10-21 — Phase 1, task 2: Django skeleton

- Added `manage.py`, `config/` (settings split into base, dev and prod, URLs, WSGI and ASGI entry points), an empty `apps/` package, `requirements/base.txt` and `dev.txt`, and `.env.example`.
- Settings read from environment variables through django-environ (D25). Dev works with no `.env`; prod refuses to start without its required variables.
- Persian language, Asia/Tehran time zone, configurable admin path.
- Recorded D24 as approved and D25 as proposed. Updated the docs and the phase 1 task list.

### 2026-10-20 — Phase 1, task 1: repo basics

- Added `.gitignore`, `.gitattributes`, `README.md`, `CHANGELOG.md` and `docs/DECISIONS.md`.
- Recorded the setup decisions D18 to D23 (Django 5.2 LTS on Python 3.13, pip with requirements files, Persian written directly in templates, local workflow, Tailwind tooling deferred to phase 2, Jalali date entry).
- Updated `docs/CLAUDE.md`, `docs/ARCHITECTURE.md` and `docs/PROJECT_STRUCTURE.md` to match: documents now live in `docs/`, phase 1 task list added.

### 2026-10-20 — Phase 0: project documentation

- Added `CLAUDE.md`, `ARCHITECTURE.md` and `PROJECT_STRUCTURE.md` (now under `docs/`).
