from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.account_change_password, name='change_password'),

    # Quản lý tài khoản nhân viên (chỉ Admin)
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/toggle/', views.staff_toggle_active, name='staff_toggle_active'),
]
