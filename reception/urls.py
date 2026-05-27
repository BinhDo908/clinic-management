from django.urls import path
from . import views

app_name = 'reception'

urlpatterns = [
    path('', views.reception_dashboard, name='dashboard'),
    
    # Quản lý bệnh nhân
    path('patient/create/', views.patient_create, name='patient_create'),
    path('patient/<int:pk>/receipt/', views.patient_receipt, name='patient_receipt'),
    path('patient/list/', views.patient_list, name='patient_list'),
]