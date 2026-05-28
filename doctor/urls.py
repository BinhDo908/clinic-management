from django.urls import path
from . import views

app_name = 'doctor'

urlpatterns = [
    path('', views.doctor_queue, name='queue'),
    path('examine/<int:appointment_id>/', views.examination, name='examination'),
    path('record/<int:appointment_id>/', views.record_detail, name='record_detail'),
]
