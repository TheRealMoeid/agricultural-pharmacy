# PROJECT_STRUCTURE.md

What each file and directory in the repository is for.

Last updated: 2026-10-22

**Current state:** the repository contains `.gitignore`, `.gitattributes`, `README.md`, `CHANGELOG.md`, `.env.example`, `manage.py` and `compose.yml` at the root, the Django skeleton (`config/`, `requirements/` and an empty `apps/` package), and the documentation in `docs/`: `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, `DECISIONS.md` and two requirements documents. Everything else below is the **planned** layout. No app, model, template or static file exists yet, and the layout may be adjusted when each phase is built. When a path is created, mark it as existing here in the same patch.

Tags: **EXISTS** (in the repo now), **PLANNED** (approved scope, not created), **OPEN** (depends on an undecided question).

---

## 1. Overview

```
pharmacy-site/
├─ README.md                     EXISTS
├─ CHANGELOG.md                  EXISTS
├─ .gitignore                    EXISTS
├─ .gitattributes                EXISTS
├─ .env.example                  EXISTS
├─ manage.py                     EXISTS
├─ compose.yml                   EXISTS
├─ requirements/                 EXISTS (base.txt and dev.txt; prod.txt PLANNED)
├─ config/                       EXISTS
├─ apps/                         EXISTS (empty package; the apps inside are PLANNED)
│  ├─ core/                      PLANNED
│  ├─ catalog/                   PLANNED
│  ├─ consultations/             PLANNED
│  ├─ pages/                     PLANNED
│  ├─ articles/                  PLANNED
│  └─ staff_panel/               PLANNED
├─ templates/                    PLANNED
├─ static/                       PLANNED
├─ media/                        PLANNED (not in Git)
├─ tests/                        PLANNED
├─ docker/                       PLANNED
├─ scripts/                      PLANNED
└─ docs/                         EXISTS (details in section 12)
```

## 2. Root files

| Path | Purpose |
|---|---|
| `README.md` | What the project is, where the documentation is. Later: how to set up the project locally, run it and run the tests. Short. |
| `CHANGELOG.md` | What changed in each merged task. |
| `.gitignore` | Keeps out virtual environments, `.env`, `media/`, built static output, caches, local databases, and `*.patch` files waiting to be applied. |
| `.gitattributes` | Forces LF line endings on every machine so patches apply cleanly (D24, proposed). |
| `.env.example` | The list of environment variables with safe example values. The real `.env` is never committed. |
| `manage.py` | Django's command-line entry point. |

## 3. `requirements/`

Plain pip requirements files (D19).

| Path | Purpose |
|---|---|
| `requirements/base.txt` | EXISTS. Needed everywhere: Django 5.2, django-environ, the PostgreSQL driver. Pillow is added with the first image field. |
| `requirements/dev.txt` | EXISTS. Includes `base.txt`. Test tools are added in phase 1, task 4. |
| `requirements/prod.txt` | PLANNED. Production extras such as Gunicorn, added with the deployment work (phase 6). |

## 4. `config/`

Project-level Django configuration. No business logic. All of it exists since phase 1, task 2.

| Path | Purpose |
|---|---|
| `config/settings/base.py` | Settings shared by all environments: installed apps, middleware, templates, static and media, Persian locale, time zone, the configurable admin path. Reads a local `.env` through django-environ (D25). |
| `config/settings/dev.py` | Local development: debug on, a throwaway secret key, local PostgreSQL by default. Works with no `.env`. |
| `config/settings/prod.py` | Production: debug off, HTTPS-only cookies, HSTS, and every secret or host setting required from the environment (it refuses to start if one is missing). |
| `config/urls.py` | Top-level URL routing. Includes each app's URLs and the non-default admin URL. |
| `config/__init__.py`, `config/settings/__init__.py` | Empty. They make the folders Python packages. |
| `config/wsgi.py` | Entry point for Gunicorn. Defaults to the prod settings. |
| `config/asgi.py` | Standard Django file, kept for completeness. |

## 5. `apps/`

Each app follows the usual Django layout. Files that an app does not need are not created. `apps/__init__.py` exists (empty). Every app below is still planned.

Typical files in an app: `models.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`, `apps.py`, `migrations/`, and `tests/`.

### `apps/core/`
Shared things used by the whole site.
- `models.py`: `SiteSettings` (single row) and, if D16 ends up as an own-database counter, `ClickEvent`.
- `context_processors.py`: puts the site settings into every template so the call bar always has the number.
- `text.py`: Persian text normalization (ی/ي, ک/ك, digits, ZWNJ, whitespace). Used by search and form validation.
- `templatetags/`: the Jalali date filter and small display helpers.
- A small view that receives call and message button taps (OPEN, depends on D16).

### `apps/catalog/`
Products and how people find them.
- `models.py`: `Product`, `ProductType`, `Crop`, `Pest`.
- `search.py`: the search logic. Kept separate from views so it can be tested on its own.
- `views.py` and `urls.py`: product list, product detail.
- `admin.py`: product management in the Django admin.

### `apps/consultations/`
Customer requests and how the store is told about them.
- `models.py`: `ConsultationRequest`.
- `forms.py`: the ask-an-expert form and the farm-visit form, with validation, honeypot and phone checks.
- `views.py` and `urls.py`: form pages, confirmation, staff inbox.
- `notifications/`: the notification interface in `base.py`, a fake sender for tests, and one file per real channel (SMS, Telegram, WhatsApp). Only the channel Moeid chooses (D3, OPEN) gets a real implementation.
- Rate limiting for the forms (how it is done is decided in phase 3).

### `apps/pages/`
Mostly static content.
- `models.py`: `Expert`, `FaqItem`.
- `views.py` and `urls.py`: home, experts, contact and location, FAQ.

### `apps/articles/`
Seasonal articles.
- `models.py`: `Article` with a season.
- `views.py` and `urls.py`: list and detail. The list is not linked from navigation until the first article is published (D11).

### `apps/staff_panel/`
The mobile page Habibollah uses most.
- `views.py` and `urls.py`: the searchable stock list and the toggle action.
- Login and staff permission required.

## 6. `templates/`

Django templates, all in Persian and RTL.

| Path | Purpose |
|---|---|
| `base.html` | Page shell: header with logo and call button, sticky call bar on mobile, footer. |
| `partials/` | Reusable pieces: product card, availability badge, call and message buttons, form field, messages. |
| `catalog/` | Product list and product detail. |
| `consultations/` | The two forms, confirmation page, staff inbox. |
| `pages/` | Home, experts, contact, FAQ. |
| `articles/` | Article list and detail. |
| `staff_panel/` | The stock page. |
| `404.html`, `500.html` | Error pages in the same style as the site. |

## 7. `static/`

Files we ship ourselves. Nothing is loaded from other websites.

| Path | Purpose |
|---|---|
| `static/css/` | Tailwind input file and the built CSS (the built file is not committed, OPEN until tooling is chosen). |
| `static/js/` | The small amount of JavaScript: the stock toggle, button tap counting, and form niceties. |
| `static/fonts/` | Vazirmatn, self-hosted. |
| `static/img/` | Logo (text placeholder first, then Moeid's SVG), the static map image, icons, and placeholder product images. |

## 8. `media/` (not in Git)

Files uploaded through the admin: product photos, expert photos, article images. Kept out of Git and included in the daily backup. Served by Nginx in production.

## 9. `tests/`

Most tests live next to their app in `apps/<app>/tests/`. This top-level folder is for tests that cross apps.

| Path | Purpose |
|---|---|
| `tests/e2e/` | Playwright smoke tests with a mobile viewport. |

## 10. `docker/`

| Path | Purpose |
|---|---|
| `docker/Dockerfile` | Builds the Django image. |
| `docker/nginx/` | Nginx configuration. |
| `compose.yml` | EXISTS, at the repository root. Local development stack: PostgreSQL 17 only (D21, D26), bound to localhost with a health check and a named data volume. Django runs outside it. |
| `compose.prod.yml` | Production and staging stack. |

Hosting is undecided (D4), so production details here wait for that decision.

## 11. `scripts/`

Small shell scripts, kept simple.

| Path | Purpose |
|---|---|
| `scripts/deploy.sh` | Pull, migrate, collect static files, restart. |
| `scripts/backup.sh` | Daily database dump and media copy to storage off the web server. |
| `scripts/restore.sh` | Restore from a backup. Tested once before launch. |

## 12. `docs/`

Written alongside the code, not before it.

| Path | Purpose |
|---|---|
| `docs/CLAUDE.md` | EXISTS. Current state, decisions, constraints, open questions and next steps. The first thing to read in any new conversation. Updated with every task. |
| `docs/ARCHITECTURE.md` | EXISTS. Stack, components, data model, flows, security, deployment, and which parts are confirmed, planned or open. |
| `docs/PROJECT_STRUCTURE.md` | EXISTS. This file. |
| `docs/DECISIONS.md` | EXISTS. Log of approved decisions (D-numbers) and their outcome. |
| `docs/AGRICULTURAL_PHARMACY_REQUIREMENTS.md` | EXISTS. Round 1 requirements: the questions and the father's answers, matched. |
| `docs/REQUIREMENTS_ROUND_3_UPDATE.md` | EXISTS. Round 3 requirements. The newest round wins where they differ. |
| `docs/DATA_MODEL.md` | Final field-by-field model, once the models exist. |
| `docs/DEPLOYMENT.md` | Server setup, deploy, rollback, backup and restore. |
| `docs/ADMIN_GUIDE_FA.md` | Persian guide with screenshots for Habibollah: stock toggle, adding a product, handling requests. |
| `docs/CONTENT_GUIDE.md` | Field-by-field rules for entering products, and photo tips. |

The three project documents (`CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`) were first delivered at the repository root. Moeid moved them into `docs/`, and that is where they live now.

## 13. Changes from the approved plan

Small refinements made while writing these documents. None changes the agreed scope. Moeid can veto any of them.

- The `requests` app is named `consultations`, so it is not confused with the well-known `requests` HTTP library.
- The `staff` app is named `staff_panel`, so it is not confused with Django's `is_staff` flag.
- A `core` app was added to hold site settings, Persian text helpers, the Jalali filter and button counting. In the plan these had no home.
- `CLAUDE.md`, `ARCHITECTURE.md` and `PROJECT_STRUCTURE.md` live in `docs/`, together with `DECISIONS.md` and the requirements documents.
- The `locale/` folder from the plan is left out until we decide whether Persian strings sit in templates or go through Django's translation system.

## 14. Rules for keeping this file accurate

- When a task creates a path, change its tag from PLANNED to EXISTS in the same patch.
- If a planned path is dropped or renamed, update this file and `CLAUDE.md` in the same patch.
- Do not describe a file as existing unless it is in `main`.
