from django.shortcuts import render

# Create your views here.

import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser
from businesses.models import BusinessProfile

from .models import BusinessScreening
from .serializers import (
    ScreeningDraftSerializer,
    ScreeningRegistrationSerializer,
    ScreeningReviewSerializer,
    validate_complete,
)


class ScreeningAnonymousThrottle(AnonRateThrottle):
    scope = "screening_anonymous"


# Verify ownership of an anonymous screening draft.

def retrieve_screening(request, pk, lock=False):

    if lock:
        queryset = BusinessScreening.objects.select_for_update()
    else:
        queryset = BusinessScreening.objects.all()

    screening = get_object_or_404(queryset, pk=pk)

    if (
        request.user.is_authenticated
        and screening.user_id == request.user.pk
    ):
        return screening

    secret = request.headers.get("X-Screening-Token", "")

    if (
        screening.status == "draft"
        and secret
        and secrets.compare_digest(
            str(screening.draft_secret), secret
        )
    ):
        return screening

    from rest_framework.exceptions import PermissionDenied

    raise PermissionDenied(
        "Screening not accessible with these credentials."
    )


# 1. Create screening draft

class ScreeningDraftCreateView(APIView):

    permission_classes = [AllowAny]
    throttle_classes = [ScreeningAnonymousThrottle]

    def post(self, request):

        serializer = ScreeningDraftSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        screening = serializer.save()

        return Response(
            {
                **ScreeningDraftSerializer(screening).data,
                "draft_token": str(screening.draft_secret),
            },
            status=status.HTTP_201_CREATED
        )


# 2. Retrieve or update a screening draft

class ScreeningDraftDetailView(APIView):

    permission_classes = [AllowAny]
    throttle_classes = [ScreeningAnonymousThrottle]

    def get(self, request, pk):

        screening = retrieve_screening(request, pk)

        return Response(
            ScreeningDraftSerializer(screening).data
        )

    def patch(self, request, pk):

        with transaction.atomic():

            screening = retrieve_screening(
                request, pk, lock=True
            )

            if screening.status != "draft":
                return Response(
                    {
                        "detail": "Submitted screenings cannot be edited."
                    },
                    status=409
                )

            serializer = ScreeningDraftSerializer(
                screening,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(
            ScreeningDraftSerializer(screening).data
        )


# 3. Create account and submit screening

class ScreeningRegisterView(APIView):

    permission_classes = [AllowAny]
    throttle_classes = [ScreeningAnonymousThrottle]

    def post(self, request, pk):

        serializer = ScreeningRegistrationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            screening = retrieve_screening(
                request, pk, lock=True
            )

            if (
                screening.status != "draft"
                or screening.user_id
            ):
                return Response(
                    {"detail": "Already submitted."},
                    status=409
                )

            validate_complete(screening)

            email = serializer.validated_data["email"]

            user = CustomUser.objects.create_user(
                username=email,
                email=email,
                password=serializer.validated_data["password"],
                user_type="business"
            )

            # Create a temporary business profile.
            # Legal identity can be disclosed after NDA.

            profile = BusinessProfile.objects.create(
                user=user,
                business_trade_name=(
                    f"Undisclosed business {str(screening.pk)[:8]}"
                ),
                business_type="other",
                sector="other",
                status="under_review",
                verification_status="pending",
                finance_amount=screening.financing_requirement.get(
                    "amount_required"
                ),
                funding_purpose=screening.financing_requirement.get(
                    "purpose_of_finance", ""
                )[:255],
                preferred_funding_term=str(
                    screening.financing_requirement.get(
                        "repayment_tenure_months", ""
                    )
                ),
            )

            screening.user = user
            screening.status = "under_review"

            screening.accuracy_confirmed = True
            screening.terms_accepted = True

            screening.submitted_at = timezone.now()

            screening.reference = (
                f"SCR-{screening.submitted_at.year}-"
                f"{screening.pk.hex[:12].upper()}"
            )

            screening.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Screening submitted for admin review.",
                "reference": screening.reference,
                "status": screening.status,
                "user": {
                    "id": user.pk,
                    "email": user.email,
                    "user_type": "business",
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=201
        )


# 4. Business dashboard - own screening

class MyScreeningView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        screening = get_object_or_404(
            BusinessScreening,
            user=request.user
        )

        return Response({
            **ScreeningDraftSerializer(screening).data,
            "review_note": screening.review_note,
            "submitted_at": screening.submitted_at,
        })


# 5. Admin - list submitted screenings

class AdminScreeningListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return Response(
                {"detail": "Admin permission required."},
                status=403
            )

        screenings = (
            BusinessScreening.objects
            .exclude(status="draft")
            .select_related("user")
        )

        selected_status = request.query_params.get("status")

        if selected_status:

            allowed = {
                "under_review",
                "approved",
                "changes_requested",
                "rejected",
            }

            if selected_status not in allowed:
                return Response(
                    {"status": "Invalid status filter."},
                    status=400
                )

            screenings = screenings.filter(
                status=selected_status
            )

        data = [
            {
                "id": screening.pk,
                "reference": screening.reference,
                "status": screening.status,
                "email": (
                    screening.user.email
                    if screening.user else None
                ),
                "submitted_at": screening.submitted_at,
            }
            for screening in screenings[:200]
        ]

        return Response(data)


# 6. Admin - review individual screening

class AdminScreeningDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def check_admin(self, request):

        return (
            request.user.is_staff
            or request.user.is_superuser
        )

    def get(self, request, pk):

        if not self.check_admin(request):
            return Response(
                {"detail": "Admin permission required."},
                status=403
            )

        screening = get_object_or_404(
            BusinessScreening.objects.exclude(status="draft"),
            pk=pk
        )

        return Response({
            **ScreeningDraftSerializer(screening).data,
            "review_note": screening.review_note,
            "submitted_at": screening.submitted_at,
        })

    def patch(self, request, pk):

        if not self.check_admin(request):
            return Response(
                {"detail": "Admin permission required."},
                status=403
            )

        serializer = ScreeningReviewSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            screening = get_object_or_404(
                BusinessScreening.objects.select_for_update(),
                pk=pk
            )

            if screening.status not in (
                "under_review",
                "changes_requested"
            ):
                return Response(
                    {
                        "detail": (
                            "Screening cannot be reviewed "
                            "from current status."
                        )
                    },
                    status=409
                )

            screening.status = serializer.validated_data[
                "status"
            ]

            screening.review_note = (
                serializer.validated_data.get(
                    "review_note", ""
                )
            )

            screening.reviewed_by = request.user
            screening.reviewed_at = timezone.now()

            screening.save(
                update_fields=[
                    "status",
                    "review_note",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

        return Response({
            "reference": screening.reference,
            "status": screening.status,
            "review_note": screening.review_note,
        })



from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import BusinessScreening
from .serializers import (
    ScreeningDraftSerializer,
    validate_complete,
)


# BUSINESS - EDIT SCREENING AFTER ADMIN REQUESTS CHANGES

class BusinessScreeningCorrectionView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request):

        with transaction.atomic():

            screening = get_object_or_404(
                BusinessScreening.objects.select_for_update(),
                user=request.user
            )

            if screening.status != "changes_requested":
                return Response(
                    {
                        "detail": (
                            "Corrections are allowed only when "
                            "the admin requests changes."
                        ),
                        "current_status": screening.status
                    },
                    status=status.HTTP_409_CONFLICT
                )

            allowed_sections = {
                "company_profile",
                "business_overview",
                "financial_snapshot",
                "financing_requirement",
                "legal_compliance",
                "business_strengths",
            }

            if (
                not request.data
                or not set(request.data).issubset(
                    allowed_sections
                )
            ):
                return Response(
                    {
                        "detail": (
                            "Provide only valid screening sections."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = ScreeningDraftSerializer(
                screening,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(
            {
                "message": "Screening corrections saved.",
                "status": screening.status,
                "screening": ScreeningDraftSerializer(
                    screening
                ).data
            },
            status=status.HTTP_200_OK
        )


# BUSINESS - RESUBMIT CORRECTED SCREENING

class BusinessScreeningResubmitView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        with transaction.atomic():

            screening = get_object_or_404(
                BusinessScreening.objects.select_for_update(),
                user=request.user
            )

            if screening.status != "changes_requested":
                return Response(
                    {
                        "detail": (
                            "Only screenings requiring changes "
                            "can be resubmitted."
                        ),
                        "current_status": screening.status
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Validate questionnaire before resubmission.
            validate_complete(screening)

            screening.status = "under_review"
            screening.submitted_at = timezone.now()

            # Clear previous review decision metadata.
            screening.reviewed_by = None
            screening.reviewed_at = None

            screening.save(
                update_fields=[
                    "status",
                    "submitted_at",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

        return Response(
            {
                "message": (
                    "Screening resubmitted successfully. "
                    "Awaiting admin review."
                ),
                "reference": screening.reference,
                "status": screening.status,
                "submitted_at": screening.submitted_at,
            },
            status=status.HTTP_200_OK
        )
