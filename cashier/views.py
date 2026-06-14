from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from accounts.decorators import role_required
from clinical.models import Invoice
from datetime import timedelta, datetime, time


@role_required('RECEPTIONIST', 'ADMIN')
def invoice_list(request):
    """
    Danh sách hóa đơn. Mặc định hiển thị hóa đơn chưa thanh toán.
    Lễ tân (kiêm thu ngân) và Admin đều truy cập được.
    """
    status_filter = request.GET.get('status', 'ALL')
    query = request.GET.get('q', '').strip()

    invoices = Invoice.objects.select_related(
        'record__appointment__patient'
    ).order_by('-created_at')

    # Lọc theo trạng thái
    if status_filter in ['UNPAID', 'PAID']:
        invoices = invoices.filter(status=status_filter)

    # Tìm theo tên bệnh nhân hoặc SĐT
    if query:
        invoices = invoices.filter(
            Q(record__appointment__patient__full_name__icontains=query) |
            Q(record__appointment__patient__phone__icontains=query)
        )

    # Đếm số hóa đơn chưa thu để hiển thị badge
    unpaid_count = Invoice.objects.filter(status='UNPAID').count()

    return render(request, 'cashier/invoice_list.html', {
        'invoices': invoices,
        'status_filter': status_filter,
        'query': query,
        'unpaid_count': unpaid_count,
    })

@role_required('RECEPTIONIST', 'ADMIN')
def invoice_detail(request, invoice_id):
    """Xem chi tiết hóa đơn với breakdown cách tính tiền."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('record__appointment__patient'),
        pk=invoice_id
    )

    record = invoice.record
    prescriptions = record.prescriptions.select_related('medicine').all()

    # Tính chi tiết từng dòng thuốc (để hiển thị minh bạch)
    medicine_lines = []
    medicine_total = Decimal('0')
    for presc in prescriptions:
        line_total = presc.medicine.unit_price * presc.quantity
        medicine_total += line_total
        medicine_lines.append({
            'name': presc.medicine.medicine_name,
            'unit': presc.medicine.get_unit_display(),
            'quantity': presc.quantity,
            'unit_price': presc.medicine.unit_price,
            'line_total': line_total,
        })

    return render(request, 'cashier/invoice_detail.html', {
        'invoice': invoice,
        'patient': record.appointment.patient,
        'record': record,
        'medicine_lines': medicine_lines,
        'medicine_total': medicine_total,
    })

@role_required('RECEPTIONIST', 'ADMIN')
def invoice_pay(request, invoice_id):
    """Xác nhận thu tiền: chuyển hóa đơn từ UNPAID sang PAID."""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    # Nếu đã thanh toán rồi thì không xử lý lại
    if invoice.status == 'PAID':
        messages.info(request, 'Hóa đơn này đã được thanh toán trước đó.')
        return redirect('cashier:invoice_detail', invoice_id=invoice.pk)

    if request.method == 'POST':
        Invoice.objects.filter(pk=invoice_id).update(
            status='PAID',
            paid_at=timezone.now(),
        )
        messages.success(
            request,
            f'✓ Đã thu {invoice.total_amount:,.0f} đ từ bệnh nhân '
            f'{invoice.record.appointment.patient.full_name}. Hóa đơn đã thanh toán.'
        )
        return redirect(reverse('cashier:invoice_list') + '?status=PAID')

    return render(request, 'cashier/invoice_pay_confirm.html', {
        'invoice': invoice,
        'patient': invoice.record.appointment.patient,
    })

def _day_range(d):
    """Trả về (start, end) datetime có timezone cho một ngày d, tránh dùng __date lookup với MySQL."""
    return (
        timezone.make_aware(datetime.combine(d, time.min)),
        timezone.make_aware(datetime.combine(d, time.max)),
    )


@role_required('ADMIN')
def revenue_dashboard(request):
    """Dashboard thống kê doanh thu - chỉ Admin xem được."""
    today = timezone.now().date()

    # Lọc theo khoảng ngày (mặc định 7 ngày gần nhất)
    date_from = request.GET.get('from', (today - timedelta(days=6)).isoformat())
    date_to = request.GET.get('to', today.isoformat())

    # Chỉ tính hóa đơn đã thanh toán
    paid_invoices = Invoice.objects.filter(status='PAID')

    # Doanh thu hôm nay
    today_start, today_end = _day_range(today)
    today_revenue = paid_invoices.filter(
        paid_at__range=(today_start, today_end)
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    today_count = paid_invoices.filter(paid_at__range=(today_start, today_end)).count()

    # Tổng doanh thu trong khoảng
    from_date = datetime.fromisoformat(date_from).date() if isinstance(date_from, str) else date_from
    to_date = datetime.fromisoformat(date_to).date() if isinstance(date_to, str) else date_to
    range_invoices = paid_invoices.filter(
        paid_at__range=(
            timezone.make_aware(datetime.combine(from_date, time.min)),
            timezone.make_aware(datetime.combine(to_date, time.max)),
        )
    )
    range_revenue = range_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    range_count = range_invoices.count()

    # Doanh thu theo từng ngày (cho biểu đồ)
    daily_revenue = []
    for i in range(7):
        day = today - timedelta(days=i)
        day_start, day_end = _day_range(day)
        day_total = paid_invoices.filter(
            paid_at__range=(day_start, day_end)
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        daily_revenue.append({
            'date': day.strftime('%d/%m'),
            'total': float(day_total),
        })
    daily_revenue.reverse()  # Sắp xếp từ cũ đến mới

    # Hóa đơn chưa thu (công nợ)
    unpaid_total = Invoice.objects.filter(status='UNPAID').aggregate(
        total=Sum('total_amount'))['total'] or Decimal('0')
    unpaid_count = Invoice.objects.filter(status='UNPAID').count()

    return render(request, 'cashier/dashboard.html', {
        'today_revenue': today_revenue,
        'today_count': today_count,
        'range_revenue': range_revenue,
        'range_count': range_count,
        'date_from': date_from,
        'date_to': date_to,
        'daily_revenue': daily_revenue,
        'unpaid_total': unpaid_total,
        'unpaid_count': unpaid_count,
    })