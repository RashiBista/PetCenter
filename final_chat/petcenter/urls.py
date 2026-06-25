from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(url='/chat/')),
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls', namespace='chat')),
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)