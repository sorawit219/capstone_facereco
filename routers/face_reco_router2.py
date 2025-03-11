from fastapi import APIRouter, BackgroundTasks,File,UploadFile,WebSocket
import pickle
import cv2
import face_recognition
import numpy as np
import asyncio
from pymongo import MongoClient
from pyzbar.pyzbar import decode
import hashlib
import datetime
import requests
import math
import random
from fastapi.responses import FileResponse
import urllib
import shutil
import uuid
from dotenv import load_dotenv
import os
import base64

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db["user_enrollments"]
router = APIRouter()
encodeListKnowWithIds = None

# Global variable to track if the camera is running
buffer = []
BUFFER_LIMIT = 5

#qr code+otp
#face_reco + otp
#face_reco + qr code

#read qr code and sent otp
@router.websocket("/qr+otp")
async def read_Qr_and_Send_otp(meeting:str,file: UploadFile = File(...)):

    global string_hash
    string_hash = "none"
    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()
    with open(file.filename, "wb") as img:
        img.write(contents)

    
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    decoded_objects = decode(gray_image)
    for obj in decoded_objects:
        object_data =  obj.data.decode('utf-8')
        sha256 = hashlib.sha256()
        sha256.update(object_data.encode('utf-8'))
        string_hash = sha256.hexdigest()
           
    result = collection.find_one({"text":string_hash},{})
    text_id = result.get("user_id")
    current_time = datetime.now()
    if result:
        send_otp(text_id)
        collection = db["time_stamps"]
        document = {"user_id" : id,
                "meeting_id":meeting,
                "OTP": None,
                "STATUS" : True,
                "datetime" :current_time}
        collection.insert_one(document)
        return {"ID":str(text_id),"msg":"OTP sent!!"}
    else: 
        collection = db["time_stamps"]
        document = {"user_id" : id,
                "meeting_id":meeting,
                "OTP": None,
                "STATUS" : False,
                "datetime" :current_time}
        collection.insert_one(document)
        return {"msg":"Not Found Qr Code was Match","match_status": "Fail" }
        



#read face reco and qr or face reco and sent otp
@router.websocket("/face_reco_+_qr_code")
async def face_reco(meeting:str,websocket:WebSocket):    
    
    await websocket.accept()
    print("🔵 WebSocket Connected!")

    global encodeListKnow
        
    try:
        with open("EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, UserId = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")
            encodeListKnowWithIds = None

    try:
        while True:
            frame_data = await websocket.receive_text()
            # แปลง Base64 เป็น OpenCV Image
            header, encoded = frame_data.split(",", 1)
            img_data = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            current_time = datetime.datetime.now()

            # ✅ ตรวจจับ QR Code
            qr_code_text = None
            decoded_objects = decode(img)
            for obj in decoded_objects:
                qr_code_text = obj.data.decode("utf-8")
                sha256 = hashlib.sha256()
                sha256.update(qr_code_text.encode("utf-8"))
                string_hash = sha256.hexdigest()
        
            print(string_hash)

            # ✅ ตรวจจับใบหน้า
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            face_location = face_recognition.face_locations(imgS)
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

            recognized_id = None
            if matches[matchIndex]:
                recognized_id = UserId[matchIndex]
                print(f"Known Face Detected - ID:{recognized_id}")

            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
            bbox = x1, y2-175, x2-x1, y2-y1
            cv2.rectangle(img, bbox, (0, 255, 0), 2)
            cv2.putText(img, str(recognized_id), (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            
            status = False
            if recognized_id and string_hash:
                result = collection.find_one({"text": string_hash})
                text_id = result["user_id"]
                if text_id == recognized_id:
                    status = True
                    msg = f" User {recognized_id} found you have enroll this meeting"
                else:
                    msg = " QR Code not match User Or not enroll in this meeting "
            elif recognized_id:
                status = False
                msg = f"User {recognized_id} Pass! But not have QR-code"

            # ✅ เพิ่มข้อมูลลง Buffer
            buffer.append({
                "user_id": recognized_id if recognized_id else "Unknown",
                "meeting_id": meeting,
                "OTP": None,
                "STATUS": status,
                "datetime": current_time
            })

            time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]  
            if len(buffer) >= BUFFER_LIMIT:
                time_stamp_collection.insert_many(buffer)
                buffer.clear() 
            
            # ✅ ส่งผลลัพธ์กลับไปยัง Frontend
            await websocket.send_json({"msg": msg, "status": status})

    except Exception as e:
        print(f"🔴 Error: {e}")



def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits

def send_otp(id:str):
    url = "https://api-v2.thaibulksms.com/sms"
    collection_name = db["profiles"]
    user_profile = collection_name.find_one({"id":str(id)})
    rand = rand_num()
    message = "Your OTP is "+str(rand)
    payload = {
        "msisdn": user_profile["phone_number"] ,
        "message": message,
        "sender": "Demo",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "authorization": "Basic MXVxbXNtODllc0RrS3JFNzNpeHlUUjFzVnVPWUpCOnJGQUNTNXQweHpKSHY2VGh4ZEt3czhsZ2pQcnlHNQ=="#token
    }

    #have 3 user token free per api key for this api therefore can sent 3 time use carefully if want to sent more pay it

    response = requests.post(url, data=payload, headers=headers)
    collection = db["OTP_user"]
    x = datetime.now()
    document = {
        "user_id" : id,
        "OTP" : str(rand),
        "datetime" : x
    }
    check = collection.insert_one(document)
    print(response.text)
    return check

