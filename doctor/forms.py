from django import forms
from clinical.models import MedicalRecord, Prescription
from pharmacy.models import Medicine


class MedicalRecordForm(forms.ModelForm):
    """Form ghi thông tin khám bệnh."""

    class Meta:
        model = MedicalRecord
        fields = ['symptoms', 'diagnosis', 'clinical_notes']
        widgets = {
            'symptoms': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Mô tả triệu chứng bệnh nhân khai báo...'
            }),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Chẩn đoán của bác sĩ...'
            }),
            'clinical_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Ghi chú kết quả xét nghiệm, cận lâm sàng (nếu có)...'
            }),
        }
        labels = {
            'symptoms': 'Triệu chứng',
            'diagnosis': 'Chẩn đoán',
            'clinical_notes': 'Ghi chú cận lâm sàng',
        }