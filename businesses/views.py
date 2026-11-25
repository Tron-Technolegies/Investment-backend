from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from business_screenings.models import BusinessScreening

from .models import BusinessProfile,BusinessDocument,BusinessNDA
from django.db import transaction,models
from django.db.models import Count
from accounts.models import CustomUser
from .models import BusinessNDA
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BusinessListSerializer,BusinessCreateSerializer,AdminFundingInterestSerializer,BusinessDetailSerializer,BusinessUpdateSerializer,BusinessDocumentSerializer,BusinessVerificationSerializer,MyBusinessProfileSerializer,BusinessProfileConfirmationSerializer,AdminFundingInterestSerializer
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.shortcuts import get_object_or_404
from django.utils import timezone
from projects.models import Project, ProjectDocument, DocumentRequirement
from businesses.models import BusinessProfile, ProjectFundingInterest
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import FundingOfferSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.exceptions import PermissionDenied

from .models import FundingOffer, ProjectFundingInterest
from .serializers import FundingOfferSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated,IsAdminUser

from .models import FundingOffer, FundingAgreement
from .serializers import FundingAgreementSerializer
from django.http import FileResponse

class BusinessListView(ListAPIView):
    queryset = (BusinessProfile.objects.select_related("user").all().order_by("-user__created_at"))
    serializer_class=BusinessListSerializer
    permission_classes=[IsAdminUser]

class BusinessCreateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        serializer = BusinessCreateSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            if CustomUser.objects.filter(
                email__iexact=data["email"]
            ).exists():
                return Response(
                    {
                        "email": "An account with this email already exists."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = CustomUser.objects.create(
                username=data["email"],
                email=data["email"],
                user_type="business",
            )

            user.set_unusable_password()
            user.save()

            business = BusinessProfile.objects.create(
                user=user,
                full_name=data["full_name"],
                business_trade_name=data["business_trade_name"],
                cin_reg_no=data.get("cin_reg_no"),
                business_type=data["business_type"],
                sector=data.get("sector"),
                city_hq=data.get("city_hq"),
                mobile_number=data.get("mobile_number"),
                status=data["status"],
                business_incorporation_date=data[
                    "business_incorporation_date"
                ],
                finance_amount=data["finance_amount"],
                customers=data["customers"],
                funding_purpose=data["funding_purpose"],
                preferred_funding_term=data[
                    "preferred_funding_term"
                ],
            )

            business.finance_type.set(data["finance_type"])

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            setup_url = (
                f"http://127.0.0.1:8000/accounts/set-password/"
                f"?uid={uid}&token={token}"
            )

            send_mail(
                subject="Complete Your Business Account Setup",
                message=(
                    f"Hello {business.full_name},\n\n"
                    "Your business account has been created on the "
                    "Business Financing Platform.\n\n"
                    "Please use the following link to set your password:\n\n"
                    f"{setup_url}\n\n"
                    "After setting your password, you can log in to the platform.\n\n"
                    "Regards,\n"
                    "Business Financing Team"
                ),
                from_email=None,
                recipient_list=[user.email],
            )

            return Response(
                {
                    "message": "Business created successfully.",
                    "business": {
                        "id": business.id,
                        "full_name": business.full_name,
                        "business_trade_name": business.business_trade_name,
                        "email": user.email,
                        "sector": business.sector,
                        "status": business.status,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class BusinessDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            business = (
                BusinessProfile.objects
                .select_related("user")
                .prefetch_related("finance_type")
                .get(pk=pk)
            )
        except BusinessProfile.DoesNotExist:
            return Response(
                {
                    "detail": "Business not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BusinessDetailSerializer(business)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class BusinessUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request,pk):

        try:
            business = (
                BusinessProfile.objects.select_related("user").get(pk=pk)
            )
        except BusinessProfile.DoesNotExist:
            return Response(
                {
                    "detail" : "Business not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = BusinessUpdateSerializer(
            business,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            business = serializer.save()

            return Response(
                {
                    "message": "Business updated successfully",
                    "business":{
                        "id":business.id,
                        "full_name": business.full_name,
                        "business_trade_name": business.business_trade_name,
                        "email": business.user.email,
                        "sector": business.sector,
                        "status": business.status,
                    }
                },
                status=status.HTTP_200_OK
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class BusinessDeactivateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):

        try:
            business = (
                BusinessProfile.objects.select_related("user").get(pk=pk)
            )
        except BusinessProfile.DoesNotExist:
            return Response(
                {
                    "detail" : "Business not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        if business.status == "inactive":
            return Response(
                {
                    "detail" : "Business is already inactive."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        business.status = "inactive"
        business.save(update_fields=["status"])

        user = business.user
        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Business deactivated successfully.",
                "business": {
                    "id": business.id,
                    "business_trade_name": business.business_trade_name,
                    "status": business.status,
                    "is_active": user.is_active,
            },
            },
            status=status.HTTP_200_OK
        )
    
class BusinessActivateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            business = (
                BusinessProfile.objects
                .select_related("user")
                .get(pk=pk)
            )
        except BusinessProfile.DoesNotExist:
            return Response(
                {"detail": "Business not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if business.status != "inactive":
            return Response(
                {"detail": "Business is already active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        business.status = "active"
        business.save(update_fields=["status"])

        user = business.user
        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Business activated successfully.",
                "business": {
                    "id": business.id,
                    "business_trade_name": business.business_trade_name,
                    "status": business.status,
                    "is_active": user.is_active,
                },
            },
            status=status.HTTP_200_OK
        )

class BusinessDocumentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, business_id):
        business = get_object_or_404(
            BusinessProfile,
            pk=business_id,
        )

        if not (
            request.user.is_staff
            or request.user.is_superuser
            or business.user_id == request.user.id
        ):
            return Response(
                {"detail": "You do not have permission to access these documents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        documents = BusinessDocument.objects.filter(
            business=business
        ).select_related("uploaded_by", "reviewed_by")

        serializer = BusinessDocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    def post(self, request, business_id):
        business = get_object_or_404(
            BusinessProfile,
            pk=business_id,
        )

        if business.user_id != request.user.id:
            return Response(
                {"detail": "Only the business owner can upload documents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BusinessDocumentSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save(
                business=business,
                uploaded_by=request.user,
                status="uploaded",
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class BusinessDocumentReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, document_id):
        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return Response(
                {"detail": "Only admins can review business documents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        document = get_object_or_404(
            BusinessDocument,
            pk=document_id,
        )

        new_status = request.data.get("status")
        admin_note = request.data.get("admin_note", "")

        allowed_statuses = {
            "under_review",
            "approved",
            "requires_change",
        }

        if new_status not in allowed_statuses:
            return Response(
                {
                    "status": (
                        "Choose under_review, approved, or requires_change."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "requires_change" and not admin_note.strip():
            return Response(
                {"admin_note": "Explain what needs to be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.status = new_status
        document.admin_note = admin_note
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()

        document.save(
            update_fields=[
                "status",
                "admin_note",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        serializer = BusinessDocumentSerializer(
            document,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class BusinessDocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        document = get_object_or_404(
            BusinessDocument,
            pk=document_id,
        )

        is_admin = (
            request.user.is_staff
            or request.user.is_superuser
        )
        is_owner = document.business.user_id == request.user.id

        if not is_admin and not is_owner:
            return Response(
                {"detail": "You do not have permission to delete this document."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_admin and document.status == "approved":
            return Response(
                {
                    "detail": (
                        "Approved documents cannot be deleted "
                        "by the business owner."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if document.file:
            document.file.delete(save=False)

        document.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

class BusinessVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"detail": "Only admins can view business verification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        business = get_object_or_404(
            BusinessProfile.objects.select_related("user", "verified_by"),
            pk=business_id,
        )

        serializer = BusinessVerificationSerializer(business)
        return Response(serializer.data)

    
    @transaction.atomic
    def patch(self, request, business_id):

        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):
            return Response(
                {"detail": "Admin permission required."},
                status=status.HTTP_403_FORBIDDEN
            )

        business = get_object_or_404(
            BusinessProfile.objects.select_for_update(),
            pk=business_id
        )

        new_status = request.data.get("verification_status")
        note = request.data.get("verification_note", "")

        allowed_statuses = {
            "under_review",
            "verified",
            "requires_change",
            "rejected",
        }

        if new_status not in allowed_statuses:
            return Response(
                {
                    "detail": "Invalid verification status.",
                    "allowed_statuses": sorted(allowed_statuses),
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status in {"requires_change", "rejected"}:
            if not isinstance(note, str) or not note.strip():
                return Response(
                    {
                        "verification_note":
                        "A reason is required."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Additional checks for final approval only
        if new_status == "verified":

            screening_approved = BusinessScreening.objects.filter(
                user=business.user,
                status="approved"
            ).exists()

            if not screening_approved:
                return Response(
                    {
                        "detail":
                        "Business screening is not approved."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            nda_verified = BusinessNDA.objects.filter(
                business=business,
                status="verified"
            ).exists()

            if not nda_verified:
                return Response(
                    {
                        "detail":
                        "Business NDA must be verified."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            required_fields = [
                "full_name",
                "business_trade_name",
                "cin_reg_no",
                "business_type",
                "sector",
                "city_hq",
                "mobile_number",
                "business_incorporation_date",
            ]

            missing_fields = [
                field
                for field in required_fields
                if not getattr(business, field, None)
            ]

            if missing_fields:
                return Response(
                    {
                        "detail":
                        "Business profile is incomplete.",
                        "missing_fields": missing_fields,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            documents = BusinessDocument.objects.filter(
                business=business
            )

            if not documents.exists():
                return Response(
                    {
                        "detail":
                        "Business verification documents are required."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            pending_documents = documents.exclude(
                status="approved"
            )

            if pending_documents.exists():
                return Response(
                    {
                        "detail":
                        "All submitted business documents must be approved.",
                        "pending_document_ids": list(
                            pending_documents.values_list(
                                "id", flat=True
                            )
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        business.verification_status = new_status
        business.verification_note = (
            note.strip() if isinstance(note, str) else ""
        )

        if new_status == "verified":
            business.verified_by = request.user
            business.verified_at = timezone.now()
        else:
            business.verified_by = None
            business.verified_at = None

        business.save(
            update_fields=[
                "verification_status",
                "verification_note",
                "verified_by",
                "verified_at",
            ]
        )

        serializer = BusinessVerificationSerializer(business)

        return Response(
            {
                "message": (
                    "Business verification updated successfully."
                ),
                "business": serializer.data,
            },
            status=status.HTTP_200_OK
        )




class MyBusinessProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_business_profile(self, request):
        # Only business accounts can use this endpoint.
        if getattr(request.user, "user_type", None) != "business":
            return None

        return getattr(request.user, "business_profile", None)

    def get(self, request):
        profile = self.get_business_profile(request)

        if profile is None:
            return Response(
                {"detail": "Business profile not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MyBusinessProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        profile = self.get_business_profile(request)

        if profile is None:
            return Response(
                {"detail": "Business profile not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not BusinessNDA.objects.filter(
            business=profile,
            status="verified"
        ).exists():
            return Response(
                {
                    "detail": (
                        "NDA verification is required before "
                        "editing business identity."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        if profile.verification_status == "verified":
            return Response(
                {
                    "detail": (
                        "Verified profiles require admin approval "
                        "before identity changes."
                    )
                },
                status=status.HTTP_409_CONFLICT
            )

        serializer = MyBusinessProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

class BusinessDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only business users can access this dashboard
        if request.user.user_type != "business":
            return Response(
                {
                    "success": False,
                    "message": "Only business users can access this dashboard."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the logged-in user's business profile
        business = getattr(request.user, "business_profile", None)

        if not business:
            return Response(
                {
                    "success": False,
                    "message": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Get only this business's projects
        projects = Project.objects.filter(
            business=business
        )

        project_ids = projects.values_list("id", flat=True)

        # Get documents uploaded for these projects
        documents = ProjectDocument.objects.filter(
            project__business=business
        )

        # Count document statuses
        submitted_count = documents.filter(
            status__in=["uploaded", "under_review", "approved", "requires_change"]
        ).count()

        approved_count = documents.filter(
            status="approved"
        ).count()

        requires_changes_count = documents.filter(
            status="requires_change"
        ).count()

        # Count active requirements applicable to each project sector.
        # A requirement may apply to every sector or to a specific sector.
        required_count = 0

        for project in projects:
            requirements = DocumentRequirement.objects.filter(
                is_active=True
            ).filter(
                models.Q(applies_to_sector__isnull=True)
                | models.Q(applies_to_sector="")
                | models.Q(applies_to_sector=project.sector)
            )

            required_count += requirements.count()

        # Count projects by stage
        stage_counts = projects.values("stage").annotate(
            total=Count("id")
        )

        project_stage_summary = {
            stage_key: 0
            for stage_key, _ in Project.STAGE_CHOICES
        }

        for item in stage_counts:
            project_stage_summary[item["stage"]] = item["total"]

        # Latest five projects
        recent_projects = projects.order_by(
            "-created_at"
        )[:5]

        recent_projects_data = [
            {
                "id": project.id,
                "reference_no": project.reference_no,
                "project_name": project.project_name,
                "sector": project.sector,
                "funding_target": project.funding_target,
                "stage": project.stage,
                "submitted_at": project.submitted_at,
                "created_at": project.created_at,
            }
            for project in recent_projects
        ]

        return Response(
            {
                "success": True,
                "business": {
                    "id": business.id,
                    "business_name": business.business_trade_name,
                    "verification_status": business.verification_status,
                },
                "documents": {
                    "total_required": required_count,
                    "submitted": submitted_count,
                    "approved": approved_count,
                    "requires_changes": requires_changes_count,
                },
                "projects": {
                    "total": projects.count(),
                    "by_stage": project_stage_summary,
                    "recent": recent_projects_data,
                },
            },
            status=status.HTTP_200_OK
        )


class BusinessFundingStatusView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        if request.user.user_type != "business":
            return Response(
                {
                    "detail": (
                        "Only business users can view funding status."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            business = request.user.business_profile

        except BusinessProfile.DoesNotExist:
            return Response(
                {"detail": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        interests = (
            ProjectFundingInterest.objects
            .filter(
                project__business=business,
                status__in=[
                    "approved",
                    "offer_sent",
                    "accepted",
                    "declined",
                ],
            )
            .select_related(
                "project",
                "funding_partner",
                "funding_partner__investor_profile",
                "funding_offer",
            )
            .order_by("-created_at")
        )

        results = []

        for interest in interests:

            investor = interest.funding_partner

            profile = getattr(
                investor,
                "investor_profile",
                None,
            )

            investor_name = (
                profile.full_name if profile
                else investor.email
            )

            organization = (
                profile.organization or ""
                if profile else ""
            )

            offer = getattr(
                interest,
                "funding_offer",
                None,
            )

            offer_data = (
                FundingOfferSerializer(offer).data
                if offer else None
            )

            results.append({
                "id": interest.id,
                "investor_name": investor_name,
                "organization": organization,
                "project_id": interest.project_id,
                "project_name": interest.project.project_name,
                "project_reference": interest.project.reference_no,
                "date": interest.created_at,
                "proposed_amount": interest.proposed_amount,
                "status": interest.status,
                "funding_offer": offer_data,
            })

        return Response(
            {"results": results},
            status=status.HTTP_200_OK,
        )




from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser

from business_screenings.models import BusinessScreening

from .models import BusinessProfile, BusinessNDA
from .serializers import (
    BusinessNDASerializer,
    BusinessNDAUploadSerializer,
    BusinessNDASignedSerializer,
    BusinessNDAReviewSerializer,
)


def get_approved_business(business_id):
    """
    Retrieve a business whose initial screening
    has been approved by admin.
    """
    business = get_object_or_404(
        BusinessProfile,
        pk=business_id
    )

    approved = BusinessScreening.objects.filter(
        user=business.user,
        status="approved"
    ).exists()

    if not approved:
        return business, False

    return business, True


# 1. ADMIN UPLOADS NDA / BUSINESS VIEWS NDA

class BusinessNDAView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, business_id):

        business = get_object_or_404(
            BusinessProfile,
            pk=business_id
        )

        # Only admin or the business owner can view
        if not (
            request.user.is_staff
            or request.user.is_superuser
            or business.user_id == request.user.pk
        ):
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN
            )

        nda = BusinessNDA.objects.filter(
            business=business
        ).first()

        if not nda:
            return Response({
                "business_id": business.id,
                "status": "not_started",
                "message": "No NDA has been issued yet."
            })

        return Response(
            BusinessNDASerializer(
                nda,
                context={"request": request}
            ).data
        )

    def post(self, request, business_id):

        if not request.user.is_staff:
            if not request.user.is_superuser:
                return Response(
                    {"detail": "Admin permission required."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = BusinessNDAUploadSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            business, approved = get_approved_business(
                business_id
            )

            if not approved:
                return Response(
                    {
                        "detail": (
                            "Business screening must be approved "
                            "before issuing an NDA."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            nda, created = (
                BusinessNDA.objects.select_for_update()
                .get_or_create(business=business)
            )

            if nda.status in ("signed", "verified"):
                return Response(
                    {
                        "detail": (
                            "This NDA has already been signed. "
                            "It cannot be replaced through this API."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            nda.nda_document = (
                serializer.validated_data["nda_document"]
            )

            nda.status = "sent"
            nda.sent_at = timezone.now()

            # Previous rejected submission is superseded
            nda.signed_document = None
            nda.signed_at = None
            nda.executed_on = None
            nda.verified_at = None
            nda.verified_by = None
            nda.admin_note = ""

            nda.save()

        return Response(
            {
                "message": "NDA issued successfully.",
                "nda": BusinessNDASerializer(
                    nda,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_201_CREATED
            if created else status.HTTP_200_OK
        )


# 2. BUSINESS UPLOADS SIGNED NDA

class BusinessNDASignView(APIView):

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, business_id):

        business = get_object_or_404(
            BusinessProfile,
            pk=business_id
        )

        # Only the owner of this business can submit
        if business.user_id != request.user.pk:
            return Response(
                {"detail": "Only the business owner can sign."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BusinessNDASignedSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            nda = get_object_or_404(
                BusinessNDA.objects.select_for_update(),
                business=business
            )

            if nda.status not in ("sent", "rejected"):
                return Response(
                    {
                        "detail": (
                            "NDA is not currently available "
                            "for signing."
                        ),
                        "current_status": nda.status
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if not nda.nda_document:
                return Response(
                    {"detail": "NDA document is missing."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            nda.signed_document = (
                serializer.validated_data["signed_document"]
            )

            nda.status = "signed"
            nda.signed_at = timezone.now()
            nda.executed_on = None
            nda.verified_at = None
            nda.verified_by = None
            nda.admin_note = ""

            nda.save()

        return Response(
            {
                "message": (
                    "Signed NDA submitted successfully. "
                    "Awaiting admin verification."
                ),
                "nda": BusinessNDASerializer(
                    nda,
                    context={"request": request}
                ).data
            },
            status=status.HTTP_200_OK
        )


# 3. ADMIN VERIFIES OR REJECTS SIGNED NDA

class BusinessNDAReviewView(APIView):

    permission_classes = [IsAdminUser]

    def patch(self, request, business_id):

        serializer = BusinessNDAReviewSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            business = get_object_or_404(
                BusinessProfile,
                pk=business_id
            )

            nda = get_object_or_404(
                BusinessNDA.objects.select_for_update(),
                business=business
            )

            if nda.status != "signed":
                return Response(
                    {
                        "detail": (
                            "Only submitted signed NDAs "
                            "can be reviewed."
                        ),
                        "current_status": nda.status
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if not nda.signed_document:
                return Response(
                    {"detail": "Signed NDA document is missing."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            decision = serializer.validated_data["status"]

            nda.status = decision
            nda.admin_note = serializer.validated_data.get(
                "admin_note", ""
            )

            if decision == "verified":

                nda.executed_on = (
                    serializer.validated_data["executed_on"]
                )
                nda.verified_at = timezone.now()
                nda.verified_by = request.user

            else:

                nda.executed_on = None
                nda.verified_at = None
                nda.verified_by = None

            nda.save()

        return Response({
            "message": f"NDA {decision} successfully.",
            "nda": BusinessNDASerializer(
                nda,
                context={"request": request}
            ).data
        })




class BusinessProfileConfirmationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        if getattr(request.user, "user_type", None) != "business":
            return Response(
                {"detail": "Business account required."},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():

            business = get_object_or_404(
                BusinessProfile.objects.select_for_update(),
                user=request.user
            )

            # Check screening approval
            screening_approved = BusinessScreening.objects.filter(
                user=request.user,
                status="approved"
            ).exists()

            if not screening_approved:
                return Response(
                    {
                        "detail": (
                            "Business screening must be approved "
                            "before profile confirmation."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check verified NDA
            nda_verified = BusinessNDA.objects.filter(
                business=business,
                status="verified"
            ).exists()

            if not nda_verified:
                return Response(
                    {
                        "detail": (
                            "NDA must be verified before "
                            "submitting company identity."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            if business.verification_status == "verified":
                return Response(
                    {
                        "detail": (
                            "Verified business profiles cannot "
                            "be changed through this API."
                        )
                    },
                    status=status.HTTP_409_CONFLICT
                )

            serializer = BusinessProfileConfirmationSerializer(
                business,
                data=request.data
            )

            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Send identity information for admin review
            business.verification_status = "under_review"
            business.verification_note = ""
            business.verified_at = None
            business.verified_by = None

            business.save(
                update_fields=[
                    "verification_status",
                    "verification_note",
                    "verified_at",
                    "verified_by",
                ]
            )

        return Response(
            {
                "message": (
                    "Business profile submitted "
                    "for admin verification."
                ),
                "business_id": business.id,
                "business_trade_name": business.business_trade_name,
                "verification_status": business.verification_status,
                "profile": BusinessProfileConfirmationSerializer(
                    business
                ).data
            },
            status=status.HTTP_200_OK
        )



class AdminFundingInterestListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):

        interests = (
            ProjectFundingInterest.objects
            .select_related(
                "project",
                "project__business",
                "funding_partner",
                "reviewed_by",
            )
            .order_by("-created_at")
        )

        requested_status = request.query_params.get(
            "status", ""
        ).strip()

        if requested_status and requested_status != "all":

            valid_statuses = dict(
                ProjectFundingInterest.STATUS_CHOICES
            )

            if requested_status not in valid_statuses:
                return Response(
                    {
                        "detail": "Invalid funding status.",
                        "allowed_statuses": list(
                            valid_statuses.keys()
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            interests = interests.filter(
                status=requested_status
            )

        serializer = AdminFundingInterestSerializer(
            interests,
            many=True
        )

        return Response({
            "success": True,
            "count": interests.count(),
            "results": serializer.data,
        }, status=status.HTTP_200_OK)



class AdminFundingInterestReviewView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, interest_id):

        interest = get_object_or_404(
            ProjectFundingInterest.objects.select_for_update(),
            pk=interest_id
        )

        new_status = request.data.get("status")
        admin_note = request.data.get("admin_note", "")

        allowed_transitions = {
            "interested": [
                "under_review",
                "approved",
                "rejected",
            ],
            "under_review": [
                "approved",
                "rejected",
            ],
        }

        if new_status not in [
            "under_review",
            "approved",
            "rejected",
        ]:
            return Response(
                {"detail": "Invalid review status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in allowed_transitions.get(
            interest.status, []
        ):
            return Response(
                {
                    "detail": "This status transition is not allowed.",
                    "current_status": interest.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        if not isinstance(admin_note, str):
            return Response(
                {"admin_note": "Enter a valid text note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "rejected" and not admin_note.strip():
            return Response(
                {"admin_note": "Rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "approved":

            if interest.project.stage != "approved":
                return Response(
                    {"detail": "The project must be approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                interest.project.business.verification_status
                != "verified"
            ):
                return Response(
                    {"detail": "The business must be verified."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        interest.status = new_status
        interest.admin_note = admin_note.strip()
        interest.reviewed_by = request.user
        interest.reviewed_at = timezone.now()

        interest.save(
            update_fields=[
                "status",
                "admin_note",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

        serializer = AdminFundingInterestSerializer(interest)

        return Response({
            "success": True,
            "message": "Funding interest reviewed successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)



class BusinessFundingInterestResponseView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, interest_id):

        if request.user.user_type != "business":
            raise PermissionDenied(
                "Only business users can respond to funding offers."
            )

        try:
            business = request.user.business_profile

        except BusinessProfile.DoesNotExist:
            return Response(
                {"detail": "Business profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_status = request.data.get("status")
        response_note = request.data.get("note", "")

        # Validate business decision
        if response_status not in ["accepted", "declined"]:
            return Response(
                {
                    "detail": (
                        "Status must be accepted or declined."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(response_note, str):
            return Response(
                {"note": "Enter a valid text note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_note = response_note.strip()

        if response_status == "declined" and not response_note:
            return Response(
                {"note": "Please provide a reason for declining."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Business can only respond to its own projects
        interest = get_object_or_404(
            ProjectFundingInterest.objects.select_for_update(),
            id=interest_id,
            project__business=business,
        )

        # Prevent duplicate or invalid decisions
        if interest.status != "offer_sent":
            return Response(
                {
                    "detail": (
                        "This funding offer is not available "
                        "for a response."
                    ),
                    "current_status": interest.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        offer = get_object_or_404(
            FundingOffer.objects.select_for_update(),
            interest=interest,
        )

        # Prevent responses to expired offers
        if offer.valid_until < timezone.localdate():
            return Response(
                {"detail": "This funding offer has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Recheck eligibility before accepting
        if response_status == "accepted":

            if interest.project.stage != "approved":
                return Response(
                    {"detail": "Project is no longer approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if business.verification_status != "verified":
                return Response(
                    {"detail": "Business verification is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Update funding interest status
        interest.status = response_status

        interest.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # Record business decision
        offer.business_response_note = response_note
        offer.business_responded_at = timezone.now()
        offer.business_responded_by = request.user

        offer.save(
            update_fields=[
                "business_response_note",
                "business_responded_at",
                "business_responded_by",
                "updated_at",
            ]
        )

        serializer = FundingOfferSerializer(offer)

        return Response(
            {
                "success": True,
                "message": (
                    f"Funding offer {response_status} successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


def validate_agreement_pdf(uploaded_file):

    if not uploaded_file:
        raise serializers.ValidationError({
            "file": "Please select an agreement PDF."
        })

    if not uploaded_file.name.lower().endswith(".pdf"):
        raise serializers.ValidationError({
            "file": "Only PDF files are allowed."
        })

    if uploaded_file.size > 10 * 1024 * 1024:
        raise serializers.ValidationError({
            "file": "Maximum file size is 10 MB."
        })

    header = uploaded_file.read(5)
    uploaded_file.seek(0)

    if header != b"%PDF-":
        raise serializers.ValidationError({
            "file": "Invalid PDF document."
        })

    return uploaded_file

def check_agreement_access(user, offer):

    if user.is_staff:
        return

    interest = offer.interest

    if (
        user.user_type == "investor"
        and interest.funding_partner_id == user.id
    ):
        return

    if (
        user.user_type == "business"
        and interest.project.business.user_id == user.id
    ):
        return

    raise PermissionDenied(
        "You do not have access to this agreement."
    )

class FundingAgreementView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, offer_id):

        offer = get_object_or_404(
            FundingOffer,
            id=offer_id,
        )

        check_agreement_access(
            request.user,
            offer,
        )

        agreement = get_object_or_404(
            FundingAgreement,
            funding_offer=offer,
        )

        return Response(
            {
                "success": True,
                "data": FundingAgreementSerializer(
                    agreement
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request, offer_id):

        if not request.user.is_staff:
            raise PermissionDenied(
                "Only admins can upload funding agreements."
            )

        offer = get_object_or_404(
            FundingOffer.objects.select_for_update(),
            id=offer_id,
        )

        # Check business acceptance
        if offer.interest.status != "accepted":
            return Response(
                {
                    "detail": (
                        "The funding offer must be accepted "
                        "by the business first."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent duplicate agreements
        if FundingAgreement.objects.filter(
            funding_offer=offer
        ).exists():
            return Response(
                {
                    "detail": "Funding agreement already exists."
                },
                status=status.HTTP_409_CONFLICT,
            )

        uploaded_file = validate_agreement_pdf(
            request.FILES.get("agreement_document")
        )

        agreement = FundingAgreement.objects.create(
            funding_offer=offer,
            agreement_document=uploaded_file,
            uploaded_by=request.user,
            status="pending_investor_signature",
        )

        serializer = FundingAgreementSerializer(
            agreement
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Funding agreement uploaded successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class FundingAgreementDownloadView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, agreement_id, document_type):

        agreement = get_object_or_404(
            FundingAgreement,
            id=agreement_id,
        )

        # Check admin, investor or business ownership
        check_agreement_access(
            request.user,
            agreement.funding_offer,
        )

        documents = {
            "original": agreement.agreement_document,
            "investor_signed": agreement.investor_signed_document,
            "business_signed": agreement.business_signed_document,
        }

        document = documents.get(document_type)

        if not document:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            file = document.open("rb")

        except FileNotFoundError:
            return Response(
                {"detail": "Document file not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = FileResponse(
            file,
            as_attachment=True,
            filename=(
                f"agreement_{agreement.id}_{document_type}.pdf"
            ),
            content_type="application/pdf",
        )

        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response

class InvestorAgreementSignView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, agreement_id):

        # Only investors can sign
        if request.user.user_type != "investor":
            raise PermissionDenied(
                "Only investors can sign this agreement."
            )

        # Check investor ownership
        agreement = get_object_or_404(
            FundingAgreement.objects.select_for_update(),
            id=agreement_id,
            funding_offer__interest__funding_partner=request.user,
        )

        # Validate current agreement status
        if agreement.status != "pending_investor_signature":
            return Response(
                {
                    "detail": (
                        "Investor signature is not pending."
                    ),
                    "current_status": agreement.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Verify accepted funding offer
        if agreement.funding_offer.interest.status != "accepted":
            return Response(
                {
                    "detail": "Funding offer is not accepted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate uploaded PDF
        uploaded_file = validate_agreement_pdf(
            request.FILES.get("signed_document")
        )

        # Save investor-signed agreement
        agreement.investor_signed_document = uploaded_file
        agreement.investor_signed_by = request.user
        agreement.investor_signed_at = timezone.now()

        # Move to business signing stage
        agreement.status = "pending_business_signature"

        agreement.save(
            update_fields=[
                "investor_signed_document",
                "investor_signed_by",
                "investor_signed_at",
                "status",
                "updated_at",
            ]
        )

        serializer = FundingAgreementSerializer(
            agreement
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Investor-signed agreement submitted successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class BusinessAgreementSignView(APIView):

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, agreement_id):

        # Only business users can sign
        if request.user.user_type != "business":
            raise PermissionDenied(
                "Only business users can sign this agreement."
            )

        # Check business ownership
        agreement = get_object_or_404(
            FundingAgreement.objects.select_for_update(),
            id=agreement_id,
            funding_offer__interest__project__business__user=request.user,
        )

        # Validate agreement status
        if agreement.status != "pending_business_signature":
            return Response(
                {
                    "detail": "Business signature is not pending.",
                    "current_status": agreement.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Investor must sign first
        if not agreement.investor_signed_document:
            return Response(
                {
                    "detail": "Investor signature is required first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate accepted funding offer
        if agreement.funding_offer.interest.status != "accepted":
            return Response(
                {
                    "detail": "Funding offer is not accepted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate uploaded PDF
        uploaded_file = validate_agreement_pdf(
            request.FILES.get("signed_document")
        )

        # Save business-signed agreement
        agreement.business_signed_document = uploaded_file
        agreement.business_signed_by = request.user
        agreement.business_signed_at = timezone.now()

        # Move to admin verification
        agreement.status = "pending_verification"

        agreement.save(
            update_fields=[
                "business_signed_document",
                "business_signed_by",
                "business_signed_at",
                "status",
                "updated_at",
            ]
        )

        serializer = FundingAgreementSerializer(agreement)

        return Response(
            {
                "success": True,
                "message": (
                    "Business-signed agreement submitted successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class AdminFundingAgreementReviewView(APIView):

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, agreement_id):

        agreement = get_object_or_404(
            FundingAgreement.objects.select_for_update(),
            id=agreement_id,
        )

        # Only pending agreements can be reviewed
        if agreement.status != "pending_verification":
            return Response(
                {
                    "detail": (
                        "Agreement is not pending verification."
                    ),
                    "current_status": agreement.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        new_status = request.data.get("status")
        admin_note = request.data.get("admin_note", "")

        # Validate review status
        if new_status not in ["verified", "rejected"]:
            return Response(
                {
                    "detail": "Status must be verified or rejected."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(admin_note, str):
            return Response(
                {"admin_note": "Enter a valid text note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_note = admin_note.strip()

        # Rejection reason is mandatory
        if new_status == "rejected" and not admin_note:
            return Response(
                {"admin_note": "Rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "verified":

            # Both signatures must be submitted
            if not (
                agreement.investor_signed_document
                and agreement.business_signed_document
                and agreement.investor_signed_at
                and agreement.business_signed_at
            ):
                return Response(
                    {
                        "detail": "Both signed documents are required."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify funding offer acceptance
            if agreement.funding_offer.interest.status != "accepted":
                return Response(
                    {
                        "detail": "Funding offer is not accepted."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate agreement execution date
            executed_on = serializers.DateField().run_validation(
                request.data.get("executed_on")
            )

            if executed_on > timezone.localdate():
                return Response(
                    {
                        "executed_on": (
                            "Execution date cannot be in the future."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            agreement.executed_on = executed_on
            agreement.verified_by = request.user
            agreement.verified_at = timezone.now()

        # Save final decision
        agreement.status = new_status
        agreement.admin_note = admin_note

        agreement.save(
            update_fields=[
                "status",
                "admin_note",
                "executed_on",
                "verified_by",
                "verified_at",
                "updated_at",
            ]
        )

        serializer = FundingAgreementSerializer(agreement)

        return Response(
            {
                "success": True,
                "message": (
                    f"Funding agreement {new_status} successfully."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
