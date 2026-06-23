# Hướng dẫn Deploy lên PythonAnywhere (miễn phí)

> Kết quả: web chạy công khai tại `https://<tên_đăng_nhập>.pythonanywhere.com`, giữ nguyên MySQL.
> Thay `USERNAME` = tên đăng nhập PythonAnywhere của bạn ở mọi chỗ bên dưới.

---

## Bước 0 — Code đã sẵn sàng ✅
Code đã sửa cho production (nạp `.env` đúng đường dẫn + `CSRF_TRUSTED_ORIGINS` cho HTTPS)
và đã được push lên **fork của bạn**: `https://github.com/BinhDo908/clinic-management` (nhánh `main`).
Server sẽ clone trực tiếp từ fork này nên không cần làm gì thêm ở bước này.

---

## Bước 1 — Đăng ký tài khoản
1. Vào https://www.pythonanywhere.com → **Pricing & signup** → **Create a Beginner account** (miễn phí, không cần thẻ).
2. Ghi nhớ `USERNAME` của bạn.

---

## Bước 2 — Tạo database MySQL
1. Vào tab **Databases**.
2. Mục *MySQL*: đặt **password** cho MySQL (ghi nhớ), bấm **Initialize MySQL**.
3. Tạo database mới tên `clinicdb` → tên đầy đủ sẽ là **`USERNAME$clinicdb`**.
4. Ghi lại các thông tin (sẽ điền vào `.env`):
   - **DB_NAME** = `USERNAME$clinicdb`
   - **DB_USER** = `USERNAME`
   - **DB_HOST** = `USERNAME.mysql.pythonanywhere-services.com`
   - **DB_PASSWORD** = mật khẩu MySQL bạn vừa đặt

---

## Bước 3 — Tải code về server
Mở tab **Consoles** → **Bash**, chạy (clone từ **fork của bạn**):
```bash
git clone https://github.com/BinhDo908/clinic-management.git
cd clinic-management
```

---

## Bước 4 — Tạo virtualenv & cài thư viện
```bash
mkvirtualenv --python=/usr/bin/python3.10 clinic-venv
pip install -r requirements.txt
```
> Virtualenv tự kích hoạt (thấy `(clinic-venv)` ở đầu dòng). Lần sau muốn kích hoạt lại: `workon clinic-venv`.

---

## Bước 5 — Tạo file `.env` trên server
Vẫn trong console (đang ở thư mục `clinic-management`):
```bash
nano .env
```
Dán nội dung sau, **thay USERNAME, mật khẩu, secret key**:
```
SECRET_KEY=doi-thanh-mot-chuoi-ngau-nhien-dai-50-ky-tu
DEBUG=False
DB_NAME=USERNAME$clinicdb
DB_USER=USERNAME
DB_PASSWORD=mat_khau_mysql_cua_ban
DB_HOST=USERNAME.mysql.pythonanywhere-services.com
DB_PORT=3306
CSRF_TRUSTED_ORIGINS=https://USERNAME.pythonanywhere.com
```
Lưu: `Ctrl+O` → `Enter` → thoát `Ctrl+X`.

> Tạo SECRET_KEY ngẫu nhiên nhanh:
> `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`

---

## Bước 6 — Khởi tạo dữ liệu
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## Bước 7 — Tạo Web app
1. Vào tab **Web** → **Add a new web app** → **Next**.
2. Chọn **Manual configuration** (KHÔNG chọn "Django") → chọn **Python 3.10** → **Next**.

---

## Bước 8 — Cấu hình Web app
Trong tab **Web**, thiết lập:

| Mục | Giá trị |
|-----|---------|
| **Source code** | `/home/USERNAME/clinic-management` |
| **Working directory** | `/home/USERNAME/clinic-management` |
| **Virtualenv** | `/home/USERNAME/.virtualenvs/clinic-venv` |

### Sửa file WSGI
Bấm vào link **WSGI configuration file** (dạng `/var/www/USERNAME_pythonanywhere_com_wsgi.py`), **xóa hết** nội dung cũ, dán đoạn này (nhớ thay USERNAME):
```python
import os
import sys

path = '/home/USERNAME/clinic-management'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'clinic_project.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
Bấm **Save**.

---

## Bước 9 — Khai báo Static files
Vẫn ở tab **Web**, kéo xuống mục **Static files**, thêm 2 dòng:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/USERNAME/clinic-management/staticfiles` |
| `/media/` | `/home/USERNAME/clinic-management/media` |

---

## Bước 10 — Chạy!
1. Lên đầu tab **Web**, bấm nút xanh **Reload**.
2. Mở `https://USERNAME.pythonanywhere.com` → đăng nhập bằng superuser vừa tạo. 🎉

---

## Khi cập nhật code về sau
```bash
workon clinic-venv
cd clinic-management
git pull
pip install -r requirements.txt        # nếu có thư viện mới
python manage.py migrate               # nếu có migration mới
python manage.py collectstatic --noinput
```
Rồi vào tab **Web** bấm **Reload**.

---

## Xử lý lỗi thường gặp
- **Lỗi 502 / "Something went wrong"**: xem **Error log** ở tab Web (cuối trang). Thường do sai đường dẫn WSGI hoặc thiếu `.env`.
- **Lỗi 403 CSRF khi đăng nhập**: kiểm tra dòng `CSRF_TRUSTED_ORIGINS` trong `.env` đúng `https://USERNAME.pythonanywhere.com` (có `https://`, không có dấu `/` cuối), rồi Reload.
- **Lỗi kết nối DB**: kiểm tra `DB_HOST`, `DB_NAME` có đúng tiền tố `USERNAME$` không.
- **Trang không có CSS**: chạy lại `collectstatic` và kiểm tra mục Static files đã map đúng.
- **Tài khoản free**: mỗi 3 tháng vào tab Web bấm nút gia hạn (PythonAnywhere gửi email nhắc).
```
