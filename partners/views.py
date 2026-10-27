from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from projects.models import Project, ProjectDocument,ProjectStageHistory
from projects.serializers import AdminProjectListSerializer,ProjectDocumentSerializer

from accounts.models import CustomUser

from .models import PartnerProfile,PartnerKYCDocument
from .serializers import (
    PartnerListSerializer,
    PartnerCreateSerializer,
    PartnerDetailSerializer,
    ConsultingPartnerProfileSerializer,
    PartnerKYCDocumentSerializer
)


class PartnerListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        partners = (
            PartnerProfile.objects
            .select_related("user")
            .all()
            .order_by("-created_at")
        )

        serializer = PartnerListSerializer(
            partners,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class PartnerCreateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        serializer = PartnerCreateSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        if CustomUser.objects.filter(
            email__iexact=data["email"]
        ).exists():
            return Response(
                {
                    "email": (
                        "An account with this email "
                        "already exists."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = CustomUser.objects.create(
            username=data["email"],
            email=data["email"],
            user_type="consulting_partner",
        )

        user.set_unusable_password()
        user.save()

        partner = PartnerProfile.objects.create(
            user=user,
            full_name=data["full_name"],
            organization_name=data["organization_name"],
            specialty=data["specialty"],
            phone=data.get("phone"),
            status=data["status"],
        )

        token = default_token_generator.make_token(user)

        uid = urlsafe_base64_encode(force_bytes(user.pk))

        setup_url = (
            f"http://127.0.0.1:8000/accounts/set-password/"
            f"?uid={uid}&token={token}"
        )
        print("Sending partner invitation to:", user.email)
        send_mail(
            subject="Complete Your Funding Partner Account Setup",
            message=(
                f"Hello {partner.full_name},\n\n"
                "Your Funding Partner account has been "
                "created on the Business Financing Platform.\n\n"
                "Please use the following link to set "
                "your password:\n\n"
                f"{setup_url}\n\n"
                "After setting your password, you can "
                "log in to the platform.\n\n"
                "Regards,\n"
                "Business Financing Team"
            ),
            from_email=None,
            recipient_list=[user.email],
        )
        print("Partner invitation sent")

        return Response(
            {
                "message": (
                    "Funding Partner created successfully."
                ),
                "partner": {
                    "id": partner.id,
                    "full_name": partner.full_name,
                    "organization_name": partner.organization_name,
                    "specialty": partner.specialty,
                    "email": user.email,
                    "phone": partner.phone,
                    "status": partner.status,
                },
            },
            status=status.HTTP_201_CREATED
        )

class PartnerDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(Self, request, pk):
        try:
            partner = (
                PartnerProfile.objects.select_related("user").get(pk=pk)
            )
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Funding Partner not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PartnerDetailSerializer(partner)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
class PartnerDeactivateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            partner = (
                PartnerProfile.objects
                .select_related("user")
                .get(pk=pk)
            )
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Funding Partner not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if partner.status == "inactive":
            return Response(
                {"detail": "Funding Partner is already inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )

        partner.status = "inactive"
        partner.save(update_fields=["status"])

        user = partner.user
        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Funding Partner deactivated successfully.",
                "partner": {
                    "id": partner.id,
                    "organization_name": partner.organization_name,
                    "status": partner.status,
                    "is_active": user.is_active,
                },
            },
            status=status.HTTP_200_OK
        )
    
class PartnerActivateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            partner = (
                PartnerProfile.objects
                .select_related("user")
                .get(pk=pk)
            )
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Funding Partner not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if partner.status != "inactive":
            return Response(
                {"detail": "Funding Partner is already active."},
                status=status.HTTP_400_BAD_REQUEST
            )

        partner.status = "active"
        partner.save(update_fields=["status"])

        user = partner.user
        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {
                "message": "Funding Partner activated successfully.",
                "partner": {
                    "id": partner.id,
                    "organization_name": partner.organization_name,
                    "status": partner.status,
                    "is_active": user.is_active,
                },
            },
            status=status.HTTP_200_OK
        )





class ConsultingPartnerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only Consulting Partners can access this dashboard.
        if request.user.user_type != "consulting_partner":
            return Response(
                {
                    "detail": (
                        "Only consulting partners can "
                        "access this dashboard."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get the logged-in user's partner profile.
        try:
            partner = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Projects assigned to this partner only.
        assigned_projects = Project.objects.filter(
            assigned_partner=partner
        )

        # Documents belonging to assigned projects.
        documents = ProjectDocument.objects.filter(
            project__assigned_partner=partner
        )

        # Total projects assigned to this partner.
        assigned_count = assigned_projects.count()

        # Documents waiting for the consultant's review.
        pending_reviews = documents.filter(
            status__in=["uploaded", "under_review"]
        ).count()

        # Projects finalized by Admin.
        completed_reviews = assigned_projects.filter(
            stage__in=["approved", "rejected"],
            partner_review_result__isnull=False,
            admin_final_reviewed_at__isnull=False,
        ).count()

        return Response(
            {
                "success": True,
                "message": (
                    "Consulting Partner dashboard "
                    "loaded successfully."
                ),
                "data": {
                    "summary": {
                        "assigned_projects": assigned_count,
                        "pending_reviews": pending_reviews,
                        "completed_reviews": completed_reviews,
                    }
                },
            },
            status=status.HTTP_200_OK,
        )



class PartnerAssignedProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only Consulting Partners can access this endpoint.
        if request.user.user_type != "consulting_partner":
            return Response(
                {
                    "detail": (
                        "Only consulting partners can "
                        "access these projects."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            partner = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Consulting Partner profile not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        projects = (
            Project.objects
            .filter(assigned_partner=partner)
            .select_related("business", "assigned_partner")
            .order_by("-created_at")
        )

        serializer = AdminProjectListSerializer(
            projects,
            many=True,
        )

        return Response(
            {
                "success": True,
                "count": projects.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class ConsultingPartnerPendingReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != "consulting_partner":
            return Response(
                {
                    "detail": (
                        "Only consulting partners can access "
                        "pending reviews."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            partner = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        documents = (
            ProjectDocument.objects
            .filter(
                project__assigned_partner=partner,
                status__in=["uploaded", "under_review"],
            )
            .select_related(
                "project",
                "project__business",
                "uploaded_by",
                "reviewed_by",
                "requirement",
            )
            .order_by("-created_at")
        )

        serializer = ProjectDocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "count": documents.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class ConsultingPartnerSubmitVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, project_id):
        user = request.user

        if user.user_type != "consulting_partner":
            return Response(
                {"detail": "Only consulting partners can submit verification."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            partner = user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            project = (
                Project.objects
                .select_for_update()
                .get(pk=project_id, assigned_partner=partner)
            )
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if project.stage not in ["partner_assigned", "partner_review"]:
            return Response(
                {
                    "detail": (
                        "This project is not currently available "
                        "for partner verification."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = request.data.get("result")
        note = request.data.get("note", "")

        allowed_results = {"verified", "requires_change"}

        if result not in allowed_results:
            return Response(
                {
                    "result": (
                        "Choose 'verified' or 'requires_change'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(note, str):
            return Response(
                {"note": "Enter a valid text note."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = note.strip()

        if result == "requires_change" and not note:
            return Response(
                {
                    "note": (
                        "Please explain why changes are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        documents = ProjectDocument.objects.filter(project=project)

        # A Verified result requires every uploaded document to be approved.
        if result == "verified":
            non_approved = documents.exclude(status="approved")

            if non_approved.exists():
                return Response(
                    {
                        "detail": (
                            "All project documents must be approved "
                            "before submitting a Verified result."
                        ),
                        "documents_not_approved": list(
                            non_approved.values(
                                "id", "document_name", "status"
                            )
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        old_stage = project.stage
        new_stage = "final_admin_review"

        project.partner_review_result = result
        project.partner_review_note = note
        project.partner_reviewed_at = timezone.now()
        project.stage = new_stage

        project.save(
            update_fields=[
                "partner_review_result",
                "partner_review_note",
                "partner_reviewed_at",
                "stage",
                "updated_at",
            ]
        )

        if old_stage != new_stage:
            ProjectStageHistory.objects.create(
                project=project,
                from_stage=old_stage,
                to_stage=new_stage,
                changed_by=user,
                internal_note=note,
            )

        return Response(
            {
                "success": True,
                "message": "Verification submitted for Admin final review.",
                "data": {
                    "project_id": project.id,
                    "reference_no": project.reference_no,
                    "result": project.partner_review_result,
                    "note": project.partner_review_note,
                    "reviewed_at": project.partner_reviewed_at,
                    "stage": project.stage,
                    "stage_label": project.get_stage_display(),
                },
            },
            status=status.HTTP_200_OK,
        )





class ConsultingPartnerCompletedReviewsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != "consulting_partner":
            return Response(
                {"detail": "Access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            partner = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        projects = Project.objects.filter(
            assigned_partner=partner,
            stage__in=["approved", "rejected"],
            partner_review_result__isnull=False,
            admin_final_reviewed_at__isnull=False,
        ).select_related("business").order_by(
            "-admin_final_reviewed_at"
        )

        data = []

        for project in projects:
            data.append({
                "id": project.id,
                "reference_no": project.reference_no,
                "project_name": project.project_name,
                "business_name": str(project.business),
                "funding_target": project.funding_target,
                "consultant_result": project.partner_review_result,
                "consultant_note": project.partner_review_note,
                "consultant_reviewed_at": project.partner_reviewed_at,
                "final_result": project.stage,
                "completed_at": project.admin_final_reviewed_at,
            })

        return Response(data, status=status.HTTP_200_OK)




class ConsultingPartnerProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get_partner(self, request):
        if request.user.user_type != "consulting_partner":
            return None

        try:
            return request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return None

    def get(self, request):
        partner = self.get_partner(request)

        if partner is None:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConsultingPartnerProfileSerializer(partner)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        partner = self.get_partner(request)

        if partner is None:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConsultingPartnerProfileSerializer(
            partner,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return Response(
            {
                "message": "Profile updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class ConsultingPartnerKYCDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    ALLOWED_EXTENSIONS = {
        "pdf", "jpg", "jpeg", "png", "doc", "docx"
    }
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    def get_partner(self, request):
        if request.user.user_type != "consulting_partner":
            return None

        try:
            return request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return None

    def get(self, request):
        partner = self.get_partner(request)

        if partner is None:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        documents = PartnerKYCDocument.objects.filter(
            partner=partner
        ).select_related("partner")

        serializer = PartnerKYCDocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "count": documents.count(),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        partner = self.get_partner(request)

        if partner is None:
            return Response(
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        document_type = request.data.get("document_type")
        uploaded_file = request.FILES.get("file")

        allowed_types = {
            choice[0]
            for choice in PartnerKYCDocument.DOCUMENT_TYPE_CHOICES
        }

        if document_type not in allowed_types:
            return Response(
                {"document_type": "Choose a valid document type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not uploaded_file:
            return Response(
                {"file": "Please select a file to upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = uploaded_file.name.rsplit(".", 1)[-1].lower()

        if "." not in uploaded_file.name or extension not in self.ALLOWED_EXTENSIONS:
            return Response(
                {"file": "Allowed formats: PDF, JPG, PNG, DOC and DOCX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > self.MAX_FILE_SIZE:
            return Response(
                {"file": "Maximum file size is 5 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document, created = PartnerKYCDocument.objects.update_or_create(
            partner=partner,
            document_type=document_type,
            defaults={
                "file": uploaded_file,
                "status": "pending",
                "admin_note": "",
            },
        )

        serializer = PartnerKYCDocumentSerializer(
            document,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": (
                    "KYC document uploaded successfully."
                    if created
                    else "KYC document replaced successfully."
                ),
                "data": serializer.data,
            },
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )
