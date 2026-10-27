from django.urls import path
from . import views

urlpatterns = [
    path("",views.PartnerListView.as_view(),name="partner-list"),
    path("create/",views.PartnerCreateView.as_view(),name="partner-create"),
    path("<int:pk>/",views.PartnerDetailView.as_view(),name="partner-detail"),
    path("<int:pk>/deactivate/",views.PartnerDeactivateView.as_view(),name="partner-deactivate"),
    path("<int:pk>/activate/",views.PartnerActivateView.as_view(),name="partner-activate"),
    path("dashboard/",views.ConsultingPartnerDashboardView.as_view(),name="consulting-partner-dashboard"),
    path("partner/my-projects/",views.PartnerAssignedProjectsView.as_view(),name="partner-assigned-projects"),
    path("pending-reviews/",views.ConsultingPartnerPendingReviewsView.as_view(),name="consulting-partner-pending-reviews"),
    path("projects/<int:project_id>/submit-verification/",views.ConsultingPartnerSubmitVerificationView.as_view(),name="consulting-partner-submit-verification"),    
    path("completed-reviews/",views.ConsultingPartnerCompletedReviewsView.as_view(),name="consulting-partner-completed-reviews"),
    path("my-profile/",views.ConsultingPartnerProfileView.as_view(),name="consulting-partner-profile"),
    path("my-kyc-documents/",views.ConsultingPartnerKYCDocumentView.as_view(),name="consulting-partner-kyc-documents")


]