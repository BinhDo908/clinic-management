# Hệ thống Quản lý Phòng khám Đa khoa

Ứng dụng web quản lý toàn bộ hoạt động của một phòng khám đa khoa quy mô vừa và nhỏ:
tiếp nhận bệnh nhân, đặt lịch hẹn (tại quầy và trực tuyến), khám bệnh, kê đơn thuốc,
quản lý kho thuốc, lập hóa đơn và thống kê doanh thu. Hệ thống được xây dựng trên
Django theo kiến trúc MVT, phân quyền theo năm vai trò người dùng.

## Mục lục

- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Vai trò người dùng](#vai-trò-người-dùng)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Hướng dẫn cài đặt và chạy dự án](#hướng-dẫn-cài-đặt-và-chạy-dự-án)
- [Tài liệu Django models](#tài-liệu-django-models)
- [Hướng dẫn sử dụng website](#hướng-dẫn-sử-dụng-website)
- [Ràng buộc nghiệp vụ đáng chú ý](#ràng-buộc-nghiệp-vụ-đáng-chú-ý)
- [Kiểm thử](#kiểm-thử)
- [Quy trình Git của nhóm](#quy-trình-git-của-nhóm)

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| Back-end | Python 3.10+, Django 4.2 |
| Front-end | Django Templates, Bootstrap 5, Bootstrap Icons |
| Cơ sở dữ liệu | MySQL 8.0 (mặc định) hoặc SQLite |
| Xác thực | Custom User model, phân quyền theo vai trò |
| Thư viện khác | mysqlclient, python-dotenv, Pillow |

## Vai trò người dùng

Hệ thống phân quyền theo 5 vai trò, mỗi vai trò có một khu vực làm việc riêng:

| Vai trò | Mã (`role`) | Chức năng chính |
|---------|-------------|-----------------|
| Quản trị viên | `ADMIN` | Toàn quyền, xem báo cáo doanh thu, quản lý tài khoản nhân viên |
| Lễ tân | `RECEPTIONIST` | Tiếp nhận bệnh nhân, đặt lịch, duyệt/check-in lịch online, thu ngân |
| Bác sĩ | `DOCTOR` | Khám bệnh, ghi bệnh án, kê đơn thuốc |
| Dược sĩ / Thủ kho | `PHARMACIST` | Quản lý danh mục, tồn kho và hạn sử dụng thuốc |
| Bệnh nhân | `PATIENT` | Đăng ký, đặt lịch trực tuyến, xem lịch sử khám |

Mọi vai trò đều có trang **hồ sơ cá nhân** (`/account/profile/`) để đổi họ tên, số điện thoại,
email, và trang đổi mật khẩu riêng (`/account/change-password/`). Tài khoản nhân viên (không
tính bệnh nhân) chỉ được tạo bởi Admin qua `/account/staff/` — không có form tự đăng ký công khai.

## Cấu trúc dự án

```
clinic-management/
├── clinic_project/      # Cấu hình dự án (settings, urls, wsgi)
├── accounts/            # Tài khoản, phân quyền, model người dùng & bệnh nhân
│   ├── decorators.py    # @role_required - chặn truy cập theo vai trò
│   └── middleware.py    # Ép đổi mật khẩu lần đầu đăng nhập
├── clinical/            # Model dùng chung: lịch hẹn, bệnh án, đơn thuốc, hóa đơn
├── pharmacy/            # Quản lý kho thuốc
├── reception/           # Module Lễ tân
├── doctor/              # Module Bác sĩ
├── cashier/             # Module Thu ngân & báo cáo doanh thu
├── patient_portal/      # Cổng thông tin bệnh nhân
├── templates/           # Template dùng chung (base, navbar, sidebar)
├── static/              # CSS, JS, hình ảnh
├── requirements.txt
└── manage.py
```

Các app `reception`, `doctor`, `cashier`, `patient_portal` không định nghĩa model riêng
mà dùng chung các model nghiệp vụ đặt trong app `clinical`.

## Hướng dẫn cài đặt và chạy dự án

### 1. Yêu cầu

- Python 3.10 trở lên
- MySQL 8.0 (nếu chạy với MySQL). Nếu chỉ muốn chạy thử nhanh, có thể dùng SQLite,
  không cần cài đặt thêm phần mềm.

### 2. Tải mã nguồn và tạo môi trường ảo

```bash
git clone https://github.com/QuocAnh1104/clinic-management.git
cd clinic-management

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

> Nếu `pip install mysqlclient` báo lỗi biên dịch trên Windows mà bạn chỉ cần chạy thử,
> hãy chọn phương án SQLite ở bước 4 — khi đó không cần `mysqlclient`.

### 3. Tạo file cấu hình `.env`

Sao chép `.env.example` thành `.env` rồi điền thông tin. File `.env` chứa thông tin nhạy cảm
và đã được loại khỏi Git.

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

### 4. Cấu hình cơ sở dữ liệu

**Phương án A — MySQL (mặc định).** Tạo database trong MySQL:

```sql
CREATE DATABASE ClinicDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Điền thông tin vào `.env`:

```
SECRET_KEY=<chuỗi bí mật ngẫu nhiên>
DEBUG=True
DB_NAME=ClinicDB
DB_USER=root
DB_PASSWORD=<mật khẩu MySQL>
DB_HOST=localhost
DB_PORT=3306
```

**Phương án B — SQLite (chạy nhanh, không cần cài MySQL).** Trong `.env` chỉ cần:

```
SECRET_KEY=<chuỗi bí mật ngẫu nhiên>
DEBUG=True
DB_ENGINE=sqlite
```

Khi `DB_ENGINE=sqlite`, hệ thống tự tạo file `db.sqlite3` ở thư mục gốc.

> Tạo nhanh `SECRET_KEY`:
> `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`

### 5. Khởi tạo dữ liệu và chạy

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Truy cập http://127.0.0.1:8000/. Tài khoản quản trị tạo bằng `createsuperuser` mặc định
có vai trò `PATIENT`; để dùng như quản trị viên, đặt lại vai trò:

```bash
python manage.py shell -c "from accounts.models import CustomUser; u=CustomUser.objects.get(username='<tên>'); u.role='ADMIN'; u.save()"
```

## Tài liệu Django models

Toàn bộ model được đặt tên bảng tường minh qua `db_table` và dùng `BigAutoField` cho khóa chính.

### `accounts.CustomUser` — bảng `Accounts`

Kế thừa `AbstractUser` của Django, bổ sung các trường nghiệp vụ.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `role` | CharField | Vai trò: `ADMIN`, `PHARMACIST`, `RECEPTIONIST`, `DOCTOR`, `PATIENT` (mặc định `PATIENT`) |
| `phone` | CharField(15) | Số điện thoại, duy nhất, có thể trống |
| `must_change_password` | BooleanField | `True` nếu bắt buộc đổi mật khẩu ở lần đăng nhập đầu |

`AUTH_USER_MODEL` của dự án được trỏ tới model này.

### `accounts.Patient` — bảng `Patients`

Hồ sơ bệnh nhân, có thể liên kết tới một tài khoản đăng nhập.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `patient_id` | AutoField | Khóa chính |
| `account` | OneToOne → CustomUser | Tài khoản đăng nhập (có thể trống với bệnh nhân vãng lai) |
| `full_name` | CharField(100) | Họ tên |
| `phone` | CharField(15) | Số điện thoại, duy nhất |
| `date_of_birth` | DateField | Ngày sinh (tùy chọn) |
| `gender` | CharField(1) | `M` / `F` / `O` |
| `address` | CharField(255) | Địa chỉ |
| `created_at` | DateTimeField | Thời điểm tạo |

### `pharmacy.Medicine` — bảng `Medicines`

Danh mục thuốc và tồn kho.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `medicine_id` | AutoField | Khóa chính |
| `medicine_name` | CharField(200) | Tên thuốc |
| `unit` | CharField | Đơn vị: `VIEN`, `VI`, `LO`, `CHAI`, `TUYP` |
| `unit_price` | DecimalField | Đơn giá (≥ 0) |
| `stock_quantity` | IntegerField | Số lượng tồn (≥ 0) |
| `expiry_date` | DateField | Hạn sử dụng (có thể trống). Thuốc hết hạn không hiển thị để kê đơn |
| `is_active` | BooleanField | `False` khi thuốc bị ẩn (xóa mềm) |
| `created_at`, `updated_at` | DateTimeField | Thời điểm tạo / cập nhật |

### `clinical.Appointment` — bảng `Appointments`

Lịch hẹn khám, là trung tâm của quy trình nghiệp vụ.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `appointment_id` | AutoField | Khóa chính |
| `patient` | FK → Patient | Bệnh nhân |
| `doctor` | FK → CustomUser | Bác sĩ phụ trách (chỉ chọn user có `role='DOCTOR'`) |
| `appt_datetime` | DateTimeField | Thời gian khám |
| `source` | CharField | `WEB` (đặt online) hoặc `DIRECT` (tại quầy) |
| `status` | CharField | `PENDING` → `CONFIRMED` → `CHECKED_IN` → `COMPLETED`, hoặc `CANCELLED` |
| `note` | TextField | Ghi chú / triệu chứng sơ bộ |
| `rejection_reason` | TextField | Lý do khi lịch bị lễ tân từ chối/hủy (bắt buộc nhập khi hủy) |

### `clinical.MedicalRecord` — bảng `MedicalRecords`

Bệnh án, quan hệ một-một với lịch hẹn.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `record_id` | AutoField | Khóa chính |
| `appointment` | OneToOne → Appointment | Lịch hẹn tương ứng |
| `symptoms` | TextField | Triệu chứng |
| `diagnosis` | TextField | Chẩn đoán |
| `clinical_notes` | TextField | Ghi chú cận lâm sàng |

### `clinical.Prescription` — bảng `Prescriptions`

Một dòng thuốc trong đơn. Một bệnh án có nhiều dòng đơn thuốc.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `prescription_id` | AutoField | Khóa chính |
| `record` | FK → MedicalRecord | Bệnh án |
| `medicine` | FK → Medicine | Thuốc (`on_delete=PROTECT` để tránh xóa thuốc đã kê) |
| `quantity` | IntegerField | Số lượng |
| `dosage` | TextField | Liều dùng |

### `clinical.Invoice` — bảng `Invoices`

Hóa đơn, quan hệ một-một với bệnh án, do hệ thống tự sinh sau khi khám.

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `invoice_id` | AutoField | Khóa chính |
| `record` | OneToOne → MedicalRecord | Bệnh án |
| `consultation_fee` | DecimalField | Phí khám (mặc định 100.000) |
| `total_amount` | DecimalField | Tổng tiền (phí khám + tiền thuốc) |
| `status` | CharField | `UNPAID` hoặc `PAID` |
| `paid_at` | DateTimeField | Thời điểm thanh toán |

**Quan hệ tổng quát:**
`Patient` → `Appointment` → `MedicalRecord` → (`Prescription` ⟶ `Medicine`) và `Invoice`.

## Hướng dẫn sử dụng website

### Đăng nhập và điều hướng

Trang `/login/` chia 2 tab: **Bệnh nhân** (đăng nhập bằng số điện thoại, có link đăng ký) và
**Nhân viên** (đăng nhập bằng tên đăng nhập do Admin cấp). Đăng nhập đúng tài khoản nhưng
sai tab (vd tài khoản bệnh nhân đăng nhập ở tab Nhân viên) sẽ bị từ chối. Sau khi đăng nhập,
hệ thống tự chuyển người dùng tới khu vực làm việc tương ứng với vai trò. Tài khoản do lễ tân
hoặc Admin tạo có mật khẩu mặc định `123456` và bị bắt buộc đổi mật khẩu ở lần đăng nhập đầu tiên.

### Lễ tân (`/reception/`)

- **Tiếp nhận bệnh nhân:** nhập họ tên, số điện thoại, ngày sinh… Hệ thống tự tạo kèm
  một tài khoản đăng nhập cho bệnh nhân (username là số điện thoại).
- **Đặt lịch tại quầy:** chọn bác sĩ và thời gian; lịch được đưa thẳng vào trạng thái
  `CHECKED_IN` để bác sĩ khám ngay.
- **Duyệt lịch online:** xem hàng đợi các lịch bệnh nhân đặt qua web, duyệt hoặc từ chối
  (từ chối bắt buộc nhập lý do, bệnh nhân xem được lý do này ở "Lịch hẹn của tôi").
- **Check-in:** ở trang Lịch hẹn tổng, lịch đã duyệt (`CONFIRMED`) có nút Check-in để
  chuyển sang `CHECKED_IN` khi bệnh nhân có mặt tại quầy, đưa vào hàng đợi khám của bác sĩ.
- **Thu ngân:** tra cứu và xác nhận thanh toán hóa đơn.

### Bác sĩ (`/doctor/`)

- Xem **hàng đợi** các bệnh nhân đã check-in của chính mình.
- **Khám bệnh:** ghi triệu chứng, chẩn đoán và kê đơn thuốc. Khi lưu, hệ thống đồng thời
  trừ tồn kho, tạo hóa đơn và chuyển lịch hẹn sang `COMPLETED` trong một giao dịch duy nhất.
  Thuốc đã hết hạn sử dụng không xuất hiện trong danh sách chọn.

### Dược sĩ (`/pharmacy/`)

- Thêm, sửa, ẩn thuốc và **nhập thêm tồn kho**. Danh sách cảnh báo thuốc sắp hết hàng
  (dưới 10 đơn vị) và thuốc sắp/đã hết hạn sử dụng (trong 30 ngày tới).

### Quản trị viên (`/cashier/dashboard/`, `/account/staff/`)

- Xem **báo cáo doanh thu** theo ngày và theo khoảng thời gian, cùng công nợ chưa thu.
- **Quản lý nhân viên:** tạo tài khoản bác sĩ/lễ tân/dược sĩ/quản trị viên mới, khóa/mở
  khóa tài khoản (trừ tài khoản của chính mình).

### Bệnh nhân (`/portal/`)

- **Đăng ký** tài khoản, **đặt lịch khám trực tuyến**, hủy lịch, và xem lại **lịch sử khám**
  cùng đơn thuốc, hóa đơn của các lần khám đã hoàn tất.

## Ràng buộc nghiệp vụ đáng chú ý

- **Chống đặt trùng lịch khi có nhiều request đồng thời:** khi tạo/duyệt lịch hẹn, hệ thống
  khóa dòng bác sĩ và dòng bệnh nhân bằng `select_for_update()` trong `transaction.atomic()`
  trước khi kiểm tra xung đột, tránh trường hợp 2 request gửi gần như cùng lúc đều "thấy"
  khung giờ còn trống rồi cùng tạo lịch. Cùng cơ chế được áp dụng khi kê đơn thuốc để tránh
  trừ kho sai khi nhiều bác sĩ thao tác đồng thời.
- Một bệnh nhân không thể có 2 lịch hẹn active cùng một khung giờ, kể cả với 2 bác sĩ khác nhau.
- Không đặt lịch quá 60 ngày trong tương lai; bệnh nhân tối đa 3 lịch đang ở trạng thái
  `PENDING` cùng lúc.
- Không hủy được lịch đã `COMPLETED`; hủy/từ chối lịch bắt buộc phải nhập lý do.
- Không kê đơn thuốc đã hết hạn sử dụng, và số lượng kê phải lớn hơn 0 (chặn cả giá trị âm,
  vì trừ kho với số âm sẽ vô tình cộng ngược vào tồn kho).

## Kiểm thử

Dự án có bộ kiểm thử tự động (end-to-end) cho các luồng nghiệp vụ chính, bao gồm cả một
test giả lập 2 request đặt lịch chạy song song thật (dùng `TransactionTestCase` + threading)
để xác nhận cơ chế khóa ở trên hoạt động đúng. Chạy:

```bash
python manage.py test clinical.tests_e2e
```

Django tạo một cơ sở dữ liệu test riêng và xóa sau khi chạy xong, không ảnh hưởng dữ liệu thật.

## Quy trình Git của nhóm

- Không commit trực tiếp lên `main`.
- Mỗi tính năng làm trên một nhánh riêng: `git checkout -b feature/ten-tinh-nang`.
- Hoàn thành thì tạo Pull Request để cả nhóm review trước khi merge.
- Khi xung đột migrations: `python manage.py makemigrations --merge`.
