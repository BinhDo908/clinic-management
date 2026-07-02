from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from accounts.decorators import role_required
from accounts.models import Patient
from clinical.models import Appointment
from .forms import PatientCreateForm, WalkInAppointmentForm
from datetime import timedelta

User = get_user_model()


@role_required('RECEPTIONIST', 'ADMIN')
def reception_dashboard(request):
    """Trang chính của Lễ tân - tổng quan hôm nay."""
    today = timezone.now().date()
    
    # Đếm các con số tổng quan
    pending_count = Appointment.objects.filter(status='PENDING').count()
    today_appointments = Appointment.objects.filter(
        appt_datetime__date=today
    ).exclude(status='CANCELLED').count()
    checked_in_count = Appointment.objects.filter(
        appt_datetime__date=today,
        status='CHECKED_IN'
    ).count()
    
    # 5 lịch hẹn gần nhất hôm nay
    upcoming = Appointment.objects.filter(
        appt_datetime__date=today
    ).exclude(status='CANCELLED').order_by('appt_datetime')[:5]
    
    return render(request, 'reception/dashboard.html', {
        'pending_count': pending_count,
        'today_appointments': today_appointments,
        'checked_in_count': checked_in_count,
        'upcoming': upcoming,
    })


@role_required('RECEPTIONIST', 'ADMIN')
def patient_create(request):
    """
    Tiếp nhận bệnh nhân mới tại quầy.
    Tự động tạo CustomUser (username=phone, password='123456').
    """
    if request.method == 'POST':
        form = PatientCreateForm(request.POST)
        if form.is_valid():
            # Dùng transaction để đảm bảo cả Patient và User đều được tạo,
            # nếu lỗi giữa chừng thì rollback toàn bộ
            try:
                with transaction.atomic():
                    # Bước 1: Tạo CustomUser
                    phone = form.cleaned_data['phone']
                    full_name = form.cleaned_data['full_name']
                    
                    # Tách họ và tên
                    name_parts = full_name.strip().split()
                    last_name = name_parts[0] if name_parts else ''
                    first_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    
                    user = User.objects.create_user(
                        username=phone,
                        password='123456',  # Password mặc định theo spec
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                        role='PATIENT',
                        must_change_password=True,  # Bắt buộc đổi mật khẩu lần đầu
                    )
                    
                    # Bước 2: Tạo Patient liên kết với User
                    patient = form.save(commit=False)
                    patient.account = user
                    patient.save()
                
                messages.success(
                    request,
                    f'✓ Tiếp nhận bệnh nhân thành công! '
                    f'Tài khoản: {phone} | Mật khẩu mặc định: 123456'
                )
                # Chuyển sang trang in phiếu hoặc tạo lịch hẹn
                return redirect('reception:patient_receipt', pk=patient.patient_id)
                
            except Exception as e:
                messages.error(request, f'Lỗi khi tạo bệnh nhân: {str(e)}')
    else:
        form = PatientCreateForm()
    
    return render(request, 'reception/patient_create.html', {'form': form})


@role_required('RECEPTIONIST', 'ADMIN')
def patient_receipt(request, pk):
    """Hiển thị phiếu in cho bệnh nhân mới (kèm thông tin tài khoản)."""
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'reception/patient_receipt.html', {
        'patient': patient,
        'default_password': '123456',
    })


@role_required('RECEPTIONIST', 'ADMIN')
def patient_list(request):
    """Danh sách bệnh nhân với tìm kiếm."""
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.all().order_by('-created_at')
    
    if query:
        from django.db.models import Q
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query)
        )
    
    return render(request, 'reception/patient_list.html', {
        'patients': patients,
        'query': query,
    })

@role_required('RECEPTIONIST', 'ADMIN')
def walkin_appointment(request, patient_id):
    """
    Tạo lịch hẹn tại quầy cho 1 bệnh nhân cụ thể.
    Status mặc định = CHECKED_IN (đã có mặt).
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    
    if request.method == 'POST':
        form = WalkInAppointmentForm(request.POST)
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
                        f'⚠ Bác sĩ {doctor.get_full_name() or doctor.username} '
                        f'đã có lịch khám vào lúc {appt_datetime.strftime("%H:%M %d/%m/%Y")}. '
                        f'Vui lòng chọn thời gian khác.'
                    )
                elif self_conflict:
                    messages.error(
                        request,
                        f'⚠ Bệnh nhân {patient.full_name} đã có một lịch hẹn khác vào '
                        f'đúng khung giờ này. Vui lòng chọn thời gian khác.'
                    )
                else:
                    # Tạo lịch hẹn với status CHECKED_IN (walk-in)
                    appt = Appointment.objects.create(
                        patient=patient,
                        doctor=doctor,
                        appt_datetime=appt_datetime,
                        source='DIRECT',
                        status='CHECKED_IN',
                        note=form.cleaned_data['note'],
                    )
                    messages.success(
                        request,
                        f'✓ Đã đặt lịch hẹn cho bệnh nhân {patient.full_name}. '
                        f'Bệnh nhân đã được xếp vào hàng đợi phòng khám của bác sĩ.'
                    )
                    return redirect('reception:appointment_list')
    else:
        form = WalkInAppointmentForm()
    
    return render(request, 'reception/walkin_appointment.html', {
        'form': form,
        'patient': patient,
    })

@role_required('RECEPTIONIST', 'ADMIN')
def pending_queue(request):
    """Hàng đợi các lịch hẹn online chờ duyệt."""
    pending_appointments = Appointment.objects.filter(
        status='PENDING',
        source='WEB',
    ).order_by('appt_datetime')
    
    return render(request, 'reception/pending_queue.html', {
        'appointments': pending_appointments,
    })


@role_required('RECEPTIONIST', 'ADMIN')
def approve_appointment(request, pk):
    """Duyệt 1 lịch hẹn online (chuyển PENDING → CONFIRMED)."""
    appt = get_object_or_404(Appointment, pk=pk, status='PENDING')
    
    if request.method == 'POST':
        with transaction.atomic():
            # Khóa dòng tài khoản bác sĩ trong lúc kiểm tra + duyệt lịch,
            # tránh duyệt trùng khi 2 lễ tân thao tác cùng lúc
            User.objects.select_for_update().get(pk=appt.doctor.pk)

            conflict = Appointment.objects.filter(
                doctor=appt.doctor,
                appt_datetime=appt.appt_datetime,
                status__in=['CONFIRMED', 'CHECKED_IN'],
            ).exclude(pk=appt.pk).exists()

            if conflict:
                messages.error(
                    request,
                    f'⚠ Đã có lịch khác được duyệt vào khung giờ này. Vui lòng từ chối lịch này.'
                )
            else:
                appt.status = 'CONFIRMED'
                appt.save()
                messages.success(
                    request,
                    f'✓ Đã duyệt lịch hẹn của bệnh nhân {appt.patient.full_name}.'
                )
        return redirect('reception:pending_queue')
    
    return render(request, 'reception/approve_confirm.html', {'appointment': appt})


@role_required('RECEPTIONIST', 'ADMIN')
def reject_appointment(request, pk):
    """
    Từ chối/hủy 1 lịch hẹn (chuyển sang CANCELLED).
    Chỉ áp dụng cho lịch chưa khám (PENDING/CONFIRMED/CHECKED_IN);
    không cho hủy lịch đã COMPLETED hoặc đã CANCELLED trước đó.
    """
    appt = get_object_or_404(
        Appointment, pk=pk,
        status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Vui lòng nhập lý do từ chối/hủy lịch hẹn.')
            return render(request, 'reception/reject_confirm.html', {'appointment': appt})

        appt.status = 'CANCELLED'
        appt.rejection_reason = reason
        appt.save()
        messages.success(request, 'Đã hủy lịch hẹn.')
        return redirect('reception:pending_queue')

    return render(request, 'reception/reject_confirm.html', {'appointment': appt})


@role_required('RECEPTIONIST', 'ADMIN')
def checkin_appointment(request, pk):
    """
    Check-in bệnh nhân khi đến khám.
    Chuyển lịch đã xác nhận (CONFIRMED) sang CHECKED_IN để đưa vào
    hàng đợi khám của bác sĩ.
    """
    appt = get_object_or_404(Appointment, pk=pk, status='CONFIRMED')

    if request.method == 'POST':
        appt.status = 'CHECKED_IN'
        appt.save()
        messages.success(
            request,
            f'✓ Đã check-in cho bệnh nhân {appt.patient.full_name}. '
            f'Bệnh nhân đã được đưa vào hàng đợi khám của bác sĩ.'
        )
        return redirect('reception:appointment_list')

    return render(request, 'reception/checkin_confirm.html', {'appointment': appt})


@role_required('RECEPTIONIST', 'ADMIN')
def appointment_list(request):
    """Danh sách lịch hẹn với filter theo ngày và bác sĩ."""
    date_filter = request.GET.get('date', '')
    doctor_filter = request.GET.get('doctor', '')
    status_filter = request.GET.get('status', '')

    appointments = Appointment.objects.all().order_by('appt_datetime')

    # Filter theo ngày — dùng __range thay vì __date để tránh lỗi CONVERT_TZ MySQL
    if date_filter:
        from datetime import datetime as dt, time
        try:
            selected_date = dt.strptime(date_filter, '%Y-%m-%d').date()
            day_start = timezone.make_aware(dt.combine(selected_date, time.min))
            day_end   = timezone.make_aware(dt.combine(selected_date, time.max))
            appointments = appointments.filter(appt_datetime__range=(day_start, day_end))
        except ValueError:
            pass
    else:
        # Mặc định: hiện từ đầu ngày hôm nay trở đi
        today_start = timezone.make_aware(
            timezone.datetime.combine(timezone.localtime(timezone.now()).date(),
                                      timezone.datetime.min.time())
        )
        appointments = appointments.filter(appt_datetime__gte=today_start)
    
    # Filter theo bác sĩ
    if doctor_filter:
        appointments = appointments.filter(doctor_id=doctor_filter)
    
    # Filter theo trạng thái
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Danh sách bác sĩ để chọn
    doctors = User.objects.filter(role='DOCTOR', is_active=True)
    
    return render(request, 'reception/appointment_list.html', {
        'appointments': appointments,
        'doctors': doctors,
        'date_filter': date_filter,
        'doctor_filter': doctor_filter,
        'status_filter': status_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    })