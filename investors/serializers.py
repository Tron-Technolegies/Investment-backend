from rest_framework import serializers

from .models import InvestorProfile
from businesses.models import ProjectFundingInterest

class InvestorListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    joined = serializers.DateTimeField(source='user.created_at', read_only=True)

    class Meta:
        model = InvestorProfile
        fields = [
            "id",
            "full_name",
            "organization",
            "investor_type",
            "email",
            "status",
            "joined",
        ]

class InvestorCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    organization = serializers.CharField(max_length=255,required=False,allow_blank=True)
    investor_type = serializers.ChoiceField(
        choices=[
            ("individual", "Individual"),
            ("angel_investor", "Angel Investor"),
            ("vc_fund", "VC Fund"),
            ("family_office", "Family Office"),
            ("hni", "HNI"),
        ]
    )
    email = serializers.EmailField()
    mobile_number = serializers.CharField(max_length=20)
    status = serializers.ChoiceField(
        choices=[
            ("active", "Active"),
            ("approved", "Approved"),
            ("under_review", "Under Review"),
            ("inactive", "Inactive"),
        ],
        default="active"
    )


class InvestorDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    joined = serializers.DateTimeField(source='user.created_at', read_only=True)

    class Meta:
        model = InvestorProfile
        fields = [
            "id",
            "full_name",
            "organization",
            "investor_type",
            "email",
            "mobile_number",
            "status",
            "joined",
        ]

class InvestorUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=255
    )

    organization = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )

    investor_type = serializers.ChoiceField(
        choices=[
            ("individual", "Individual"),
            ("angel_investor", "Angel Investor"),
            ("vc_fund", "VC Fund"),
            ("family_office", "Family Office"),
            ("hni", "HNI"),
        ]
    )

    email = serializers.EmailField(
        source="user.email"
    )

    mobile_number = serializers.CharField(
        max_length=20
    )

    status = serializers.ChoiceField(
        choices=[
            ("active", "Active"),
            ("approved", "Approved"),
            ("under_review", "Under Review"),
            ("inactive", "Inactive"),
        ]
    )

    def update(self, instance, validated_data):
        user = instance.user

        user_data = validated_data.pop("user", {})

        if "email" in user_data:
            user.email = user_data["email"]
            user.username = user.email
            user.save()

        instance.full_name = validated_data.get(
            "full_name",
            instance.full_name
        )

        instance.organization = validated_data.get(
            "organization",
            instance.organization
        )

        instance.investor_type = validated_data.get(
            "investor_type",
            instance.investor_type
        )

        instance.mobile_number = validated_data.get(
            "mobile_number",
            instance.mobile_number
        )

        instance.status = validated_data.get(
            "status",
            instance.status
        )

        instance.save()

        return instance
    



class MyInvestorProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    joined = serializers.DateTimeField(
        source="user.created_at",
        read_only=True
    )

    class Meta:
        model = InvestorProfile
        fields = [
            "id",
            "full_name",
            "organization",
            "investor_type",
            "mobile_number",
            "email",
            "status",
            "joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "status",
            "joined",
        ]


from rest_framework import serializers
from projects.models import Project


class ExploreBusinessSerializer(serializers.ModelSerializer):
    business_id = serializers.IntegerField(
        source="business.id",
        read_only=True
    )
    business_name = serializers.CharField(
        source="business.business_trade_name",
        read_only=True
    )
    location = serializers.CharField(
        source="business.city_hq",
        read_only=True,
        allow_null=True
    )
    funding_required = serializers.DecimalField(
        source="funding_target",
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    application_reference = serializers.CharField(
        source="reference_no",
        read_only=True
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "business_id",
            "business_name",
            "project_name",
            "sector",
            "location",
            "funding_required",
            "stage",
            "application_reference",
            "description",
            "estimated_start_date",
            "estimated_end_date",
        ]



class MyInterestListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.project_name",
        read_only=True
    )
    project_reference = serializers.CharField(
        source="project.reference_no",
        read_only=True
    )
    business_name = serializers.CharField(
        source="project.business.business_trade_name",
        read_only=True
    )
    sector = serializers.CharField(
        source="project.sector",
        read_only=True
    )
    funding_required = serializers.DecimalField(
        source="project.funding_target",
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    location = serializers.CharField(
        source="project.business.city_hq",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = ProjectFundingInterest
        fields = [
            "id",
            "project",
            "project_name",
            "project_reference",
            "business_name",
            "sector",
            "funding_required",
            "location",
            "status",
            "created_at",
            "updated_at",
        ]


class MyFundingRequestSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source="project.project_name",
        read_only=True
    )
    project_reference = serializers.CharField(
        source="project.reference_no",
        read_only=True
    )
    business_name = serializers.CharField(
        source="project.business.business_trade_name",
        read_only=True
    )
    sector = serializers.CharField(
        source="project.sector",
        read_only=True
    )
    funding_target = serializers.DecimalField(
        source="project.funding_target",
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    project_stage = serializers.CharField(
        source="project.stage",
        read_only=True
    )

    class Meta:
        model = ProjectFundingInterest
        fields = [
            "id",
            "project",
            "project_name",
            "project_reference",
            "business_name",
            "sector",
            "funding_target",
            "project_stage",
            "proposed_amount",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
