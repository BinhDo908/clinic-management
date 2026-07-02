from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Patient


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'get_display_name', 'role', 'phone', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin phòng khám', {'fields': ('role', 'phone', 'must_change_password')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Thông tin phòng khám', {'fields': ('role', 'phone')}),
    )


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'gender', 'created_at')
    search_fields = ('full_name', 'phone')
