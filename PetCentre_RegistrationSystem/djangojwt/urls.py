"""
URL configuration for djangojwt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from myapp.views import (
    DashboardView,
    LoginView,
    UserDashboardView,
    UserRegisterView,
    VetDashboardView,
    VetRegisterView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Registration — separate flows per role
    path('api/auth/register/user/', UserRegisterView.as_view(), name='register_user'),
    path('api/auth/register/vet/', VetRegisterView.as_view(), name='register_vet'),

    # Auth
    path('api/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Dashboards
    path('api/auth/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/auth/dashboard/user/', UserDashboardView.as_view(), name='dashboard_user'),
    path('api/auth/dashboard/vet/', VetDashboardView.as_view(), name='dashboard_vet'),
]
