# D:\QuanLyGarage\first_project\first_project\urls.py

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
# 1. Import 'views' từ first_app
from first_app import views
from django.contrib.auth import views as auth_views

# 2. Import 2 class Login/Logout
from first_app.views import MyLoginView, MyLogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 3. Đặt tất cả các đường dẫn của bạn Ở ĐÂY
    path('', views.index, name='index'), 
    path('services/', views.services, name='services'),
    path('services/<slug:slug>/', views.service_detail, name='service_detail'),
    path('contact/', views.contact, name='contact'), # Đây là form liên hệ
    path('booking/', views.create_appointment, name='create_appointment'),

    # 5. URLs cho quản lý xe của người dùng
    path('my-cars/', views.my_cars, name='my_cars'),
    path('my-cars/add/', views.manage_car, name='add_car'),
    path('my-cars/edit/<int:car_id>/', views.manage_car, name='edit_car'),
    path('my-cars/delete/<int:car_id>/', views.delete_car, name='delete_car'),

    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('my-profile/', views.my_profile, name='my_profile'),

    # 4. Các đường dẫn Login/Logout
    path('register/', views.register, name='register'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('search/', views.search, name='search'),

    # Password Reset URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='password_reset/password_reset_form.html',
             email_template_name='password_reset/password_reset_email.html'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    path('verify_otp', views.verify_otp, name='verify_otp'),
    path('parts/', views.all_parts, name='parts_list'),
    path('parts/<int:category_id>/', views.parts_by_category, name='parts_by_category'),
    path('parts/<int:part_id>/', views.part_detail, name='part_detail'),

    # URLs cho Giỏ hàng
    path('cart/add/<int:part_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:part_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('order/create/', views.order_create, name='order_create'),

    # URLs for VNPay
    path('payment/return/', views.payment_return, name='payment_return'),
    path('payment/ipn/', views.payment_ipn, name='payment_ipn'),
]
# --- ADMIN URLs ---
urlpatterns += [
    path('admin-dashboard/appointments/', views.all_appointments, name='all_appointments'),
    path('admin-dashboard/appointments/update/<int:appt_id>/<str:new_status>/', views.update_appointment_status, name='update_appointment_status'),
    path('admin-dashboard/revenue/', views.revenue_dashboard, name='revenue_dashboard'),
]