from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvestorListView.as_view(), name='investor-list'),
    path('create/', views.InvestorCreateView.as_view(), name='investor-create'),
    path('<int:pk>/', views.InvestorDetailView.as_view(), name='investor-detail'),
    path('<int:pk>/update/',views.InvestorUpdateView.as_view(),name="investor-update"),
    path('<int:pk>/deactivate/',views.InvestorDeactiveView.as_view(),name="investor-deactive"),
    path("my-profile/",views.MyInvestorProfileView.as_view(),name="my-investor-profile"),
    path("explore-businesses/",views.ExploreBusinessesView.as_view(),name="explore-businesses"),
    path("explore-businesses/<int:pk>/",views.ExploreBusinessDetailView.as_view(),name="explore-business-detail"),
    path("projects/<int:project_id>/express-interest/",views.ExpressInterestView.as_view(),name="express-interest"),
    path("projects/<int:project_id>/withdraw-interest/",views.WithdrawInterestView.as_view(),name="withdraw-interest"), 
    path("my-interests/",views.MyInterestListView.as_view(),name="my-interest-list"),
    path("my-funding-requests/",views.MyFundingRequestsView.as_view(),name="my-funding-requests"),
    path("dashboard-summary/",views.InvestorDashboardSummaryView.as_view(),name="investor-dashboard-summary"),

]