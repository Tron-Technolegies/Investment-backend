from django.db import models
from accounts.models import CustomUser, FinanceType
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid
from django.conf import settings
from django.core.validators import FileExtensionValidator
from .private_storage import private_agreement_storage

# Create your models here.
class BusinessProfile(models.Model):

    BUSINESS_TYPE_CHOICES = [
        ("sole_proprietorship", "Sole Proprietorship"),
        ("partnership", "Partnership"),
        ("llp", "LLP"),
        ("pvt_ltd", "Pvt Ltd"),
        ("public_ltd", "Public Ltd"),
        ("other", "Other"),
    ]

    SECTOR_CHOICES = [
        ("technology", "Technology"),
        ("agriculture", "Agriculture"),
        ("healthcare", "Healthcare"),
        ("infrastructure", "Infrastructure"),
        ("manufacturing", "Manufacturing"),
        ("retail", "Retail"),
        ("education", "Education"),
        ("real_estate", "Real Estate"),
        ("logistics", "Logistics"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("approved", "Approved"),
        ("under_review", "Under Review"),
        ("inactive", "Inactive"),
    ]
    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending Verification"),
        ("under_review", "Under Review"),
        ("verified", "Verified"),
        ("requires_change", "Requires Changes"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='business_profile')

    
    full_name = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )
    business_trade_name = models.CharField(max_length=255)

    cin_reg_no = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    business_type = models.CharField(
        max_length=50,
        choices=BUSINESS_TYPE_CHOICES,
        default="pvt_ltd"
    )

    sector = models.CharField(
        max_length=50,
        choices=SECTOR_CHOICES,
        blank=True,
        null=True
    )

    city_hq = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="active"
    )

    business_incorporation_date = models.DateField(
        null=True,
        blank=True
    )
    finance_type = models.ManyToManyField(FinanceType,related_name='businesses')
    finance_amount = models.DecimalField(
            max_digits=15,
            decimal_places=2,
            null=True,
            blank=True
        )
    customers = models.TextField(
            blank=True,
            default=""
        )
    funding_purpose = models.CharField(max_length=255,blank=True,default="")
    preferred_funding_term = models.CharField(max_length=100,blank=True,default="")
    verification_status = models.CharField(
        max_length=30,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending",
    )

    verification_note = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_business_profiles",
    )

    def __str__(self):
        return self.business_trade_name






class BusinessDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("trade_licence", "Trade Licence"),
        ("company_registration", "Company Registration"),
        ("tax_documents", "Tax Documents"),
        ("legal_documents", "Legal Documents"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("requires_change", "Requires Change"),
    ]

    business = models.ForeignKey(
        "businesses.BusinessProfile",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
    )

    document_name = models.CharField(max_length=255)

    file = models.FileField(
        upload_to="business_documents/%Y/%m/",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="uploaded",
    )

    admin_note = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_business_documents",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_business_documents",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business} - {self.document_name}"


from django.conf import settings
from django.db import models


class ProjectFundingInterest(models.Model):
    STATUS_CHOICES = [
        ("interested", "Interested"),
        ("under_review", "Under Review"),
        ("approved", "Approved by Admin"),
        ("rejected", "Rejected by Admin"),
        ("offer_sent", "Offer Sent"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("withdrawn", "Withdrawn"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="funding_interests",
    )

    funding_partner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_funding_interests",
    )

    proposed_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="interested",
    )

    notes = models.TextField(blank=True)
    admin_note = models.TextField(blank=True,default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="reviewed_funding_interests")
    reviewed_at = models.DateTimeField(null=True,blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "funding_partner"],
                name="unique_project_funding_partner",
            )
        ]

    def __str__(self):
        return (
            f"{self.project.reference_no} - "
            f"{self.funding_partner.email}"
        )



class BusinessNDA(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent for Signature"),
        ("signed", "Signed - Awaiting Verification"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    business = models.OneToOneField(
        "businesses.BusinessProfile",
        on_delete=models.CASCADE,
        related_name="nda"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    # NDA document provided by admin
    nda_document = models.FileField(
        upload_to="business_nda/documents/",
        null=True,
        blank=True
    )

    # Signed NDA uploaded by business
    signed_document = models.FileField(
        upload_to="business_nda/signed/",
        null=True,
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    signed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Date the NDA was legally executed
    executed_on = models.DateField(
        null=True,
        blank=True
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_business_ndas"
    )

    admin_note = models.TextField(
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.business.business_trade_name} "
            f"- NDA ({self.status})"
        )



class FundingOffer(models.Model):

    CURRENCY_CHOICES = [
        ("AED", "AED"),
        ("USD", "USD"),
    ]

    FINANCING_TYPE_CHOICES = [
        ("debt", "Debt Financing"),
        ("equity", "Equity Financing"),
        ("islamic", "Islamic Financing"),
    ]

    REPAYMENT_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annually", "Annually"),
        ("maturity", "At Maturity"),
    ]

    interest = models.OneToOneField(
        ProjectFundingInterest,
        on_delete=models.PROTECT,
        related_name="funding_offer",
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="AED",
    )

    financing_type = models.CharField(
        max_length=20,
        choices=FINANCING_TYPE_CHOICES,
    )

    tenure_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )

    annual_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )

    equity_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.01")),
            MaxValueValidator(Decimal("100")),
        ],
    )

    repayment_frequency = models.CharField(
        max_length=20,
        choices=REPAYMENT_CHOICES,
        blank=True,
        default="",
    )

    valid_until = models.DateField()

    terms_and_conditions = models.TextField()

    business_response_note = models.TextField(
    blank=True,
    default="",
    )

    business_responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    business_responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responded_funding_offers",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Offer #{self.pk} - "
            f"{self.amount} {self.currency}"
        )



class FundingAgreement(models.Model):

    STATUS_CHOICES = [
        (
            "pending_investor_signature",
            "Pending Investor Signature",
        ),
        (
            "pending_business_signature",
            "Pending Business Signature",
        ),
        (
            "pending_verification",
            "Pending Admin Verification",
        ),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    funding_offer = models.OneToOneField(
        FundingOffer,
        on_delete=models.PROTECT,
        related_name="agreement",
    )

    agreement_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    agreement_document = models.FileField(
        upload_to="funding_agreements/original/",
        storage=private_agreement_storage,
        validators=[FileExtensionValidator(["pdf"])],
    )

    investor_signed_document = models.FileField(
        upload_to="funding_agreements/investor_signed/",
        storage=private_agreement_storage,
        validators=[FileExtensionValidator(["pdf"])],
        null=True,
        blank=True,
    )

    business_signed_document = models.FileField(
        upload_to="funding_agreements/business_signed/",
        storage=private_agreement_storage,
        validators=[FileExtensionValidator(["pdf"])],
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default="pending_investor_signature",
        db_index=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_funding_agreements",
    )

    investor_signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="investor_signed_agreements",
    )

    investor_signed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    business_signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_signed_agreements",
    )

    business_signed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_funding_agreements",
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    executed_on = models.DateField(
        null=True,
        blank=True,
    )

    admin_note = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.agreement_number)
