from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from apps.chat.views import MessageHistoryView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='chat/index.html'), name='chat'),
    path('api/messages/<int:other_user_id>/', MessageHistoryView.as_view(), name='message_history'),
]