from datetime import timedelta

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Medicine(models.Model):
    UNIT_CHOICES = (
        ('VIEN', 'Viên'),
        ('VI', 'Vỉ'),
        ('LO', 'Lọ'),
        ('CHAI', 'Chai'),
        ('TUYP', 'Tuýp'),
    )

    # Số ngày còn lại tính là "sắp hết hạn" để cảnh báo cho dược sĩ
    NEAR_EXPIRY_DAYS = 30

    medicine_id = models.AutoField(primary_key=True)
    medicine_name = models.CharField(max_length=200)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='VIEN')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    expiry_date = models.DateField(null=True, blank=True, verbose_name='Hạn sử dụng')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Medicines'
        ordering = ['medicine_name']

    def __str__(self):
        return f"{self.medicine_name} ({self.unit})"

    def is_expired(self):
        """Thuốc đã hết hạn sử dụng (so với ngày hiện tại)."""
        return bool(self.expiry_date) and self.expiry_date < timezone.localdate()

    def is_near_expiry(self):
        """Thuốc còn hạn nhưng sắp hết hạn trong NEAR_EXPIRY_DAYS ngày tới."""
        if not self.expiry_date or self.is_expired():
            return False
        return self.expiry_date <= timezone.localdate() + timedelta(days=self.NEAR_EXPIRY_DAYS)