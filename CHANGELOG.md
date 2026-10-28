# Changelog

What changed in each merged task, newest first.

## Unreleased

### 2026-10-28 — Phase 1, task 12: articles and sample data

- Started the `articles` app with `Article`: title, a plain-text body (a blank line starts a new paragraph), a season (spring, summer, autumn or winter), an optional cover image, a publish box and a publication date. Proposed D34.
- An article is a draft until published. The date is typed in Jalali in the admin; if the article is published without one, today's date (store time) is filled in, and the database refuses a published article without a date. The cover image is stored like a product photo (D31): a small WebP plus a thumbnail. The list in the admin has a tick box that publishes an article in one step, and filters by publication and season. `Article.objects.published()` gives the published articles, newest first, for the public pages; the section stays hidden until there is one (D11).
- Added `python manage.py seed_sample_data`: loads clearly fake sample data for development (types, crops, pests, 12 products, two experts, FAQ items, four articles, four requests), every name marked "[نمونه]". Safe to repeat. `--clear` removes exactly the marked rows. It refuses to run unless DEBUG is on, so fake dosages cannot reach a live site. No photos are created. Proposed D35.
- 55 new tests. D33 is recorded as approved (task 11 merged). Phase 1 is complete once this is merged.

### 2026-10-27 — Phase 1, task 11: consultation requests and the admin inbox

- Started the `consultations` app with `ConsultationRequest`: kind (question or farm visit), name, phone, message, optional crop, village or address, status (new or handled), creation time, and a place for the notification result (not attempted, sent, failed, plus the reason; phase 3 fills it in). Proposed D33.
- Rules: name and phone are always required and the phone is stored as 09XXXXXXXXX whatever way it was typed; a question needs its text, a farm visit needs the village or address and its text is optional; the text is limited to 2000 characters. A name that is only spaces, or text that grows past its column when cleaned, gives a normal form message. Deleting a crop keeps the requests that name it.
- The admin is the inbox. Customer details are read-only and only the status can be changed; requests cannot be added there. Open requests are listed first, newest first in each group; the time is shown in Jalali in store time; the phone is a tap-to-call link; search finds phones typed with Persian digits and names typed with Arabic letters. Two actions mark the selected requests as handled or put them back to new. Someone with view-only rights cannot run them.
- The phone number is left out of `__str__()`, so it does not end up in logs or admin messages.
- 50 new tests. D32 is recorded as approved (task 10 merged).

### 2026-10-26 — Phase 1, task 10: experts and FAQ

- Started the `pages` app with two models and their admin pages. `Expert`: name and degree are required; role, experience, specialty and photo are optional, and a line left empty is simply not shown, which is how Rahmatollah (degree, experience, role) and Habibollah (degree, specialty) get different profiles from the same model. `FaqItem`: question, answer (several lines allowed) and order; the FAQ page will exist only if there are questions.
- Text is cleaned on save like in the catalog (Arabic yeh and kaf, spacing). A required value that is only spaces is refused with a normal form message, and so is a value that grows past its column when cleaned.
- Expert photos reuse `WebPImageField` with their own numbers: 480 px, about 30 KB, no thumbnail (proposed D32). Files go to `media/experts/`.
- Both lists have an editable order column in the admin; lower comes first.
- 41 new tests. D31 is recorded as approved (task 9 merged).

### 2026-10-25 — Phase 1, task 9: product photos

- Many visitors are in villages with weak mobile coverage, so photos are built to be small, not just converted. Every new product photo is checked and stored as two WebP files: a main image (longest side at most 800 px) and a thumbnail (at most 320 px) for list pages, `<name>.webp` and `<name>_thumb.webp`. Each has a byte budget (about 50 KB and 12 KB): quality starts at 80 and is lowered step by step to 40, and if that is not enough the picture is made up to 15% smaller a few times (never under 200 px). Proposed D31.
- Only real JPEG, PNG or WebP files (judged by content, not name) up to 10 MB and 40 megapixels are accepted; the orientation flag is applied and all camera metadata (including any GPS position) is dropped. Files get random names. The original upload is not kept.
- Added `apps/core/images.py` (`load_image()`, `encode_webp()`, `process_image()`, the validator, `ImageRejected`) and `apps/core/fields.py` (`WebPImageField`, an `ImageField` that does the conversion in `pre_save`, so it works the same from the admin, a script or a test, and `photo.thumb_url` for templates). `Product.photo` uses it (migration `0004`); the same field can be reused for the expert photos in task 10.
- Bad uploads are refused in the admin with a specific Persian message next to the field (not an image, wrong format, too big, too many pixels). The validator's error code is `image_rejected`: using Django's own `invalid_image` made Django replace these messages with its generic one.
- Catalog tests now write uploads to a temporary folder instead of the real `media/`.
- 63 new tests. The static map image field (see `CLAUDE.md`, section 8) is not part of this task.

### 2026-10-24 — Phase 1, task 8: Jalali dates in the admin

- Added `apps/core/jalali.py`: Gregorian/Jalali conversion, ported from the standard published algorithm (the same one jalaali-js and most Persian software use), not a third-party package (D23). Tested against several independently sourced Nowruz dates, the published reference `jalCal()` output for 1390-1393, and an exhaustive day-by-day round trip from 1800 to 2250.
- Added `apps/core/forms.py` with `JalaliDateField`: a text field that reads Persian, Arabic-Indic or ASCII digits with "/" or "-" separators, parses them as a Jalali date, and converts to/from the Gregorian date the model actually stores. Wired into `ProductAdmin` for `production_date` and `expiry_date` via `formfield_overrides`, so both fields are now typed and shown in Jalali in the admin, matching D23.
- Known limitation, not something this patch can fix on its own: the standard arithmetic Jalali algorithm has a documented, currently unresolved one-day discrepancy against the true astronomically-observed Iranian calendar for the Esfand 1403 / Farvardin 1404 boundary (around 20-21 March 2025) -- see the new note in `docs/DECISIONS.md`. 77 new tests.

### 2026-10-23 — Phase 1, task 7: product model

- Added the `Product` model to `apps/catalog`: trade name, generic (active-ingredient) name, type, usage, dosage, timing, photo, manufacturer, importer, country of origin, production/expiry dates, availability, crops and pests. Admin page with filters, a dual-list widget for crops and pests, and a plain search box.
- Trade name, generic name, type, manufacturer, importer and country of origin are required, matching what the client confirmed every product names. Usage, dosage, timing, photo and both dates are optional. Dates are entered as Gregorian for now; Jalali entry is task 8.
- A product type in use can no longer be deleted (`PROTECT`), so an in-use type cannot silently orphan products.
- Added Pillow to `requirements/base.txt` for the new photo field (resizing and WebP conversion come in task 9; for now the field stores whatever image is uploaded, with a basic extension check).
- The slug is made once from the trade name, the way the task 6 reference lists already work, and does not change if the name is corrected later.
- 39 new tests (184 in total, catalog alone). Proposed D28 and D29.

### 2026-10-23 — Phase 1, task 6: catalog reference models

- Started the `catalog` app with `ProductType`, `Crop` and `Pest`, their first migration, and admin pages.
- Names are cleaned on save (Arabic yeh/kaf, spacing) and checked against a stored comparison key, so "قارچ‌کش" and "قارچکش", or a name typed on an Arabic keyboard, cannot be added twice. Slugs are made once from the name (Persian letters kept) and do not change when a name is fixed later.
- Crops and pests have a list of alternate names (one per line) and a `search_keys()` method for the search work in phase 2. Product types have an `order` field, editable straight from the list.
- The admin search box for the three lists ignores typing style, half spaces and آ/ا, and checks alternate names too.
- 108 new tests. Proposed D27.

### 2026-10-22 — Phase 1, task 5: site settings

- `apps/core` is now a Django app. Added the single-row `SiteSettings` model (store details, shared number, Telegram username, Rubika link, map links, notification channel, farm-visit fee switch) with its first migration, a one-page admin, and the `site` context processor.
- Added `apps/core/phone.py`: any common way of typing an Iranian mobile number becomes 09XXXXXXXXX, with the international (`989...`) and display (`0911 274 7628`) forms derived from it.
- 48 new tests (120 in total). A test fails if a model change is missing its migration.
- `pytest.ini` ignores one Django 6.0 upgrade notice about URL fields.

### 2026-10-22 — Phase 1, task 4b: alef folding in the search key

- `normalize_for_search()` now folds آ, أ, إ and ٱ into plain ا, because people type ا for آ. Stored text is unchanged. New tests cover it.

### 2026-10-22 — Phase 1, task 4: Persian text helper

- Added pytest and pytest-django (`requirements/dev.txt`, `pytest.ini`).
- Added `apps/core/text.py`: `normalize_letters`, `normalize_text`, `normalize_digits` and `normalize_for_search`, with 66 tests in `apps/core/tests/test_text.py`.
- Recorded D26 (PostgreSQL 17 in development and production) as approved, and fixed the wording in `ARCHITECTURE.md` that made it sound development-only.

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
