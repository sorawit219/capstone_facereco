from fastapi import APIRouter,WebSocket,WebSocketDisconnect
import pickle
import cv2
import face_recognition
import numpy as np
import asyncio
from pymongo import MongoClient
from pyzbar.pyzbar import decode
import hashlib
from datetime import datetime, timedelta
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
collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]
router = APIRouter()
encodeListKnowWithIds = None

# Global variable to track if the camera is running
buffer = []
BUFFER_LIMIT = 5

#qr code+otp
#face_reco + otp
#face_reco + qr code

#read qr-code and sent otp        
@router.websocket("/qr+otp")
async def read_qr(websocket: WebSocket):
    await websocket.accept()
    otp_sent_users = set()
    try:
        while True:
            qr_data = await websocket.receive_text()  # รับข้อมูล QR Code
            sha256 = hashlib.sha256()
            sha256.update(qr_data.encode('utf-8'))
            string_hash = sha256.hexdigest()

            # ค้นหา QR Code ในฐานข้อมูล
            result = collection.find_one({"text": string_hash})
            if result:
                user_id = result["user_id"]                
                if user_id not in otp_sent_users:
                    otp_sent_users.add(user_id)
                    otp = send_otp(user_id)  # ส่ง OTP
                    await websocket.send_text(f"OTP sent to user {user_id}")
            else:
                await websocket.send_text("QR Code not found in database")

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        await websocket.close()


#read face-recognition and sent otp
@router.websocket("/face_reco+otp")
async def face_reco(websocket:WebSocket):    
    await websocket.accept()
    print("WebSocket Connected!")

    global encodeListKnow
    otp_sent_users = set()
        
    try:
        with open("EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, UserId = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")
            encodeListKnowWithIds = None
    
    if encodeListKnowWithIds is None:
        await websocket.send_text("Face encoding data not available")
        await websocket.close()
        return

    try:
        while True:
            frame_data = await websocket.receive_text()
            # แปลง Base64 เป็น OpenCV Image
            header, encoded = frame_data.split(",", 1)            
            img_data = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_text("No face detected")
                continue
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                if not any(matches):  # ไม่มีใบหน้าตรงกัน
                    await websocket.send_text("Face not recognized")
                    continue

                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    name = collection.find_one({"user_id": recognized_id})["name"]
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    
                    
                    if recognized_id not in otp_sent_users:
                        otp_sent_users.add(recognized_id)
                        otp = send_otp(recognized_id)  # ส่ง OTP
                        await websocket.send_text(f"OTP sent to user {recognized_id}")
    except WebSocketDisconnect:
        print("WebSocket Disconnected")       
    except Exception as e:
        print(f"Error: {e}")


#read face-recognition and qr-code
@router.websocket("/face_reco+qr")
async def face_reco(meeting:str,websocket:WebSocket):
    
    await websocket.accept()
    print("WebSocket Connected!")

    global encodeListKnow
        
    try:
        with open("EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, UserId = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")
            encodeListKnowWithIds = None

    if encodeListKnowWithIds is None:
        await websocket.send_text("Face encoding data not available")
        await websocket.close()
        return

    try:
        while True:
            frame_data = await websocket.receive_text()
            # แปลง Base64 เป็น OpenCV Image
            header, encoded = frame_data.split(",", 1)
            img_data = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            current_time = datetime.now()

            #ตรวจจับ QR Code
            qr_code_text = None
            decoded_objects = decode(img)
            for obj in decoded_objects:
                qr_code_text = obj.data.decode("utf-8")
                sha256 = hashlib.sha256()
                sha256.update(qr_code_text.encode("utf-8"))
                string_hash = sha256.hexdigest()
        
            print(string_hash)

            #ตรวจจับใบหน้า
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_text("No face detected")
                continue
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                if not any(matches):  # ไม่มีใบหน้าตรงกัน
                    await websocket.send_text("Face not recognized")
                    continue
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                recognized_id = None
                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    print(f"Known Face Detected - ID:{recognized_id}")
                    name = collection.find_one({"user_id": recognized_id})["name"]
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                    bbox = x1, y2-175, x2-x1, y2-y1
                    cv2.rectangle(img, bbox, (0, 255, 0), 2)
                    cv2.putText(img, name, (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            
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
                msg = f"User {recognized_id} Pass! But not have QR-code.Plase scan QR-code"

            document = {
                "user_id": recognized_id if recognized_id else "Unknown",
                "meeting_id": meeting,
                "OTP": None,
                "STATUS": status,
                "datetime": current_time
            }

            time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
            if status:
                time_stamp_collection.insert_one(document)

            #เพิ่มข้อมูลลง Buffer
            if status:
                buffer.append(document)

            if len(buffer) >= BUFFER_LIMIT:
                time_stamp_collection.insert_many(buffer)
                buffer.clear() 
            
            #ส่งผลลัพธ์กลับไปยัง Frontend
            await websocket.send_json({"msg": msg, "status": status})

    except WebSocketDisconnect:
        print("WebSocket Disconnected")

    except Exception as e:
        print(f"Error: {e}")




def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits

async def send_otp(id:str):
    url = "https://api-v2.thaibulksms.com/sms"
    collection_name = db["profiles"]
    user_profile = collection_name.find_one({"id":str(id)})
    rand = rand_num()
    message = "Your OTP is "+str(rand)
    payload = {
        "msisdn": user_profile["phone_number"] ,
        "message": message,
        "sender": "FaceTicket",
        "force" : "corporate",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "authorization": os.getenv('API_KEY')
    }

    #have 3 user token free per api key for this api therefore can sent 3 time use carefully if want to sent more pay it

    response = requests.post(url, data=payload, headers=headers)
    collection_store_otp = db[os.getenv('COLLECTION_USER_OTP')]
    x = datetime.now()
    document = {
        "user_id" : id,
        "OTP" : str(rand),
        "datetime" : x
    }
    check = collection_store_otp.insert_one(document) #save otp to database
    print(response.text)
    return check
