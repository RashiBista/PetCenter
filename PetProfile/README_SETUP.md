# PetProfile module

This folder is a self-contained Django project. It has its own `manage.py`, virtual environment, database configuration, templates, static files, and media directory. It does not edit `petcentral_backend`, `NotificationSystem`, `ChatbotApp`, or any other folder.

## Included actions

1. Edit profile details.
2. Change the pet photo.
3. Edit the medical summary.
4. Redirect the Assistant button to the chatbot module.
5. View all medical records, vaccination history, and prescriptions.
6. Redirect Upcoming to the open-list module, with a local appointment list as a fallback.
7. Add another pet and switch between pets.

## First run

From the repository root:

```bash
cd PetProfile
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_petprofile
python manage.py createsuperuser
python manage.py runserver 8003
```

Open:

- Profile UI: `http://127.0.0.1:8003/`
- Admin: `http://127.0.0.1:8003/admin/`

## Connect the chatbot and open-list modules

Update `.env` with the real routes:

```env
CHATBOT_URL=http://127.0.0.1:8001/chat/?pet_id={pet_id}
OPEN_LIST_URL=http://127.0.0.1:8002/open-list/?pet_id={pet_id}
```

Restart the PetProfile server after editing `.env`.

## PostgreSQL option

The first run uses SQLite so the module can be tested immediately. To use PostgreSQL, create a database and user, then change `.env`:

```env
USE_POSTGRES=True
DB_NAME=petprofile_db
DB_USER=petprofile_user
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Run migrations again after changing databases.
