from django.db import models

from django.db import models
from accounts.models import CustomUser


class PartnerProfile(models.Model):

    SPECIALTY_CHOICES = [
        ("due_diligence", "Due Diligence"),
        ("financial_verification", "Financial Verification"),
        ("legal_review", "Legal Review"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("approved", "Approved"),
        ("under_review", "Under Review"),
        ("inactive", "Inactive"),
    ]

    user = models.OneToOneField(CustomUser,on_delete=models.CASCADE,related_name="partner_profile")
    full_name = models.CharField(max_length=255)
    organization_name = models.CharField(max_length=255)
    specialty = models.CharField(max_length=50,choices=SPECIALTY_CHOICES,default="other")
    phone = models.CharField(max_length=20,blank=True,null=True)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    years_of_experience = models.CharField(max_length=50,blank=True,default="")
    sebi_registration_number = models.CharField(max_length=100,blank=True,default="")
    license_certificate_number = models.CharField(max_length=100,blank=True,default="")
    linkedin_url = models.URLField(blank=True,default="")
    city = models.CharField(max_length=100,blank=True,default="")
    id_type = models.CharField(max_length=50,blank=True,default="")
    id_number = models.CharField(max_length=100,blank=True,default="")

    def __str__(self):
        return self.organization_name



class PartnerKYCDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("government_id", "Government ID"),
        ("professional_certification", "Professional Certification"),
        ("sebi_certificate", "SEBI Registration Certificate"),
        ("bank_proof", "Bank Account Proof"),
        ("address_proof", "Address Proof"),
        ("agreement", "Agreement / NDA"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("under_review", "Under Review"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
        ("requires_update", "Requires Update"),
    ]

    partner = models.ForeignKey(
        PartnerProfile,
        on_delete=models.CASCADE,
        related_name="kyc_documents",
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
    )

    file = models.FileField(
        upload_to="partner_kyc/%Y/%m/",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )

    admin_note = models.TextField(blank=True, default="")

    uploaded_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["partner", "document_type"],
                name="unique_partner_kyc_document_type",
            )
        ]

    def __str__(self):
        return (
            f"{self.partner.organization_name} - "
            f"{self.get_document_type_display()}"
        )
