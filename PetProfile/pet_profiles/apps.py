from django.apps import AppConfig


class PetProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pet_profiles"
    verbose_name = "Pet Profiles"

    def ready(self):
        import pet_profiles.signals  # noqa: F401
