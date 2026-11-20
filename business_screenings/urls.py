
from django.urls import path
from . import views

urlpatterns = [
    path("drafts/",views.ScreeningDraftCreateView.as_view(),name="screening-create-draft"),
    path("drafts/<uuid:pk>/",views.ScreeningDraftDetailView.as_view(),name="screening-draft"),
    path("drafts/<uuid:pk>/register/",views.ScreeningRegisterView.as_view(),name="screening-register"),
    path("me/",views.MyScreeningView.as_view(),name="screening-me"),
    path("admin/",views.AdminScreeningListView.as_view(),name="screening-admin-list"),
    path("admin/<uuid:pk>/",views.AdminScreeningDetailView.as_view(),name="screening-admin-detail"),
    path("me/corrections/",views.BusinessScreeningCorrectionView.as_view(),name="business-screening-corrections"),
    path("me/resubmit/",views.BusinessScreeningResubmitView.as_view(),name="business-screening-resubmit"),
]
