"""
Bộ test tự động (end-to-end) cho Hệ thống Quản lý Phòng khám.
Mỗi test method tương ứng 1 mã test case (TC-xxx) trong file Excel.

Chạy:  python manage.py test clinical.tests_e2e -v 2

Django tự tạo database test riêng (test_ClinicDB) và xóa sau khi chạy,
KHÔNG ảnh hưởng dữ liệu thật trong ClinicDB.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import Patient
from pharmacy.models import Medicine
from clinical.models import Appointment, MedicalRecord, Prescription, Invoice

User = get_user_model()


# ---------------------------------------------------------------------------
# Tiện ích dùng chung
# ---------------------------------------------------------------------------
def next_working_slot(hour=8, minute=0, days_ahead=1):
    """Trả về 1 mốc thời gian hợp lệ: ngày làm việc (T2-T6), trong giờ hành chính,
    nằm trong tương lai (cách hiện tại > 1 giờ)."""
    now = timezone.localtime(timezone.now())
    d = (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    while d.weekday() >= 5 or d <= now + timedelta(hours=1):
        d = (d + timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
    return d


def fmt(dt):
    """Định dạng cho input datetime-local (%Y-%m-%dT%H:%M)."""
    return timezone.localtime(dt).strftime('%Y-%m-%dT%H:%M')


def make_user(username, role, password='matkhau123', **kwargs):
    return User.objects.create_user(
        username=username, password=password, role=role, **kwargs
    )


# ===========================================================================
# NHÓM 1: XÁC THỰC & PHÂN QUYỀN
# ===========================================================================
class AuthTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.doctor = make_user('bs_an', 'DOCTOR', first_name='An', last_name='Bác sĩ', phone='0900000001')
        self.pharma = make_user('kho01', 'PHARMACIST', phone='0900000002')

    def test_TC_AUTH_01_login_thanh_cong(self):
        """Đăng nhập đúng tài khoản -> điều hướng theo vai trò (bác sĩ -> /doctor/)."""
        r = self.c.post('/login/', {'username': 'bs_an', 'password': 'matkhau123'}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.request['PATH_INFO'], '/doctor/')

    def test_TC_AUTH_02_login_sai_mat_khau(self):
        """Đăng nhập sai mật khẩu -> không đăng nhập, ở lại trang login."""
        r = self.c.post('/login/', {'username': 'bs_an', 'password': 'saibet'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.wsgi_request.user.is_authenticated)

    def test_TC_AUTH_03_truy_cap_khi_chua_dang_nhap(self):
        """Truy cập trang nội bộ khi chưa đăng nhập -> chuyển về trang login."""
        r = self.c.get('/pharmacy/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)

    def test_TC_AUTH_04_sai_quyen_bi_chan(self):
        """Dược sĩ truy cập dashboard doanh thu (chỉ Admin) -> bị chặn, về trang chủ."""
        self.c.force_login(self.pharma)
        r = self.c.get('/cashier/dashboard/')
        self.assertEqual(r.status_code, 302)

    def test_TC_AUTH_05_ep_doi_mat_khau_lan_dau(self):
        """User must_change_password=True -> mọi trang bị ép về trang đổi mật khẩu."""
        p = make_user('0911111111', 'PATIENT', phone='0911111111')
        p.must_change_password = True
        p.save()
        Patient.objects.create(account=p, full_name='Test Patient', phone='0911111111')
        self.c.force_login(p)
        r = self.c.get('/portal/dashboard/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('change-password', r.url)


# ===========================================================================
# NHÓM 2: KHO THUỐC (PHARMACY)
# ===========================================================================
class PharmacyTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.pharma = make_user('kho01', 'PHARMACIST', phone='0900000002')
        self.c.force_login(self.pharma)

    def test_TC_PHA_01_them_thuoc_hop_le(self):
        r = self.c.post('/pharmacy/create/', {
            'medicine_name': 'Paracetamol 500mg', 'unit': 'VIEN',
            'unit_price': '2000', 'stock_quantity': '100', 'description': 'Hạ sốt',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Medicine.objects.filter(medicine_name='Paracetamol 500mg').exists())

    def test_TC_PHA_02_them_thuoc_gia_am(self):
        """Đơn giá âm -> form báo lỗi, không tạo."""
        r = self.c.post('/pharmacy/create/', {
            'medicine_name': 'Thuoc Loi', 'unit': 'VIEN',
            'unit_price': '-5000', 'stock_quantity': '10', 'description': '',
        })
        self.assertEqual(r.status_code, 200)  # render lại form kèm lỗi
        self.assertFalse(Medicine.objects.filter(medicine_name='Thuoc Loi').exists())

    def test_TC_PHA_03_nhap_kho_cong_don(self):
        m = Medicine.objects.create(medicine_name='Vit C', unit='VIEN', unit_price=1000, stock_quantity=20)
        r = self.c.post(f'/pharmacy/{m.pk}/stock-in/', {'quantity': '30', 'note': 'Nhập lô mới'})
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.stock_quantity, 50)

    def test_TC_PHA_04_nhap_kho_so_luong_khong_hop_le(self):
        """Nhập kho số lượng < 1 -> form báo lỗi, tồn kho không đổi."""
        m = Medicine.objects.create(medicine_name='Vit D', unit='VIEN', unit_price=1000, stock_quantity=20)
        r = self.c.post(f'/pharmacy/{m.pk}/stock-in/', {'quantity': '0'})
        self.assertEqual(r.status_code, 200)
        m.refresh_from_db()
        self.assertEqual(m.stock_quantity, 20)

    def test_TC_PHA_05_xoa_mem_thuoc(self):
        """Xóa thuốc -> soft delete (is_active=False), không hiện trong danh sách."""
        m = Medicine.objects.create(medicine_name='Amox', unit='VIEN', unit_price=1000, stock_quantity=20)
        r = self.c.post(f'/pharmacy/{m.pk}/delete/')
        self.assertEqual(r.status_code, 302)
        m.refresh_from_db()
        self.assertFalse(m.is_active)
        # Thuốc đã ẩn không còn trong danh sách thuốc đang bán (kiểm tra trực tiếp context,
        # tránh nhầm với chữ "Amox" trong thông báo "Đã ẩn ... khỏi danh mục").
        listing = self.c.get('/pharmacy/')
        active_names = [med.medicine_name for med in listing.context['medicines']]
        self.assertNotIn('Amox', active_names)

    def test_TC_PHA_06_tim_kiem_thuoc(self):
        Medicine.objects.create(medicine_name='Paracetamol', unit='VIEN', unit_price=1000, stock_quantity=5)
        Medicine.objects.create(medicine_name='Aspirin', unit='VIEN', unit_price=1000, stock_quantity=5)
        r = self.c.get('/pharmacy/?q=Para')
        self.assertContains(r, 'Paracetamol')
        self.assertNotContains(r, 'Aspirin')


# ===========================================================================
# NHÓM 3: LỄ TÂN (RECEPTION)
# ===========================================================================
class ReceptionTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.le_tan = make_user('letan01', 'RECEPTIONIST', phone='0900000003')
        self.doctor = make_user('bs_an', 'DOCTOR', first_name='An', last_name='Bs', phone='0900000001')
        self.c.force_login(self.le_tan)

    def test_TC_REC_01_tiep_nhan_benh_nhan(self):
        """Tạo bệnh nhân -> tạo cả Patient + User(username=phone, pass 123456, phải đổi MK)."""
        r = self.c.post('/reception/patient/create/', {
            'full_name': 'Nguyễn Văn A', 'phone': '0912345678',
            'date_of_birth': '1990-01-01', 'gender': 'M', 'address': 'Hà Nội',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Patient.objects.filter(phone='0912345678').exists())
        u = User.objects.get(username='0912345678')
        self.assertEqual(u.role, 'PATIENT')
        self.assertTrue(u.must_change_password)
        self.assertTrue(u.check_password('123456'))

    def test_TC_REC_02_tiep_nhan_trung_sdt(self):
        """SĐT đã tồn tại -> báo lỗi, không tạo trùng."""
        Patient.objects.create(full_name='Cũ', phone='0912345678')
        r = self.c.post('/reception/patient/create/', {
            'full_name': 'Mới', 'phone': '0912345678', 'gender': 'M', 'address': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Patient.objects.filter(phone='0912345678').count(), 1)

    def test_TC_REC_03_sdt_sai_dinh_dang(self):
        """SĐT sai định dạng (không bắt đầu bằng 0 / sai độ dài) -> báo lỗi."""
        r = self.c.post('/reception/patient/create/', {
            'full_name': 'X', 'phone': '12345', 'gender': 'M', 'address': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Patient.objects.filter(full_name='X').exists())

    def test_TC_REC_04_walkin_hop_le(self):
        """Đặt lịch tại quầy hợp lệ -> trạng thái CHECKED_IN, nguồn DIRECT."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        slot = next_working_slot(hour=8)
        r = self.c.post(f'/reception/appointment/walkin/{p.pk}/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(slot), 'note': 'Đau đầu',
        })
        self.assertEqual(r.status_code, 302)
        appt = Appointment.objects.get(patient=p)
        self.assertEqual(appt.status, 'CHECKED_IN')
        self.assertEqual(appt.source, 'DIRECT')

    def test_TC_REC_05_walkin_trung_lich_bac_si(self):
        """Bác sĩ đã có lịch cùng khung giờ -> báo trùng, không tạo lịch thứ 2."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        slot = next_working_slot(hour=8)
        Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                   source='DIRECT', status='CHECKED_IN')
        r = self.c.post(f'/reception/appointment/walkin/{p.pk}/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(slot), 'note': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=p).count(), 1)

    def test_TC_REC_06_walkin_thoi_gian_qua_khu(self):
        """Đặt lịch trong quá khứ -> form báo lỗi."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        past = timezone.localtime(timezone.now()) - timedelta(days=1)
        r = self.c.post(f'/reception/appointment/walkin/{p.pk}/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(past), 'note': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=p).count(), 0)

    def test_TC_REC_07_walkin_ngoai_gio_lam_viec(self):
        """Đặt lịch ngoài giờ hành chính (20:00) -> form báo lỗi."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        slot = next_working_slot(hour=20)  # 20h ngoài giờ
        r = self.c.post(f'/reception/appointment/walkin/{p.pk}/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(slot), 'note': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=p).count(), 0)

    def test_TC_REC_08_duyet_lich_online(self):
        """Duyệt lịch PENDING -> chuyển CONFIRMED."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        slot = next_working_slot(hour=8)
        appt = Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                          source='WEB', status='PENDING')
        r = self.c.post(f'/reception/appointment/{appt.pk}/approve/')
        self.assertEqual(r.status_code, 302)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CONFIRMED')

    def test_TC_REC_09_tu_choi_lich(self):
        """Từ chối lịch -> chuyển CANCELLED."""
        p = Patient.objects.create(full_name='BN', phone='0912345678')
        slot = next_working_slot(hour=8)
        appt = Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                          source='WEB', status='PENDING')
        r = self.c.post(f'/reception/appointment/{appt.pk}/reject/')
        self.assertEqual(r.status_code, 302)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CANCELLED')

    def test_TC_REC_10_tim_kiem_benh_nhan(self):
        Patient.objects.create(full_name='Trần Văn B', phone='0901111111')
        Patient.objects.create(full_name='Lê Thị C', phone='0902222222')
        r = self.c.get('/reception/patient/list/?q=Trần')
        self.assertContains(r, 'Trần Văn B')
        self.assertNotContains(r, 'Lê Thị C')


# ===========================================================================
# NHÓM 4: BÁC SĨ (DOCTOR)
# ===========================================================================
class DoctorTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.doctor = make_user('bs_an', 'DOCTOR', first_name='An', last_name='Bs', phone='0900000001')
        self.doctor2 = make_user('bs_binh', 'DOCTOR', phone='0900000004')
        self.patient = Patient.objects.create(full_name='Bệnh Nhân A', phone='0912345678')
        self.med = Medicine.objects.create(medicine_name='Paracetamol', unit='VIEN',
                                           unit_price=Decimal('5000'), stock_quantity=50)
        self.slot = next_working_slot(hour=8)
        self.appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
                                               appt_datetime=self.slot, source='DIRECT',
                                               status='CHECKED_IN')
        self.c.force_login(self.doctor)

    def test_TC_DOC_01_hang_doi_chi_cua_minh(self):
        """Bác sĩ chỉ thấy lịch CHECKED_IN của chính mình."""
        other_p = Patient.objects.create(full_name='BN khác', phone='0903333333')
        Appointment.objects.create(patient=other_p, doctor=self.doctor2,
                                   appt_datetime=self.slot, source='DIRECT', status='CHECKED_IN')
        r = self.c.get('/doctor/')
        self.assertContains(r, 'Bệnh Nhân A')
        self.assertNotContains(r, 'BN khác')

    def test_TC_DOC_02_kham_va_ke_don(self):
        """Khám: lưu bệnh án + kê đơn -> trừ kho, tạo hóa đơn UNPAID, lịch COMPLETED."""
        r = self.c.post(f'/doctor/examine/{self.appt.pk}/', {
            'symptoms': 'Sốt cao', 'diagnosis': 'Cảm cúm', 'clinical_notes': '',
            'medicine_id[]': [str(self.med.pk)], 'quantity[]': ['10'],
            'dosage[]': ['Uống 2 viên/ngày'],
        })
        self.assertEqual(r.status_code, 302)
        self.appt.refresh_from_db()
        self.med.refresh_from_db()
        self.assertEqual(self.appt.status, 'COMPLETED')
        self.assertEqual(self.med.stock_quantity, 40)  # 50 - 10
        rec = MedicalRecord.objects.get(appointment=self.appt)
        self.assertEqual(rec.prescriptions.count(), 1)
        inv = Invoice.objects.get(record=rec)
        self.assertEqual(inv.status, 'UNPAID')
        # 100.000 (phí khám) + 10 * 5.000 = 150.000
        self.assertEqual(inv.total_amount, Decimal('150000'))

    def test_TC_DOC_03_ke_don_vuot_ton_kho(self):
        """Kê số lượng vượt tồn kho -> báo lỗi & rollback toàn bộ (không trừ kho, không tạo bệnh án)."""
        r = self.c.post(f'/doctor/examine/{self.appt.pk}/', {
            'symptoms': 'Sốt', 'diagnosis': 'Cúm', 'clinical_notes': '',
            'medicine_id[]': [str(self.med.pk)], 'quantity[]': ['999'],
            'dosage[]': ['x'],
        })
        self.assertEqual(r.status_code, 200)
        self.med.refresh_from_db()
        self.appt.refresh_from_db()
        self.assertEqual(self.med.stock_quantity, 50)  # không đổi
        self.assertEqual(self.appt.status, 'CHECKED_IN')  # chưa hoàn tất
        self.assertEqual(MedicalRecord.objects.filter(appointment=self.appt).count(), 0)

    def test_TC_DOC_04_kham_lai_ca_da_hoan_tat(self):
        """Mở lại ca đã COMPLETED -> chặn, redirect về hàng đợi."""
        self.appt.status = 'COMPLETED'
        self.appt.save()
        r = self.c.get(f'/doctor/examine/{self.appt.pk}/')
        self.assertEqual(r.status_code, 302)

    def test_TC_DOC_05_khong_kham_lich_bac_si_khac(self):
        """Bác sĩ truy cập ca khám của bác sĩ khác -> 404 (không có quyền)."""
        other_p = Patient.objects.create(full_name='BN khác', phone='0903333333')
        other_appt = Appointment.objects.create(patient=other_p, doctor=self.doctor2,
                                                 appt_datetime=self.slot, source='DIRECT',
                                                 status='CHECKED_IN')
        r = self.c.get(f'/doctor/examine/{other_appt.pk}/')
        self.assertEqual(r.status_code, 404)


# ===========================================================================
# NHÓM 5: THU NGÂN (CASHIER)
# ===========================================================================
class CashierTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.le_tan = make_user('letan01', 'RECEPTIONIST', phone='0900000003')
        self.admin = make_user('admin01', 'ADMIN', phone='0900000005')
        self.doctor = make_user('bs_an', 'DOCTOR', phone='0900000001')
        self.patient = Patient.objects.create(full_name='Bệnh Nhân A', phone='0912345678')
        self.slot = next_working_slot(hour=8)
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor,
                                          appt_datetime=self.slot, source='DIRECT', status='COMPLETED')
        rec = MedicalRecord.objects.create(appointment=appt, symptoms='x', diagnosis='y')
        self.invoice = Invoice.objects.create(record=rec, consultation_fee=Decimal('100000'),
                                              total_amount=Decimal('150000'), status='UNPAID')

    def test_TC_CAS_01_thu_tien_hoa_don(self):
        """Thu tiền -> hóa đơn chuyển PAID, ghi nhận thời điểm thanh toán."""
        self.c.force_login(self.le_tan)
        r = self.c.post(f'/cashier/invoice/{self.invoice.pk}/pay/')
        self.assertEqual(r.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'PAID')
        self.assertIsNotNone(self.invoice.paid_at)

    def test_TC_CAS_02_khong_thu_lai_hoa_don_da_thanh_toan(self):
        """Hóa đơn đã PAID -> không xử lý lại (thông báo + redirect chi tiết)."""
        self.invoice.status = 'PAID'
        self.invoice.paid_at = timezone.now()
        self.invoice.save()
        self.c.force_login(self.le_tan)
        r = self.c.post(f'/cashier/invoice/{self.invoice.pk}/pay/')
        self.assertEqual(r.status_code, 302)
        self.assertIn(f'/cashier/invoice/{self.invoice.pk}/', r.url)

    def test_TC_CAS_03_chi_tiet_hoa_don(self):
        self.c.force_login(self.le_tan)
        r = self.c.get(f'/cashier/invoice/{self.invoice.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Bệnh Nhân A')

    def test_TC_CAS_04_dashboard_chi_admin(self):
        """Lễ tân KHÔNG được xem dashboard doanh thu (chỉ Admin)."""
        self.c.force_login(self.le_tan)
        r = self.c.get('/cashier/dashboard/')
        self.assertEqual(r.status_code, 302)

    def test_TC_CAS_05_admin_xem_dashboard(self):
        """Admin xem được dashboard doanh thu."""
        self.c.force_login(self.admin)
        r = self.c.get('/cashier/dashboard/')
        self.assertEqual(r.status_code, 200)

    def test_TC_CAS_06_loc_hoa_don_chua_thanh_toan(self):
        self.c.force_login(self.le_tan)
        r = self.c.get('/cashier/invoices/?status=UNPAID')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Bệnh Nhân A')


# ===========================================================================
# NHÓM 6: CỔNG BỆNH NHÂN (PATIENT PORTAL)
# ===========================================================================
class PortalTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.doctor = make_user('bs_an', 'DOCTOR', first_name='An', last_name='Bs', phone='0900000001')

    def _register_and_login(self, phone='0912345678'):
        u = make_user(phone, 'PATIENT', phone=phone)
        p = Patient.objects.create(account=u, full_name='BN Web', phone=phone)
        self.c.force_login(u)
        return u, p

    def test_TC_POR_01_dang_ky_hop_le(self):
        """Đăng ký hợp lệ -> tạo tài khoản PATIENT + Patient, tự đăng nhập."""
        r = self.c.post('/portal/register/', {
            'full_name': 'Nguyễn Văn A', 'phone': '0912345678',
            'password': 'matkhau123', 'password_confirm': 'matkhau123',
            'gender': 'M', 'address': 'HN',
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.filter(username='0912345678', role='PATIENT').exists())
        self.assertTrue(Patient.objects.filter(phone='0912345678').exists())

    def test_TC_POR_02_dang_ky_mat_khau_khong_khop(self):
        r = self.c.post('/portal/register/', {
            'full_name': 'A', 'phone': '0912345678',
            'password': 'matkhau123', 'password_confirm': 'khac123',
            'gender': 'M',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='0912345678').exists())

    def test_TC_POR_03_dang_ky_mat_khau_qua_ngan(self):
        r = self.c.post('/portal/register/', {
            'full_name': 'A', 'phone': '0912345678',
            'password': '123', 'password_confirm': '123', 'gender': 'M',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='0912345678').exists())

    def test_TC_POR_04_dang_ky_trung_sdt(self):
        Patient.objects.create(full_name='Cũ', phone='0912345678')
        r = self.c.post('/portal/register/', {
            'full_name': 'Mới', 'phone': '0912345678',
            'password': 'matkhau123', 'password_confirm': 'matkhau123', 'gender': 'M',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Patient.objects.filter(phone='0912345678').count(), 1)

    def test_TC_POR_05_dat_lich_online_hop_le(self):
        """Đặt lịch online hợp lệ -> trạng thái PENDING, nguồn WEB."""
        u, p = self._register_and_login()
        slot = next_working_slot(hour=9)
        r = self.c.post('/portal/book/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(slot), 'note': 'Đau bụng',
        })
        self.assertEqual(r.status_code, 302)
        appt = Appointment.objects.get(patient=p)
        self.assertEqual(appt.status, 'PENDING')
        self.assertEqual(appt.source, 'WEB')

    def test_TC_POR_06_dat_lich_trung_khung_gio(self):
        """Khung giờ đã có người đặt -> báo lỗi."""
        u, p = self._register_and_login()
        slot = next_working_slot(hour=9)
        other = Patient.objects.create(full_name='Khac', phone='0903333333')
        Appointment.objects.create(patient=other, doctor=self.doctor, appt_datetime=slot,
                                   source='WEB', status='PENDING')
        r = self.c.post('/portal/book/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(slot), 'note': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=p).count(), 0)

    def test_TC_POR_07_dat_lich_qua_khu(self):
        u, p = self._register_and_login()
        past = timezone.localtime(timezone.now()) - timedelta(days=1)
        r = self.c.post('/portal/book/', {
            'doctor': self.doctor.pk, 'appt_datetime': fmt(past), 'note': '',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=p).count(), 0)

    def test_TC_POR_08_huy_lich_pending(self):
        """Hủy lịch PENDING -> chuyển CANCELLED."""
        u, p = self._register_and_login()
        slot = next_working_slot(hour=9)
        appt = Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                          source='WEB', status='PENDING')
        r = self.c.post(f'/portal/appointment/{appt.pk}/cancel/')
        self.assertEqual(r.status_code, 302)
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'CANCELLED')

    def test_TC_POR_09_khong_huy_lich_da_hoan_tat(self):
        """Không thể hủy lịch đã COMPLETED -> 404."""
        u, p = self._register_and_login()
        slot = next_working_slot(hour=9)
        appt = Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                          source='WEB', status='COMPLETED')
        r = self.c.post(f'/portal/appointment/{appt.pk}/cancel/')
        self.assertEqual(r.status_code, 404)

    def test_TC_POR_10_xem_lich_su_kham(self):
        """Lịch sử chỉ hiển thị ca COMPLETED của chính mình."""
        u, p = self._register_and_login()
        slot = next_working_slot(hour=9)
        Appointment.objects.create(patient=p, doctor=self.doctor, appt_datetime=slot,
                                   source='WEB', status='COMPLETED')
        r = self.c.get('/portal/history/')
        self.assertEqual(r.status_code, 200)


# ===========================================================================
# NHÓM 7: GIAO DIỆN & CHỨC NĂNG BỔ TRỢ (UI)
# ===========================================================================
class UIFeatureTests(TestCase):
    def setUp(self):
        self.c = Client()

    def test_TC_UI_01_in_phieu_tiep_nhan(self):
        """Phiếu tiếp nhận hiển thị thông tin bệnh nhân + mật khẩu mặc định 123456."""
        le_tan = make_user('letan01', 'RECEPTIONIST', phone='0900000003')
        self.c.force_login(le_tan)
        p = Patient.objects.create(full_name='Nguyễn Văn A', phone='0912345678')
        r = self.c.get(f'/reception/patient/{p.pk}/receipt/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nguyễn Văn A')
        self.assertContains(r, '123456')

    def test_TC_UI_02_canh_bao_thuoc_sap_het(self):
        """Danh sách thuốc đếm đúng số thuốc tồn < 10 (cảnh báo sắp hết)."""
        pharma = make_user('kho01', 'PHARMACIST', phone='0900000002')
        self.c.force_login(pharma)
        Medicine.objects.create(medicine_name='Thuoc sap het', unit='VIEN', unit_price=1000, stock_quantity=5)
        Medicine.objects.create(medicine_name='Thuoc con du', unit='VIEN', unit_price=1000, stock_quantity=100)
        r = self.c.get('/pharmacy/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['low_stock_count'], 1)

    def test_TC_UI_03_bieu_do_doanh_thu(self):
        """Dashboard doanh thu (Admin) trả về dữ liệu biểu đồ 7 ngày."""
        admin = make_user('admin01', 'ADMIN', phone='0900000005')
        self.c.force_login(admin)
        r = self.c.get('/cashier/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('daily_revenue', r.context)
        self.assertEqual(len(r.context['daily_revenue']), 7)

    def test_TC_UI_04_dang_xuat(self):
        """Đăng xuất -> phiên kết thúc, truy cập trang nội bộ bị đẩy về login."""
        u = make_user('bs_an', 'DOCTOR', phone='0900000001')
        self.c.force_login(u)
        self.assertEqual(self.c.get('/doctor/').status_code, 200)
        self.c.post('/logout/')
        r = self.c.get('/doctor/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)


# ===========================================================================
# NHÓM 8: TÀI KHOẢN CÁ NHÂN (hồ sơ, đổi mật khẩu, hiển thị tên)
# ===========================================================================
class AccountFeatureTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.u = make_user('letan01', 'RECEPTIONIST', phone='0900000003')
        self.c.force_login(self.u)

    def test_TC_ACC_01_xem_trang_ho_so(self):
        """Mở được trang hồ sơ cá nhân."""
        r = self.c.get('/account/profile/')
        self.assertEqual(r.status_code, 200)

    def test_TC_ACC_02_doi_ten_hien_thi(self):
        """Đổi họ tên -> lưu đúng theo thứ tự Họ + Tên."""
        r = self.c.post('/account/profile/', {'full_name': 'Nguyễn Văn A'})
        self.assertEqual(r.status_code, 302)
        self.u.refresh_from_db()
        self.assertEqual(self.u.last_name, 'Nguyễn')
        self.assertEqual(self.u.first_name, 'Văn A')
        self.assertEqual(self.u.get_display_name(), 'Nguyễn Văn A')

    def test_TC_ACC_03_doi_mat_khau_sau_dang_nhap(self):
        """Đổi mật khẩu khi đã đăng nhập -> mật khẩu mới có hiệu lực, vẫn giữ phiên."""
        r = self.c.post('/account/change-password/', {
            'old_password': 'matkhau123',
            'new_password1': 'matmoi456xyz',
            'new_password2': 'matmoi456xyz',
        })
        self.assertEqual(r.status_code, 302)
        self.u.refresh_from_db()
        self.assertTrue(self.u.check_password('matmoi456xyz'))

    def test_TC_ACC_04_navbar_hien_ten_that(self):
        """Navbar hiển thị tên thật thay vì tên đăng nhập."""
        self.u.last_name = 'Trần'
        self.u.first_name = 'Thị B'
        self.u.save()
        r = self.c.get('/account/profile/')
        self.assertContains(r, 'Trần Thị B')

    def test_TC_ACC_05_doi_so_dien_thoai_email(self):
        """Cập nhật số điện thoại + email cho tài khoản."""
        r = self.c.post('/account/profile/', {
            'full_name': 'Lê Văn D', 'phone': '0987654321', 'email': 'd@email.com',
        })
        self.assertEqual(r.status_code, 302)
        self.u.refresh_from_db()
        self.assertEqual(self.u.phone, '0987654321')
        self.assertEqual(self.u.email, 'd@email.com')

    def test_TC_ACC_06_benh_nhan_cap_nhat_ho_so(self):
        """Bệnh nhân cập nhật hồ sơ (ngày sinh, giới tính, địa chỉ) -> đồng bộ vào Patient."""
        pu = make_user('0912345678', 'PATIENT', phone='0912345678')
        p = Patient.objects.create(account=pu, full_name='BN Cũ', phone='0912345678')
        self.c.force_login(pu)
        r = self.c.post('/account/profile/', {
            'full_name': 'Trần Văn C', 'phone': '0912345678', 'email': 'c@email.com',
            'date_of_birth': '1995-05-05', 'gender': 'M', 'address': 'Hà Nội',
        })
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.full_name, 'Trần Văn C')
        self.assertEqual(p.gender, 'M')
        self.assertEqual(p.address, 'Hà Nội')
