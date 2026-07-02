from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .decorators import role_required
from .forms import ProfileForm, StyledPasswordChangeForm, RoleAwareAuthenticationForm, StaffCreateForm
from .models import CustomUser, Patient


class RoleAwareLoginView(auth_views.LoginView):
    """LoginView dùng form nhận biết tab (Bệnh nhân / Nhân viên) để chặn đăng nhập nhầm nhóm."""
    form_class = RoleAwareAuthenticationForm


@login_required
def change_password(request):
    """Bắt buộc đổi mật khẩu lần đầu đăng nhập."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Giữ đăng nhập sau khi đổi mật khẩu
            user.must_change_password = False
            user.save()
            messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/change_password.html', {'form': form})


@login_required
def dashboard(request):
    """Trang chủ sau khi đăng nhập — điều hướng theo role."""
    role = request.user.role
    if role == 'ADMIN':
        return redirect('/cashier/dashboard/')
    elif role == 'PHARMACIST':
        return redirect('/pharmacy/')
    elif role == 'RECEPTIONIST':
        return redirect('/reception/')
    elif role == 'DOCTOR':
        return redirect('/doctor/')
    elif role == 'PATIENT':
        return redirect('/portal/dashboard/')
    else:
        return render(request, 'dashboard.html')


@login_required
def profile(request):
    """Trang hồ sơ cá nhân - cập nhật họ tên, SĐT, email (và thông tin bệnh nhân nếu có)."""
    user = request.user
    patient = Patient.objects.filter(account=user).first()

    if request.method == 'POST':
        form = ProfileForm(request.POST, user=user, patient=patient)
        if form.is_valid():
            cd = form.cleaned_data
            full_name = cd['full_name']
            # Tách họ tên theo quy ước: từ đầu là họ, phần còn lại là tên đệm + tên
            parts = full_name.split()
            user.last_name = parts[0] if parts else ''
            user.first_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
            phone = cd.get('phone')
            if phone:
                user.phone = phone
            user.email = cd.get('email', '')
            user.save()
            # Đồng bộ thông tin hồ sơ bệnh nhân
            if patient:
                patient.full_name = full_name
                if phone:
                    patient.phone = phone
                if cd.get('date_of_birth') is not None:
                    patient.date_of_birth = cd['date_of_birth']
                if cd.get('gender'):
                    patient.gender = cd['gender']
                patient.address = cd.get('address', '')
                patient.save()
            messages.success(request, 'Đã cập nhật thông tin tài khoản.')
            return redirect('accounts:profile')
    else:
        initial = {
            'full_name': f"{user.last_name} {user.first_name}".strip(),
            'phone': user.phone or '',
            'email': user.email or '',
        }
        if patient:
            initial.update({
                'date_of_birth': patient.date_of_birth,
                'gender': patient.gender,
                'address': patient.address,
            })
        form = ProfileForm(initial=initial, user=user, patient=patient)
    return render(request, 'account/profile.html', {'form': form})


@login_required
def account_change_password(request):
    """Đổi mật khẩu khi đang đăng nhập (khác với ép đổi mật khẩu lần đầu)."""
    if request.method == 'POST':
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Giữ phiên đăng nhập sau khi đổi
            messages.success(request, 'Đổi mật khẩu thành công.')
            return redirect('accounts:profile')
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, 'account/change_password.html', {'form': form})


@role_required('ADMIN')
def staff_list(request):
    """Danh sách tài khoản nhân viên (không gồm bệnh nhân) - chỉ Admin xem được."""
    staffs = CustomUser.objects.exclude(role='PATIENT').order_by('role', 'username')
    return render(request, 'account/staff_list.html', {'staffs': staffs})


@role_required('ADMIN')
def staff_create(request):
    """Admin tạo tài khoản nhân viên mới (bác sĩ, lễ tân, dược sĩ, quản trị viên).
    Mật khẩu mặc định giống quy ước tiếp nhận bệnh nhân của Lễ tân, bắt buộc đổi khi đăng nhập lần đầu."""
    if request.method == 'POST':
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            name_parts = full_name.strip().split()
            last_name = name_parts[0] if name_parts else ''
            first_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                password='123456',
                first_name=first_name,
                last_name=last_name,
                phone=form.cleaned_data['phone'] or None,
                role=form.cleaned_data['role'],
                must_change_password=True,
            )
            messages.success(
                request,
                f'✓ Đã tạo tài khoản "{user.username}" ({user.get_role_display()}). '
                f'Mật khẩu mặc định: 123456 (bắt buộc đổi khi đăng nhập lần đầu).'
            )
            return redirect('accounts:staff_list')
    else:
        form = StaffCreateForm()
    return render(request, 'account/staff_form.html', {'form': form})


@role_required('ADMIN')
def staff_toggle_active(request, pk):
    """Khóa / mở khóa tài khoản nhân viên (soft lock, không xóa dữ liệu)."""
    staff = get_object_or_404(CustomUser.objects.exclude(role='PATIENT'), pk=pk)

    if staff.pk == request.user.pk:
        messages.error(request, 'Không thể tự khóa tài khoản của chính mình.')
        return redirect('accounts:staff_list')

    if request.method == 'POST':
        staff.is_active = not staff.is_active
        staff.save()
        trang_thai = 'kích hoạt' if staff.is_active else 'khóa'
        messages.success(request, f'Đã {trang_thai} tài khoản "{staff.username}".')
    return redirect('accounts:staff_list')
