from django.urls import path
from . import views

app_name = 'cashier'

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<int:invoice_id>/pay/', views.invoice_pay, name='invoice_pay'),
    path('dashboard/', views.revenue_dashboard, name='revenue_dashboard'),
]