from fastapi import APIRouter, BackgroundTasks,File,UploadFile
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
load_dotenv()

client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db["user_enrollments"]
router = APIRouter()


# Global variable to track if the camera is running


#read qr code and and sent otp
@router.get("/qr+otp")
async def read_qr(meeting:str,file: UploadFile = File(...)):

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
@router.get("/video+otp_or_face+otp")
async def face_reco(qrcode:bool,meeting:str,file: UploadFile = File(...)):    
    encodeListKnowWithIds = None
    encodeListKnow = None
    global string_hash
    string_hash = "none"
    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()
    with open(file.filename, "wb") as img:
        img.write(contents)
    
    try:
        with open("EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, studentIds = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")

    current_time = datetime.now()

    if qrcode:
        decoded_objs = decode(img)
        for obj in decoded_objs:
            text = obj.data.decode("utf-8")
            sha256 = hashlib.sha256()
            sha256.update(text.encode('utf-8'))
            string_hash = sha256.hexdigest()
        
    print(string_hash)

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
    faceCurFrame = face_recognition.face_locations(imgS)
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
        matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
        faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
        matchIndex = np.argmin(faceDis)

        if matches[matchIndex]:
            id = studentIds[matchIndex]
                
            print("Known Face Detected - ID:", id)

            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
            bbox = x1, y2-175, x2-x1, y2-y1
            cv2.rectangle(img, bbox, (0, 255, 0), 2)
            cv2.putText(img, str(id), (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            if qrcode:
                result = collection.find_one({"text":text},{})
                text_id = result["user_id"]
                    
                if text_id == id:
                    #success 
                    collection = db["time_stamps"]
                    document = {"user_id" : id,
                    "meeting_id":meeting,
                    "OTP": None,
                    "STATUS" : True,
                    "datetime" :current_time}
                    collection.insert_one(document)
                    return {"msg":"User"+id+" found you have enroll this meeting"}
                        
                else: 
                    #fail
                    collection = db["time_stamps"]
                    document = {"user_id" : id,
                        "meeting_id":meeting,
                        "OTP": None,
                        "STATUS" : False,
                        "datetime" :current_time}
                    collection.insert_one(document)
                    return {"msg":"User "+id+" not found in this meeting"}
            else:
                send_otp(id)
                collection = db["time_stamps"]
                document = {"user_id" : id,
                    "meeting_id":meeting,
                    "OTP": None,
                    "STATUS" : True,
                    "datetime" :current_time}
                collection.insert_one(document)
                return {"msg":"OTP sent to User"+id}





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

