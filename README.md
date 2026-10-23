# Agricultural pharmacy website

A Persian-language catalog and consultation website for داروخانه گیاه‌پزشکی مهندس غیادی, a plant-protection pharmacy in Gonbad-e Kavus, Golestan.

The site shows the store's products and experts and makes it easy to call or message the store. It has no prices, cart, online payment or customer accounts. Customers order by phone.

## Status

Early development. The documentation, the Django skeleton, the local database setup, the site settings and the catalog's reference lists (product types, crops, pests) are in place, but there are no products or public pages yet.

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

## Running the tests

With the virtualenv active, run this from the repository root:

```
pytest
```

The text and phone tests need no database. The rest (site settings, catalog, admin) need `docker compose up -d db` to be running. pytest-django creates and removes its own test database, so your development data is not touched.

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
