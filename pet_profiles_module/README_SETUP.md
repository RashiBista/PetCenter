# Pet Profile Module Setup

This folder contains a standalone Django app named `pet_profiles`.

## 1. Copy the app

Copy the complete `pet_profiles` folder into the same directory as `manage.py`.

Expected project structure:

```text
petcentre_project/
├── manage.py
├── petcentre/
│   ├── settings.py
│   └── urls.py
├── core/
└── pet_profiles/
```

## 2. Install image support

Add Pillow to `requirements.txt`:

```text
Django>=5.2,<6.0
Pillow>=10.4,<12.0
```

Then install dependencies:

```bash
python -m pip install -r requirements.txt
```

## 3. Update `petcentre/settings.py`

Add the app:

```python
INSTALLED_APPS = [
    # existing apps
    "pet_profiles.apps.PetProfilesConfig",
]
```

Add media settings:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Temporary demo mode, because the existing project currently uses click-through login screens:

```python
PET_PROFILES_DEMO_MODE = True
PET_PROFILES_DEMO_USERNAME = "demo_pet_owner"
```

Chatbot integration:

```python
PET_PROFILE_CHATBOT_URL_NAME = "core:chatbot"
```

When the separate appointment list app is ready, set its list URL name here:

```python
PET_PROFILE_APPOINTMENT_URL_NAME = "appointments:list"
```

Leave it blank to use the appointment list included in this app:

```python
PET_PROFILE_APPOINTMENT_URL_NAME = ""
```

After real login is implemented, change demo mode to:

```python
PET_PROFILES_DEMO_MODE = False
```

## 4. Update `petcentre/urls.py`

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("pets/", include("pet_profiles.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 5. Create database tables

```bash
python manage.py makemigrations pet_profiles
python manage.py migrate
```

## 6. Create demo data

```bash
python manage.py seed_pet_profile
```

The command prints the URL to open, usually:

```text
http://127.0.0.1:8000/pets/1/
```

## 7. Run the project

```bash
python manage.py runserver
```

## 8. Connect the dashboard button

In the pet owner dashboard template:

```html
<a href="{% url 'pet_profiles:home' %}">Pet profile</a>
```

## Button routing

- Edit profile: `pet_profiles:edit`
- Photo: `pet_profiles:photo_edit`
- Medical summary pen: `pet_profiles:medical_summary_edit`
- Assistant: redirects to the URL name in `PET_PROFILE_CHATBOT_URL_NAME`
- View all records: `pet_profiles:records`
- Upcoming: redirects to the configured appointment module, or opens the local appointment list
- Add another pet: `pet_profiles:create`

## Chatbot context

The assistant redirect adds these query parameters:

```text
?pet_id=1&pet_name=Pet+A
```

The chatbot view can read them with:

```python
pet_id = request.GET.get("pet_id")
pet_name = request.GET.get("pet_name")
```

## Production checklist

1. Set `PET_PROFILES_DEMO_MODE = False`.
2. Protect the rest of the project with real Django authentication.
3. Use cloud object storage for uploaded photos and medical attachments.
4. Validate medical attachment file types if attachments are enabled for public users.
5. Connect the external appointments app through `PET_PROFILE_APPOINTMENT_URL_NAME`.
6. Run tests with `python manage.py test pet_profiles`.
