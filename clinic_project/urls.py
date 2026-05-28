from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', accounts_views.dashboard, name='dashboard'),  # Trang chủ
    path('change-password/', accounts_views.change_password, name='change_password'),
    path('login/', auth_views.LoginView.as_view(
        redirect_authenticated_user=False  # Luôn hiện form login, không tự bỏ qua
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('pharmacy/', include('pharmacy.urls')),
    # Các app khác sẽ thêm sau khi các thành viên hoàn thành
    path('reception/', include('reception.urls')),
]