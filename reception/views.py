from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from accounts.decorators import role_required
from accounts.models import Patient
from clinical.models import Appointment
from .forms import PatientCreateForm, WalkInAppointmentForm

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
            
            # Kiểm tra xung đột lịch hẹn (theo spec dự án)
            conflict = Appointment.objects.filter(
                doctor=doctor,
                appt_datetime=appt_datetime,
            ).exclude(status='CANCELLED').exists()
            
            if conflict:
                messages.error(
                    request,
                    f'⚠ Bác sĩ {doctor.get_full_name() or doctor.username} '
                    f'đã có lịch khám vào lúc {appt_datetime.strftime("%H:%M %d/%m/%Y")}. '
                    f'Vui lòng chọn thời gian khác.'
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
        # Mặc định: giờ hiện tại
        form = WalkInAppointmentForm(initial={
            'appt_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M')
        })
    
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
        # Kiểm tra lại xung đột trước khi duyệt
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
    """Từ chối/hủy 1 lịch hẹn (chuyển sang CANCELLED)."""
    appt = get_object_or_404(Appointment, pk=pk)
    
    if request.method == 'POST':
        appt.status = 'CANCELLED'
        appt.save()
        messages.success(request, 'Đã hủy lịch hẹn.')
        return redirect('reception:pending_queue')
    
    return render(request, 'reception/reject_confirm.html', {'appointment': appt})