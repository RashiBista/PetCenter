# Add these lines to petcentre/settings.py.

INSTALLED_APPS += [
    "pet_profiles.apps.PetProfilesConfig",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Temporary only, while the current project has no real authentication.
PET_PROFILES_DEMO_MODE = True
PET_PROFILES_DEMO_USERNAME = "demo_pet_owner"

# Existing chatbot route in the current core app.
PET_PROFILE_CHATBOT_URL_NAME = "core:chatbot"

# Blank means use the appointment list included in pet_profiles.
# Later, replace with the external module URL name, such as "appointments:list".
PET_PROFILE_APPOINTMENT_URL_NAME = ""
