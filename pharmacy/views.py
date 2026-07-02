from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from accounts.decorators import role_required
from .models import Medicine
from .forms import MedicineForm, StockInForm


@role_required('PHARMACIST', 'ADMIN')
def medicine_list(request):
    query = request.GET.get('q', '')
    medicines = Medicine.objects.filter(is_active=True)
    if query:
        medicines = medicines.filter(Q(medicine_name__icontains=query))
    low_stock_count = medicines.filter(stock_quantity__lt=10).count()

    today = timezone.localdate()
    expired_count = medicines.filter(expiry_date__lt=today).count()
    near_expiry_count = medicines.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=Medicine.NEAR_EXPIRY_DAYS),
    ).count()

    return render(request, 'pharmacy/medicine_list.html', {
        'medicines': medicines,
        'query': query,
        'low_stock_count': low_stock_count,
        'expired_count': expired_count,
        'near_expiry_count': near_expiry_count,
        'near_expiry_days': Medicine.NEAR_EXPIRY_DAYS,
    })


@role_required('PHARMACIST', 'ADMIN')
def medicine_create(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thêm thuốc mới thành công!')
            return redirect('pharmacy:medicine_list')
    else:
        form = MedicineForm()
    return render(request, 'pharmacy/medicine_form.html', {
        'form': form, 
        'title': 'Thêm thuốc mới'
    })


@role_required('PHARMACIST', 'ADMIN')
def medicine_update(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thuốc thành công!')
            return redirect('pharmacy:medicine_list')
    else:
        form = MedicineForm(instance=medicine)
    return render(request, 'pharmacy/medicine_form.html', {
        'form': form, 
        'title': f'Sửa thông tin: {medicine.medicine_name}'
    })


@role_required('PHARMACIST', 'ADMIN')
def medicine_stock_in(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        form = StockInForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            medicine.stock_quantity += quantity
            medicine.save()
            messages.success(
                request, 
                f'Đã nhập thêm {quantity} {medicine.get_unit_display()} vào kho.'
            )
            return redirect('pharmacy:medicine_list')
    else:
        form = StockInForm()
    return render(request, 'pharmacy/stock_in.html', {
        'form': form, 
        'medicine': medicine
    })


@role_required('PHARMACIST', 'ADMIN')
def medicine_delete(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    if request.method == 'POST':
        medicine.is_active = False  # Soft delete - không xóa thật
        medicine.save()
        messages.success(request, f'Đã ẩn "{medicine.medicine_name}" khỏi danh mục.')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/medicine_confirm_delete.html', {
        'medicine': medicine
    })