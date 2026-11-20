from django.db import models

# Create your models here.

import uuid

from django.conf import settings
from django.db import models


class BusinessScreening(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("changes_requested", "Changes Requested"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    draft_secret = models.UUIDField(
        default=uuid.uuid4,
        editable=False
    )

    reference = models.CharField(
        max_length=48,
        unique=True,
        null=True,
        blank=True
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="business_screening"
    )

    # Step 1
    company_profile = models.JSONField(
        default=dict,
        blank=True
    )

    # Step 2
    business_overview = models.JSONField(
        default=dict,
        blank=True
    )

    # Step 3
    financial_snapshot = models.JSONField(
        default=dict,
        blank=True
    )

    # Step 4
    financing_requirement = models.JSONField(
        default=dict,
        blank=True
    )

    # Step 5
    legal_compliance = models.JSONField(
        default=dict,
        blank=True
    )

    # Step 6
    business_strengths = models.JSONField(
        default=dict,
        blank=True
    )

    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default="draft"
    )

    accuracy_confirmed = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_screenings"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    review_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference or f"Draft {self.id}"
