from django.urls import path

from news.views import dashboard

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.portal_login, name="login"),
    path("signup/", views.portal_signup, name="signup"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("logout/", views.portal_logout, name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("portal/<str:module>/", views.portal_module, name="portal_module"),
    path("portal/<str:module>/new/", views.portal_module_new, name="portal_module_new"),
    path("author/<str:slug>/", views.author_detail, name="author_detail"),
]
