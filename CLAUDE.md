# ПитайБаце (pitaibace)

## What this project is

ПитайБаце is a **ticket system** built with Django 5. Clients pay for website
services (design, development, maintenance, etc.), and **experts** handle the
resulting work through **tickets**. In short: a client orders a service, pays
for it, and the request is tracked and resolved as a ticket by an assigned
expert.

## App structure

The project package is `pitaibace/`. Business logic is split across these apps:

- **accounts** — users and authentication. A custom `User` model lives here
  (clients and experts). *(Coming next — do not run migrations until it exists.)*
- **departments** — organizational units / teams that experts belong to and
  that tickets can be routed to.
- **services** — the catalog of website services clients can pay for.
- **orders** — a client's purchase of one or more services, including payment.
- **tickets** — the work items experts handle; created from orders and worked
  through to resolution.
- **logs** — audit / activity logging across the system.

## Configuration

- Settings load `SECRET_KEY`, `DEBUG`, and a separate `FERNET_KEY` from a `.env`
  file via `python-dotenv`. See `.env.example` for the required keys.
- `FERNET_KEY` is kept separate from `SECRET_KEY` so it can be rotated
  independently; it is used for symmetric encryption of sensitive data at rest.
- Development database is **SQLite** (`db.sqlite3`).
- `LANGUAGE_CODE = "bg"`, `TIME_ZONE = "Europe/Sofia"`.
- Project-level `templates/` and `static/` directories are configured; the base
  template is `templates/base.html`.

## Conventions — please follow

- **Never use CSS frameworks.** No Bootstrap, no Tailwind, no component
  libraries. All styling is **plain, hand-written CSS** in
  `static/css/style.css`. Keep the design **simple and minimal**.
- **All user-facing strings in templates are in Bulgarian.** Navigation,
  labels, buttons, messages shown to users — write them in Bulgarian. (Code
  identifiers, comments, and internal names stay in English.)
- Use semantic HTML (`header`, `nav`, `main`, `footer`, etc.).

## Development

```bash
# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the dev server (after migrations exist)
python manage.py runserver
```

> Migrations have **not** been run yet — a custom `User` model in `accounts`
> comes first, then migrate.
