from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser,IsAuthenticated

from .models import BusinessProfile,BusinessDocument
from django.db import transaction,models
from django.db.models import Count
from accounts.models import CustomUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import BusinessListSerializer,BusinessCreateSerializer,BusinessDetailSerializer,BusinessUpdateSerializer,BusinessDocumentSerializer,BusinessVerificationSerializer,MyBusinessProfileSerializer
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.shortcuts import get_object_or_404
from django.utils import timezone
from projects.models import Project, ProjectDocument, DocumentRequirement
from businesses.models import BusinessProfile
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser


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

    def patch(self, request, business_id):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"detail": "Only admins can update business verification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        business = get_object_or_404(BusinessProfile, pk=business_id)

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
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status in {"requires_change", "rejected"} and not note.strip():
            return Response(
                {"detail": "A verification note is required for this status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        business.verification_status = new_status
        business.verification_note = note
        business.verified_by = request.user
        business.verified_at = timezone.now()
        business.save(
            update_fields=[
                "verification_status",
                "verification_note",
                "verified_by",
                "verified_at",
            ]
        )

        serializer = BusinessVerificationSerializer(business)
        return Response(serializer.data, status=status.HTTP_200_OK)



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