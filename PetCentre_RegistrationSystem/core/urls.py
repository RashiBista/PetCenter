from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    path('login/pet-owner/', views.pet_owner_login_view, name='pet_owner_login'),
    path('login/veterinary/', views.veterinary_login_view, name='veterinary_login'),
    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/pet-owner/', views.pet_owner_dashboard, name='pet_owner_dashboard'),
    path('dashboard/veterinary/', views.veterinary_dashboard, name='veterinary_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    path('chatbot/', views.chatbot_view, name='chatbot'),
]