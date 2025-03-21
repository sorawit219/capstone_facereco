import requests
from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from datetime import datetime,timedelta
import random
import math
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(
    prefix="/otp",
    tags=['OTP'],
    responses={404:{
        'message': "User not found"
    }}
)


client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]


def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits

@router.post("/send")
async def send_otp(id:str):
    url = "https://api-v2.thaibulksms.com/sms"
    collection_name = db["profiles"]
    user_profile = collection_name.find_one({"id":str(id)})
    rand = rand_num()
    message = "Your OTP is "+str(rand)
    payload = {
        "msisdn": user_profile["phone_number"] ,
        "message": message,
        "sender": "Demo",
        "force" : "corporate",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "authorization": "Basic MXVxbXNtODllc0RrS3JFNzNpeHlUUjFzVnVPWUpCOnJGQUNTNXQweHpKSHY2VGh4ZEt3czhsZ2pQcnlHNQ=="
    }

    #have 3 user token free per api key for this api therefore can sent 3 time use carefully if want to sent more pay it

    response = requests.post(url, data=payload, headers=headers)
    collection = db["OTP_user"]
    x = datetime.now()
    document = {
        "user_id" : id,
        "OTP" : str(rand),
        "datetime" :  x
    }
    check = collection.insert_one(document)
    print(response.text)
    if check:
        result = {'msg': "OTP has sent to your phone number and have a 3 minute to assign OTP"}
    else:
        result = {'msg': "Cannot create collection for OTP"}
    return result

@router.post("/verify_otp")
async def verify_otp(user_id: str,meeting:str, otp: str):

    OTP_EXPIRY_TIME = timedelta(minutes=5)

    collection_store_otp = db[os.getenv('COLLECTION_USER_OTP')]
    otp_sent_users = collection_store_otp.find_one({"user_id": user_id})

    status = True

    if otp_sent_users is None:
        status = False
        raise HTTPException(status_code=404, detail="No OTP found for this user")

    if otp_sent_users["OTP"] != otp:
        status = False
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # ตรวจสอบว่า OTP หมดอายุหรือยัง
    if datetime.now() - otp_sent_users["datetime"] > OTP_EXPIRY_TIME:
        status = False
        raise HTTPException(status_code=400, detail="OTP expired")

    #save log
    time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
    document = {
        "user_id" : user_id,
        "meeting_id":meeting,
        "OTP": otp,
        "STATUS" : status,
        "datetime" :datetime.now()
    }
    time_stamp_collection.insert_one(document)

    return {"message": "OTP verified successfully"}
