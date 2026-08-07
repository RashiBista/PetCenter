# PetCentre

A Django web platform connecting pet owners with veterinarians — appointment booking with real vet-managed availability, real-time chat, a medicine dictionary, an AI assistant, and appointment/vaccination reminders.

The live application is the Django project in [`PetCentre_RegistrationSystem/`](PetCentre_RegistrationSystem). The other top-level folders (`ChatbotApp`, `NotificationSystem`, `PetProfile`, `final_chat`, `petcentral_backend`, `frontend`, `search`, `rag`) are earlier standalone prototypes for individual modules that were since merged into that one unified app — kept here for reference, not part of the running system.

## Features

- **Role-based accounts** — Pet Owner, Veterinarian, and Admin, each with their own dashboard. Signup is verified by a one-time email code (a phone-OTP option exists in the UI but isn't wired to a real SMS provider).
- **Appointment booking** — vets set their own available date/time slots; owners book directly into open slots. Appointments move through Requested → Confirmed → Completed/Cancelled.
- **Real-time chat** — a WebSocket chat room (Django Channels + Redis) opens once an appointment is confirmed, letting the owner and vet message each other live.
- **Payments** — optional Khalti ePayment integration once an appointment is marked Completed, with a manual "Mark as Paid" fallback since chat/confirmation are never gated behind payment.
- **PetPal AI assistant** — a retrieval-augmented chatbot (Google Gemini for embeddings + generation, pgvector for similarity search over a knowledge base stored in Postgres) that answers pet-care questions, shown on the pet owner dashboard.
- **Medicine Dictionary** — a typo-tolerant, symptom-aware search engine (TF-IDF) over a veterinary medicine dataset, with lay-term-to-clinical-term expansion (e.g. "throwing up" → vomiting).
- **Find Nearby Care** — locates registered vet clinics near the owner using PostGIS distance queries.
- **Notifications** — in-app notifications plus email delivery (via Django's mail backend), with toast pop-ups for booking/confirmation events and daily scheduled reminders for upcoming appointments and vaccinations.
- **Admin dashboard** — live (auto-refreshing) system stats, user management, and a medicine catalog editor.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6, Django Channels (ASGI/WebSockets), Daphne |
| Database | PostgreSQL (Neon), PostGIS (geospatial), pgvector (AI similarity search) |
| Real-time | Redis (channel layer + cache) |
| AI | Google Gemini (`google-genai`) — embeddings + generation |
| Payments | Khalti ePayment API v2 |
| Frontend | Django templates, Tailwind CSS |
| Deployment | Docker Compose (web, pgbouncer, Redis), Render |
| CI/CD | GitHub Actions — test suite on push, daily scheduled reminders/cleanup |

## Running Locally

The project runs in Docker; `manage.py` is only meant to be run inside the `web` container.

1. Copy `.env` into `PetCentre_RegistrationSystem/` with at least:

   ```
   DJANGO_SECRET_KEY=...
   DB_HOST=... DB_NAME=... DB_USER=... DB_PASSWORD=...
   GEMINI_API_KEY=...        # PetPal assistant
   KHALTI_SECRET_KEY=...     # optional, for payments
   EMAIL_HOST=... EMAIL_HOST_USER=... EMAIL_HOST_PASSWORD=...
   ```

2. Start the stack:

   ```bash
   cd PetCentre_RegistrationSystem
   docker compose up -d --build
   ```

3. Run migrations and (optionally) seed demo data:

   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py seed_demo_data
   ```

4. Visit `http://localhost:8000`.

Code changes need `docker compose restart web` to take effect — the dev server does not autoreload in this setup.

## Tests

```bash
docker compose exec web python manage.py test
```
