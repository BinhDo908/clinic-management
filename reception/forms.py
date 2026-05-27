from django import forms
from accounts.models import Patient
from clinical.models import Appointment
from django.contrib.auth import get_user_model

User = get_user_model()


class PatientCreateForm(forms.ModelForm):
    """Form tiếp nhận bệnh nhân mới tại quầy."""
    
    class Meta:
        model = Patient
        fields = ['full_name', 'phone', 'date_of_birth', 'gender', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'VD: Nguyễn Văn A'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'VD: 0901234567'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Địa chỉ thường trú'
            }),
        }
        labels = {
            'full_name': 'Họ và tên',
            'phone': 'Số điện thoại',
            'date_of_birth': 'Ngày sinh',
            'gender': 'Giới tính',
            'address': 'Địa chỉ',
        }
    
    def clean_phone(self):
        """Kiểm tra số điện thoại chưa tồn tại trong hệ thống."""
        phone = self.cleaned_data['phone']
        
        # Loại bỏ khoảng trắng
        phone = phone.strip().replace(' ', '')
        
        # Validate format: phải bắt đầu bằng 0, đủ 10-11 chữ số
        if not phone.startswith('0') or not phone.isdigit() or len(phone) not in [10, 11]:
            raise forms.ValidationError(
                'Số điện thoại không hợp lệ. Phải bắt đầu bằng 0 và có 10-11 chữ số.'
            )
        
        # Kiểm tra trùng
        if Patient.objects.filter(phone=phone).exists():
            raise forms.ValidationError(
                'Số điện thoại này đã tồn tại trong hệ thống. '
                'Vui lòng tra cứu thông tin bệnh nhân thay vì tạo mới.'
            )
        
        return phone


class WalkInAppointmentForm(forms.Form):
    """Form tạo lịch hẹn trực tiếp tại quầy (walk-in)."""
    
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role='DOCTOR', is_active=True),
        label='Bác sĩ khám',
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='-- Chọn bác sĩ --'
    )
    appt_datetime = forms.DateTimeField(
        label='Thời gian khám',
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    note = forms.CharField(
        label='Ghi chú',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Triệu chứng sơ bộ, lý do khám...'
        })
    )