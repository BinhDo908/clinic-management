from django import forms
from accounts.models import Patient
from clinical.models import Appointment
from django.contrib.auth import get_user_model
from django.utils import timezone

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
            'type': 'datetime-local',
            'placeholder': 'VD: 2026-05-28 08:30',
        }),
        input_formats=['%Y-%m-%dT%H:%M'],
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

    def clean_appt_datetime(self):
        appt_dt = self.cleaned_data.get('appt_datetime')
        if not appt_dt:
            return appt_dt

        now = timezone.localtime(timezone.now())

        # Không được đặt lịch trong quá khứ
        if appt_dt <= now:
            raise forms.ValidationError('Không thể đặt lịch trong quá khứ. Vui lòng chọn thời gian trong tương lai.')

        # Không được đặt vào cuối tuần
        if appt_dt.weekday() >= 5:
            raise forms.ValidationError('Phòng khám không làm việc vào thứ Bảy và Chủ Nhật.')

        hour = appt_dt.hour
        minute = appt_dt.minute
        time_val = hour * 60 + minute  # Đổi sang phút để so sánh dễ hơn

        morning_start = 7 * 60        # 07:00
        morning_end   = 11 * 60 + 30  # 11:30
        afternoon_start = 13 * 60     # 13:00
        afternoon_end   = 17 * 60 + 30  # 17:30

        in_morning   = morning_start <= time_val < morning_end
        in_afternoon = afternoon_start <= time_val < afternoon_end

        if not (in_morning or in_afternoon):
            raise forms.ValidationError(
                'Chỉ được đặt lịch trong giờ làm việc: '
                '07:00 – 11:30 (sáng) hoặc 13:00 – 17:30 (chiều).'
            )

        return appt_dt