from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),

    path('login/pet-owner/', views.pet_owner_login_view, name='pet_owner_login'),
    path('signup/pet-owner/', views.pet_owner_signup_view, name='pet_owner_signup'),
    path('signup/verify/', views.verify_signup_view, name='verify_signup'),
    path('signup/resend-otp/', views.resend_signup_otp_view, name='resend_signup_otp'),

    path('login/veterinary/', views.veterinary_login_view, name='veterinary_login'),
    path('signup/veterinary/', views.veterinary_signup_view, name='veterinary_signup'),

    path('login/pharmacy/', views.pharmacy_login_view, name='pharmacy_login'),
    path('signup/pharmacy/', views.pharmacy_signup_view, name='pharmacy_signup'),

    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('logout/', views.logout_view, name='logout'),

    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),

    path('appointments/book/', views.book_appointment_view, name='appointment_booking'),
    path('appointments/<int:appointment_id>/status/', views.update_appointment_status_view, name='update_appointment_status'),

    path('medicine/', views.medicine_search_view, name='medicine_search'),
    path('medicine/<int:pk>/', views.medicine_detail_view, name='medicine_detail'),
    path('accessory/<int:pk>/', views.accessory_detail_view, name='accessory_detail'),
    path('search/', views.search_view, name='search'),
    path('pets/<int:pet_id>/medicine-reminder/', views.create_medicine_reminder_view, name='create_medicine_reminder'),

    path('notifications/', views.pet_owner_notifications_view, name='pet_owner_notifications'),
    path('profile/', views.pet_profile_view, name='pet_profile'),
    path('find-vets/', views.find_nearest_vets_view, name='find_nearest_vets'),

    path('dashboard/pet-owner/', views.pet_owner_dashboard, name='pet_owner_dashboard'),
    path('dashboard/veterinary/', views.veterinary_dashboard, name='veterinary_dashboard'),
    path('dashboard/veterinary/appointments/', views.veterinary_appointments_view, name='veterinary_appointments'),
    path('dashboard/veterinary/appointments/', views.veterinary_appointments_view, name='veterinary_appointments'),
    path('dashboard/pharmacy/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/users/create/', views.admin_create_user_view, name='admin_create_user'),
    path('dashboard/admin/users/<int:user_id>/toggle-active/', views.toggle_user_active_view, name='toggle_user_active'),
    path('dashboard/admin/medicine/add/', views.admin_add_medicine_view, name='admin_add_medicine'),
    path('dashboard/admin/medicine/<int:item_id>/toggle-stock/', views.admin_toggle_medicine_stock_view, name='admin_toggle_medicine_stock'),
    path('dashboard/admin/medicine/<int:item_id>/delete/', views.admin_delete_medicine_view, name='admin_delete_medicine'),
    path('dashboard/admin/accessory/add/', views.admin_add_accessory_view, name='admin_add_accessory'),
    path('dashboard/admin/accessory/<int:item_id>/toggle-stock/', views.admin_toggle_accessory_stock_view, name='admin_toggle_accessory_stock'),
    path('dashboard/admin/accessory/<int:item_id>/delete/', views.admin_delete_accessory_view, name='admin_delete_accessory'),

    path('chatbot/', views.chatbot_view, name='chatbot'),
]