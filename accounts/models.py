from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Quản trị viên'),
        ('PHARMACIST', 'Quản lý kho'),
        ('RECEPTIONIST', 'Lễ tân'),
        ('DOCTOR', 'Bác sĩ'),
        ('PATIENT', 'Bệnh nhân'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    class Meta:
        db_table = 'Accounts'

    def get_display_name(self):
        """Tên hiển thị theo thứ tự tiếng Việt (Họ + Tên).
        Nếu chưa có họ tên thì hiển thị tên đăng nhập."""
        name = f"{self.last_name} {self.first_name}".strip()
        return name or self.username


class Patient(models.Model):
    GENDER_CHOICES = (('M', 'Nam'), ('F', 'Nữ'), ('O', 'Khác'))
    
    patient_id = models.AutoField(primary_key=True)
    account = models.OneToOneField(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='patient_profile'
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='O')
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'Patients'
    
    def __str__(self):
        return f"{self.full_name} - {self.phone}"