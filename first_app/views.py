from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.conf import settings
from django.core.mail import send_mail
from django.utils.timezone import now

import datetime
import hashlib
import hmac
import json
import urllib
import urllib.parse
import urllib.request
import random

from .cart import Cart
from .forms import ContactForm, MyRegistrationForm, AppointmentForm, CarForm, OrderCreateForm, UserUpdateForm, UserProfileForm, MyAuthenticationForm
from .models import Services, Part, PartCategory, Car, PartGroup, OrderItem, UserProfile, Order, Appointment

# Create your views here.
def index(request):
    context={
        'message':'Chao mung banj den voi trang quan ly garage!'
    }
    return render(request,'index.html',context)


class MyLoginView(LoginView):
    """
    View xử lý trang đăng nhập.
    """
    # Tên file template bạn vừa tạo
    template_name = 'login.html'
    form_class = MyAuthenticationForm

    # URL để chuyển hướng đến sau khi đăng nhập thành công
    # 'index' là name= của trang chủ trong urls.py
    success_url = reverse_lazy('index')


class MyLogoutView(LogoutView):
    """
    View xử lý khi người dùng bấm "Đăng xuất".
    """
    # Dòng này để chuyển hướng về trang chủ sau khi logout
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

def services(request):
    all_services = Services.objects.all().order_by('name')
    context = {
        'danh_sach_dich_vu': all_services,
    }
    return render(request,'services.html', context)
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'Cảm ơn bạn đã liên hệ với chúng tôi ')
            return redirect('contact')
    else:
        form = ContactForm()
    context = {
        'form': form
    }
    return render(request, 'contact.html', context)
def search(request):
    # 1. Lấy từ khóa người dùng gõ vào (biến 'q')
    query = request.GET.get('q')

    services_results = []
    parts_results = []

    if query:
        # 2. Tìm trong Dịch Vụ (Tìm theo Tên hoặc Mô tả)
        services_results = Services.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

        # 3. Tìm trong Phụ Tùng (Tìm theo Tên, Mã SP, hoặc Thương hiệu)
        parts_results = Part.objects.filter(
            Q(name__icontains=query) |
            Q(part_number__icontains=query) |
            Q(brand__icontains=query)
        )

    context = {
        'query': query,
        'services_results': services_results,
        'parts_results': parts_results,
    }
    return render(request, 'search_results.html', context)


def register(request):
    if request.method == "POST":
        form = MyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            avatar_img = form.cleaned_data.get('avatar')
            profile, created = UserProfile.objects.get_or_create(user=user)
            if avatar_img:
                profile.avatar = avatar_img

            otp = str(random.randint(100000, 999999))
            # Để test, in OTP ra màn hình đen
            print(f"⚠️ OTP CỦA BẠN LÀ: {otp}")

            profile.otp_code = otp
            profile.save()

            # Gửi mail (bỏ qua lỗi nếu chưa cấu hình xong)
            try:
                subject = 'Mã xác nhận đăng ký Garage'
                message = f'Mã xác nhận của bạn là: {otp}'
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [user.email]
                send_mail(subject, message, email_from, recipient_list)
            except:
                pass

            request.session['verifying_user_id'] = user.id
            return redirect('verify_otp')

    else:
        form = MyRegistrationForm()

    # ⬅️ QUAN TRỌNG: Dòng này phải nằm ngoài cùng (thẳng hàng với if/else)
    return render(request, 'register.html', {'form': form})

# 2. HÀM XÁC NHẬN OTP (MỚI)
def verify_otp(request):
    if request.method == "POST":
        otp_input = request.POST.get('otp')
        user_id = request.session.get('verifying_user_id')

        if not user_id:
            return redirect('register')

        try:
            user = User.objects.get(id=user_id)
            profile = UserProfile.objects.get(user=user)

            if profile.otp_code == otp_input:
                # Mã đúng! Kích hoạt tài khoản
                user.is_active = True
                user.save()

                # Xóa OTP cho sạch
                profile.otp_code = None
                profile.save()

                # Đăng nhập luôn và về trang chủ
                login(request, user)
                request.session.pop('verifying_user_id', None)

                return redirect('index')
            else:
                return render(request, 'verify_otp.html', {'error': 'Mã xác nhận không đúng!'})

        except User.DoesNotExist:
            return redirect('register')

    return render(request, 'verify_otp.html')
def custom_logout(request):
    logout(request) # Xóa session đăng nhập
    return redirect('index') # Chuyển về trang chủ

def parts_by_category(request, category_id):
    # 1. Dùng cái ID nhận được để tìm xem khách đang muốn xem loại nào
    # (Ví dụ: category_id=1 -> Tìm ra loại "Bánh xe")
    category = get_object_or_404(PartCategory, id=category_id)

    # 2. Lấy tất cả phụ tùng thuộc loại đó
    parts = Part.objects.filter(category=category)

    # Lấy tất cả nhóm phụ tùng và các loại phụ tùng liên quan
    all_part_groups = PartGroup.objects.prefetch_related('categories').all()

    # 3. Gửi ra template
    context = {
        'category': category,
        'parts': parts,
        'all_part_groups': all_part_groups, # Thêm dữ liệu nhóm phụ tùng vào context
    }
    return render(request, 'parts_list.html', context)


def all_parts(request):
    # Lấy danh sách ID của các category được chọn từ query params
    selected_category_ids = request.GET.getlist('category')

    # Lấy tất cả phụ tùng, sắp xếp cái mới nhập lên đầu (-id)
    parts = Part.objects.all().order_by('-id')

    # Nếu có category được chọn, lọc danh sách phụ tùng
    if selected_category_ids:
        parts = parts.filter(category__id__in=selected_category_ids)

    # Lấy tất cả nhóm phụ tùng và các loại phụ tùng liên quan để hiển thị sidebar
    all_part_groups = PartGroup.objects.prefetch_related('categories').all()

    # Chuyển đổi ID sang integer để template dễ so sánh
    selected_ids_int = [int(id) for id in selected_category_ids]

    # Gửi sang trang parts_list.html
    context = {
        'parts': parts,
        'all_part_groups': all_part_groups,
        'selected_category_ids': selected_ids_int,  # Gửi ID đã chọn sang template
        'category': None, # Giữ lại để tránh lỗi template nếu có dùng
    }
    return render(request, 'parts_list.html', context)

@login_required
def create_appointment(request):
    if request.method == 'POST':
        # Pass the user to the form
        form = AppointmentForm(request.POST, user=request.user)
        if form.is_valid():
            # Create an appointment object but don't save to database yet
            appointment = form.save(commit=False)
            # Assign the current user to the customer field
            appointment.customer = request.user
            # Now, save the object
            appointment.save()
            # Important: You need to save the many-to-many data for the form.
            form.save_m2m()
            
            messages.success(request, 'Bạn đã đặt lịch thành công! Chúng tôi sẽ sớm liên hệ với bạn.')
            return redirect('index') # Redirect to the homepage after successful booking
    else:
        # Pass the user to the form to filter cars
        form = AppointmentForm(user=request.user)

    context = {
        'form': form
    }
    return render(request, 'appointment_form.html', context)

@login_required
def my_cars(request):
    cars = Car.objects.filter(owner=request.user).order_by('-year')
    return render(request, 'my_cars.html', {'cars': cars})

@login_required
def manage_car(request, car_id=None):
    if car_id:
        # Editing an existing car
        car = get_object_or_404(Car, id=car_id, owner=request.user)
        title = "Chỉnh sửa thông tin xe"
    else:
        # Adding a new car
        car = None
        title = "Thêm xe mới"

    if request.method == 'POST':
        form = CarForm(request.POST, instance=car)
        if form.is_valid():
            new_car = form.save(commit=False)
            new_car.owner = request.user
            new_car.save()
            messages.success(request, f'Đã lưu thông tin xe {new_car.license_plate} thành công.')
            return redirect('my_cars')
    else:
        form = CarForm(instance=car)

    return render(request, 'car_form.html', {'form': form, 'title': title})

@login_required
def delete_car(request, car_id):
    car = get_object_or_404(Car, id=car_id, owner=request.user)
    if request.method == 'POST':
        plate = car.license_plate
        car.delete()
        messages.success(request, f'Đã xóa xe {plate} thành công.')
        return redirect('my_cars')
    # If not POST, just show the confirmation page
    return render(request, 'car_confirm_delete.html', {'car': car})

@login_required
def my_appointments(request):
    """
    Hiển thị danh sách các lịch hẹn của người dùng đã đăng nhập.
    """
    # Lấy tất cả lịch hẹn của user hiện tại, sắp xếp theo ngày hẹn gần nhất lên đầu
    appointments = Appointment.objects.filter(customer=request.user).order_by('-appointment_date')
    context = {
        'appointments': appointments
    }
    return render(request, 'my_appointments.html', context)

@login_required
def my_profile(request):
    # Dùng get_or_create để đảm bảo user nào cũng có profile, kể cả admin
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = UserProfileForm(request.POST,
                                   request.FILES,
                                   instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Tài khoản của bạn đã được cập nhật!')
            return redirect('my_profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = UserProfileForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'my_profile.html', context)

def part_detail(request, part_id):

    part = get_object_or_404(Part, id=part_id)

    context = {

        'part': part

    }

    return render(request, 'part_detail.html', context)



@require_POST

def add_to_cart(request, part_id):

    cart = Cart(request)

    part = get_object_or_404(Part, id=part_id)

    quantity = int(request.POST.get('quantity', 1))



    # Logic to check stock before adding

    current_quantity_in_cart = cart.cart.get(str(part.id), {}).get('quantity', 0)

    

    if part.quantity <= 0:

         messages.error(request, f'Sản phẩm "{part.name}" đã hết hàng.')

    elif current_quantity_in_cart + quantity > part.quantity:

        messages.error(request, f'Không đủ hàng cho sản phẩm "{part.name}". Chỉ còn {part.quantity} sản phẩm trong kho.')

    else:

        cart.add(part=part, quantity=quantity)



    # Redirect to the page the user was on, or a default

    return redirect(request.POST.get('next', 'parts_list'))



def cart_detail(request):

    cart = Cart(request)

    return render(request, 'cart/cart_detail.html', {'cart': cart})



def remove_from_cart(request, part_id):

    cart = Cart(request)

    part = get_object_or_404(Part, id=part_id)

    cart.remove(part)

    return redirect('cart_detail')

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.customer = request.user
            order.total_price = cart.get_total_price()
            order.save() # Lưu đơn hàng để có ID

            for item in cart:
                OrderItem.objects.create(order=order,
                                         part=item['part'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            
            # Xóa giỏ hàng
            cart.clear()

            if order.payment_method == 'vnpay':
                # ========== LOGIC THANH TOÁN VNPAY ==========
                vnp_TmnCode = settings.VNPAY_TMN_CODE
                vnp_HashSecret = settings.VNPAY_HASH_SECRET_KEY
                vnp_Url = settings.VNPAY_PAYMENT_URL
                vnp_ReturnUrl = settings.VNPAY_RETURN_URL
                
                # Mã tham chiếu của giao dịch. Nó bắt buộc phải duy nhất trong ngày.
                # Lưu ý: Mỗi đơn hàng sẽ có 1 mã TxnRef duy nhất.
                vnp_TxnRef = f"{order.id}_{now().strftime('%Y%m%d%H%M%S')}" 
                
                vnp_OrderInfo = f"Thanh toan don hang {order.id}"
                vnp_Amount = int(order.total_price) * 100 # Số tiền cần nhân 100
                vnp_CurrCode = 'VND'
                vnp_IpAddr = get_client_ip(request)
                vnp_Locale = 'vn'
                vnp_OrderType = 'other' # Loại hàng hóa

                vnp_CreateDate = now().strftime('%Y%m%d%H%M%S')
                
                # Dữ liệu gửi đi
                input_data = {
                    'vnp_Version': '2.1.0',
                    'vnp_Command': 'pay',
                    'vnp_TmnCode': vnp_TmnCode,
                    'vnp_Amount': vnp_Amount,
                    'vnp_CurrCode': vnp_CurrCode,
                    'vnp_TxnRef': vnp_TxnRef,
                    'vnp_OrderInfo': vnp_OrderInfo,
                    'vnp_OrderType': vnp_OrderType,
                    'vnp_Locale': vnp_Locale,
                    'vnp_ReturnUrl': vnp_ReturnUrl,
                    'vnp_IpAddr': vnp_IpAddr,
                    'vnp_CreateDate': vnp_CreateDate,
                }
                
                # Sắp xếp các key và tạo chuỗi hash
                input_data = dict(sorted(input_data.items()))
                hash_data = "&".join([f"{key}={urllib.parse.quote_plus(str(value))}" for key, value in input_data.items()])
                
                # Tạo chữ ký an toàn
                secure_hash = hmac.new(vnp_HashSecret.encode(), hash_data.encode(), hashlib.sha512).hexdigest()
                
                # Thêm chữ ký vào dữ liệu
                input_data['vnp_SecureHash'] = secure_hash
                
                # Tạo URL thanh toán cuối cùng
                payment_url = vnp_Url + "?" + urllib.parse.urlencode(input_data)
                
                # Chuyển hướng người dùng sang VNPay
                return redirect(payment_url)

            else: # Trường hợp là COD
                messages.success(request, 'Đơn hàng của bạn đã được tạo thành công!')
                return redirect('index')
    else:
        # Pre-fill form if user is logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'full_name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        form = OrderCreateForm(initial=initial_data)
        
    return render(request,
                  'orders/order_create.html',
                  {'cart': cart, 'form': form})


def get_client_ip(request):
    """Hàm để lấy địa chỉ IP của client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def payment_return(request):
    input_data = request.GET.copy() # Sử dụng .copy() để có thể thay đổi
    
    if not input_data:
        messages.error(request, "Không nhận được dữ liệu trả về từ VNPay.")
        return redirect('index')

    vnp_SecureHash = input_data.get('vnp_SecureHash')
    
    # Xóa các tham số không cần thiết khỏi dữ liệu để kiểm tra chữ ký
    if 'vnp_SecureHash' in input_data:
        del input_data['vnp_SecureHash']
    if 'vnp_SecureHashType' in input_data:
        del input_data['vnp_SecureHashType']
        
    # Sắp xếp dữ liệu theo key
    input_data = dict(sorted(input_data.items()))
    
    vnp_HashSecret = settings.VNPAY_HASH_SECRET_KEY
    
    # Tạo chuỗi hash
    hash_data = "&".join([f"{key}={urllib.parse.quote_plus(str(value))}" for key, value in input_data.items()])
    
    # Tạo chữ ký mới để so sánh
    secure_hash = hmac.new(vnp_HashSecret.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    # So sánh chữ ký
    if secure_hash == vnp_SecureHash:
        try:
            # Lấy mã đơn hàng từ vnp_TxnRef
            order_id_full = input_data.get('vnp_TxnRef')
            order_id_str = order_id_full.split('_')[0]
            order_id = int(order_id_str)
            
            order = Order.objects.get(id=order_id)
            
            response_code = input_data.get('vnp_ResponseCode')
            
            # Nếu giao dịch thành công
            if response_code == '00':
                order.paid = True
                order.save()
                
                context = {
                    'success': True,
                    'order': order,
                    'message': 'Đơn hàng của bạn đã được thanh toán thành công!'
                }
                return render(request, 'payment_return.html', context)
            
            # Nếu giao dịch không thành công
            else:
                # Có thể xóa đơn hàng nếu muốn
                # order.delete() 
                context = {
                    'success': False,
                    'error_message': f"Thanh toán không thành công. Mã lỗi từ VNPay: {response_code}"
                }
                return render(request, 'payment_return.html', context)

        except Order.DoesNotExist:
            context = {'success': False, 'error_message': 'Không tìm thấy đơn hàng trong hệ thống.'}
            return render(request, 'payment_return.html', context)
        except (ValueError, IndexError):
            context = {'success': False, 'error_message': 'Mã tham chiếu đơn hàng không hợp lệ.'}
            return render(request, 'payment_return.html', context)
            
    # Nếu chữ ký không hợp lệ
    else:
        context = {'success': False, 'error_message': 'Chữ ký không hợp lệ. Giao dịch có thể đã bị thay đổi.'}
        return render(request, 'payment_return.html', context)

@csrf_exempt
def payment_ipn(request):
    """
    View xử lý Instant Payment Notification (IPN) từ VNPay.
    """
    if request.method == 'GET':
        input_data = request.GET.copy()
        if not input_data:
            return JsonResponse({'RspCode': '99', 'Message': 'Invalid data'})

        vnp_SecureHash = input_data.get('vnp_SecureHash')

        if 'vnp_SecureHash' in input_data:
            del input_data['vnp_SecureHash']
        if 'vnp_SecureHashType' in input_data:
            del input_data['vnp_SecureHashType']
            
        input_data = dict(sorted(input_data.items()))
        
        vnp_HashSecret = settings.VNPAY_HASH_SECRET_KEY
        
        hash_data = "&".join([f"{key}={urllib.parse.quote_plus(str(value))}" for key, value in input_data.items()])
        secure_hash = hmac.new(vnp_HashSecret.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

        if secure_hash == vnp_SecureHash:
            try:
                order_id_full = input_data.get('vnp_TxnRef')
                order_id_str = order_id_full.split('_')[0]
                order_id = int(order_id_str)
                order = Order.objects.get(id=order_id)
                
                response_code = input_data.get('vnp_ResponseCode')
                
                # Kiểm tra xem đơn hàng đã được xử lý chưa
                if order.paid:
                    return JsonResponse({'RspCode': '02', 'Message': 'Order already confirmed'})

                # Nếu thanh toán thành công
                if response_code == '00':
                    order.paid = True
                    order.save()
                    return JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    # Giao dịch thất bại, có thể cập nhật trạng thái đơn hàng nếu cần
                    return JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'}) # VNPay yêu cầu trả về 00 cho cả TH thất bại
            except Order.DoesNotExist:
                return JsonResponse({'RspCode': '01', 'Message': 'Order not found'})
            except (ValueError, IndexError):
                return JsonResponse({'RspCode': '99', 'Message': 'Invalid TxnRef'})
        else:
            return JsonResponse({'RspCode': '97', 'Message': 'Invalid Signature'})
            
    return JsonResponse({'RspCode': '99', 'Message': 'Invalid request method'})

def service_detail(request, slug):
    """
    Hiển thị chi tiết một dịch vụ cụ thể dựa vào slug.
    """
    service = get_object_or_404(Services, slug=slug)
    context = {
        'service': service,
    }
    return render(request, 'service_detail.html', context)

# ===================================================================
# ======================== ADMIN/STAFF VIEWS ========================
# ===================================================================

def staff_required(user):
    return user.is_staff

@user_passes_test(staff_required)
def all_appointments(request):
    """
    Hiển thị tất cả các lịch hẹn cho admin/staff quản lý.
    """
    appointments = Appointment.objects.all().order_by('-appointment_date')
    context = {
        'appointments': appointments
    }
    return render(request, 'all_appointments.html', context)

@user_passes_test(staff_required)
def update_appointment_status(request, appt_id, new_status):
    """
    Cập nhật trạng thái của một lịch hẹn.
    """
    appointment = get_object_or_404(Appointment, id=appt_id)
    
    # Validate the new_status to make sure it's a valid choice
    valid_statuses = [status[0] for status in Appointment.STATUS_CHOICES]
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        messages.success(request, f"Đã cập nhật trạng thái lịch hẹn thành '{appointment.get_status_display()}'.")
    else:
        messages.error(request, "Trạng thái cập nhật không hợp lệ.")
        
    return redirect('all_appointments')

@user_passes_test(staff_required)
def revenue_dashboard(request):
    """
    Hiển thị trang tổng quan doanh thu cho admin.
    """
    # 1. Doanh thu từ bán phụ tùng (chỉ tính các đơn đã thanh toán)
    parts_revenue = Order.objects.filter(paid=True).aggregate(total=Sum('total_price'))['total'] or 0

    # 2. Doanh thu từ dịch vụ (chỉ tính các lịch hẹn đã hoàn thành)
    services_revenue = Services.objects.filter(appointment__status='completed').aggregate(total=Sum('price'))['total'] or 0

    # 3. Tổng doanh thu
    total_revenue = parts_revenue + services_revenue

    context = {
        'parts_revenue': parts_revenue,
        'services_revenue': services_revenue,
        'total_revenue': total_revenue,
    }

    return render(request, 'revenue_dashboard.html', context)





    
