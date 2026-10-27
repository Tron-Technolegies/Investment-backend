from django.urls import path
from . import views

urlpatterns = [
    path("",views.BusinessListView.as_view(),name="businesses-list"),
    path('create/',views.BusinessCreateView.as_view(),name="businesses-create"),
    path('<int:pk>/',views.BusinessDetailView.as_view(),name='business-detail'),
    path('<int:pk>/update/',views.BusinessUpdateView.as_view(),name='business-update'),
    path('<int:pk>/deactivate/',views.BusinessDeactivateView.as_view(),name='business-deactivate'),
    path('<int:pk>/activate/',views.BusinessActivateView.as_view(),name='business-activate'),
    path("<int:business_id>/documents/",views.BusinessDocumentListCreateView.as_view(),name="business-documents"),
    path("documents/<int:document_id>/review/",views.BusinessDocumentReviewView.as_view(),name="review-business-document"),
    path("documents/<int:document_id>/",views.BusinessDocumentDeleteView.as_view(),name="delete-business-document"),
    path("<int:business_id>/verification/",views.BusinessVerificationView.as_view(),name="business-verification"),
    path("my-profile/",views.MyBusinessProfileView.as_view(),name="my-business-profile"),
    path("dashboard-summary/",views.BusinessDashboardSummaryView.as_view(),name="business-dashboard-summary"),
]
