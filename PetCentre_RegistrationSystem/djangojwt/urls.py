from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from myapp.views import UserSearchView
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

    path('chat/', include('chat.urls')),

    path('api/auth/register/user/', UserRegisterView.as_view(), name='register_user'),
    path('api/auth/register/vet/', VetRegisterView.as_view(), name='register_vet'),
    path('api/users/search/', UserSearchView.as_view(), name='user_search'),

    path('api/auth/login/', LoginView.as_view(), name='auth_login'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('api/auth/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/auth/dashboard/user/', UserDashboardView.as_view(), name='dashboard_user'),
    path('api/auth/dashboard/vet/', VetDashboardView.as_view(), name='dashboard_vet'),
]