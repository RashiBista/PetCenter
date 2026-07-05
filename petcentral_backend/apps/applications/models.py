import uuid
from django.conf import settings
from django.db import models
from apps.animals.models import Animal


class AdoptionApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        REFERENCE_CHECK = "reference_check", "Reference Check"
        MEET_AND_GREET_SCHEDULED = "meet_and_greet_scheduled", "Meet & Greet Scheduled"
        APPROVED = "approved", "Approved"
        DENIED = "denied", "Denied"
        WITHDRAWN = "withdrawn", "Withdrawn"
        FINALIZED = "finalized", "Finalized"  # adoption completed

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adoption_applications"
    )

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)

    # Snapshot fields captured at time of application (in case profile changes later)
    household_info = models.JSONField(default=dict)  # home type, yard, other pets, kids, etc.
    reason_for_adopting = models.TextField(blank=True)
    availability_for_visit = models.TextField(blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications_reviewed",
    )
    review_notes = models.TextField(blank=True)
    denial_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["animal", "status"])]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Application<{self.applicant} -> {self.animal}> [{self.status}]"


class ApplicationDocument(models.Model):
    """Supporting documents uploaded with an application (ID, landlord approval, etc.)."""

    class DocumentType(models.TextChoices):
        ID = "id", "Government ID"
        LANDLORD_APPROVAL = "landlord_approval", "Landlord Approval"
        VET_REFERENCE = "vet_reference", "Vet Reference"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(AdoptionApplication, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(upload_to="application_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class MeetAndGreet(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(AdoptionApplication, on_delete=models.CASCADE, related_name="meet_and_greets")
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    is_home_visit = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AdoptionRecord(models.Model):
    """Created once an application is finalized. Represents the completed adoption."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(AdoptionApplication, on_delete=models.CASCADE, related_name="adoption_record")
    animal = models.OneToOneField(Animal, on_delete=models.CASCADE, related_name="adoption_record")
    adopter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adoptions")
    adoption_fee_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    contract_document = models.FileField(upload_to="adoption_contracts/", null=True, blank=True)
    finalized_at = models.DateTimeField(auto_now_add=True)


class PostAdoptionCheckIn(models.Model):
    """Scheduled follow-ups after adoption (e.g. 1 week, 1 month, 3 months)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    adoption_record = models.ForeignKey(AdoptionRecord, on_delete=models.CASCADE, related_name="check_ins")
    due_date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
