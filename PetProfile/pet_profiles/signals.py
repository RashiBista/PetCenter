from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MedicalSummary, Pet


@receiver(post_save, sender=Pet)
def create_medical_summary(sender, instance, created, **kwargs):
    if created:
        MedicalSummary.objects.get_or_create(pet=instance)
