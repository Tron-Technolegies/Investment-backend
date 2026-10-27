from django.urls import path
from . import views

urlpatterns = [
    path("",views.AdminProjectListView.as_view(),name="admin-project-list"),
    path("create/",views.ProjectCreateView.as_view(),name="project-create"),
    path("my-projects/",views.MyProjectListView.as_view(),name="my-projects"),
    path("<int:pk>/",views.ProjectDetailView.as_view(),name="project-detail"),
    path("<int:pk>/stage/",views.ProjectStageUpdateView.as_view(),name="project-stage-update"),
    path("<int:pk>/stage-history/",views.ProjectStageHistoryView.as_view(),name="project-stage-history"),
    path("<int:pk>/assign-partner/",views.ProjectPartnerAssignView.as_view(),name="project-assign-partner"),
    path("partner/my-projects/",views.PartnerAssignedProjectsView.as_view(),name="partner-assigned-projects"),
    path("partner/my-projects/<int:pk>/",views.PartnerAssignedProjectDetailView.as_view(),name="partner-assigned-project-detail"),
    path("<int:pk>/documents/",views.project_documents,name="project-documents"),
    path("documents/<int:document_id>/review/",views.review_project_document,name="review-project-document"),
    path("documents/<int:document_id>/",views.delete_project_document,name="delete-project-document"),
    path("document-requirements/",views.DocumentRequirementListCreateView.as_view(),name="document-requirements"),
    path("document-requirements/<int:pk>/",views.DocumentRequirementDetailView.as_view(),name="document-requirement-detail"),
    path("<int:pk>/missing-documents/",views.ProjectMissingDocumentsView.as_view(),name="project-missing-documents"),
    path("admin/document-review-queue/",views.AdminDocumentReviewQueueView.as_view(),name="admin-document-review-queue"),
    path("admin/dashboard-stats/",views.AdminDashboardStatsView.as_view(),name="admin-dashboard-stats"),
    path("admin/business-verification/",views.AdminBusinessVerificationQueueView.as_view(),name="admin-business-verification"), 
    path("admin/business-verification/<int:business_id>/",views.AdminBusinessVerificationActionView.as_view(),name="admin-business-verification-action"),
    path("my-funding-status/",views.BusinessFundingStatusView.as_view(),name="business-funding-status"),


]