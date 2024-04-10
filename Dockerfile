FROM python:3.10-slim
 
WORKDIR /capstone

RUN apt-get update && apt-get install -y build-essential cmake

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
 
 
COPY main.py main.py
COPY routers routers
COPY all_img all_img

EXPOSE 8000

CMD [ "uvicorn", "--host", "0.0.0.0", "main:app","--reload" ]