# ARCHITECTURE.md

Architecture of the agricultural pharmacy website. Nothing here is built yet. This document describes what was agreed in the technical plan, and it says clearly which parts are settled, which are planned detail, and which are still open.

Last updated: 2026-10-22

Status tags:

- **CONFIRMED**: Moeid approved it.
- **PLANNED**: inside the approved scope, details may still change when we get to it.
- **OPEN**: undecided. Do not build around it without asking.

---

## 1. Goals and shape of the system

The site exists to help a plant-protection pharmacy in Gonbad-e Kavus sell more. Sales happen by phone, so the site's job is to show what the store carries, show who the experts are, and make calling or messaging the store as easy as possible. **[CONFIRMED]**

What it is not: a shop. No prices, no cart, no payment, no customer accounts. **[CONFIRMED]**

Who uses it:

| User | What they do | Device |
|---|---|---|
| Customer (farmer, orchardist) | Browse products, search by crop or pest, call, message, send a question or a farm-visit request | Mostly mid-range Android phones, often a slow connection |
| Habibollah (staff) | Flip products between available and unavailable, edit products, answer requests | His phone |
| Moeid (developer, superuser) | Everything, including deployment | Laptop |

## 2. Technology stack

| Layer | Choice | Status |
|---|---|---|
| Language and framework | Python, Django | CONFIRMED (D1) |
| Database | PostgreSQL. Version 17 in local development | CONFIRMED (D1). The version is PROPOSED (D26) |
| Rendering | Server-rendered Django templates, no single-page app | CONFIRMED (D1) |
| Styling | Tailwind CSS, RTL, mobile first | CONFIRMED (D1) |
| Interactivity | Small amount of vanilla JS or HTMX | CONFIRMED (D1) |
| Font | Vazirmatn, self-hosted | CONFIRMED |
| Admin | Django admin plus a custom mobile stock page | CONFIRMED (D2) |
| Images | Resized and converted to WebP on upload | CONFIRMED |
| Web server | Nginx in front of Gunicorn | PLANNED |
| Packaging | Docker Compose (Nginx, Django/Gunicorn, PostgreSQL) | PLANNED |
| Python and Django versions | Python 3.13, Django 5.2 LTS. Move to newer versions when they are ready | CONFIRMED (D18) |
| Dependency tooling | pip with `requirements/` files | CONFIRMED (D19) |
| Local development | Django in a virtualenv, PostgreSQL in Docker Compose | CONFIRMED (D21) |
| Settings and secrets | Environment variables read with django-environ, optional local `.env` file | CONFIRMED (D25) |
| Persian strings | Written directly in templates and model labels, no gettext | CONFIRMED (D20) |
| Tailwind build tooling | Not chosen | OPEN (D22), settle at the start of phase 2 |
| Hosting and domain | Not chosen | OPEN (D4), only blocks deployment |

Why this stack: Moeid knows Python best and will maintain the site alone. Django's admin, forms, migrations and auth cover most of what is needed. With 50 to 200 products there is no reason for anything heavier, and server-rendered pages stay light on slow mobile connections and work well for Persian search engines.

Deliberately left out at the start: Redis, task queues, a JavaScript framework, a CDN, third-party scripts and third-party fonts.

## 3. System overview

```
 Customer / Habibollah (browser)
              |
              v
        Nginx (HTTPS, static files, media files)
              |
              v
     Gunicorn + Django application
        |                |
        v                v
   PostgreSQL      Notification adapter ---> SMS | Telegram | WhatsApp
                   (channel not chosen yet, D3)

   Daily backup job: database dump + media ---> storage off the web server
```

It is one Django project (a monolith) split into small apps. Everything runs in one process group. There is no queue: when a request form is submitted, it is saved first and the notification is sent right after with a short timeout. A failed notification never loses the request, because the staff inbox is the source of truth.

## 4. Components and what each one is responsible for

All are **PLANNED**. App names refine the approved structure slightly (see PROJECT_STRUCTURE.md).

### `core`
Things used everywhere.
- `SiteSettings`: a single row holding the shared phone number, the messaging links, the notification channel, address, hours, map links, and the farm-visit fee text with its show/hide switch.
- A context processor that makes those settings available in every template, so the sticky call bar always has the number.
- Persian text normalization helpers, used by search and by form validation.
- Jalali date display filter (D13).
- Click counting for call and message buttons (D16). Mechanism OPEN.

### `catalog`
Products and how people find them.
- Models: `Product`, `ProductType`, `Crop`, `Pest`.
- Product list with type filter and search, product detail page.
- Persian-aware search (section 8).

### `consultations`
Everything a customer can send or ask.
- Model: `ConsultationRequest`, covering both "ask an expert" and "farm visit".
- The two forms, spam protection (D12), validation.
- Notification adapter and its channel implementations (section 9).
- Staff inbox: list of requests, mark as handled.

### `pages`
Mostly static content.
- Models: `Expert`, `FaqItem`.
- Views: home, experts, contact and location, FAQ.

### `articles`
Seasonal articles by the experts.
- Model: `Article` with a season tag.
- Built from the start but hidden from navigation until the first article is published (D11).

### `staff_panel`
The custom mobile page for Habibollah.
- Searchable product list, one large toggle per row for available/unavailable, saved without a page reload.
- Login required, staff permission required, CSRF protected.

## 5. Data model

Planned fields. Types and constraints are finalized when the models are written in phase 1.

**Product** (D6, D7, D8)
- Trade name, generic (active-ingredient) name, slug
- Product type (foreign key)
- Usage, dosage, timing (text)
- Photo
- Manufacturer, importer, country of origin (plain text, one per product)
- Production date, expiry date (both optional, stored as Gregorian dates)
- `is_available` (the only stock information; no quantity, no price)
- Crops and pests (many-to-many)
- Created and updated timestamps

**ProductType**: name, ordering. A table rather than a fixed list, so types can be added without code changes. Expected starting types: fungicide, insecticide, herbicide, biological, booster fertilizer. The exact list comes from the client.

**Crop** and **Pest**: name, slug, alternate spellings used for search.

**ConsultationRequest**
- Kind: question or farm visit
- Name, phone, message
- Optional crop
- Village or address (farm visits)
- Status: new or handled
- Created time
- Notification result (sent, failed, and why)

**Expert**: name, degree, role, experience (optional), specialty (optional), photo, order. Which fields appear for whom is controlled by which fields are filled in. Rahmatollah has degree, experience and role. Habibollah has degree and specialty only.

**Article**: title, slug, body, season, published flag, date.

**FaqItem**: question, answer, order. Only used if the client provides questions.

**SiteSettings**: see `core` above. A single row.

**ClickEvent** (only if D16 ends up as an own-database counter): kind (call, WhatsApp, Telegram, Rubika), page path, created time. No personal data.

Not in the model, on purpose: price, quantity, customer accounts, orders, batch tracking.

## 6. Key flows

**Customer finds a product.** Opens the product list, filters by type or searches by name, crop or pest, opens the product page. The page shows the details, an availability badge, and a "call to ask the price" button. Unavailable products stay visible and are marked as unavailable.

**Customer contacts the store.** Taps the sticky call bar (a `tel:` link), or a message button, or fills in a form. A tap on a call or message button is counted (D16).

**Customer sends a request.** The form is validated (phone format, length, honeypot, rate limit), the request is saved, the notification adapter is called, and the result is stored on the request. The customer sees a confirmation either way.

**Habibollah updates stock.** Opens the stock page on his phone, finds the product with the search box, taps the toggle. The change is saved immediately.

**Habibollah handles a request.** Opens the inbox, reads the request, calls the customer, marks it handled.

**A new shipment arrives.** Habibollah edits the product's production and expiry dates in the admin (D7). He types them in Jalali and they are stored as Gregorian (D13, D23).

## 7. Frontend and design

- Persian only, RTL throughout. Layout uses logical (start/end) spacing so RTL is the default, not an override. **[PLANNED]**
- Mobile first, large tap targets, high contrast. **[CONFIRMED]**
- Official, professional, green. Uncluttered. No brand logos, no certificate images. **[CONFIRMED]**
- A sticky call bar on mobile and a call button in the header on desktop, on every page. **[CONFIRMED]**
- Store logo in the header. A styled text placeholder until Moeid's SVG is ready (D14). **[CONFIRMED]**
- No requests to other websites: font, scripts and images are all served by us. **[CONFIRMED]**
- Lazy-loaded images, small CSS bundle. **[PLANNED]**
- Map: static image plus links, no embed (D10). **[CONFIRMED]**
- Dates shown in the Jalali calendar (D13). **[CONFIRMED]**

## 8. Search

**[PLANNED]** Postgres is enough at this size. The detail that matters is Persian text.

- Normalize both what is stored and what is typed: Arabic ی/ي and ک/ك to the Persian forms, Persian and Arabic digits to one form, and ZWNJ and extra whitespace handled.
- Match against trade name, generic name, usage text, and the names and alternate spellings of crops and pests.
- Until crop/pest tags exist for the products, search works on names and usage text only (D8).
- This is the most important thing to test (see section 11).

## 9. Notifications

**Channel: OPEN (D3).** The design does not depend on the answer.

- A small interface with one method, "send a notification about this request".
- One implementation per channel. Phase 3 will build the interface and a fake implementation for tests. The real channel is built once Moeid chooses.
- The channel is a setting, so switching later is a configuration change.
- Failures are caught, logged, and stored on the request. They never block the customer.

Things to know when choosing: SMS is the most dependable for non-technical staff. Telegram is the easiest to build. Neither is decided.

## 10. Security and privacy

Mostly **[CONFIRMED]** as part of the approved plan (D12, D17); the exact settings are PLANNED.

- HTTPS only, secure cookies, HSTS, Django's CSRF protection.
- Admin on a non-default URL, strong passwords, two kinds of account: Moeid as superuser, Habibollah as limited staff. The exact permission set for Habibollah is settled in phase 4.
- Forms: honeypot, per-IP rate limiting, Iranian mobile number validation, length limits. No Google reCAPTCHA because it often fails from Iran (D12).
- Customer phone numbers are personal data. They appear only to logged-in staff, never on public pages, never in logs.
- Upload validation for type and size. Images are re-encoded on upload.
- Secrets live in environment variables, never in the repository.
- Daily backups of database and media to somewhere other than the web server. One restore is tested before launch (D17).

## 11. Performance

**[PLANNED]**

- Target: usable on a slow mobile connection.
- WebP images, lazy loading, no third-party scripts, small CSS.
- Indexes on product type, availability and the search fields.
- Caching only if measurements show a need.

## 12. Testing

**[PLANNED]**

- **Unit and integration** (pytest with Django): models and constraints, the Persian search normalization, form validation and rate limiting, stock toggle permissions, notification adapter with a fake sender, and that a failed notification still saves the request.
- **Browser smoke tests** (Playwright, mobile viewport): home to product to call button, each form, the staff toggle.
- **Manual**: a real Android phone, RTL layout check, Lighthouse on key pages, and Habibollah trying the stock page himself on staging.
- **Acceptance**: walk through the Round 3 requirements item by item.

## 13. Deployment

**[PLANNED]**, except hosting and domain, which are **OPEN (D4)**.

- Docker Compose with Nginx, Gunicorn/Django and PostgreSQL.
- A staging copy, used for Habibollah's trial before going live.
- Deploy by pulling from Git and running a short script: migrate, collect static files, restart.
- No CI at the start. It can be added later.
- Iran-based hosting is faster for local customers; foreign hosting can be easier to buy. A .ir domain needs an Iranian owner's registration details. None of this is decided, and prices should be checked when we get there.

## 14. Decision index

| ID | Topic | Status |
|---|---|---|
| D1 | Stack | CONFIRMED |
| D2 | Admin approach | CONFIRMED |
| D3 | Notification channel | OPEN |
| D4 | Hosting and domain | OPEN |
| D5 | Shared contact number (09112747628) | CONFIRMED |
| D6 | Producer, importer, country as per-product text | CONFIRMED |
| D7 | Dates: one set per product, nothing shown if empty | CONFIRMED, batch rule to confirm with client |
| D8 | Crop/pest tags | CONFIRMED that they will exist; readiness date OPEN |
| D9 | Farm-visit fee: hidden by default, switch in settings | CONFIRMED default; actual display OPEN |
| D10 | Map: static image plus links | CONFIRMED |
| D11 | Articles built, hidden at launch | CONFIRMED |
| D12 | Spam protection without reCAPTCHA | CONFIRMED |
| D13 | Jalali date display | CONFIRMED |
| D14 | Logo placeholder until the SVG is ready | CONFIRMED |
| D15 | All four consultation options | CONFIRMED |
| D16 | Count taps on call and message buttons | CONFIRMED; mechanism OPEN |
| D17 | Daily off-server backups | CONFIRMED |
| D18 | Django 5.2 LTS on Python 3.13, upgrade later | CONFIRMED |
| D19 | pip with `requirements/` files | CONFIRMED |
| D20 | Persian written directly in templates, no gettext | CONFIRMED |
| D21 | Local workflow: virtualenv plus PostgreSQL in Docker Compose | CONFIRMED |
| D22 | Tailwind build tooling | OPEN, decide at the start of phase 2 |
| D23 | Dates typed in Jalali in the admin, stored as Gregorian | CONFIRMED |
| D24 | LF-only repository (`.gitattributes`) | CONFIRMED |
| D25 | Settings and secrets from environment variables via django-environ | CONFIRMED |
| D26 | PostgreSQL 17 | PROPOSED in phase 1, task 3 |

## 15. Out of scope and future ideas

- Online ordering and payment: possible later, not part of this project.
- Prices on the site: the client decided against them.
- Customer accounts and order history.
- Multiple languages.
- Per-batch stock tracking.
