from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import CustomUser


class ProfileForm(forms.Form):
    """Form cập nhật thông tin tài khoản của người dùng đang đăng nhập.
    Với bệnh nhân, form bổ sung thêm ngày sinh / giới tính / địa chỉ."""

    GENDER_CHOICES = [('M', 'Nam'), ('F', 'Nữ'), ('O', 'Khác')]

    full_name = forms.CharField(
        max_length=150, label='Họ và tên',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Nguyễn Văn A'})
    )
    phone = forms.CharField(
        max_length=15, required=False, label='Số điện thoại',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0901234567'})
    )
    email = forms.EmailField(
        required=False, label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'VD: ten@email.com'})
    )

    def __init__(self, *args, user=None, patient=None, **kwargs):
        self.user = user
        self.patient = patient
        super().__init__(*args, **kwargs)
        # Bệnh nhân được cập nhật thêm thông tin hồ sơ
        if patient is not None:
            self.fields['date_of_birth'] = forms.DateField(
                required=False, label='Ngày sinh',
                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
            )
            self.fields['gender'] = forms.ChoiceField(
                required=False, choices=self.GENDER_CHOICES, label='Giới tính',
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            self.fields['address'] = forms.CharField(
                required=False, label='Địa chỉ',
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
            )

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if not name:
            raise forms.ValidationError('Vui lòng nhập họ và tên.')
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip().replace(' ', '')
        if not phone:
            return phone
        if not phone.startswith('0') or not phone.isdigit() or len(phone) not in [10, 11]:
            raise forms.ValidationError('Số điện thoại không hợp lệ. Phải bắt đầu bằng 0 và có 10-11 chữ số.')
        # Không trùng số của tài khoản khác
        qs = CustomUser.objects.filter(phone=phone)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError('Số điện thoại này đã được dùng bởi tài khoản khác.')
        return phone


class StyledPasswordChangeForm(PasswordChangeForm):
    """PasswordChangeForm gắn sẵn class Bootstrap cho các ô nhập."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class RoleAwareAuthenticationForm(AuthenticationForm):
    """
    Form đăng nhập nhận biết tab người dùng chọn (Bệnh nhân / Nhân viên).
    Trang login.html gửi kèm field ẩn `login_as` theo tab đang active, dùng để
    chặn trường hợp bệnh nhân đăng nhập nhầm ở tab Nhân viên (và ngược lại).
    `login_as` để trống nếu không xác định thì bỏ qua kiểm tra (không chặn).
    """

    login_as = forms.CharField(required=False, widget=forms.HiddenInput())

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        login_as = self.cleaned_data.get('login_as')
        if login_as == 'patient' and user.role != 'PATIENT':
            raise forms.ValidationError(
                'Đây không phải tài khoản bệnh nhân. Vui lòng đăng nhập ở mục "Nhân viên".',
                code='wrong_tab',
            )
        if login_as == 'staff' and user.role == 'PATIENT':
            raise forms.ValidationError(
                'Tài khoản bệnh nhân vui lòng đăng nhập ở mục "Bệnh nhân".',
                code='wrong_tab',
            )


class StaffCreateForm(forms.Form):
    """Form dành cho Admin tạo tài khoản nhân viên (bác sĩ, lễ tân, dược sĩ, quản trị viên)."""

    ROLE_CHOICES = [
        ('DOCTOR', 'Bác sĩ'),
        ('RECEPTIONIST', 'Lễ tân'),
        ('PHARMACIST', 'Dược sĩ'),
        ('ADMIN', 'Quản trị viên'),
    ]

    full_name = forms.CharField(
        max_length=150, label='Họ và tên',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Nguyễn Văn A'})
    )
    username = forms.CharField(
        max_length=150, label='Tên đăng nhập',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: bacsi_an'})
    )
    phone = forms.CharField(
        max_length=15, required=False, label='Số điện thoại',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: 0901234567'})
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, label='Vai trò',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('Tên đăng nhập này đã tồn tại.')
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip().replace(' ', '')
        if not phone:
            return ''
        if CustomUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError('Số điện thoại này đã được dùng bởi tài khoản khác.')
        return phone
