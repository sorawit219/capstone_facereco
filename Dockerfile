# ใช้ Python 3.10 เป็น Base Image
FROM python:3.10

# ตั้งค่าไม่ให้ Python Buffer Logs (Log ออกทันที)
ENV PYTHONUNBUFFERED=1 

# ป้องกันปัญหาภาษาใน face_recognition และ OpenCV
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 

# ติดตั้ง dependencies ที่จำเป็น
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    && apt-get clean

# กำหนดโฟลเดอร์ทำงานใน Container
WORKDIR /capstone

# อัปเกรด pip และติดตั้ง requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์โปรเจกต์ทั้งหมดไปยัง Container
COPY . .

# เปิดพอร์ตที่ FastAPI ใช้งาน
EXPOSE 8070

# ใช้ ENTRYPOINT แทน CMD เพื่อให้รองรับ Signal Handling ได้ดีขึ้น
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8070"]
