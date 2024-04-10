FROM python:3.10-slim
 
WORKDIR /capstone
 
COPY ./requirements.txt ./
RUN pip install -r requirements.txt
 
# Stage 2
FROM python:3-alpine AS runner
 
WORKDIR /app
 
COPY main.py main.py
COPY routers routers
COPY all_img all_img

 
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
 
EXPOSE 8000

CMD [ "uvicorn", "--host", "0.0.0.0", "main:app" ]