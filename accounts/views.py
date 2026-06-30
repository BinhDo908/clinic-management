from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .forms import ProfileForm, StyledPasswordChangeForm
from .models import Patient


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
