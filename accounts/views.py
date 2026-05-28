from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages


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
        return redirect('/admin/')
    elif role == 'PHARMACIST':
        return redirect('/pharmacy/')
    elif role == 'RECEPTIONIST':
        return redirect('/reception/')
    elif role == 'DOCTOR':
        return redirect('/doctor/')
    else:
        return render(request, 'dashboard.html')
