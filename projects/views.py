from django.db import transaction
from django.utils import timezone
from django.db.models import Count,Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,IsAdminUser


from .models import Project,ProjectStageHistory,PartnerProfile,ProjectDocument,DocumentRequirement
from .serializers import ProjectCreateSerializer,ProjectListSerializer,AdminProjectListSerializer,ProjectDetailSerializer,ProjectStageUpdateSerializer,ProjectStageHistorySerializer,ProjectDocumentSerializer,DocumentRequirementSerializer, BusinessFundingStatusSerializer

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from partners.models import PartnerProfile
from businesses.models import BusinessProfile, BusinessDocument, ProjectFundingInterest

class ProjectCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # Only business users can create projects
        if request.user.user_type != "business":
            return Response(
                {
                    "detail": "Only business users can create projects."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            business = request.user.business_profile
        except Exception:
            return Response(
                {
                    "detail": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProjectCreateSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Generate application reference
        year = timezone.now().year

        project_count = Project.objects.filter(
            reference_no__startswith=f"APP-{year}-"
        ).count()

        reference_no = f"APP-{year}-{project_count + 1:03d}"

        # Make sure reference is unique
        while Project.objects.filter(
            reference_no=reference_no
        ).exists():
            project_count += 1
            reference_no = f"APP-{year}-{project_count + 1:03d}"

        project = Project.objects.create(
            business=business,
            reference_no=reference_no,
            project_name=data["project_name"],
            sector=data["sector"],
            funding_target=data["funding_target"],
            estimated_start_date=data.get(
                "estimated_start_date"
            ),
            estimated_end_date=data.get(
                "estimated_end_date"
            ),
            description=data["description"],
            stage="documents_pending",
        )

        return Response(
            {
                "message": "Project application created successfully.",
                "project": {
                    "id": project.id,
                    "reference_no": project.reference_no,
                    "project_name": project.project_name,
                    "sector": project.sector,
                    "funding_target": project.funding_target,
                    "estimated_start_date": (
                        project.estimated_start_date
                    ),
                    "estimated_end_date": (
                        project.estimated_end_date
                    ),
                    "description": project.description,
                    "stage": project.stage,
                    "submitted_at": project.submitted_at,
                }
            },
            status=status.HTTP_201_CREATED
        )
class MyProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != "business":
            return Response(
                {
                    "detail": "Only business users can access their projects."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            business = request.user.business_profile
        except Exception:
            return Response(
                {
                    "detail": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        projects = (
            Project.objects
            .filter(business=business)
            .order_by("-created_at")
        )

        serializer = ProjectListSerializer(
            projects,
            many=True
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )

class AdminProjectListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        projects = (
            Project.objects
            .select_related("business", "assigned_partner")
            .all()
            .order_by("-created_at")
        )

        # Search by project, reference, business, sector or partner
        search = request.query_params.get("search", "").strip()

        if search:
            projects = projects.filter(
                Q(reference_no__icontains=search)
                | Q(project_name__icontains=search)
                | Q(business__business_trade_name__icontains=search)
                | Q(sector__icontains=search)
                | Q(
                    assigned_partner__organization_name__icontains=search
                )
            )

        # Filter by project stage
        stage = request.query_params.get("stage", "").strip()

        if stage and stage.lower() != "all":
            valid_stages = dict(Project.STAGE_CHOICES)

            if stage not in valid_stages:
                return Response(
                    {
                        "detail": "Invalid project stage.",
                        "valid_stages": list(valid_stages.keys()),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            projects = projects.filter(stage=stage)

        serializer = AdminProjectListSerializer(
            projects,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    
class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            project = (
                Project.objects
                .select_related(
                    "business",
                    "assigned_partner"
                )
                .get(pk=pk)
            )
        except Project.DoesNotExist:
            return Response(
                {
                    "detail": "Project not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Business users can only view their own project
        if request.user.user_type == "business":
            try:
                business = request.user.business_profile
            except Exception:
                return Response(
                    {
                        "detail": "Business profile not found."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            if project.business_id != business.id:
                return Response(
                    {
                        "detail": "You do not have access to this project."
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

        # Only admin and the owning business can view for now
        elif not request.user.is_staff:
            return Response(
                {
                    "detail": "You do not have permission to view this project."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectDetailSerializer(project)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class ProjectStageUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            project = Project.objects.select_related(
                "business", "assigned_partner"
            ).get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectStageUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_stage = serializer.validated_data["stage"]
        internal_note = serializer.validated_data.get("internal_note", "")

        if project.stage == new_stage:
            return Response(
                {"detail": "Project is already in this stage."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_stage = project.stage

        # Preserve the project stage history.
        ProjectStageHistory.objects.create(
            project=project,
            from_stage=old_stage,
            to_stage=new_stage,
            changed_by=request.user,
            internal_note=internal_note,
        )

        project.stage = new_stage

        # Record when Admin makes the final decision.
        if (
            old_stage == "final_admin_review"
            and new_stage in ["approved", "rejected"]
        ):
            project.admin_final_reviewed_at = timezone.now()

        project.save(
            update_fields=[
                "stage",
                "admin_final_reviewed_at",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": "Project stage updated successfully.",
                "project": {
                    "id": project.id,
                    "reference_no": project.reference_no,
                    "stage": project.stage,
                    "stage_label": project.get_stage_display(),
                    "internal_note": internal_note,
                },
            },
            status=status.HTTP_200_OK,
        )


class ProjectStageHistoryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {
                    "detail": "Project not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        history = (
            ProjectStageHistory.objects
            .filter(project=project)
            .select_related("changed_by")
            .order_by("-created_at")
        )

        serializer = ProjectStageHistorySerializer(
            history,
            many=True
        )

        return Response(
            {
                "project": {
                    "id": project.id,
                    "reference_no": project.reference_no,
                    "project_name": project.project_name,
                },
                "history": serializer.data,
            },
            status=status.HTTP_200_OK
        )


class ProjectPartnerAssignView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            project = Project.objects.select_for_update().get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        partner_id = request.data.get("partner_id")
        internal_note = request.data.get("internal_note", "")

        if partner_id is None:
            return Response(
                {"partner_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            partner_id = int(partner_id)
        except (TypeError, ValueError):
            return Response(
                {"partner_id": "Enter a valid partner ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            partner = PartnerProfile.objects.get(pk=partner_id)
        except PartnerProfile.DoesNotExist:
            return Response(
                {"partner_id": "Funding partner not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if partner.status not in ["active", "approved"]:
            return Response(
                {
                    "partner_id": (
                        "Only active or approved partners can be assigned."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_stage = project.stage
        new_stage = "partner_assigned"

        # Record the workflow change when the stage changes.
        if old_stage != new_stage:
            ProjectStageHistory.objects.create(
                project=project,
                from_stage=old_stage,
                to_stage=new_stage,
                changed_by=request.user,
                internal_note=internal_note,
            )

        project.assigned_partner = partner
        project.stage = new_stage
        project.save(
            update_fields=[
                "assigned_partner",
                "stage",
                "updated_at",
            ]
        )

        return Response(
            {
                "message": "Funding partner assigned successfully.",
                "project": {
                    "id": project.id,
                    "reference_no": project.reference_no,
                    "project_name": project.project_name,
                    "stage": project.stage,
                    "stage_label": project.get_stage_display(),
                    "assigned_partner_id": partner.id,
                    "assigned_partner_name": partner.organization_name,
                },
            },
            status=status.HTTP_200_OK,
        )

class PartnerAssignedProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ensure the logged-in user is a funding partner
        try:
            partner = request.user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {"detail": "You are not registered as a funding partner."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only show projects assigned to this partner
        projects = (
            Project.objects
            .filter(assigned_partner=partner)
            .select_related("business", "assigned_partner")
            .order_by("-created_at")
        )

        serializer = AdminProjectListSerializer(projects, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)



class PartnerAssignedProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Allow only Consulting Partners
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
                {"detail": "Consulting Partner profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            project = (
                Project.objects
                .select_related("business", "assigned_partner")
                .get(pk=pk, assigned_partner=partner)
            )
        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectDetailSerializer(project)

        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



def can_view_project_documents(user, project):
    """Allow the business owner, admin, or assigned partner to view documents."""
    if user.is_staff or user.is_superuser:
        return True

    if project.business.user_id == user.id:
        return True

    partner = PartnerProfile.objects.filter(user=user).first()
    if partner and project.assigned_partner_id == partner.id:
        return True

    return False


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def project_documents(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # GET: list documents for this project
    if request.method == "GET":
        if not can_view_project_documents(request.user, project):
            return Response(
                {"detail": "You do not have permission to view these documents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        documents = ProjectDocument.objects.filter(project=project).order_by("-created_at")
        serializer = ProjectDocumentSerializer(
            documents, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST: only the owning business can upload documents
    if project.business.user_id != request.user.id:
        return Response(
            {"detail": "Only the business owner can upload documents."},
            status=status.HTTP_403_FORBIDDEN,
        )

    
    document_name = request.data.get("document_name")
    print("CONTENT_TYPE:", request.content_type)
    print("REQUEST DATA:", request.data)
    print("FILES:", request.FILES)
    uploaded_file = request.FILES.get("file")
    requirement_id = request.data.get("requirement")

    if not document_name:
        return Response(
            {"document_name": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not uploaded_file:
        return Response(
            {"file": "Please attach a file to upload."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # A requirement must be specified for this upload.
    if not requirement_id:
        return Response(
            {"requirement": "Select a document requirement."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find the requirement and ensure it is active.
    try:
        requirement = DocumentRequirement.objects.get(
            pk=requirement_id,
            is_active=True,
        )
    except (DocumentRequirement.DoesNotExist, ValueError, TypeError):
        return Response(
            {"requirement": "Invalid or inactive document requirement."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check whether this requirement applies to the project's sector.
    if (
        requirement.applies_to_sector
        and requirement.applies_to_sector.strip().casefold()
        != project.sector.strip().casefold()
    ):
        return Response(
            {
                "requirement": (
                    "This document requirement does not apply "
                    "to the project's sector."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate file extension.
    file_name = uploaded_file.name
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if extension not in requirement.accepted_formats:
        return Response(
            {
                "file": (
                    f"Unsupported file format. Allowed formats: "
                    f"{', '.join(requirement.accepted_formats)}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate maximum file size.
    max_size_bytes = requirement.max_file_size_mb * 1024 * 1024

    if uploaded_file.size > max_size_bytes:
        return Response(
            {
                "file": (
                    f"File size exceeds the maximum of "
                    f"{requirement.max_file_size_mb} MB."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Save the uploaded document with its requirement.
    document = ProjectDocument.objects.create(
        project=project,
        requirement=requirement,
        document_name=document_name,
        file=uploaded_file,
        status="uploaded",
        uploaded_by=request.user,
        uploaded_at=timezone.now(),
    )

    serializer = ProjectDocumentSerializer(
        document,
        context={"request": request},
    )

    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED,
    )




@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def review_project_document(request, document_id):
    user = request.user

    # 1. Check whether the user is an Admin.
    is_admin = user.is_staff or user.is_superuser

    # 2. Allow only Admins and Consulting Partners.
    is_consulting_partner = (
        user.user_type == "consulting_partner"
    )

    if not is_admin and not is_consulting_partner:
        return Response(
            {
                "detail": (
                    "Only admins and consulting partners "
                    "can review documents."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3. Get the document and its related project.
    document = get_object_or_404(
        ProjectDocument.objects.select_related(
            "project",
            "project__assigned_partner",
        ),
        pk=document_id,
    )

    # 4. Consultants can review only their assigned projects.
    if is_consulting_partner and not is_admin:
        try:
            partner = user.partner_profile
        except PartnerProfile.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Consulting Partner profile not found."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if document.project.assigned_partner_id != partner.id:
            return Response(
                {
                    "detail": (
                        "You can only review documents "
                        "belonging to projects assigned to you."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

    # 5. Validate the requested review status.
    new_status = request.data.get("status")
    note = request.data.get("admin_note", "")

    if not isinstance(note, str):
        return Response(
            {"admin_note": "Enter a valid text note."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_statuses = [
        "under_review",
        "approved",
        "requires_change",
    ]

    if new_status not in allowed_statuses:
        return Response(
            {
                "status": (
                    "Choose under_review, approved, "
                    "or requires_change."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 6. A reason is mandatory when requesting changes.
    if new_status == "requires_change" and not note.strip():
        return Response(
            {
                "admin_note": (
                    "Add a note explaining the required changes."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 7. Save the review.
    document.status = new_status
    document.admin_note = note.strip()
    document.reviewed_by = user
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

    # 8. Return the updated document.
    serializer = ProjectDocumentSerializer(
        document,
        context={"request": request},
    )

    return Response(
        {
            "success": True,
            "message": "Document review updated successfully.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )



@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_project_document(request, document_id):
    document = get_object_or_404(ProjectDocument, pk=document_id)
    user = request.user

    is_admin = user.is_staff or user.is_superuser
    is_business_owner = document.project.business.user_id == user.id

    # Business owners can delete their own documents before approval.
    if not is_admin and not is_business_owner:
        return Response(
            {"detail": "You do not have permission to delete this document."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not is_admin and document.status == "approved":
        return Response(
            {"detail": "Approved documents cannot be deleted by the business owner."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if document.file:
        document.file.delete(save=False)

    document.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)



class DocumentRequirementListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Admin-only access
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        requirements = DocumentRequirement.objects.all()

        # Optional filters
        sector = request.query_params.get("sector")
        is_active = request.query_params.get("is_active")

        if sector:
            requirements = requirements.filter(
                applies_to_sector__in=["", sector]
            )

        if is_active is not None:
            if is_active.lower() in ["true", "1"]:
                requirements = requirements.filter(is_active=True)
            elif is_active.lower() in ["false", "0"]:
                requirements = requirements.filter(is_active=False)

        serializer = DocumentRequirementSerializer(
            requirements, many=True
        )

        return Response({
            "success": True,
            "count": requirements.count(),
            "data": serializer.data
        })

    def post(self, request):
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = DocumentRequirementSerializer(data=request.data)

        if serializer.is_valid():
            requirement = serializer.save()

            return Response({
                "success": True,
                "message": "Document requirement created successfully.",
                "data": DocumentRequirementSerializer(requirement).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DocumentRequirementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_requirement(self, pk):
        try:
            return DocumentRequirement.objects.get(pk=pk)
        except DocumentRequirement.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        requirement = self.get_requirement(pk)

        if not requirement:
            return Response(
                {"success": False, "message": "Document requirement not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DocumentRequirementSerializer(requirement)

        return Response({
            "success": True,
            "data": serializer.data
        })

    def put(self, request, pk):
        return self.update_requirement(request, pk, partial=False)

    def patch(self, request, pk):
        return self.update_requirement(request, pk, partial=True)

    def update_requirement(self, request, pk, partial=False):
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        requirement = self.get_requirement(pk)

        if not requirement:
            return Response(
                {"success": False, "message": "Document requirement not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DocumentRequirementSerializer(
            requirement,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            requirement = serializer.save()

            return Response({
                "success": True,
                "message": "Document requirement updated successfully.",
                "data": DocumentRequirementSerializer(requirement).data
            })

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )

        requirement = self.get_requirement(pk)

        if not requirement:
            return Response(
                {"success": False, "message": "Document requirement not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Soft delete: keep the record, but deactivate it.
        requirement.is_active = False
        requirement.save(update_fields=["is_active", "updated_at"])

        return Response({
            "success": True,
            "message": "Document requirement deactivated successfully."
        }, status=status.HTTP_200_OK)


class ProjectMissingDocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # 1. Get the project
        project = get_object_or_404(Project, pk=pk)

        # 2. Check whether the user can view project documents
        if not can_view_project_documents(request.user, project):
            return Response(
                {
                    "detail": "You do not have permission to view these documents."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Get active document requirements applicable to this project
        requirements = DocumentRequirement.objects.filter(
            is_active=True
        ).filter(
            Q(applies_to_sector="") |
            Q(applies_to_sector__iexact=project.sector)
        ).order_by("name")

        documents_data = []

        # 4. Check each requirement against uploaded project documents
        for requirement in requirements:
            document = ProjectDocument.objects.filter(
                project=project,
                requirement=requirement
            ).order_by("-created_at").first()

            if document:
                document_status = document.status
            else:
                document_status = "missing"

            documents_data.append({
                "requirement_id": requirement.id,
                "requirement_name": requirement.name,
                "description": requirement.description,
                "accepted_formats": requirement.accepted_formats,
                "max_file_size_mb": requirement.max_file_size_mb,
                "status": document_status,
                "document_id": document.id if document else None,
                "document_name": (
                    document.document_name if document else None
                ),
            })

        # 5. Count requirements that have no linked document
        missing_count = sum(
            1 for item in documents_data
            if item["status"] == "missing"
        )

        # 6. Return the response
        return Response(
            {
                "project_id": project.id,
                "project_name": project.project_name,
                "total_requirements": len(documents_data),
                "missing_count": missing_count,
                "documents": documents_data,
            },
            status=status.HTTP_200_OK
        )


class AdminDocumentReviewQueueView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Get all project documents
        documents = ProjectDocument.objects.select_related(
            "project",
            "project__business",
            "uploaded_by",
            "reviewed_by",
            "requirement",
        ).order_by("-created_at")

        # Filter by document status
        document_status = request.query_params.get("status", "").strip()

        if document_status and document_status.lower() != "all":
            valid_statuses = {
                choice[0]
                for choice in ProjectDocument._meta
                .get_field("status").choices
            }

            if document_status not in valid_statuses:
                return Response(
                    {
                        "detail": "Invalid document status.",
                        "valid_statuses": sorted(valid_statuses),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            documents = documents.filter(status=document_status)

        # Search by project, reference, business or document name
        search = request.query_params.get("search", "").strip()

        if search:
            documents = documents.filter(
                Q(project__project_name__icontains=search)
                | Q(project__reference_no__icontains=search)
                | Q(
                    project__business__business_trade_name__icontains=search
                )
                | Q(document_name__icontains=search)
            )

        # Optional filter by project ID
        project_id = request.query_params.get("project_id", "").strip()

        if project_id:
            if not project_id.isdigit():
                return Response(
                    {"project_id": "Enter a valid project ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            documents = documents.filter(project_id=int(project_id))

        serializer = ProjectDocumentSerializer(
            documents,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "count": documents.count(),
                "filters": {
                    "status": document_status or "all",
                    "search": search,
                    "project_id": project_id or None,
                },
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Main dashboard cards
        total_businesses = BusinessProfile.objects.count()
        total_partners = PartnerProfile.objects.count()
        total_projects = Project.objects.count()

        # Project documents awaiting admin review
        pending_project_documents = ProjectDocument.objects.filter(
            status__in=["uploaded", "under_review"]
        ).count()

        # Business verification statistics
        verification_counts = {
            "pending": BusinessProfile.objects.filter(
                verification_status="pending"
            ).count(),
            "under_review": BusinessProfile.objects.filter(
                verification_status="under_review"
            ).count(),
            "verified": BusinessProfile.objects.filter(
                verification_status="verified"
            ).count(),
            "requires_change": BusinessProfile.objects.filter(
                verification_status="requires_change"
            ).count(),
            "rejected": BusinessProfile.objects.filter(
                verification_status="rejected"
            ).count(),
        }

        # Business documents awaiting review
        pending_business_documents = BusinessDocument.objects.filter(
            status__in=["uploaded", "under_review"]
        ).count()

        # Count projects in each stage, including stages with zero projects
        actual_stage_counts = {
            item["stage"]: item["count"]
            for item in Project.objects.values("stage").annotate(
                count=Count("id")
            )
        }

        project_stage_counts = {
            stage_value: actual_stage_counts.get(stage_value, 0)
            for stage_value, stage_label in Project.STAGE_CHOICES
        }

        # Document requirements
        total_document_requirements = DocumentRequirement.objects.filter(
            is_active=True
        ).count()

        # Recent projects
        recent_projects = Project.objects.select_related(
            "business",
            "assigned_partner",
        ).order_by("-created_at")[:5]

        recent_projects_data = [
            {
                "id": project.id,
                "reference_no": project.reference_no,
                "project_name": project.project_name,
                "business_name": project.business.business_trade_name,
                "stage": project.stage,
                "stage_label": project.get_stage_display(),
                "funding_target": str(project.funding_target),
                "assigned_partner": (
                    project.assigned_partner.organization_name
                    if project.assigned_partner
                    else None
                ),
                "created_at": project.created_at,
            }
            for project in recent_projects
        ]

        return Response(
            {
                "success": True,
                "message": "Admin dashboard statistics retrieved successfully.",
                "data": {
                    "summary": {
                        "total_businesses": total_businesses,
                        "total_funding_partners": total_partners,
                        "total_projects": total_projects,
                        "pending_project_document_reviews": (
                            pending_project_documents
                        ),
                        "pending_business_document_reviews": (
                            pending_business_documents
                        ),
                        "active_document_requirements": (
                            total_document_requirements
                        ),
                    },
                    "business_verification": verification_counts,
                    "project_stage_counts": project_stage_counts,
                    "recent_projects": recent_projects_data,
                },
            },
            status=status.HTTP_200_OK,
        )



class AdminBusinessVerificationQueueView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        businesses = BusinessProfile.objects.select_related(
            "user",
            "verified_by",
        ).order_by("-id")

        # Filter by verification status
        verification_status = request.query_params.get(
            "status", ""
        ).strip()

        valid_statuses = {
            choice[0]
            for choice in BusinessProfile.VERIFICATION_STATUS_CHOICES
        }

        if verification_status:
            if verification_status not in valid_statuses:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid verification status.",
                        "valid_statuses": sorted(valid_statuses),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            businesses = businesses.filter(
                verification_status=verification_status
            )

        # Search by business name, contact name, or email
        search = request.query_params.get("search", "").strip()

        if search:
            businesses = businesses.filter(
                Q(business_trade_name__icontains=search)
                | Q(full_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        results = [
            {
                "id": business.id,
                "business_name": business.business_trade_name,
                "contact_name": business.full_name,
                "email": business.user.email,
                "mobile_number": business.mobile_number,
                "sector": business.sector,
                "business_type": business.get_business_type_display(),
                "verification_status": business.verification_status,
                "verification_status_label": (
                    business.get_verification_status_display()
                ),
                "verification_note": business.verification_note,
                "verified_at": business.verified_at,
                "verified_by": (
                    business.verified_by.email
                    if business.verified_by
                    else None
                ),
            }
            for business in businesses
        ]

        return Response(
            {
                "success": True,
                "count": len(results),
                "filters": {
                    "status": verification_status or "all",
                    "search": search,
                },
                "data": results,
            },
            status=status.HTTP_200_OK,
        )


class AdminBusinessVerificationActionView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, business_id):
        try:
            business = BusinessProfile.objects.select_related(
                "user", "verified_by"
            ).get(pk=business_id)
        except BusinessProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Business not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        verification_status = request.data.get("verification_status")
        note = request.data.get("verification_note", "").strip()

        allowed_statuses = {
            "under_review",
            "verified",
            "requires_change",
            "rejected",
        }

        if verification_status not in allowed_statuses:
            return Response(
                {
                    "success": False,
                    "message": "Invalid verification status.",
                    "allowed_statuses": sorted(allowed_statuses),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification_status in {"requires_change", "rejected"} and not note:
            return Response(
                {
                    "success": False,
                    "message": (
                        "A verification note is required for "
                        "requires_change or rejected status."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        business.verification_status = verification_status
        business.verification_note = note

        if verification_status == "verified":
            business.verified_at = timezone.now()
            business.verified_by = request.user
        else:
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
                "success": True,
                "message": "Business verification status updated successfully.",
                "business": {
                    "id": business.id,
                    "business_name": business.business_trade_name,
                    "email": business.user.email,
                    "verification_status": business.verification_status,
                    "verification_note": business.verification_note,
                    "verified_at": business.verified_at,
                    "verified_by": (
                        business.verified_by.email
                        if business.verified_by
                        else None
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )


class BusinessFundingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != "business":
            return Response(
                {
                    "success": False,
                    "message": "Only business users can access funding status."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        business = getattr(request.user, "business_profile", None)

        if not business:
            return Response(
                {
                    "success": False,
                    "message": "Business profile not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        funding_statuses = (
            ProjectFundingInterest.objects
            .filter(project__business=business)
            .select_related("project", "funding_partner")
            .order_by("-updated_at")
        )

        requested_status = request.query_params.get("status")

        if requested_status:
            valid_statuses = dict(
                ProjectFundingInterest.STATUS_CHOICES
            )

            if requested_status not in valid_statuses:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid funding status.",
                        "valid_statuses": list(valid_statuses.keys())
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            funding_statuses = funding_statuses.filter(
                status=requested_status
            )

        serializer = BusinessFundingStatusSerializer(
            funding_statuses,
            many=True
        )

        return Response(
            {
                "success": True,
                "count": funding_statuses.count(),
                "results": serializer.data
            },
            status=status.HTTP_200_OK
        )