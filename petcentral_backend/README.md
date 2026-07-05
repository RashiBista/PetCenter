# PetCentral — Rescue & Adoption Backend (Django + DRF + PostgreSQL)

## Structure

```
petcentral_backend/
├── config/                  # project settings, urls, wsgi
├── apps/
│   ├── accounts/             # custom User model, adopter profiles, auth
│   ├── shelters/              # shelter orgs + staff memberships
│   ├── animals/                # pet listings, photos, medical records, search
│   ├── applications/            # adoption application workflow + records
│   ├── fosters/                  # foster volunteer + assignment tracking
│   ├── messaging/                 # conversations, messages, notifications
│   └── common/                     # shared permission classes
└── requirements.txt
```

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

createdb petcentral   # or via psql: CREATE DATABASE petcentral;

python manage.py makemigrations accounts shelters animals applications fosters messaging
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Set these environment variables (or put them in a `.env` file, read via `python-decouple`):
`DJANGO_SECRET_KEY`, `DEBUG`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `CORS_ALLOWED_ORIGINS`.

## Auth

JWT via `djangorestframework-simplejwt`.

- `POST /api/auth/register/` — public adopter self-registration
- `POST /api/auth/token/` — obtain access + refresh token (login)
- `POST /api/auth/token/refresh/`
- `GET/PATCH /api/auth/me/` — current user profile (includes adopter profile)

Shelter staff accounts are provisioned by a platform admin (via Django admin or an
internal onboarding endpoint you'd add) — public registration only creates adopters.

## Core API Surface

| Resource | Endpoint | Notes |
|---|---|---|
| Shelters | `/api/shelters/` | Public read; write limited to that shelter's own staff |
| Animals | `/api/animals/` | Public browse/search with filters (species, breed, size, age range, good-with-X, location) |
| Animal favorite | `POST /api/animals/{id}/favorite/` | Toggle favorite for logged-in adopter |
| Saved searches | `/api/saved-searches/` | Adopter's saved filter sets, used for match alerts |
| Applications | `/api/applications/` | Adopter sees own; staff sees their shelter's |
| Application decide | `POST /api/applications/{id}/decide/` | Staff moves status forward (enforces valid transitions) |
| Application withdraw | `POST /api/applications/{id}/withdraw/` | Applicant cancels |
| Application finalize | `POST /api/applications/{id}/finalize/` | Staff completes adoption, creates AdoptionRecord, auto-denies competing applications |
| Foster volunteers | `/api/foster-volunteers/` | Shelter-managed foster roster |
| Foster assignments | `/api/foster-assignments/` | Links animal ↔ foster, auto-updates animal status |
| Conversations/Messages | `/api/conversations/` | Tied optionally to an application |
| Notifications | `/api/notifications/` | In-app notification feed |

Interactive schema/docs: wire up `drf-spectacular`'s `SpectacularAPIView` /
`SpectacularSwaggerView` in `config/urls.py` to get a live Swagger UI at `/api/docs/`.

## Application Status Flow

```
submitted → under_review → reference_check → meet_and_greet_scheduled → approved → finalized
                 └──────────────┴──────────────────────┴──────────────┘
                                       ↘ denied (from most states)
```

Allowed transitions are enforced server-side in `applications/views.py`
(`ALLOWED_TRANSITIONS`) so shelter staff can't skip steps by mistake, and finalizing
one application automatically denies other open applications for the same animal.

## Key Design Decisions

- **UUID primary keys** everywhere — safer for public-facing IDs in URLs, and makes
  future multi-region/replication easier.
- **Animal.status is the single source of truth** for availability; it's updated
  automatically by application, foster, and adoption-finalization actions rather than
  left for the frontend to manage.
- **Snapshot fields on AdoptionApplication** (`household_info`) copy the adopter's
  profile info at submission time, so a shelter reviewing an old application sees what
  the adopter said *then*, even if their profile changes later.
- **Role-based permissions** (`apps/common/permissions.py`) check shelter staff
  membership per-object, so one shelter's staff can never edit another shelter's animals
  or applications.
- **Celery + Redis** are wired into settings for async work you'll want soon: saved-search
  match emails, meet-and-greet reminders, and post-adoption check-in nudges.

## Suggested Next Additions

- `donations` app (one-off + recurring, optionally tied to a specific animal)
- Geo search using PostGIS (`django.contrib.gis`) if you want true radius search instead
  of city/state string filters
- Async tasks: `saved_search_match_check`, `send_checkin_reminder`, `meet_and_greet_reminder`
- Rate limiting on `/api/applications/` to prevent application spam
- Audit log on `AdoptionApplication` status changes (who/when/why) if you need a full history
