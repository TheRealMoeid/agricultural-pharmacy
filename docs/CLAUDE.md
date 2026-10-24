# CLAUDE.md

Project reference for the agricultural pharmacy website. Read this first in every new conversation. Update it at the end of every task, in the same patch as the work.

Last updated: 2026-10-24 (phase 1, task 7: Product model. No Jalali dates, image handling or public pages yet)

Status tags used in this file and in the other docs:

- **CONFIRMED**: Moeid approved it, or it comes straight from the client's answers.
- **PLANNED**: part of the approved scope, not built yet. Details may still be refined.
- **OPEN**: undecided or waiting on information. Do not build around it without asking.

---

## 1. The project

A website for داروخانه گیاه‌پزشکی مهندس غیادی, a plant-protection pharmacy in Gonbad-e Kavus, Golestan. Moeid is building it for his father's store.

It is a **catalog and consultation site**. It shows products and experts and makes it easy to call or message the store. There are no prices, no cart, no online payment and no customer accounts. Customers order by phone. The site is Persian only.

The one problem the site has to solve, in the client's words: **increase sales**. Because sales happen by phone, calling must be the easiest action on every page.

Online selling is a possible future step, not part of this project.

## 2. People

| Who | Role |
|---|---|
| Moeid | Developer. Final-semester Computer Engineering student. Also designs the store logo. |
| Rahmatollah Ghayyadi | Store owner and the source of the requirement answers. Also an expert on the site: BSc agronomy and plant breeding, 30 years at the Agricultural Jihad office (retired), plus 8 years in retail. The site shows his degree, experience and role. |
| Habibollah Ghayyadi | Store staff, BSc plant protection. Manages the site from his phone: stock status, product edits. Prepares the product information. The site shows only his degree and specialty, not his experience. |

Habibollah is not technical. Anything he has to do in the admin must work on a phone and take as few taps as possible.

## 3. Working agreement

- **Plan before code.** The technical plan is approved. No application code is written until Moeid says to start.
- **Patch files only.** Every change is delivered as a `.patch` file (plain `git diff` format, applied with `git apply`). Moeid's flow per task: create a branch, apply the patch, commit, merge into `main` when the task is done.
  - One patch per task. Each patch must apply cleanly to `main` as it stands after the previous task was merged.
  - Each delivery comes with a suggested branch name, a commit message, and the apply command.
  - Do not assume anything is in the repo beyond what earlier patches delivered. If unsure whether `main` has changed, ask.
- **Approvals.** Any decision that needs Moeid's approval gets a D-number and is flagged in the reply. Once code starts, approved decisions are also recorded in `docs/DECISIONS.md`.
- **Language.** Moeid writes in English and Persian. Documentation is in English. Everything customers see is Persian. The guide for Habibollah is in Persian.
- **Style.** Moeid prefers natural-sounding writing over anything that reads like generated text.
- **Where things live.** All documentation is in `docs/`, including this file. The repository is LF-only (`.gitattributes`, D24), and patches are generated with LF line endings. Moeid's working copy may show CRLF on Windows, so each delivery says how to check it applies (`git apply --check`).
- **Keep this file honest.** When something changes, move it between the CONFIRMED, PLANNED and OPEN lists. Do not leave stale statements.

## 4. Progress

| Phase | Content | Status |
|---|---|---|
| 0 | Documentation: `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md` | Merged into `main` (now under `docs/`) |
| 1 | Project skeleton, settings, data model, Django admin | In progress, see the task list below |
| 2 | Catalog: product list, product page, filters, search | Not started |
| 3 | Consultation flows, contact buttons, notifications | Not started |
| 4 | Staff stock page, remaining pages, design polish | Not started |
| 5 | Tests, performance pass, staging trial with Habibollah | Not started |
| 6 | Deployment, backups, handover guide | Not started (blocked by D4, hosting) |

### Phase 1 tasks (approved)

One patch and one branch per task. Each task also updates `CLAUDE.md` and `PROJECT_STRUCTURE.md`.

| # | Branch | Content | Status |
|---|---|---|---|
| 1 | `phase1/01-repo-basics` | `.gitignore`, `.gitattributes`, README stub, CHANGELOG, `docs/DECISIONS.md`, docs updated for D18 to D24 | Merged into `main` |
| 2 | `phase1/02-django-skeleton` | `manage.py`, `config/` with split settings, `.env.example`, `requirements/`, empty `apps/` package | Merged into `main` |
| 3 | `phase1/03-dev-database` | `compose.yml` with PostgreSQL for local development, README run steps | Merged into `main` |
| 4 | `phase1/04-persian-text` | pytest-django setup, `apps/core/text.py` (Persian normalization) with tests | Merged into `main` |
| 4b | `phase1/04b-search-alef-folding` | Small fix after task 4: the search key folds آ, أ, إ into ا, so "اب" finds "آب" | Merged into `main` |
| 5 | `phase1/05-site-settings` | `SiteSettings` model, admin, context processor | Merged into `main` |
| 6 | `phase1/06-catalog-reference` | `ProductType`, `Crop`, `Pest`, admin, tests | Merged into `main` |
| 7 | `phase1/07-product-model` | `Product` model, admin, tests | Delivered as a patch, waiting for Moeid to merge |
| 8 | `phase1/08-jalali-dates` | Jalali entry and display of production and expiry dates in the admin (D23), with tests | Not started |
| 9 | `phase1/09-image-uploads` | Upload validation, resize, WebP conversion for the product photo | Not started |
| 10 | `phase1/10-pages-models` | `Expert` and `FaqItem` models, admin | Not started |
| 11 | `phase1/11-consultations-model` | `ConsultationRequest` model, admin inbox with a "mark handled" action | Not started |
| 12 | `phase1/12-articles-and-seed-data` | `Article` model, admin, and a management command that loads clearly fake sample data | Not started |

## 5. Confirmed requirements

From the client's answers in rounds 1 to 3. Where rounds differ, the newest wins.

- Customers are mostly farmers and orchardists.
- The store sells chemical and biological pesticides (fungicides, insecticides, herbicides) and booster fertilizers. Free consultation is central to the business.
- Look: official and professional, green. Uncluttered. No brand logos and no certificates.
- No prices anywhere. Habibollah only sets each product **available / unavailable**. Customers call for price and ordering.
- No cart, no online payment, no customer registration.
- About 50 to 200 products. Filter by product type, search by crop and pest.
- Each product shows: trade name, generic (active-ingredient) name, type, usage, dosage, timing, photo, manufacturer, importer, country of origin (all three as plain text), production date and expiry date, availability.
- Both experts are introduced first on the site. See section 2 for what each one shows.
- Store name with a logo at the top of the site. Moeid designs the logo.
- Articles come after launch, written by the experts and themed by season. The site needs room for them from the start.
- Shipping is by post or Tipax/freight, and the customer pays.
- Farm visits are only within Gonbad-e Kavus county and are paid.
- The store is closed only on Fridays.
- One phone number is shared by the call, WhatsApp, Telegram and Rubika buttons: **09112747628** (international form 989112747628).

## 6. Confirmed technical decisions

IDs come from the approved technical plan.

| ID | Decision |
|---|---|
| D1 | Django + PostgreSQL, server-rendered pages, Tailwind CSS in RTL, light vanilla JS or HTMX. No single-page app. |
| D2 | Django admin for occasional edits, plus one custom mobile "stock page" for Habibollah's frequent job (search plus one big available/unavailable toggle per product). |
| D5 | One shared number in site settings feeds all contact buttons (number above). |
| D6 | Manufacturer, importer and country of origin are plain text fields on each product, not shared tables. |
| D7 | One set of production/expiry dates per product, no per-batch tracking. If no dates are entered, show no date line (do not hide the product). If two batches are in stock, enter the earlier expiry. Still to confirm with the client, see section 8. |
| D8 | Crop/pest tags will exist for products. Until the tags are filled in, search falls back to type filter plus free text. |
| D9 | Farm-visit fee: a show/hide switch and a free-text field in site settings. Hidden by default. |
| D10 | Map: a static location image plus "open in maps" links (Google Maps and one Iranian map app). No embedded map. |
| D11 | Articles: model, admin and templates are built, but the section stays hidden from navigation until the first article is published. |
| D12 | Spam protection on forms: honeypot field, per-IP rate limiting, phone and length validation. No Google reCAPTCHA. A self-hosted challenge only if spam appears. |
| D13 | Dates are stored as Gregorian and displayed in the Jalali calendar. |
| D14 | Text logo placeholder during development, Moeid's SVG swapped in before launch. |
| D15 | All four consultation options: call button, ask-an-expert form, farm-visit form, message buttons. |
| D16 | Measure the site's goal by counting taps on call and message buttons. Mechanism is open, see section 8. |
| D17 | Daily backups of database and media, stored somewhere other than the web server. Restore tested once before launch. |
| D18 | Django 5.2 LTS on Python 3.13. Move to newer versions (for example the next Django LTS and a newer Python) when they are ready. |
| D19 | Dependency tooling: plain pip with `requirements/base.txt`, `dev.txt` and `prod.txt`. |
| D20 | Persian text is written directly in templates and model labels. No gettext. |
| D21 | Local workflow: Django in a virtualenv on Moeid's machine, only PostgreSQL in Docker Compose. Full containers wait for deployment. |
| D22 | The Tailwind build tooling is decided at the start of phase 2. |
| D23 | Production and expiry dates are typed in Jalali in the admin and stored as Gregorian. The conversion is written and tested in the project. |
| D24 | The repository is LF-only, enforced with `.gitattributes`, so patches apply cleanly. |
| D25 | Settings and secrets come from environment variables, read with the `django-environ` package, plus an optional local `.env` file. |
| D26 | PostgreSQL 17, in local development and on the server. If hosting (D4) forces a different version on the server, this gets revisited. |
| D27 | Reference lists (product types, crops, pests): names cleaned on save, a stored unique comparison key blocks spelling variants, slugs made once and kept, alternate names as free text one per line, `Pest` covers pests, diseases and weeds. CONFIRMED (task 6 merged). |
| D28 | `Product`: manufacturer, importer and country of origin are required (the client confirmed every product names them); usage, dosage, timing and photo stay optional; new products default to available. **Proposed in task 7, counts as approved once merged.** |
| D29 | `Product`: an expiry date cannot be entered without a production date (DB-enforced, friendly message); expiry must be strictly after production when both are given. **Proposed in task 7, counts as approved once merged.** |

Other agreed technical points: self-hosted Vazirmatn font and no third-party scripts, images converted to WebP on upload, Docker Compose with Nginx, Gunicorn and PostgreSQL, a staging copy for Habibollah's trial, notification adapter with one implementation per channel.

## 7. Planned features (approved scope, not built)

Public site: home, product list with type filter and search, product page with availability badge and "call to ask the price" button, sticky call bar on every page, ask-an-expert form, farm-visit form, WhatsApp/Telegram/Rubika buttons, experts page, store info and map, FAQ (only if the client provides questions), hidden seasonal articles section.

Staff side: mobile stock page, product add and edit, crop/pest/type management, inbox of consultation requests with a "handled" mark.

Search: Persian-aware. It normalizes ی/ي, ک/ك, digits, ZWNJ and the forms of alef (آ/ا) so products are found however someone types. Stored text keeps its correct spelling.

## 8. Open questions

| # | Question | Notes |
|---|---|---|
| D3 | Which channel notifies the store of new requests: SMS, Telegram or WhatsApp? | Moeid parked this. The adapter stays channel-neutral until he chooses. |
| D4 | Hosting and domain. | Moeid parked this. Only blocks deployment. A .ir domain needs registration details of an Iranian owner; verify requirements before choosing. |
| Fee | Whether to show the farm-visit fee, and what to show. | Moeid will ask his father in person. Default is hidden (D9). |
| Usernames | Telegram username and Rubika link for the store. | The father has none. Moeid will create the accounts. The settings page already has the two fields (Telegram username, Rubika link pasted as given by Rubika, so we don't guess its format), and each button stays hidden while its field is empty. |
| Tags and list | When the product list and the crop/pest tags will be ready. | Moeid will ask his father to prepare them. Habibollah prepares the product information. |
| D7 | Which batch's dates to show when two batches are in stock. | Default is the earlier expiry. Needs the client's confirmation. |
| D16 | How to count button taps: a small counter in our own database, or a self-hosted analytics tool. | Decide when phase 3 starts. |
| Logo | When Moeid's logo SVG will be ready. | Placeholder until then (D14). |
| Map | The store's exact location, and which Iranian map app to link. | Location comes from the client. The settings page has fields for the Google Maps link, the Iranian app's name and link. The static map image field is added when image handling exists (task 9). |
| FAQ | Customers' common pre-purchase questions. | Optional. Without them there is no FAQ page. |
| D22 | Which tool builds the Tailwind CSS. | Decide at the start of phase 2. |

## 9. Content still to collect

- Product list with all fields from section 5, and product photos.
- New photos of the store and of both experts.
- Google Maps location of the store.
- Logo (Moeid).
- Domain name and hosting (D4).

## 10. Next steps

1. Moeid applies the task 7 patch on its own branch, commits it and merges to `main`. Merging approves D28 and D29.
2. Task 8: Jalali entry and display of production and expiry dates in the admin (D23).
3. Moeid talks to his father about the fee, the usernames, and the product list and tags, and creates the Telegram and Rubika accounts.

## 11. Where the detail lives

- `docs/ARCHITECTURE.md`: stack, components, data model, key flows, security, deployment.
- `docs/PROJECT_STRUCTURE.md`: what every planned file and directory is for.
- `docs/DECISIONS.md`: the log of approved decisions, with notes and open items.
- `docs/AGRICULTURAL_PHARMACY_REQUIREMENTS.md` (round 1) and `docs/REQUIREMENTS_ROUND_3_UPDATE.md` (round 3) are in the repository. The round 2 update and the follow-up question files live outside it, with Moeid.
