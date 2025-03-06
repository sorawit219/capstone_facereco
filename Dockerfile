FROM python:3.10.0-alpine
 
WORKDIR /capstone
RUN apt update && apt install -y cmake g++ make \
    && pip install dlib face-recognition
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
 
 
COPY main.py main.py
COPY ./routers ./routers
COPY ./lall_img ./lall_img


CMD [ "uvicorn", "--host", "0.0.0.0", "main:app","--port","8070","--reload" ]