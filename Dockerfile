FROM python:3.10.0-slim
 
WORKDIR /capstone

RUN apt-get update \
    && apt-get install -y build-essential cmake 
RUN apt install libgl1-mesa-glx -y
RUN apt-get install 'ffmpeg'\
    'libsm6'\
    'libxext6'  -y
RUN apt-get install -y libzbar0
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
 
 
COPY main.py main.py
COPY ./routers ./routers
COPY ./lall_img ./lall_img


CMD [ "uvicorn", "--host", "0.0.0.0", "main:app","--port","8000","--reload" ]