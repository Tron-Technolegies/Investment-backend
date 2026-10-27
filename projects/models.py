from django.db import models
from accounts.models import CustomUser
from businesses.models import BusinessProfile
from partners.models import PartnerProfile


class Project(models.Model):

    STAGE_CHOICES = [
        ("documents_pending", "Documents Pending"),
        ("submitted", "Submitted"),
        ("admin_review", "Admin Review"),
        ("partner_assigned", "Partner Assigned"),
        ("partner_review", "Partner Review"),
        ("final_admin_review", "Final Admin Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    business = models.ForeignKey(BusinessProfile,on_delete=models.CASCADE,related_name="projects")
    reference_no = models.CharField(max_length=30,unique=True,blank=True)
    project_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100)
    funding_target = models.DecimalField(max_digits=15,decimal_places=2)
    estimated_start_date = models.DateField(null=True,blank=True)
    estimated_end_date = models.DateField(null=True,blank=True)
    description = models.TextField()
    stage = models.CharField(max_length=50,choices=STAGE_CHOICES,default="documents_pending")
    assigned_partner = models.ForeignKey(PartnerProfile,on_delete=models.SET_NULL,related_name="assigned_projects",null=True,blank=True)
    PARTNER_REVIEW_RESULT_CHOICES = [
        ("verified", "Verified"),
        ("requires_change", "Requires Change"),
    ]
    partner_review_result = models.CharField(max_length=30,choices=PARTNER_REVIEW_RESULT_CHOICES,null=True,blank=True,)
    partner_review_note = models.TextField(blank=True,default="",)
    partner_reviewed_at = models.DateTimeField(null=True,blank=True,)
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_final_reviewed_at = models.DateTimeField(null=True,blank=True,)


    def __str__(self):
        return f"{self.reference_no} - {self.project_name}"

class ProjectStageHistory(models.Model):
    project = models.ForeignKey(Project,on_delete=models.CASCADE,related_name="stage_history")
    from_stage = models.CharField(max_length=50,choices=Project.STAGE_CHOICES,null=True,blank=True)
    to_stage = models.CharField(max_length=50,choices=Project.STAGE_CHOICES)
    changed_by = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,related_name="project_stage_changes")
    internal_note = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
            return (
            f"{self.project.reference_no}: "
            f"{self.from_stage} → {self.to_stage}"
        )


class ProjectDocument(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("uploaded", "Uploaded"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("requires_change", "Requires Change"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_name = models.CharField(max_length=255)

    file = models.FileField(
        upload_to="project_documents/%Y/%m/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
    )

    admin_note = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_project_documents",
    )

    uploaded_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_project_documents",
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    requirement = models.ForeignKey("DocumentRequirement",on_delete=models.SET_NULL,null=True,blank=True,related_name="project_documents")

    def __str__(self):
        return f"{self.project.reference_no} - {self.document_name}"



class DocumentRequirement(models.Model):

    DOCUMENT_FORMAT_CHOICES = [
        ("pdf", "PDF"),
        ("jpg", "JPG"),
        ("png", "PNG"),
        ("doc", "DOC"),
        ("docx", "DOCX"),
        ("xls", "XLS"),
        ("xlsx", "XLSX"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    accepted_formats = models.JSONField(
        default=list,
        help_text="Example: ['pdf', 'jpg', 'png']",
    )

    max_file_size_mb = models.PositiveIntegerField(default=5)

    applies_to_sector = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Leave blank to apply to all sectors.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
