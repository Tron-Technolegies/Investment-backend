from rest_framework.generics import ListAPIView,RetrieveAPIView,UpdateAPIView,RetrieveUpdateAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.db import transaction
from accounts.models import CustomUser
from django.shortcuts import get_object_or_404
from .models import InvestorProfile
from .serializers import InvestorDetailSerializer, InvestorListSerializer, InvestorCreateSerializer,InvestorUpdateSerializer,MyInvestorProfileSerializer,ExploreBusinessSerializer,MyInterestListSerializer,MyFundingRequestSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from projects.models import Project
from rest_framework import status
from django.core.mail import send_mail
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from businesses.models import ProjectFundingInterest
from projects.models import Project
import logging
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail


logger = logging.getLogger(__name__)
class InvestorListView(ListAPIView):
    queryset = InvestorProfile.objects.select_related("user").all().order_by("-user__created_at")
    serializer_class = InvestorListSerializer
    permission_classes = [IsAdminUser]


class InvestorCreateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        serializer = InvestorCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        # Check whether email already exists
        if CustomUser.objects.filter(
            email__iexact=data["email"]
        ).exists():
            return Response(
                {"email": "An account with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create investor account
        user = CustomUser.objects.create_user(
            username=data["email"],
            email=data["email"],
            user_type="investor",
        )

        # Investor must set a password before logging in
        user.set_unusable_password()
        user.save(update_fields=["password"])

        # Create investor profile
        investor = InvestorProfile.objects.create(
            user=user,
            full_name=data["full_name"],
            organization=data.get("organization", ""),
            investor_type=data["investor_type"],
            mobile_number=data["mobile_number"],
            status=data["status"],
        )

        # Generate password setup token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Use the deployed frontend URL from Render environment variables.
        frontend_url = os.getenv(
            "FRONTEND_URL",
            "http://localhost:5174"
        ).rstrip("/")

        # Ensure this path matches your frontend router.
        setup_url = (
            f"{frontend_url}/set-password"
            f"?uid={uid}&token={token}"
        )

        # Email failure must not turn successful investor creation
        # into an HTTP 500 response.
        email_sent = False

        try:
            send_mail(
                subject="Complete Your Investor Account Setup",
                message=(
                    f"Hello {investor.full_name},\n\n"
                    "Your investor account has been created.\n\n"
                    "Please use the following link to set your password:\n\n"
                    f"{setup_url}\n\n"
                    "Regards,\n"
                    "Business Financing Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            email_sent = True

        except Exception:
            logger.exception(
                "Failed to send investor setup email for investor ID %s",
                investor.id,
            )

        message = "Investor created successfully."

        if email_sent:
            message += " Password setup email has been sent."
        else:
            message += (
                " The setup email could not be sent. "
                "Please retry email delivery."
            )

        return Response(
            {
                "message": message,
                "email_sent": email_sent,
                "investor": {
                    "id": investor.id,
                    "full_name": investor.full_name,
                    "organization": investor.organization,
                    "investor_type": investor.investor_type,
                    "email": user.email,
                    "mobile_number": investor.mobile_number,
                    "status": investor.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class InvestorDetailView(RetrieveAPIView):
    queryset = InvestorProfile.objects.select_related("user").all()
    serializer_class = InvestorDetailSerializer
    permission_classes = [IsAdminUser]

class InvestorUpdateView(UpdateAPIView):
    queryset = InvestorProfile.objects.select_related("user").all()
    serializer_class = InvestorUpdateSerializer
    permission_classes = [IsAdminUser]


class InvestorDeactiveView(UpdateAPIView):
    queryset = InvestorProfile.objects.all()
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        investor =self.get_object()
        investor.status = 'inactive'
        investor.save(update_fields=["status"])

        return Response(
            {
                "message" : "Investor has been deactivated successfully.",
                "status" : investor.status
            },
            status=status.HTTP_200_OK
        )


class MyInvestorProfileView(RetrieveUpdateAPIView):
    serializer_class = MyInvestorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        if self.request.user.user_type != "investor":
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Only investors can access this profile."
            )

        try:
            return self.request.user.investor_profile
        except InvestorProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Investor profile not found.")




class ExploreBusinessesView(ListAPIView):
    serializer_class = ExploreBusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type != "investor":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Only funding partners can explore businesses."
            )

        return (
            Project.objects
            .select_related("business")
            .filter(
                stage="approved",
                business__status__in=["active", "approved"],
                business__verification_status="verified",
                business__user__is_active=True,
            )
            .order_by("-created_at")
        )


class ExploreBusinessDetailView(RetrieveAPIView):
    serializer_class = ExploreBusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type != "investor":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Only funding partners can view business details."
            )

        return (
            Project.objects
            .select_related("business")
            .filter(
                stage="approved",
                business__status__in=["active", "approved"],
                business__verification_status="verified",
                business__user__is_active=True,
            )
        )



class ExpressInterestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        # Only investors can express interest
        if request.user.user_type != "investor":
            raise PermissionDenied(
                "Only funding partners can express interest."
            )

        # Find an approved project with an eligible business
        project = get_object_or_404(
            Project.objects.select_related(
                "business",
                "business__user",
            ),
            id=project_id,
            stage="approved",
            business__status__in=["active", "approved"],
            business__verification_status="verified",
            business__user__is_active=True,
        )

        # Check whether this investor already has an interest record
        interest = ProjectFundingInterest.objects.filter(
            project=project,
            funding_partner=request.user,
        ).first()

        if interest:
            if interest.status != "withdrawn":
                return Response(
                    {
                        "message": "You have already expressed interest in this project.",
                        "interest_id": interest.id,
                        "status": interest.status,
                    },
                    status=status.HTTP_200_OK,
                )

            # Allow an investor to express interest again after withdrawal
            interest.status = "interested"
            interest.proposed_amount = None
            interest.notes = ""
            interest.save(
                update_fields=[
                    "status",
                    "proposed_amount",
                    "notes",
                    "updated_at",
                ]
            )
        else:
            interest = ProjectFundingInterest.objects.create(
                project=project,
                funding_partner=request.user,
                status="interested",
            )

        return Response(
            {
                "message": "Interest expressed successfully.",
                "interest_id": interest.id,
                "project_id": project.id,
                "project_name": project.project_name,
                "business_name": project.business.business_trade_name,
                "status": interest.status,
                "created_at": interest.created_at,
            },
            status=status.HTTP_201_CREATED,
        )



class WithdrawInterestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        if request.user.user_type != "investor":
            raise PermissionDenied(
                "Only funding partners can withdraw interest."
            )

        interest = get_object_or_404(
            ProjectFundingInterest,
            project_id=project_id,
            funding_partner=request.user,
        )

        if interest.status == "withdrawn":
            return Response(
                {"message": "Interest has already been withdrawn."},
                status=status.HTTP_200_OK,
            )

        interest.status = "withdrawn"
        interest.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Interest withdrawn successfully.",
                "interest_id": interest.id,
                "project_id": interest.project_id,
                "status": interest.status,
            },
            status=status.HTTP_200_OK,
        )



class MyInterestListView(ListAPIView):
    serializer_class = MyInterestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type != "investor":
            raise PermissionDenied(
                "Only funding partners can view their interest list."
            )

        return (
            ProjectFundingInterest.objects
            .filter(funding_partner=self.request.user)
            .select_related("project", "project__business")
            .order_by("-updated_at")
        )





class MyFundingRequestsView(ListAPIView):
    serializer_class = MyFundingRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type != "investor":
            raise PermissionDenied(
                "Only funding partners can view funding requests."
            )

        return (
            ProjectFundingInterest.objects
            .filter(funding_partner=self.request.user)
            .select_related("project", "project__business")
            .order_by("-updated_at")
        )



class InvestorDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.user_type != "investor":
            raise PermissionDenied(
                "Only funding partners can access this dashboard."
            )

        # Approved opportunities visible to this investor
        available_projects = (
            Project.objects
            .select_related("business")
            .filter(
                stage="approved",
                business__status__in=["active", "approved"],
                business__verification_status="verified",
                business__user__is_active=True,
            )
            .order_by("-created_at")
        )

        # This investor's interest records
        interests = ProjectFundingInterest.objects.filter(
            funding_partner=request.user
        )

        # Count interests that are currently active
        my_interests_count = interests.exclude(
            status="withdrawn"
        ).count()

        # Requests still in progress
        active_requests_count = interests.filter(
            status__in=["interested", "under_review", "offer_sent"]
        ).count()

        # Latest five available opportunities
        recent_projects = available_projects[:5]

        recent_projects_data = [
            {
                "id": project.id,
                "business_id": project.business_id,
                "business_name": project.business.business_trade_name,
                "project_name": project.project_name,
                "sector": project.sector,
                "location": project.business.city_hq,
                "funding_required": project.funding_target,
                "stage": project.stage,
                "reference_no": project.reference_no,
                "description": project.description,
            }
            for project in recent_projects
        ]

        return Response(
            {
                "success": True,
                "dashboard": {
                    "available_businesses": available_projects.count(),
                    "my_interests": my_interests_count,
                    "active_requests": active_requests_count,
                },
                "recent_opportunities": recent_projects_data,
            },
            status=status.HTTP_200_OK,
        )
