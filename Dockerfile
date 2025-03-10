FROM python:3.10

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    libboost-all-dev \
    && apt-get clean


WORKDIR /capstone


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


EXPOSE 8070


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8070", "--reload"]
