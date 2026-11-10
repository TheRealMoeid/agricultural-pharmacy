# Agricultural pharmacy website

A Persian-language catalog and consultation website for داروخانه گیاه‌پزشکی مهندس غیادی, a plant-protection pharmacy in Gonbad-e Kavus, Golestan.

The site shows the store's products and experts and makes it easy to call or message the store. It has no prices, cart, online payment or customer accounts. Customers order by phone.

## Status

Early development. The documentation, the Django skeleton, the local database setup, the site settings, the full catalog data model (product types, crops, pests, products), the experts and FAQ models, the consultation request model with its admin inbox and the articles model are in place. The public pages so far are a placeholder home page, the product list at `/products/` (type filter, Persian-aware search) and the product page at `/products/<slug>/`, with the call-to-ask-the-price button and Jalali dates, and the two consultation forms at `/consultation/`. A new request is announced in the store's own Telegram chat through a bot.

## Notifications

A submitted consultation request is always saved first, then the store is told about it over Telegram, so the admin inbox stays the source of truth even if a message never goes out.

To receive them locally, set these two in your `.env` (see `.env.example`):

```
DJANGO_TELEGRAM_BOT_TOKEN=123456789:AA...
DJANGO_TELEGRAM_CHAT_ID=-1001234567890
```

Get the token from [@BotFather](https://t.me/BotFather) (`/newbot`), then start a chat with your new bot (or add it to a group) and get the chat id -- the simplest way is to send it any message and read `https://api.telegram.org/bot<token>/getUpdates`.

With either value left empty or missing, nothing is sent: the request is still saved, and its notification result is recorded as "not attempted". This is the normal state for local development without a bot configured.

## Running it locally

You need Python 3.13, Git, and Docker (Docker Desktop on Windows or macOS). Django runs on your machine in a virtualenv, and only PostgreSQL runs in Docker.

```
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell or cmd)
source .venv/bin/activate         # macOS and Linux

pip install -r requirements/dev.txt

docker compose up -d db           # starts PostgreSQL in the background
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The admin is then at http://localhost:8000/admin/ (the path comes from `DJANGO_ADMIN_URL`). The first thing in it is "تنظیمات سایت" (site settings), already filled in with the store's details.

No `.env` file is needed for local work: the defaults in `config/settings/dev.py` match `compose.yml`. Copy `.env.example` to `.env` only if you want to change something.

Useful commands:

| Command | What it does |
|---|---|
| `docker compose ps` | Shows whether the database is running and healthy |
| `docker compose stop db` | Stops the database and keeps its data |
| `docker compose down -v` | Removes the database container **and all its data**. Use it to start from scratch |
| `docker compose logs db` | Shows the database log, useful when something fails to connect |

If port 5432 is already used on your machine (for example by a local PostgreSQL), change the first number in the `ports` line of `compose.yml` to another port, such as 5433, and set `DATABASE_URL` in `.env` with the same port.

## Sample data

To try the site with something in it, load clearly fake data (every name starts with "[نمونه]"):

```
python manage.py seed_sample_data           # load it, safe to repeat
python manage.py seed_sample_data --clear   # remove it again, nothing else is touched
```

It only runs with `DEBUG` on, which is the case locally and never in production.

## Styles

The CSS is built with the Tailwind standalone program, so no Node.js or npm is needed. The built file, `static/css/site.css`, is committed: running or deploying the site needs nothing extra. Only when you change how a template looks:

```
python scripts/tailwind.py install   # once: downloads the pinned version (about 110 MB)
python scripts/tailwind.py watch     # rebuilds while you work
python scripts/tailwind.py build     # final build; commit static/css/site.css
```

A test fails if `site.css` is out of date. Use only normal and bold text in templates: those are the two weights of the font.

## Running the tests

With the virtualenv active, run this from the repository root:

```
pytest
```

The text and phone tests need no database. The rest (site settings, catalog, admin) need `docker compose up -d db` to be running. pytest-django creates and removes its own test database, so your development data is not touched.

## Staging on Render (free tier)

A free, shareable staging copy — for testing and demos, not for real customers or real data (D44).

1. Push this repository to GitHub (or GitLab/Bitbucket).
2. In the [Render dashboard](https://dashboard.render.com), choose **New +** → **Blueprint**, and point it at the repo. Render reads `render.yaml` at the repo root and proposes a free web service plus a free PostgreSQL database.
3. When prompted for `DJANGO_ADMIN_URL`, type a hard-to-guess path (not `admin/`).
4. Deploy. The first build runs migrations; once it finishes, open `https://<service-name>.onrender.com/<your-admin-path>/` and run `createsuperuser` from the **Shell** tab in the Render dashboard (`python manage.py createsuperuser`).

**What the free tier gives up**, so there are no surprises:

- **The service sleeps.** After 15 minutes with no traffic it spins down; the next visitor waits about a minute while it wakes back up. Fine for sharing a link with a tester, not for anything that must respond instantly.
- **Uploaded files are not kept.** Render's free web services have no persistent disk: every product photo, expert photo or article image uploaded through the admin is lost the next time the service redeploys, restarts, or simply spins down from being idle. The database survives (it is a separate service); photos do not. Re-upload after any gap in traffic, or treat photos as something to test only right after a deploy.
- **The free database expires.** It is deleted 30 days after creation (14-day grace period to upgrade first). For a short testing window this does not matter; for anything longer, recreate it or move to a paid plan before day 30.
- **It is genuinely staging, not production.** No backups, no SLA, and Render can restart either service at any time. This is the free tier Moeid asked to accept for testing and sharing (D44); `docs/ARCHITECTURE.md` section 13 still has the real deployment plan (Nginx, Gunicorn, PostgreSQL in Docker Compose) for when hosting (D4) is chosen.

To update the staging site, push to `main`: Render redeploys automatically.

## Documentation

Everything lives in `docs/`. Start with `docs/CLAUDE.md`, which holds the current state, decisions and next steps.

| File | What it covers |
|---|---|
| `docs/CLAUDE.md` | Project reference: state, progress, decisions, open questions, next steps |
| `docs/ARCHITECTURE.md` | Stack, components, data model, flows, security, deployment |
| `docs/PROJECT_STRUCTURE.md` | What each file and directory is for |
| `docs/DECISIONS.md` | Log of approved decisions |
| `docs/AGRICULTURAL_PHARMACY_REQUIREMENTS.md` | Round 1 requirements |
| `docs/REQUIREMENTS_ROUND_3_UPDATE.md` | Round 3 requirements (the newest one wins where rounds differ) |

## Planned stack

Python 3.13, Django 5.2 LTS, PostgreSQL, server-rendered templates, Tailwind CSS (RTL), Docker Compose for deployment.
