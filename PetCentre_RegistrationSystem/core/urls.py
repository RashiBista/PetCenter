from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    path('login/pet-owner/', views.pet_owner_login_view, name='pet_owner_login'),
    path('signup/pet-owner/', views.pet_owner_signup_view, name='pet_owner_signup'),

    path('login/veterinary/', views.veterinary_login_view, name='veterinary_login'),
    path('signup/veterinary/', views.veterinary_signup_view, name='veterinary_signup'),

    path('login/pharmacy/', views.pharmacy_login_view, name='pharmacy_login'),
    path('signup/pharmacy/', views.pharmacy_signup_view, name='pharmacy_signup'),

    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),

    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    path('appointments/book/', views.book_appointment_view, name='book_appointment'),

    path('dashboard/pet-owner/', views.pet_owner_dashboard, name='pet_owner_dashboard'),
    path('dashboard/veterinary/', views.veterinary_dashboard, name='veterinary_dashboard'),
    path('dashboard/pharmacy/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    path('chatbot/', views.chatbot_view, name='chatbot'),
]