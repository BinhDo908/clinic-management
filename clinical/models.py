from django.db import models
from django.conf import settings
from accounts.models import Patient
from pharmacy.models import Medicine


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Chờ duyệt'),
        ('CONFIRMED', 'Đã xác nhận'),
        ('CHECKED_IN', 'Đã có mặt'),
        ('COMPLETED', 'Hoàn tất'),
        ('CANCELLED', 'Đã hủy'),
    )
    SOURCE_CHOICES = (
        ('WEB', 'Đặt online'),
        ('DIRECT', 'Tại quầy'),
    )
    
    appointment_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='doctor_appointments',
        limit_choices_to={'role': 'DOCTOR'}
    )
    appt_datetime = models.DateTimeField()
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    note = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True, verbose_name='Lý do từ chối/hủy')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'Appointments'
        ordering = ['-appt_datetime']


class MedicalRecord(models.Model):
    record_id = models.AutoField(primary_key=True)
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name='medical_record'
    )
    symptoms = models.TextField()
    diagnosis = models.TextField()
    clinical_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'MedicalRecords'


class Prescription(models.Model):
    prescription_id = models.AutoField(primary_key=True)
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    dosage = models.TextField(help_text="VD: Uống 2 viên/ngày sau ăn")
    
    class Meta:
        db_table = 'Prescriptions'


class Invoice(models.Model):
    STATUS_CHOICES = (('UNPAID', 'Chưa thanh toán'), ('PAID', 'Đã thanh toán'))
    
    invoice_id = models.AutoField(primary_key=True)
    record = models.OneToOneField(MedicalRecord, on_delete=models.CASCADE, related_name='invoice')
    consultation_fee = models.DecimalField(max_digits=12, decimal_places=2, default=100000)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='UNPAID')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'Invoices'