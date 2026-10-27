from rest_framework import serializers

from businesses.models import BusinessProfile,ProjectFundingInterest
from .models import Project,ProjectStageHistory, ProjectDocument,DocumentRequirement


class ProjectCreateSerializer(serializers.Serializer):
    project_name = serializers.CharField(max_length=255)
    sector = serializers.CharField(max_length=100)
    funding_target = serializers.DecimalField(max_digits=15,decimal_places=2)
    estimated_start_date = serializers.DateField(required=False,allow_null=True)
    estimated_end_date = serializers.DateField(required=False,allow_null=True)
    description = serializers.CharField()

    def validate(self, data):
        start_date = data.get("estimated_start_date")
        end_date = data.get("estimated_end_date")

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "estimated_end_date": (
                    "Estimated end date cannot be before "
                    "estimated start date."
                )
            })

        return data


class ProjectListSerializer(serializers.ModelSerializer):
    stage_label = serializers.CharField(
        source="get_stage_display",
        read_only=True
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "reference_no",
            "project_name",
            "sector",
            "funding_target",
            "estimated_start_date",
            "estimated_end_date",
            "stage",
            "stage_label",
            "submitted_at",
            "updated_at",
        ]

class AdminProjectListSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.business_trade_name",read_only=True)
    assigned_partner_name = serializers.CharField(source="assigned_partner.organization_name",read_only=True)
    stage_label = serializers.CharField(source="get_stage_display",read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "reference_no",
            "business_name",
            "project_name",
            "sector",
            "funding_target",
            "stage",
            "stage_label",
            "assigned_partner_name",
            "submitted_at",
            "updated_at",
        ]

class ProjectDetailSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.business_trade_name",read_only=True)
    business_id = serializers.IntegerField(source="business.id",read_only=True)
    assigned_partner_name = serializers.CharField(source="assigned_partner.organization_name",read_only=True)
    stage_label = serializers.CharField(source="get_stage_display",read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "reference_no",
            "business_id",
            "business_name",
            "project_name",
            "sector",
            "funding_target",
            "estimated_start_date",
            "estimated_end_date",
            "description",
            "stage",
            "stage_label",
            "assigned_partner_name",
            "submitted_at",
            "created_at",
            "updated_at",
        ]

class ProjectStageUpdateSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Project.STAGE_CHOICES)
    internal_note = serializers.CharField(required=False,allow_blank=True,allow_null=True)


class ProjectStageHistorySerializer(serializers.ModelSerializer):
    from_stage_label = serializers.CharField(
        source="get_from_stage_display",
        read_only=True
    )

    to_stage_label = serializers.CharField(
        source="get_to_stage_display",
        read_only=True
    )

    changed_by_email = serializers.EmailField(
        source="changed_by.email",
        read_only=True
    )

    class Meta:
        model = ProjectStageHistory
        fields = [
            "id",
            "from_stage",
            "from_stage_label",
            "to_stage",
            "to_stage_label",
            "changed_by_email",
            "internal_note",
            "created_at",
        ]


from rest_framework import serializers
from .models import ProjectDocument


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True,
    )
    reviewed_by_email = serializers.EmailField(
        source="reviewed_by.email",
        read_only=True,
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDocument
        fields = [
            "id",
            "project",
            "requirement",
            "document_name",
            "file",
            "file_url",
            "status",
            "admin_note",
            "uploaded_by",
            "uploaded_by_email",
            "uploaded_at",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "admin_note",
            "uploaded_by",
            "uploaded_at",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")

        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)

        if obj.file:
            return obj.file.url

        return None


class DocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequirement
        fields = [
            "id",
            "name",
            "description",
            "accepted_formats",
            "max_file_size_mb",
            "applies_to_sector",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class BusinessFundingStatusSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.project_name",
        read_only=True
    )
    project_reference = serializers.CharField(
        source="project.reference_no",
        read_only=True
    )
    funding_partner_name = serializers.CharField(
        source="funding_partner.get_full_name",
        read_only=True
    )
    funding_partner_email = serializers.EmailField(
        source="funding_partner.email",
        read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )

    class Meta:
        model = ProjectFundingInterest
        fields = [
            "id",
            "project",
            "project_name",
            "project_reference",
            "funding_partner",
            "funding_partner_name",
            "funding_partner_email",
            "proposed_amount",
            "status",
            "status_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields