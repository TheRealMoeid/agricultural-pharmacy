# PROJECT_STRUCTURE.md

What each file and directory in the repository is for.

Last updated: 2026-10-29 (phase 2, task 1)

**Current state:** the repository contains `.gitignore`, `.gitattributes`, `README.md`, `CHANGELOG.md`, `.env.example`, `manage.py`, `compose.yml` and `pytest.ini` at the root, the Django skeleton (`config/`, `requirements/`), the `apps/core` app (text and phone helpers, `SiteSettings` with its admin and context processor), `apps/catalog` with `ProductType`, `Crop`, `Pest` and `Product`, each with admin, `apps/pages` with `Expert` and `FaqItem` and their admin, `apps/consultations` with `ConsultationRequest` and its admin inbox, `apps/articles` with `Article` and its admin, and the documentation in `docs/`: `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, `DECISIONS.md` and two requirements documents. Everything else below is the **planned** layout. No public page exists yet except a placeholder home page, and the layout may be adjusted when each phase is built. When a path is created, mark it as existing here in the same patch.

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
├─ pytest.ini                    EXISTS
├─ requirements/                 EXISTS (base.txt and dev.txt; prod.txt PLANNED)
├─ config/                       EXISTS
├─ apps/                         EXISTS (core, catalog, pages, consultations and articles exist in part; staff_panel is PLANNED)
│  ├─ core/                      EXISTS (helpers and SiteSettings; ClickEvent and the Jalali filter PLANNED)
│  ├─ catalog/                   EXISTS (reference models, Product, and admin; search and views PLANNED)
│  ├─ consultations/             EXISTS (ConsultationRequest and admin inbox; forms, views and notifications PLANNED)
│  ├─ pages/                     EXISTS (Expert, FaqItem and admin; views PLANNED)
│  ├─ articles/                  EXISTS (Article and admin; views PLANNED)
│  └─ staff_panel/               PLANNED
├─ templates/                    EXISTS (base.html, partials/call_bar.html, pages/home.html; the rest PLANNED)
├─ static/                       EXISTS (css/ and fonts/; js/ and img/ PLANNED)
├─ media/                        PLANNED (not in Git)
├─ tests/                        PLANNED
├─ docker/                       PLANNED
├─ scripts/                      EXISTS (tailwind.py, subset_fonts.py; deploy, backup and restore PLANNED)
└─ docs/                         EXISTS (details in section 12)
```

## 2. Root files

| Path | Purpose |
|---|---|
| `README.md` | What the project is, where the documentation is. Later: how to set up the project locally, run it and run the tests. Short. |
| `CHANGELOG.md` | What changed in each merged task. |
| `.gitignore` | Keeps out virtual environments, `.env`, `media/`, collected static files (`staticfiles/`), the Tailwind program that `scripts/tailwind.py` downloads (`.tools/`), caches, local databases, and `*.patch` files waiting to be applied. |
| `.gitattributes` | Forces LF line endings on every machine so patches apply cleanly (D24). |
| `.env.example` | The list of environment variables with safe example values. The real `.env` is never committed. |
| `pytest.ini` | pytest configuration: uses the dev settings, looks for tests under `apps/`, and rejects unknown markers. |
| `manage.py` | Django's command-line entry point. |

## 3. `requirements/`

Plain pip requirements files (D19).

| Path | Purpose |
|---|---|
| `requirements/base.txt` | EXISTS. Needed everywhere: Django 5.2, django-environ, the PostgreSQL driver, Pillow (added in task 7, for `Product.photo`). |
| `requirements/dev.txt` | EXISTS. Includes `base.txt` and adds pytest and pytest-django, plus fonttools and brotli (only for `scripts/subset_fonts.py` and the font test). |
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

Each app follows the usual Django layout. Files that an app does not need are not created. `apps/__init__.py` exists (empty). Every app below is still planned, except `core`, `catalog`, `pages`, `consultations` and `articles`, which exist in part.

Typical files in an app: `models.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`, `apps.py`, `migrations/`, and `tests/`.

### `apps/core/`
Shared things used by the whole site. It is a Django app since task 5 and is listed in `INSTALLED_APPS`.
- `apps.py`: EXISTS. App configuration.
- `models.py`: `SiteSettings` EXISTS (single row, see `ARCHITECTURE.md`). `ClickEvent` is PLANNED, only if D16 ends up as an own-database counter.
- `admin.py`: EXISTS. The settings page: one screen, no list, no add, no delete.
- `migrations/`: EXISTS. `0001_initial.py` creates `SiteSettings`.
- `context_processors.py`: EXISTS. Puts the settings into every template as `site`, so the call bar always has the number.
- `phone.py`: EXISTS. Iranian mobile numbers: `normalize_iran_mobile()` (any typing to 09XXXXXXXXX), `to_international()`, `format_display()` and the form validator.
- `text.py`: EXISTS. Persian text normalization at three levels: `normalize_letters()` (yeh, kaf, kashida, vowel marks), `normalize_text()` (also whitespace and invisible characters) and `normalize_for_search()` (also ASCII digits, no ZWNJ, alef forms folded into ا, case-folded), plus `normalize_digits()`. Used by search and form validation.
- `jalali.py`: EXISTS (task 8). Gregorian/Jalali conversion, hand-written (D23, D30), not a third-party package.
- `forms.py`: EXISTS (task 8). `JalaliDateField`, a form field that reads/shows Jalali text for a model `DateField`.
- `images.py`: EXISTS (task 9). `load_image()` (check, decode, rotate), `encode_webp()` (shrink and convert to WebP within a byte budget), `process_image()`, the upload validator and `ImageRejected` (D31).
- `fields.py`: EXISTS (task 9). `WebPImageField`, an `ImageField` that stores every new upload as a main WebP image plus a thumbnail when the model is saved, and `WebPFieldFile`, whose `thumb_url` templates use for lists.
- `tests/`: EXISTS. `test_text.py`, `test_phone.py`, `test_jalali.py` and `test_images.py` (no database), `test_site_settings.py`, `test_admin.py`, `test_context_processor.py` and `test_jalali_form_field.py` (these use the database or Django's form machinery).
- `management/commands/seed_sample_data.py`: EXISTS (task 12, D35). Loads clearly fake sample data for development, marked "[نمونه]", and removes it again with `--clear`. DEBUG only. Tested in `tests/test_seed_sample_data.py`.
- `tests/test_static_assets.py` and `tests/test_tailwind_script.py`: EXISTS (phase 2, task 1). They check the built CSS (made by the pinned version, up to date when the program is installed, small, nothing from other sites, only templates scanned), the fonts (small WOFF2, every Persian letter people type is in them, license present) and the Tailwind script (platform choice, checksums, a failed download leaves nothing behind).
- `templatetags/`: the Jalali date filter and small display helpers.
- A small view that receives call and message button taps (OPEN, depends on D16).

### `apps/catalog/`
Products and how people find them. It is a Django app since task 6 and is listed in `INSTALLED_APPS`.
- `apps.py`: EXISTS. App configuration.
- `models.py`: `ProductType`, `Crop` and `Pest` EXIST, built on two shared abstract bases (`ReferenceItem`, `SearchTag`). `Product` EXISTS since task 7.
- `admin.py`: EXISTS. The three reference lists have a search box that ignores typing style; `Product` has filters, a dual-list widget for crops and pests, and a plain search box.
- `migrations/`: EXISTS. `0001_initial.py` creates the three reference tables, `0002_product.py` creates `Product`, `0003` and `0004` adjust its date and photo fields.
- `tests/`: EXISTS. `test_models.py`, `test_admin.py` (reference lists), `test_product.py`, `test_product_admin.py`, `test_product_jalali_admin.py` (task 8), `test_product_photo.py` (task 9) and `conftest.py` with shared fixtures (all use the database).
- `search.py`: PLANNED, for phase 2. The search logic. Kept separate from views so it can be tested on its own.
- `views.py` and `urls.py`: PLANNED, for phase 2. Product list, product detail.

### `apps/consultations/`
Customer requests and how the store is told about them. It is a Django app since task 11 and is listed in `INSTALLED_APPS`.
- `apps.py`: EXISTS. App configuration.
- `models.py`: EXISTS. `ConsultationRequest` (D33).
- `admin.py`: EXISTS. The staff inbox: read-only customer details, status filter, tap-to-call phone, Jalali time, search that ignores digit and letter typing style, and the two actions that switch requests between new and handled.
- `migrations/`: EXISTS. `0001_initial.py` creates the table (it depends on the catalog's latest migration, because of the crop).
- `tests/`: EXISTS. `test_models.py` and `test_admin.py`.
- `forms.py`: PLANNED, phase 3. the ask-an-expert form and the farm-visit form, with validation, honeypot and phone checks.
- `views.py` and `urls.py`: form pages, confirmation, staff inbox.
- `notifications/`: the notification interface in `base.py`, a fake sender for tests, and one file per real channel (SMS, Telegram, WhatsApp). Only the channel Moeid chooses (D3, OPEN) gets a real implementation.
- Rate limiting for the forms (how it is done is decided in phase 3).

### `apps/pages/`
Mostly static content. It is a Django app since task 10 and is listed in `INSTALLED_APPS`.
- `apps.py`: EXISTS. App configuration.
- `models.py`: EXISTS. `Expert` (photo through `WebPImageField`, no thumbnail, D32) and `FaqItem`.
- `admin.py`: EXISTS. Both lists have an editable order column; experts are searchable.
- `migrations/`: EXISTS. `0001_initial.py` creates both tables.
- `tests/`: EXISTS. `test_models.py`, `test_admin.py` and `conftest.py` (uploads go to a temporary folder).
- `views.py` and `urls.py`: EXISTS (phase 2, task 1) as a placeholder `home` view at `/`, only so the base template has a page. The real pages are PLANNED (phase 4): home, experts, contact and location, FAQ.

### `apps/articles/`
Seasonal articles. It is a Django app since task 12 and is listed in `INSTALLED_APPS`.
- `apps.py`: EXISTS. App configuration.
- `models.py`: EXISTS. `Article` (four seasons, plain-text body, optional cover image through `WebPImageField`, `published()` queryset method, D34).
- `admin.py`: EXISTS. A tick box in the list publishes an article; Jalali date entry; filters by publication and season.
- `migrations/`: EXISTS. `0001_initial.py` creates the table.
- `tests/`: EXISTS. `test_models.py`, `test_admin.py` and `conftest.py` (uploads go to a temporary folder).
- `views.py` and `urls.py`: PLANNED. List and detail. The list is not linked from navigation until the first article is published (D11).

### `apps/staff_panel/`
The mobile page Habibollah uses most.
- `views.py` and `urls.py`: the searchable stock list and the toggle action.
- Login and staff permission required.

## 6. `templates/`

Django templates, all in Persian and RTL.

| Path | Purpose |
|---|---|
| `base.html` | EXISTS. Page shell: `<html lang="fa" dir="rtl">`, header with the text logo and a call button (wide screens), footer with address, hours and number, and the call bar. |
| `partials/` | `call_bar.html` EXISTS: the bar fixed to the bottom of the screen on phones. PLANNED: product card, availability badge, message buttons, form field, messages. |
| `catalog/` | Product list and product detail. |
| `consultations/` | The two forms, confirmation page, staff inbox. |
| `pages/` | `home.html` EXISTS as a placeholder. PLANNED: experts, contact, FAQ. |
| `articles/` | Article list and detail. |
| `staff_panel/` | The stock page. |
| `404.html`, `500.html` | Error pages in the same style as the site. |

## 7. `static/`

Files we ship ourselves. Nothing is loaded from other websites.

| Path | Purpose |
|---|---|
| `static/css/` | EXISTS. `input.css` is the Tailwind input (theme, the two `@font-face` rules, only `templates/` scanned). `site.css` is the built, minified result and **is committed** (D36), so nothing needs to build it on the server. Rebuild with `python scripts/tailwind.py build`. |
| `static/js/` | The small amount of JavaScript: the stock toggle, button tap counting, and form niceties. |
| `static/fonts/` | EXISTS. `Vazirmatn-Regular.woff2` and `Vazirmatn-Bold.woff2`, cut down by `scripts/subset_fonts.py` (D37), and `OFL.txt`, the font's license, which has to stay with them. |
| `static/img/` | Logo (text placeholder first, then Moeid's SVG), the static map image, icons, and placeholder product images. |

## 8. `media/` (not in Git)

Files uploaded through the admin: product photos (`products/`), expert photos (`experts/`), article images. Kept out of Git and included in the daily backup. Served by Nginx in production.

## 9. `tests/`

Most tests live next to their app in `apps/<app>/tests/`. This top-level folder is for tests that cross apps. Run everything with `pytest` from the repository root. `pytest.ini` points it at `apps/` for now, and `tests/` is added to `testpaths` when it exists.

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

Small scripts, kept simple. They are Python where they have to run on Windows too.

| Path | Purpose |
|---|---|
| `scripts/tailwind.py` | EXISTS (D36). Downloads the pinned Tailwind program into `.tools/` after checking its checksum (`install`), then builds (`build`) or watches (`watch`) the stylesheet. |
| `scripts/subset_fonts.py` | EXISTS (D37). One-time step that cuts Vazirmatn down to the characters the site uses. Reproduces the committed font files byte for byte. |
| `scripts/deploy.sh` | PLANNED. Pull, migrate, collect static files, restart. |
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
