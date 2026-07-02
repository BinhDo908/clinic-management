from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from accounts.models import Patient
from clinical.models import Appointment

User = get_user_model()


class PatientRegistrationForm(forms.Form):
    """Form bệnh nhân tự đăng ký tài khoản trên web."""

    full_name = forms.CharField(
        max_length=100, label='Họ và tên',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Nguyễn Văn A'})
    )
    phone = forms.CharField(
        max_length=15, label='Số điện thoại',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0901234567'})
    )
    password = forms.CharField(
        label='Mật khẩu',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Tối thiểu 6 ký tự'})
    )
    password_confirm = forms.CharField(
        label='Xác nhận mật khẩu',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        required=False, label='Ngày sinh',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=[('M', 'Nam'), ('F', 'Nữ'), ('O', 'Khác')],
        label='Giới tính',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    address = forms.CharField(
        max_length=255, required=False, label='Địa chỉ',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip().replace(' ', '')

        if not phone.startswith('0') or not phone.isdigit() or len(phone) not in [10, 11]:
            raise forms.ValidationError(
                'Số điện thoại không hợp lệ. Phải bắt đầu bằng 0 và có 10-11 chữ số.'
            )

        if User.objects.filter(username=phone).exists() or Patient.objects.filter(phone=phone).exists():
            raise forms.ValidationError(
                'Số điện thoại này đã được đăng ký. Vui lòng đăng nhập.'
            )

        return phone

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 6:
            raise forms.ValidationError('Mật khẩu phải có ít nhất 6 ký tự.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Mật khẩu xác nhận không khớp.')

        return cleaned_data


class OnlineAppointmentForm(forms.Form):
    """Form đặt lịch hẹn online cho bệnh nhân."""

    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role='DOCTOR', is_active=True),
        label='Chọn bác sĩ',
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='-- Chọn bác sĩ --'
    )
    appt_datetime = forms.DateTimeField(
        label='Thời gian mong muốn',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    note = forms.CharField(
        label='Lý do khám / Triệu chứng',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Mô tả ngắn về triệu chứng hoặc lý do bạn muốn đi khám...'
        })
    )

    MAX_ADVANCE_DAYS = 60  # Không cho đặt lịch xa hơn 60 ngày kể từ hôm nay

    def clean_appt_datetime(self):
        from django.utils import timezone
        from datetime import timedelta
        appt_time = self.cleaned_data['appt_datetime']
        now = timezone.now()

        # Không cho đặt lịch trong quá khứ
        if appt_time < now:
            raise forms.ValidationError('Không thể đặt lịch trong quá khứ.')

        # Phải đặt trước ít nhất 1 giờ
        if appt_time < now + timedelta(hours=1):
            raise forms.ValidationError('Vui lòng đặt lịch trước ít nhất 1 giờ.')

        # Không cho đặt lịch quá xa trong tương lai (tránh nhập nhầm năm/tháng)
        if appt_time > now + timedelta(days=self.MAX_ADVANCE_DAYS):
            raise forms.ValidationError(
                f'Chỉ có thể đặt lịch trước tối đa {self.MAX_ADVANCE_DAYS} ngày kể từ hôm nay.'
            )

        return appt_time


class ForcePasswordChangeForm(forms.Form):
    """Form ép đổi mật khẩu lần đầu."""

    new_password = forms.CharField(
        label='Mật khẩu mới',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Tối thiểu 6 ký tự'})
    )
    confirm_password = forms.CharField(
        label='Xác nhận mật khẩu mới',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_new_password(self):
        password = self.cleaned_data['new_password']
        if len(password) < 6:
            raise forms.ValidationError('Mật khẩu phải có ít nhất 6 ký tự.')
        if password == '123456':
            raise forms.ValidationError('Vui lòng đặt mật khẩu khác mật khẩu mặc định.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('Mật khẩu xác nhận không khớp.')

        return cleaned_data