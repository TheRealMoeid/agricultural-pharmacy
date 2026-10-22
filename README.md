# Agricultural pharmacy website

A Persian-language catalog and consultation website for داروخانه گیاه‌پزشکی مهندس غیادی, a plant-protection pharmacy in Gonbad-e Kavus, Golestan.

The site shows the store's products and experts and makes it easy to call or message the store. It has no prices, cart, online payment or customer accounts. Customers order by phone.

## Status

Early development. The documentation and the Django skeleton are in place, but there are no models or pages yet. Setup and run instructions will be added with the local database setup (phase 1, task 3).

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
