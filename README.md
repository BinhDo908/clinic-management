# Hệ thống Quản lý Phòng khám Đa khoa

## Setup môi trường

1. Clone repo: `git clone https://github.com/your-username/clinic-management.git`
2. Tạo venv: `python -m venv venv && venv\Scripts\activate`
3. Cài đặt: `pip install -r requirements.txt`
4. Cài MySQL Server 8.0 + Workbench
5. Tạo database trong Workbench:
```sql
   CREATE DATABASE ClinicDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
6. Tạo file `.env` (copy từ `.env.example`), điền thông tin DB của máy bạn
7. Chạy: `python manage.py migrate && python manage.py runserver`

## Quy trình Git

- Không bao giờ code trực tiếp trên `main`
- Tạo nhánh tính năng: `git checkout -b feature/ten-tinh-nang`
- Tối Chủ Nhật hàng tuần: tạo Pull Request, cả nhóm review rồi merge
- Conflict migrations: `python manage.py makemigrations --merge`
