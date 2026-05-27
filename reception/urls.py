from django.urls import path
from . import views

app_name = 'reception'

urlpatterns = [
    path('', views.reception_dashboard, name='dashboard'),
    
    # Quản lý bệnh nhân
    path('patient/create/', views.patient_create, name='patient_create'),
    path('patient/<int:pk>/receipt/', views.patient_receipt, name='patient_receipt'),
    path('patient/list/', views.patient_list, name='patient_list'),

    # Lịch hẹn walk-in
    path('appointment/walkin/<int:patient_id>/', views.walkin_appointment, name='walkin_appointment'),

    # Hàng đợi duyệt lịch online
    path('pending/', views.pending_queue, name='pending_queue'),
    path('appointment/<int:pk>/approve/', views.approve_appointment, name='approve_appointment'),
    path('appointment/<int:pk>/reject/', views.reject_appointment, name='reject_appointment'),
]