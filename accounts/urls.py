from django.urls import path
from . import views

urlpatterns = [
    path('register/investor/', views.InvestorRegistrationView.as_view(), name='investor-registration'),
    path('register/business/',views.BusinessRegistrationView.as_view(),name='business-registration'),

    path('login/',views.LoginView.as_view(),name='login'),
    path("me/", views.MeView.as_view(), name="me"),

    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path("set-password/", views.SetPasswordView.as_view(), name="set-password"),

    path('logout/',views.LogoutView.as_view(),name='logout-view')

]
