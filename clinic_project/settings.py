"""
Django settings for clinic_project.
Dự án: Hệ thống Quản lý Phòng khám Đa khoa
Database: MySQL 8.0
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ==============================================================================
# CẤU HÌNH ĐƯỜNG DẪN GỐC
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Tải biến môi trường từ file .env (chỉ định rõ đường dẫn để chạy đúng
# cả khi deploy — vd PythonAnywhere — nơi thư mục làm việc khác thư mục dự án)
load_dotenv(BASE_DIR / '.env')


# ==============================================================================
# CẤU HÌNH BẢO MẬT
# ==============================================================================
# SECRET_KEY được lấy từ file .env, KHÔNG hardcode trực tiếp vào đây
SECRET_KEY = os.getenv('SECRET_KEY')

# DEBUG=True khi phát triển, BẮT BUỘC đổi thành False khi deploy production
DEBUG = os.getenv('DEBUG') == 'True'

# Danh sách host được phép truy cập. Khi deploy, thay '*' bằng domain thật
ALLOWED_HOSTS = ['*']

# Khi deploy HTTPS (vd PythonAnywhere), Django yêu cầu khai báo origin tin cậy
# cho CSRF, nếu không các form POST (đăng nhập, đặt lịch...) sẽ bị lỗi 403.
# Đặt trong .env: CSRF_TRUSTED_ORIGINS=https://tenban.pythonanywhere.com
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]


# ==============================================================================
# DANH SÁCH CÁC APP TRONG DỰ ÁN
# ==============================================================================
INSTALLED_APPS = [
    # App mặc định của Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # App của dự án (do nhóm phát triển)
    'accounts',          # Quản lý tài khoản & phân quyền (Thành viên 1)
    'pharmacy',          # Quản lý kho thuốc (Thành viên 1)
    'clinical',          # Bệnh án, lịch hẹn, đơn thuốc, hóa đơn (dùng chung)
    'reception',         # Module Lễ tân (Thành viên 2)
    'doctor',            # Module Bác sĩ (Thành viên 3)
    'cashier',           # Module Thu ngân & Báo cáo (Thành viên 4)
    'patient_portal',    # Cổng thông tin bệnh nhân (Thành viên 5)
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware ép đổi mật khẩu lần đầu
    'accounts.middleware.ForcePasswordChangeMiddleware',
]


# ==============================================================================
# CẤU HÌNH URL & WSGI
# ==============================================================================
ROOT_URLCONF = 'clinic_project.urls'

WSGI_APPLICATION = 'clinic_project.wsgi.application'


# ==============================================================================
# CẤU HÌNH TEMPLATE
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Thư mục templates dùng chung
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# ==============================================================================
# CẤU HÌNH CƠ SỞ DỮ LIỆU
# ==============================================================================
# Mặc định dùng MySQL 8.0 (môi trường phát triển ở local).
# Khi deploy lên nơi không có MySQL (vd PythonAnywhere free), đặt trong .env:
#     DB_ENGINE=sqlite
# thì hệ thống tự dùng SQLite (1 file, không cần cài đặt phần mềm gì thêm).
if os.getenv('DB_ENGINE', 'mysql') == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                # Bắt buộc cho tiếng Việt và emoji
                'charset': 'utf8mb4',
                # Bật strict mode để MySQL báo lỗi rõ ràng khi dữ liệu sai
                # thay vì âm thầm cắt bớt hoặc làm tròn
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


# ==============================================================================
# CẤU HÌNH XÁC THỰC NGƯỜI DÙNG
# ==============================================================================
# Sử dụng CustomUser model tự định nghĩa (có thêm trường role, phone)
AUTH_USER_MODEL = 'accounts.CustomUser'

# URL điều hướng cho login/logout
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Các rule kiểm tra độ mạnh password
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,  # Tối thiểu 6 ký tự (phù hợp đồ án sinh viên)
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ==============================================================================
# CẤU HÌNH NGÔN NGỮ & MÚI GIỜ
# ==============================================================================
LANGUAGE_CODE = 'vi'              # Tiếng Việt
TIME_ZONE = 'Asia/Ho_Chi_Minh'    # Múi giờ Việt Nam (GMT+7)
USE_I18N = True                   # Bật hỗ trợ đa ngôn ngữ
USE_TZ = True                     # Lưu thời gian theo UTC trong DB


# ==============================================================================
# CẤU HÌNH STATIC FILES (CSS, JS, Hình ảnh tĩnh)
# ==============================================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']    # Thư mục static dùng chung
STATIC_ROOT = BASE_DIR / 'staticfiles'      # Thư mục collect static khi deploy


# ==============================================================================
# CẤU HÌNH MEDIA FILES (File upload từ người dùng)
# ==============================================================================
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# CẤU HÌNH KHÁC
# ==============================================================================
# Kiểu dữ liệu cho khóa chính mặc định
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cấu hình message tags để hiển thị alert Bootstrap đúng màu
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',  # Bootstrap dùng 'danger' thay vì 'error'
}