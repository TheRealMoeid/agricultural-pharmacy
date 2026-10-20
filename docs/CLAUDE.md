# CLAUDE.md

Project reference for the agricultural pharmacy website. Read this first in every new conversation. Update it at the end of every task, in the same patch as the work.

Last updated: 2026-10-20 (documentation phase, no application code yet)

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
- **Keep this file honest.** When something changes, move it between the CONFIRMED, PLANNED and OPEN lists. Do not leave stale statements.

## 4. Progress

| Phase | Content | Status |
|---|---|---|
| 0 | Documentation: `CLAUDE.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md` | Delivered as a patch, waiting for Moeid to merge |
| 1 | Project skeleton, settings, data model, Django admin | Not started |
| 2 | Catalog: product list, product page, filters, search | Not started |
| 3 | Consultation flows, contact buttons, notifications | Not started |
| 4 | Staff stock page, remaining pages, design polish | Not started |
| 5 | Tests, performance pass, staging trial with Habibollah | Not started |
| 6 | Deployment, backups, handover guide | Not started (blocked by D4, hosting) |

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

Other agreed technical points: self-hosted Vazirmatn font and no third-party scripts, images converted to WebP on upload, Docker Compose with Nginx, Gunicorn and PostgreSQL, a staging copy for Habibollah's trial, notification adapter with one implementation per channel.

## 7. Planned features (approved scope, not built)

Public site: home, product list with type filter and search, product page with availability badge and "call to ask the price" button, sticky call bar on every page, ask-an-expert form, farm-visit form, WhatsApp/Telegram/Rubika buttons, experts page, store info and map, FAQ (only if the client provides questions), hidden seasonal articles section.

Staff side: mobile stock page, product add and edit, crop/pest/type management, inbox of consultation requests with a "handled" mark.

Search: Persian-aware. It normalizes ی/ي, ک/ك, digits and ZWNJ so products are found however someone types.

## 8. Open questions

| # | Question | Notes |
|---|---|---|
| D3 | Which channel notifies the store of new requests: SMS, Telegram or WhatsApp? | Moeid parked this. The adapter stays channel-neutral until he chooses. |
| D4 | Hosting and domain. | Moeid parked this. Only blocks deployment. A .ir domain needs registration details of an Iranian owner; verify requirements before choosing. |
| Fee | Whether to show the farm-visit fee, and what to show. | Moeid will ask his father in person. Default is hidden (D9). |
| Usernames | Telegram and Rubika usernames for the store. | The father has none. Moeid will create the accounts. Links usually need a username, not a phone number. Verify the Rubika link format before building. |
| Tags and list | When the product list and the crop/pest tags will be ready. | Moeid will ask his father to prepare them. Habibollah prepares the product information. |
| D7 | Which batch's dates to show when two batches are in stock. | Default is the earlier expiry. Needs the client's confirmation. |
| D16 | How to count button taps: a small counter in our own database, or a self-hosted analytics tool. | Decide when phase 3 starts. |
| Logo | When Moeid's logo SVG will be ready. | Placeholder until then (D14). |
| Map | The store's exact location, and which Iranian map app to link. | Location comes from the client. |
| FAQ | Customers' common pre-purchase questions. | Optional. Without them there is no FAQ page. |
| Setup | Python and Django versions, dependency tooling, Tailwind build tooling, and whether Persian strings live in templates or go through Django's translation system. | Small implementation choices. Settle at the start of phase 1 and record them in `docs/DECISIONS.md`. |

## 9. Content still to collect

- Product list with all fields from section 5, and product photos.
- New photos of the store and of both experts.
- Google Maps location of the store.
- Logo (Moeid).
- Domain name and hosting (D4).

## 10. Next steps

1. Moeid applies the documentation patch on its own branch, commits it and merges to `main`.
2. Propose the phase 1 task breakdown (skeleton, settings, models, admin) for Moeid's approval, with one patch per task.
3. Settle the small setup questions in section 8 at the start of phase 1.
4. Moeid talks to his father about the fee, the usernames, and the product list and tags.

## 11. Where the detail lives

- `ARCHITECTURE.md`: stack, components, data model, key flows, security, deployment.
- `PROJECT_STRUCTURE.md`: what every planned file and directory is for.
- The five requirements documents from rounds 1 to 3 live outside this repository, with Moeid.
