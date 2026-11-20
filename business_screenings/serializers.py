
import json
from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from accounts.models import CustomUser
from .models import BusinessScreening


# STEP 1 - Company profile

class CompanyProfileSerializer(serializers.Serializer):
    legal_trading_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    year_established = serializers.IntegerField(
        min_value=1800, required=False
    )
    country_emirate = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    legal_structure = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    industry_sector = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    number_of_employees = serializers.IntegerField(
        min_value=0, required=False
    )
    ownership_structure = serializers.CharField(
        required=False, allow_blank=True
    )

    def validate_year_established(self, value):
        if value > timezone.now().year:
            raise serializers.ValidationError(
                "Year established cannot be in the future."
            )
        return value


# STEP 2 - Business overview

class BusinessOverviewSerializer(serializers.Serializer):
    core_business_activity = serializers.CharField(
        required=False, allow_blank=True
    )
    main_markets = serializers.CharField(
        required=False, allow_blank=True
    )
    active_customers = serializers.IntegerField(
        min_value=0, required=False
    )
    largest_customer_revenue_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False
    )
    primary_bank_relationship_years = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        min_value=0,
        required=False
    )


# STEP 3 - Financial snapshot

class AnnualFiguresSerializer(serializers.Serializer):
    revenue = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        required=False, allow_null=True
    )
    gross_profit = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        required=False, allow_null=True
    )
    net_profit = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        required=False, allow_null=True
    )
    ebitda = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        required=False, allow_null=True
    )


class FinancialSnapshotSerializer(serializers.Serializer):
    currency = serializers.ChoiceField(
        choices=["AED", "USD"], required=False
    )

    annual_figures = serializers.DictField(
        child=AnnualFiguresSerializer(),
        required=False
    )

    total_assets = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        min_value=0, required=False, allow_null=True
    )

    total_liabilities_debt = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        min_value=0, required=False, allow_null=True
    )

    current_cash_balance = serializers.DecimalField(
        max_digits=18, decimal_places=2,
        min_value=0, required=False, allow_null=True
    )

    existing_finance_facilities = serializers.CharField(
        required=False, allow_blank=True
    )

    def validate_annual_figures(self, value):
        allowed_years = {
            "FY2024", "FY2025", "FY2026E", "FY2027E"
        }
        if set(value) - allowed_years:
            raise serializers.ValidationError(
                "Unsupported financial year."
            )
        return value


# STEP 4 - Financing requirement

class FinancingRequirementSerializer(serializers.Serializer):
    finance_type = serializers.ChoiceField(
        choices=["capex", "working_capital", "both"],
        required=False
    )
    currency = serializers.ChoiceField(
        choices=["AED", "USD"], required=False
    )
    amount_required = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False
    )
    purpose_of_finance = serializers.CharField(
        required=False, allow_blank=True
    )
    preferred_islamic_structure = serializers.ChoiceField(
        choices=[
            "murabaha",
            "ijara",
            "musharaka",
            "istisna",
            "tawarruq",
            "not_sure",
        ],
        required=False
    )
    repayment_tenure_months = serializers.IntegerField(
        min_value=1, max_value=1200, required=False
    )
    repayment_source = serializers.CharField(
        required=False, allow_blank=True
    )
    collateral_available = serializers.CharField(
        required=False, allow_blank=True
    )


# STEP 5 - Legal and compliance

class LegalComplianceSerializer(serializers.Serializer):
    material_litigation = serializers.BooleanField(required=False)
    litigation_details = serializers.CharField(
        required=False, allow_blank=True
    )
    tax_regulatory_issues = serializers.BooleanField(required=False)
    tax_regulatory_details = serializers.CharField(
        required=False, allow_blank=True
    )
    facility_default_restructuring = serializers.BooleanField(
        required=False
    )
    facility_details = serializers.CharField(
        required=False, allow_blank=True
    )

    def validate(self, attrs):
        pairs = [
            ("material_litigation", "litigation_details"),
            ("tax_regulatory_issues", "tax_regulatory_details"),
            ("facility_default_restructuring", "facility_details"),
        ]
        for flag, detail in pairs:
            if attrs.get(flag) is True and not attrs.get(detail, "").strip():
                raise serializers.ValidationError({
                    detail: "Details required when answering Yes."
                })
        return attrs


# STEP 6 - Business strengths

class BusinessStrengthsSerializer(serializers.Serializer):
    strength_1 = serializers.CharField(
        required=False, allow_blank=True
    )
    strength_2 = serializers.CharField(
        required=False, allow_blank=True
    )
    strength_3 = serializers.CharField(
        required=False, allow_blank=True
    )


SECTION_SERIALIZERS = {
    "company_profile": CompanyProfileSerializer,
    "business_overview": BusinessOverviewSerializer,
    "financial_snapshot": FinancialSnapshotSerializer,
    "financing_requirement": FinancingRequirementSerializer,
    "legal_compliance": LegalComplianceSerializer,
    "business_strengths": BusinessStrengthsSerializer,
}


# Main draft serializer

class ScreeningDraftSerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessScreening
        fields = [
            "id",
            "reference",
            "company_profile",
            "business_overview",
            "financial_snapshot",
            "financing_requirement",
            "legal_compliance",
            "business_strengths",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "reference", "status",
            "created_at", "updated_at"
        ]

    def validate(self, attrs):
        for name, serializer_class in SECTION_SERIALIZERS.items():
            if name in attrs:
                serializer = serializer_class(data=attrs[name])
                serializer.is_valid(raise_exception=True)

                # Convert Decimal values safely for JSON storage.
                attrs[name] = json.loads(
                    json.dumps(
                        serializer.validated_data,
                        default=str
                    )
                )
        return attrs


# Required fields for final submission

SUBMISSION_REQUIRED = {
    "company_profile": [
        "year_established",
        "country_emirate",
        "legal_structure",
        "industry_sector",
        "number_of_employees",
        "ownership_structure",
    ],
    "business_overview": [
        "core_business_activity",
        "main_markets",
        "active_customers",
        "largest_customer_revenue_percentage",
        "primary_bank_relationship_years",
    ],
    "financial_snapshot": [
        "currency",
        "annual_figures",
        "total_assets",
        "total_liabilities_debt",
        "current_cash_balance",
        "existing_finance_facilities",
    ],
    "financing_requirement": [
        "finance_type",
        "currency",
        "amount_required",
        "purpose_of_finance",
        "preferred_islamic_structure",
        "repayment_tenure_months",
        "repayment_source",
        "collateral_available",
    ],
    "legal_compliance": [
        "material_litigation",
        "tax_regulatory_issues",
        "facility_default_restructuring",
    ],
    "business_strengths": ["strength_1"],
}


def validate_complete(screening):
    errors = {}

    for section, required_fields in SUBMISSION_REQUIRED.items():
        values = getattr(screening, section)

        missing = [
            key for key in required_fields
            if (
                key not in values
                or values[key] is None
                or values[key] == ""
                or values[key] == {}
            )
        ]

        if missing:
            errors[section] = {
                key: "This field is required to submit."
                for key in missing
            }

    annual_figures = screening.financial_snapshot.get(
        "annual_figures", {}
    )

    expected_years = {
        "FY2024", "FY2025",
        "FY2026E", "FY2027E"
    }

    if set(annual_figures) != expected_years:
        errors.setdefault("financial_snapshot", {})[
            "annual_figures"
        ] = "All four financial years are required."
    else:
        for year, figures in annual_figures.items():
            for metric in [
                "revenue", "gross_profit", "net_profit", "ebitda"
            ]:
                if figures.get(metric) in (None, ""):
                    section_errors = errors.setdefault(
                        "financial_snapshot", {}
                    )
                    year_errors = section_errors.setdefault(
                        "annual_figures", {}
                    )
                    year_errors[f"{year}.{metric}"] = "Required."

    snapshot_currency = screening.financial_snapshot.get("currency")
    finance_currency = screening.financing_requirement.get("currency")

    if (
        snapshot_currency
        and finance_currency
        and snapshot_currency != finance_currency
    ):
        errors.setdefault("financing_requirement", {})[
            "currency"
        ] = "Use the same currency as the financial snapshot."

    if errors:
        raise serializers.ValidationError(errors)


# Registration after screening

class ScreeningRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    confirm_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    terms_accepted = serializers.BooleanField()
    accuracy_confirmed = serializers.BooleanField()

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        validate_password(attrs["password"])

        if not attrs["terms_accepted"] or not attrs["accuracy_confirmed"]:
            raise serializers.ValidationError(
                "Terms and accuracy confirmation are required."
            )

        if (
            CustomUser.objects.filter(
                email__iexact=attrs["email"]
            ).exists()
            or CustomUser.objects.filter(
                username__iexact=attrs["email"]
            ).exists()
        ):
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            })

        return attrs


# Admin screening review

class ScreeningReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["approved", "changes_requested", "rejected"]
    )
    review_note = serializers.CharField(
        required=False, allow_blank=True
    )

    def validate(self, attrs):
        if (
            attrs["status"] in ("changes_requested", "rejected")
            and not attrs.get("review_note", "").strip()
        ):
            raise serializers.ValidationError({
                "review_note": "Reason is required."
            })
        return attrs
