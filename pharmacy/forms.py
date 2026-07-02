from django import forms
from .models import Medicine


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['medicine_name', 'unit', 'unit_price', 'stock_quantity', 'expiry_date', 'description']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'medicine_name': 'Tên thuốc',
            'unit': 'Đơn vị',
            'unit_price': 'Đơn giá (VNĐ)',
            'stock_quantity': 'Số lượng tồn kho',
            'expiry_date': 'Hạn sử dụng',
            'description': 'Mô tả / Công dụng',
        }

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if price is not None and price < 0:
            raise forms.ValidationError('Đơn giá không được là số âm.')
        return price

    def clean_stock_quantity(self):
        qty = self.cleaned_data.get('stock_quantity')
        if qty is not None and qty < 0:
            raise forms.ValidationError('Số lượng tồn kho không được là số âm.')
        return qty


class StockInForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1, 
        label='Số lượng nhập thêm',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    note = forms.CharField(
        required=False, 
        label='Ghi chú nhập kho',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )