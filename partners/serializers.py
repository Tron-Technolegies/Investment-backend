from rest_framework import serializers

from accounts.models import CustomUser
from .models import PartnerProfile,PartnerKYCDocument


class PartnerListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = PartnerProfile
        fields = [
            "id",
            "full_name",
            "organization_name",
            "specialty",
            "email",
            "status",
        ]
class PartnerCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=255
    )

    organization_name = serializers.CharField(
        max_length=255
    )

    specialty = serializers.ChoiceField(
        choices=PartnerProfile.SPECIALTY_CHOICES
    )

    email = serializers.EmailField()

    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    status = serializers.ChoiceField(
        choices=PartnerProfile.STATUS_CHOICES,
        default="active"
    )

class PartnerDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = PartnerProfile
        fields = [
            "id",
            "full_name",
            "organization_name",
            "specialty",
            "email",
            "phone",
            "status",
            "created_at",
        ]

class PartnerUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=255
    )

    organization_name = serializers.CharField(
        max_length=255
    )

    specialty = serializers.ChoiceField(
        choices=PartnerProfile.SPECIALTY_CHOICES
    )

    email = serializers.EmailField()

    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    status = serializers.ChoiceField(
        choices=PartnerProfile.STATUS_CHOICES
    )

    def validate_email(self, value):
        return value.lower()

    def validate(self, data):
        email = data["email"]
        if CustomUser.objects.filter(email__iexact=email).exclude(
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
        user.save(update_fields=["email","username"])

        instance.full_name = validated_data["full_name"]
        instance.organization_name = validated_data["organization_name"]
        instance.specialty = validated_data["specialty"]
        instance.phone = validated_data.get("phone")
        instance.status = validated_data["status"]

        instance.save()

        return instance




class PartnerDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = PartnerProfile
        fields = [
            "id",
            "full_name",
            "organization_name",
            "specialty",
            "email",
            "phone",
            "status",
            "years_of_experience",
            "sebi_registration_number",
            "license_certificate_number",
            "linkedin_url",
            "city",
            "id_type",
            "id_number",
            "created_at",
        ]


class ConsultingPartnerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    class Meta:
        model = PartnerProfile
        fields = [
            "id",
            "full_name",
            "organization_name",
            "specialty",
            "email",
            "phone",
            "status",
            "years_of_experience",
            "sebi_registration_number",
            "license_certificate_number",
            "linkedin_url",
            "city",
            "id_type",
            "id_number",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "status",
            "created_at",
        ]



class PartnerKYCDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True,
    )

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PartnerKYCDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "file",
            "file_url",
            "status",
            "admin_note",
            "uploaded_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "admin_note",
            "uploaded_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")

        if not obj.file:
            return None

        if request:
            return request.build_absolute_uri(obj.file.url)

        return obj.file.url
