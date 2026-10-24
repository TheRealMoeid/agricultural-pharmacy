# DECISIONS.md

Log of the decisions that needed Moeid's approval. The IDs are the same D-numbers used in `CLAUDE.md` and `ARCHITECTURE.md`. A new decision gets the next free number and is added here in the same patch that records it.

Last updated: 2026-10-24

## Approved

All of these were approved on 2026-10-20, in the planning conversation, unless a different date is given.

| ID | Decision | Notes |
|---|---|---|
| D1 | Django + PostgreSQL, server-rendered pages, Tailwind CSS in RTL, a little vanilla JS or HTMX. No single-page app. | Moeid knows Python best and will maintain the site alone. At 50 to 200 products nothing heavier is needed. |
| D2 | Django admin for occasional edits, plus one custom mobile stock page for Habibollah (search plus one available/unavailable toggle per product). | Habibollah is not technical and works from his phone. |
| D5 | One shared number for the call and message buttons: 09112747628 (international form 989112747628). | Stored once in site settings. Telegram and Rubika links usually need a username, see the pending list below. |
| D6 | Manufacturer, importer and country of origin are plain text fields on each product. | Simplest to enter. Drawback: the same company can be typed in slightly different ways. |
| D7 | One set of production and expiry dates per product. If no dates are entered, no date line is shown and the product is not hidden. With two batches in stock, enter the earlier expiry. | The batch rule still needs the client's confirmation. |
| D8 | Crop/pest tags will exist for products. Until they are filled in, search works on type filter plus free text. | Moeid will ask his father to prepare them. |
| D9 | Farm-visit fee: a show/hide switch and a free-text field in site settings, hidden by default. | What to show is still open. Moeid will ask his father. |
| D10 | Map: a static location image plus "open in maps" links (Google Maps and one Iranian map app). No embed. | Embeds can load slowly or fail from Iran. |
| D11 | Articles: model, admin and templates are built, the section stays hidden from navigation until the first article is published. | |
| D12 | Spam protection: honeypot, per-IP rate limiting, phone and length validation. No Google reCAPTCHA. | A self-hosted challenge only if spam appears. |
| D13 | Dates are stored as Gregorian and displayed in the Jalali calendar. | |
| D14 | Text logo placeholder during development, Moeid's SVG before launch. | |
| D15 | All four consultation options: call button, ask-an-expert form, farm-visit form, message buttons. | |
| D16 | Count taps on call and message buttons to measure the goal (more sales). | The mechanism is still open. |
| D17 | Daily backups of database and media, stored somewhere other than the web server. One restore tested before launch. | |
| D18 | Django 5.2 LTS on Python 3.13. Move to newer versions when they arrive. | Django 5.2 is supported until April 2028. Python 3.15 was considered and left for later: Django 5.2 does not support it, and the first Django version that does (6.1) is not an LTS. Availability of ready-made builds of Pillow and the PostgreSQL driver for 3.15 was not checked. The likely upgrade is the next Django LTS (6.2, due April 2027) together with a newer Python, once the packages we use support it. |
| D19 | Dependency tooling: plain pip with `requirements/base.txt`, `dev.txt` and `prod.txt`. | Nothing extra to learn, works the same inside Docker later. |
| D20 | Persian text is written directly in templates and model labels. No gettext. | The site is Persian only. Django's admin already ships a Persian translation. |
| D21 | Local workflow: Django runs on Moeid's machine in a virtualenv, only PostgreSQL runs in Docker Compose. The full container setup (Nginx, Gunicorn) waits for the deployment phase. | |
| D22 | The Tailwind build tooling is decided at the start of phase 2, not phase 1. | Nothing in phase 1 uses it. |
| D23 | Habibollah types production and expiry dates in Jalali in the admin. They are stored as Gregorian. The conversion is written in the project and tested, not taken from a package. | Django's admin date field is Gregorian, which would confuse a Persian-speaking, non-technical user. |
| D24 | Line endings: the repository is LF-only, enforced with `.gitattributes`. | Approved 2026-10-21 by merging phase 1, task 1. Moeid's working copy had Windows (CRLF) line endings, while patches are generated with LF. Mixing the two can make a patch fail to apply. |
| D25 | Settings and secrets come from environment variables, read with the `django-environ` package, with an optional local `.env` file. | Approved 2026-10-22. It mainly saves writing the list and database-URL parsing ourselves. The alternative was reading `os.environ` by hand, to avoid one dependency. |
| D26 | PostgreSQL major version: 17, in local development (`compose.yml`) and on the server. | Approved 2026-10-22 by merging phase 1, task 3. Version 17 is mature and supported until late 2029. Version 18 is newer but changes how the Docker image stores data. If hosting (D4) forces a different version on the server, this gets revisited. |
| D28 | `Product.manufacturer`, `importer` and `country_of_origin` are required fields, matching the client's round 3 answer that every product names them. `usage`, `dosage`, `timing` and the photo stay optional, since the full product list and photos are still being collected. New products default to `is_available = True`. | Approved 2026-10-24 by merging phase 1, task 7. |
| D29 | A product's expiry date cannot be entered without a production date (enforced at the database level, with a friendly message through `full_clean()`). Both empty is fine (D7); expiry alone is treated as a data-entry mistake, not a case the site needs to support. Expiry must also be strictly after production when both are given. | Approved 2026-10-24 by merging phase 1, task 7. |

## Proposed, waiting for approval

| ID | Decision | Notes |
|---|---|---|
| D30 | Production and expiry dates are typed and shown in Jalali in the admin (D23), using a hand-written, line-by-line port of the standard published Jalali/Gregorian algorithm -- the same one jalaali-js, moment-jalaali and most Persian software use -- rather than a third-party package, matching D23's "written in the project, not taken from a package". | Proposed 2026-10-24 in phase 1, task 8. Counts as approved once the task is merged, but the note below needs a read regardless: the algorithm has a known, currently unresolved limitation worth knowing about, not something to silently accept. |

**About D30's algorithm — please read:** the arithmetic algorithm behind Jalali date conversion is the industry standard (it is what jalaali-js, moment-jalaali, and most Persian software use), but it is an approximation of the true calendar, which is officially defined by the actual astronomical equinox in Tehran, not a fixed arithmetic rule. For the vast majority of years the two agree exactly, and this patch's tests check that against several independently sourced historical Nowruz dates. However, there is a documented, currently open bug in this exact algorithm (jalaali/jalaali-js issue #52) affecting the boundary between Jalali 1403 and 1404 -- in Gregorian terms, 20-21 March 2025. A production or expiry date entered anywhere in roughly that one-day window would show one day later in the admin than Iran's true official calendar says. Fixing this properly would mean replacing the arithmetic conversion with a real astronomical (ephemeris-based) calculation, which is a much larger piece of work for an edge case that, by the nature of the Persian calendar, repeats only once every several decades and affects only dates within about a day of a single Nowruz. My recommendation is to accept this as-is and move on; flagging it is the point of this note, not asking you to choose between two built options.
| D27 | How the three reference lists (product types, crops, pests) store names. (1) The name is cleaned on save but keeps its correct spelling. (2) A comparison key made by `normalize_for_search()` is stored with each row and must be unique, so spelling variants (half space, Arabic kaf or yeh, ا for آ) cannot be entered twice. (3) The slug is made once from the name, keeps Persian letters, and never changes when the name is edited. Product types get a slug too, which the plan did not list. (4) Alternate names for crops and pests are free text, one per line. (5) `Pest` covers pests, diseases and weeds, because herbicides and fungicides need a target as much as insecticides do. | Proposed 2026-10-23 in phase 1, task 6. Counts as approved once the task is merged. Cost of (2): two different words that share a key, such as آفت and افت, cannot both be in the same list. The editor gets a message naming the existing entry. Cost of (3): a link keeps the old spelling after a rename. Alternative for (4): a separate table of alternate names, more flexible but more screens for Habibollah. |

## Open (parked or waiting for information)

| ID | Question | State |
|---|---|---|
| D3 | Which channel notifies the store of new requests: SMS, Telegram or WhatsApp. | Parked by Moeid. The notification adapter stays channel-neutral. |
| D4 | Hosting and domain. | Parked by Moeid. Only blocks deployment. A .ir domain needs registration details of an Iranian owner, check before choosing. |
| D7 | Which batch's dates to show when two batches are in stock. | Default above, client to confirm. |
| D9 | Whether and how to show the farm-visit fee. | Moeid will ask his father. |
| D16 | How the taps are counted: own database or a self-hosted analytics tool. | Decide when phase 3 starts. |
| Usernames | Telegram and Rubika usernames for the store. | The store has none. Moeid will create the accounts. Verify the Rubika link format before building. |
| Tags | When the product list and crop/pest tags will be ready. | Moeid will ask his father. |
