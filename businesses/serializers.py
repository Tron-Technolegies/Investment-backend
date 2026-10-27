from rest_framework import serializers

from .models import BusinessProfile, BusinessDocument
from accounts.models import FinanceType
from accounts.models import CustomUser


class BusinessListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    joined = serializers.DateTimeField(
        source="user.created_at",
        read_only=True
    )

    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "full_name",
            "business_trade_name",
            "sector",
            "email",
            "status",
            "joined",
        ]

class BusinessCreateSerializer(serializers.Serializer):
    
    full_name = serializers.CharField(
        max_length=255
    )

    business_trade_name = serializers.CharField(
        max_length=255
    )

    cin_reg_no = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    business_type = serializers.ChoiceField(
        choices=BusinessProfile.BUSINESS_TYPE_CHOICES
    )

    sector = serializers.ChoiceField(
        choices=BusinessProfile.SECTOR_CHOICES,
        required=False,
        allow_blank=True
    )

    city_hq = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    email = serializers.EmailField()

    mobile_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    status = serializers.ChoiceField(
        choices=BusinessProfile.STATUS_CHOICES,
        default="active"
    )

    business_incorporation_date = serializers.DateField()

    finance_type = serializers.PrimaryKeyRelatedField(
        queryset=FinanceType.objects.all(),
        many=True,
        allow_empty=False
    )

    finance_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    customers = serializers.CharField()

    funding_purpose = serializers.CharField(
        max_length=255
    )

    preferred_funding_term = serializers.CharField(
        max_length=100
    )

class BusinessDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    joined = serializers.DateTimeField(
        source="user.created_at",
        read_only=True
    )

    finance_type = serializers.SerializerMethodField()

    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "full_name",
            "business_trade_name",
            "cin_reg_no",
            "business_type",
            "sector",
            "city_hq",
            "email",
            "mobile_number",
            "status",
            "business_incorporation_date",
            "finance_type",
            "finance_amount",
            "customers",
            "funding_purpose",
            "preferred_funding_term",
            "joined",
        ]

    def get_finance_type(self, obj):
        return [
            {
                "id": finance.id,
                "name": finance.name
            }
            for finance in obj.finance_type.all()
        ]


class BusinessUpdateSerializer(serializers.Serializer):

    full_name = serializers.CharField(
        max_length=255
    )

    business_trade_name = serializers.CharField(
        max_length=255
    )

    cin_reg_no = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    business_type = serializers.ChoiceField(
        choices=BusinessProfile.BUSINESS_TYPE_CHOICES
    )

    sector = serializers.ChoiceField(
        choices=BusinessProfile.SECTOR_CHOICES,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    city_hq = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    email = serializers.EmailField()

    mobile_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    status = serializers.ChoiceField(
        choices=BusinessProfile.STATUS_CHOICES
    )

    def validate_email(self, value):
        return value.lower()

    def validate(self, data):

        email = data["email"]

        if CustomUser.objects.filter(
            email__iexact=email
        ).exclude(
            pk=self.instance.user.pk
        ).exists():
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            })

        return data

    def update(self, instance, validated_data):

        user = instance.user

        user.email = validated_data["email"]
        user.username = validated_data["email"]

        user.save(
            update_fields=["email", "username"]
        )

        instance.full_name = validated_data["full_name"]
        instance.business_trade_name = validated_data["business_trade_name"]
        instance.cin_reg_no = validated_data.get(
            "cin_reg_no"
        )
        instance.business_type = validated_data["business_type"]
        instance.sector = validated_data.get(
            "sector"
        )
        instance.city_hq = validated_data.get(
            "city_hq"
        )
        instance.mobile_number = validated_data.get(
            "mobile_number"
        )
        instance.status = validated_data["status"]

        instance.save()

        return instance



class BusinessDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email",
        read_only=True,
    )
    reviewed_by_email = serializers.EmailField(
        source="reviewed_by.email",
        read_only=True,
    )

    class Meta:
        model = BusinessDocument
        fields = [
            "id",
            "business",
            "document_type",
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
            "business",
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




class BusinessVerificationSerializer(serializers.ModelSerializer):
    verified_by_email = serializers.EmailField(
        source="verified_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "business_trade_name",
            "verification_status",
            "verification_note",
            "verified_at",
            "verified_by",
            "verified_by_email",
        ]
        read_only_fields = [
            "id",
            "business_trade_name",
            "verified_at",
            "verified_by",
            "verified_by_email",
        ]


class MyBusinessProfileSerializer(serializers.ModelSerializer):
    email_address = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    business_type_display = serializers.CharField(
        source="get_business_type_display",
        read_only=True,
    )

    sector_display = serializers.CharField(
        source="get_sector_display",
        read_only=True,
    )

    class Meta:
        model = BusinessProfile
        fields = [
            "id",
            "full_name",
            "business_trade_name",
            "cin_reg_no",
            "business_type",
            "business_type_display",
            "sector",
            "sector_display",
            "city_hq",
            "email_address",
            "mobile_number",
            "status",
            "verification_status",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "status",
            "verification_status",
        ]


from rest_framework import serializers
from .models import ProjectFundingInterest


