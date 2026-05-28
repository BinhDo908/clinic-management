from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from accounts.decorators import role_required
from clinical.models import Appointment, MedicalRecord, Prescription, Invoice
from pharmacy.models import Medicine
from doctor.forms import MedicalRecordForm


@role_required('DOCTOR', 'ADMIN')
def doctor_queue(request):
    """
    Hàng đợi bệnh nhân chờ khám.
    Bác sĩ chỉ thấy các lịch CHECKED_IN của CHÍNH MÌNH.
    """
    # Lấy các lịch đã check-in, gán cho bác sĩ đang đăng nhập
    queue = Appointment.objects.filter(
        doctor=request.user,
        status='CHECKED_IN',
    ).order_by('appt_datetime')

    # Lịch đã khám xong hôm nay (để bác sĩ xem lại)
    today = timezone.now().date()
    completed_today = Appointment.objects.filter(
        doctor=request.user,
        status='COMPLETED',
        appt_datetime__date=today,
    ).order_by('-appt_datetime')

    return render(request, 'doctor/queue.html', {
        'queue': queue,
        'completed_today': completed_today,
        'queue_count': queue.count(),
    })

@role_required('DOCTOR', 'ADMIN')
def examination(request, appointment_id):
    """
    Màn hình khám bệnh: ghi bệnh án + kê đơn thuốc + trừ kho.
    """
    appointment = get_object_or_404(
        Appointment, pk=appointment_id, doctor=request.user
    )

    # Nếu lịch đã khám xong rồi thì không cho khám lại
    if appointment.status == 'COMPLETED':
        messages.warning(request, 'Ca khám này đã hoàn tất trước đó.')
        return redirect('doctor:queue')

    # Danh sách thuốc còn hàng để bác sĩ chọn
    medicines = Medicine.objects.filter(is_active=True, stock_quantity__gt=0)
    medicines_data = [
        {
            'id': m.medicine_id,
            'name': m.medicine_name,
            'unit': m.get_unit_display(),
            'stock': m.stock_quantity,
            'price': float(m.unit_price),
        }
        for m in medicines
    ]

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)

        # Lấy dữ liệu đơn thuốc từ form (các input động)
        medicine_ids = request.POST.getlist('medicine_id[]')
        quantities = request.POST.getlist('quantity[]')
        dosages = request.POST.getlist('dosage[]')

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Bước 1: Tạo bệnh án
                    record = form.save(commit=False)
                    record.appointment = appointment
                    record.save()

                    # Bước 2: Xử lý từng thuốc trong đơn
                    for med_id, qty, dosage in zip(medicine_ids, quantities, dosages):
                        if not med_id or not qty:
                            continue  # Bỏ qua dòng trống

                        medicine = Medicine.objects.select_for_update().get(pk=med_id)
                        qty = int(qty)

                        # Kiểm tra tồn kho đủ không
                        if medicine.stock_quantity < qty:
                            raise ValueError(
                                f'Thuốc "{medicine.medicine_name}" chỉ còn '
                                f'{medicine.stock_quantity} {medicine.get_unit_display()}, '
                                f'không đủ để kê {qty}.'
                            )

                        # Tạo dòng đơn thuốc
                        Prescription.objects.create(
                            record=record,
                            medicine=medicine,
                            quantity=qty,
                            dosage=dosage or 'Theo chỉ định bác sĩ',
                        )

                        # Trừ kho
                        medicine.stock_quantity -= qty
                        medicine.save()

                    # Bước 3: Tạo hóa đơn (chưa thanh toán) cho Thu ngân xử lý
                    self_create_invoice(record)

                    # Bước 4: Chuyển trạng thái lịch hẹn sang COMPLETED
                    appointment.status = 'COMPLETED'
                    appointment.save()

                messages.success(
                    request,
                    f'✓ Đã hoàn tất khám cho bệnh nhân {appointment.patient.full_name}. '
                    f'Bệnh án và đơn thuốc đã được lưu, kho đã cập nhật.'
                )
                return redirect('doctor:queue')

            except ValueError as e:
                messages.error(request, f'⚠ {str(e)}')
            except Exception as e:
                messages.error(request, f'Lỗi khi lưu: {str(e)}')
    else:
        form = MedicalRecordForm()

    return render(request, 'doctor/examination.html', {
        'appointment': appointment,
        'patient': appointment.patient,
        'form': form,
        'medicines_data': medicines_data,
    })


def self_create_invoice(record):
    """Hàm phụ: tự động tạo hóa đơn từ bệnh án (tính sẵn tiền thuốc)."""
    from decimal import Decimal

    consultation_fee = Decimal('100000')  # Phí khám cố định

    # Tính tổng tiền thuốc
    medicine_total = Decimal('0')
    for presc in record.prescriptions.all():
        medicine_total += presc.medicine.unit_price * presc.quantity

    total = consultation_fee + medicine_total

    Invoice.objects.create(
        record=record,
        consultation_fee=consultation_fee,
        total_amount=total,
        status='UNPAID',
    )

@role_required('DOCTOR', 'ADMIN')
def record_detail(request, appointment_id):
    """Xem lại chi tiết bệnh án đã khám."""
    appointment = get_object_or_404(Appointment, pk=appointment_id, doctor=request.user)

    try:
        record = appointment.medical_record
        prescriptions = record.prescriptions.all()
    except MedicalRecord.DoesNotExist:
        messages.error(request, 'Chưa có bệnh án cho lịch hẹn này.')
        return redirect('doctor:queue')

    return render(request, 'doctor/record_detail.html', {
        'appointment': appointment,
        'patient': appointment.patient,
        'record': record,
        'prescriptions': prescriptions,
    })