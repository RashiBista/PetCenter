from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.shelters.urls")),
    path("api/", include("apps.animals.urls")),
    path("api/", include("apps.applications.urls")),
    path("api/", include("apps.fosters.urls")),
    path("api/", include("apps.messaging.urls")),
]
