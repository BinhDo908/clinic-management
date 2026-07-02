from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from accounts.decorators import role_required
from accounts.models import Patient
from clinical.models import Appointment, MedicalRecord
from .forms import (
    PatientRegistrationForm,
    OnlineAppointmentForm,
    ForcePasswordChangeForm,
)

def get_patient_or_redirect(request):
    """Lấy Patient của user hiện tại. Nếu không có thì báo lỗi."""
    try:
        return request.user.patient_profile
    except Patient.DoesNotExist:
        messages.error(request, 'Không tìm thấy hồ sơ bệnh nhân.')
        return None

User = get_user_model()


def home(request):
    """Trang chủ công khai của phòng khám."""
    # Danh sách bác sĩ để giới thiệu công khai
    doctors = User.objects.filter(role='DOCTOR', is_active=True)[:6]

    return render(request, 'patient_portal/home.html', {
        'doctors': doctors,
    })

def register(request):
    """Bệnh nhân tự đăng ký tài khoản qua web."""
    if request.user.is_authenticated:
        return redirect('patient_portal:my_dashboard')

    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    phone = form.cleaned_data['phone']
                    full_name = form.cleaned_data['full_name']

                    # Tách họ tên
                    name_parts = full_name.strip().split()
                    last_name = name_parts[0] if name_parts else ''
                    first_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    # Tạo CustomUser
                    user = User.objects.create_user(
                        username=phone,
                        password=form.cleaned_data['password'],
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                        role='PATIENT',
                        must_change_password=False,  # Tự đăng ký nên không cần ép đổi
                    )

                    # Tạo Patient
                    Patient.objects.create(
                        account=user,
                        full_name=full_name,
                        phone=phone,
                        date_of_birth=form.cleaned_data.get('date_of_birth'),
                        gender=form.cleaned_data['gender'],
                        address=form.cleaned_data.get('address', ''),
                    )

                    # Tự động đăng nhập sau khi đăng ký
                    login(request, user)

                messages.success(
                    request,
                    f'Đăng ký thành công! Chào mừng {full_name} đến với phòng khám.'
                )
                return redirect('patient_portal:my_dashboard')

            except Exception as e:
                messages.error(request, f'Lỗi khi đăng ký: {str(e)}')
    else:
        form = PatientRegistrationForm()

    return render(request, 'patient_portal/register.html', {'form': form})

@login_required
def change_password(request):
    """Trang ép đổi mật khẩu lần đầu."""

    # Nếu không cần đổi mật khẩu, redirect về dashboard
    if not request.user.must_change_password:
        return redirect('patient_portal:my_dashboard')

    if request.method == 'POST':
        form = ForcePasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']

            # Đổi mật khẩu và tắt flag
            request.user.set_password(new_password)
            request.user.must_change_password = False
            request.user.save()

            # Đăng nhập lại với mật khẩu mới (để không bị logout)
            from django.contrib.auth import login as auth_login
            from django.contrib.auth import authenticate
            user = authenticate(username=request.user.username, password=new_password)
            if user:
                auth_login(request, user)

            messages.success(
                request,
                'Đã đổi mật khẩu thành công! Chào mừng bạn đến với cổng thông tin bệnh nhân.'
            )
            return redirect('patient_portal:my_dashboard')
    else:
        form = ForcePasswordChangeForm()

    return render(request, 'patient_portal/change_password.html', {'form': form})

@role_required('PATIENT')
def my_dashboard(request):
    """Trang chính sau khi bệnh nhân đăng nhập."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    # Các lịch hẹn sắp tới
    upcoming = Appointment.objects.filter(
        patient=patient,
        appt_datetime__gte=timezone.now(),
        status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
    ).order_by('appt_datetime')[:5]

    # Số lịch sử khám
    history_count = Appointment.objects.filter(
        patient=patient, status='COMPLETED'
    ).count()

    return render(request, 'patient_portal/my_dashboard.html', {
        'patient': patient,
        'upcoming': upcoming,
        'history_count': history_count,
    })

MAX_PENDING_APPOINTMENTS = 3  # Số lịch "chờ duyệt" tối đa 1 bệnh nhân được giữ cùng lúc


@role_required('PATIENT')
def book_appointment(request):
    """Bệnh nhân đặt lịch hẹn online (status = PENDING)."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    if request.method == 'POST':
        form = OnlineAppointmentForm(request.POST)
        if form.is_valid():
            doctor = form.cleaned_data['doctor']
            appt_datetime = form.cleaned_data['appt_datetime']

            with transaction.atomic():
                # Khóa dòng tài khoản bác sĩ + hồ sơ bệnh nhân trong lúc kiểm tra + tạo lịch,
                # tránh đặt trùng giờ cùng lúc lọt qua kiểm tra xung đột
                User.objects.select_for_update().get(pk=doctor.pk)
                Patient.objects.select_for_update().get(pk=patient.pk)

                conflict = Appointment.objects.filter(
                    doctor=doctor,
                    appt_datetime=appt_datetime,
                ).exclude(status='CANCELLED').exists()

                # Một bệnh nhân không thể có mặt ở 2 nơi cùng lúc, dù khác bác sĩ
                self_conflict = Appointment.objects.filter(
                    patient=patient,
                    appt_datetime=appt_datetime,
                ).exclude(status='CANCELLED').exists()

                if conflict:
                    messages.error(
                        request,
                        'Khung giờ này vừa có người đặt thành công, vui lòng chọn khung giờ khác!'
                    )
                elif self_conflict:
                    messages.error(
                        request,
                        'Bạn đã có một lịch hẹn khác vào đúng khung giờ này. '
                        'Vui lòng chọn thời gian khác.'
                    )
                elif Appointment.objects.filter(patient=patient, status='PENDING').count() >= MAX_PENDING_APPOINTMENTS:
                    # Chặn đặt lịch tràn lan: bệnh nhân phải chờ lễ tân duyệt/xử lý
                    # bớt các lịch đang chờ trước khi đặt thêm
                    messages.error(
                        request,
                        f'Bạn đang có {MAX_PENDING_APPOINTMENTS} lịch hẹn chờ duyệt. '
                        f'Vui lòng chờ Lễ tân xử lý trước khi đặt thêm lịch mới.'
                    )
                else:
                    Appointment.objects.create(
                        patient=patient,
                        doctor=doctor,
                        appt_datetime=appt_datetime,
                        source='WEB',
                        status='PENDING',  # Chờ Lễ tân duyệt
                        note=form.cleaned_data.get('note', ''),
                    )
                    messages.success(
                        request,
                        'Đặt lịch thành công! Lễ tân sẽ gọi điện xác nhận trong thời gian sớm nhất.'
                    )
                    return redirect('patient_portal:my_appointments')
    else:
        form = OnlineAppointmentForm()

    return render(request, 'patient_portal/book_appointment.html', {
        'form': form,
        'patient': patient,
    })


@role_required('PATIENT')
def my_appointments(request):
    """Danh sách lịch hẹn của bệnh nhân."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    appointments = Appointment.objects.filter(patient=patient).order_by('-appt_datetime')

    return render(request, 'patient_portal/my_appointments.html', {
        'patient': patient,
        'appointments': appointments,
    })


@role_required('PATIENT')
def cancel_appointment(request, pk):
    """Hủy lịch hẹn (chỉ hủy được lịch PENDING hoặc CONFIRMED)."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    # Chỉ cho hủy lịch của chính mình
    appointment = get_object_or_404(
        Appointment, pk=pk, patient=patient,
        status__in=['PENDING', 'CONFIRMED']
    )

    if request.method == 'POST':
        appointment.status = 'CANCELLED'
        appointment.save()
        messages.success(request, 'Đã hủy lịch hẹn.')
        return redirect('patient_portal:my_appointments')

    return render(request, 'patient_portal/cancel_confirm.html', {
        'appointment': appointment,
    })

@role_required('PATIENT')
def my_history(request):
    """Sổ nhật ký khám bệnh cá nhân."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    # Lấy các ca khám đã hoàn tất
    completed_appointments = Appointment.objects.filter(
        patient=patient,
        status='COMPLETED',
    ).select_related('doctor').prefetch_related(
        'medical_record__prescriptions__medicine',
        'medical_record__invoice',
    ).order_by('-appt_datetime')

    return render(request, 'patient_portal/my_history.html', {
        'patient': patient,
        'appointments': completed_appointments,
    })


@role_required('PATIENT')
def history_detail(request, appointment_id):
    """Chi tiết một lần khám cụ thể."""
    patient = get_patient_or_redirect(request)
    if not patient:
        return redirect('home')

    # Chỉ cho xem ca khám của chính mình
    appointment = get_object_or_404(
        Appointment, pk=appointment_id, patient=patient, status='COMPLETED'
    )

    try:
        record = appointment.medical_record
        prescriptions = record.prescriptions.all()
        invoice = getattr(record, 'invoice', None)
    except MedicalRecord.DoesNotExist:
        record = None
        prescriptions = []
        invoice = None

    return render(request, 'patient_portal/history_detail.html', {
        'patient': patient,
        'appointment': appointment,
        'record': record,
        'prescriptions': prescriptions,
        'invoice': invoice,
    })