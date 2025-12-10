# 1. Chọn hệ điều hành nền (Python 3.9 hoặc version bạn đang dùng)
FROM python:3.10-slim

# 2. Ngăn Python tạo file .pyc và buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Tạo thư mục làm việc trong container
WORKDIR /app

# 4. Copy file thư viện vào và cài đặt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code vào container
COPY . /app/

# 6. Mở port 8000 (Port mặc định của Django)
EXPOSE 8000

# 7. Lệnh chạy server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]