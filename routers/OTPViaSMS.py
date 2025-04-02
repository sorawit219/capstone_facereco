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
    print(f"Received OTP send request for user ID: {id}")
    url = "https://api-v2.thaibulksms.com/sms"
    collection_name = db["profiles"]
    user_profile = collection_name.find_one({"id":str(id)})
    
    if not user_profile:
        print(f"User profile not found for ID: {id}")
        raise HTTPException(status_code=404, detail="User profile not found")
        
    rand = rand_num()
    message = "Your OTP is "+str(rand)
    print(f"Generated OTP: {rand} for user: {id}")
    
    payload = {
        "msisdn": user_profile["phone_number"],
        "message": message,
        "sender": "FaceTicket",
        "force" : "corporate",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "authorization": os.getenv('API_KEY')
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        print(f"SMS API Response: {response.text}")
        
        collection = db["OTP_user"]
        x = datetime.now()
        document = {
            "user_id" : id,
            "OTP" : str(rand),
            "datetime" : x
        }
        check = collection.insert_one(document)
        
        if check:
            print(f"OTP saved to database for user: {id}")
            result = {'msg': "OTP has sent to your phone number and have a 3 minute to assign OTP"}
        else:
            print(f"Failed to save OTP to database for user: {id}")
            result = {'msg': "Cannot create collection for OTP"}
            
        return result
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # #have 3 user token free per api key for this api therefore can sent 3 time use carefully if want to sent more pay it

    # response = requests.post(url, data=payload, headers=headers)
    # collection = db["OTP_user"]
    # x = datetime.now()
    # document = {
    #     "user_id" : id,
    #     "OTP" : str(rand),
    #     "datetime" :  x
    # }
    # check = collection.insert_one(document)
    # print(response.text)
    # if check:
    #     result = {'msg': "OTP has sent to your phone number and have a 3 minute to assign OTP"}
    # else:
    #     result = {'msg': "Cannot create collection for OTP"}
    # return result

@router.post("/verify_otp")
async def verify_otp(user_id: str, meeting_id: str, otp: str):
    print(f"Received OTP verification request - User: {user_id}, Meeting: {meeting_id}")
    
    OTP_EXPIRY_TIME = timedelta(minutes=5)

    collection_store_otp = db[os.getenv('COLLECTION_USER_OTP')]
    otp_sent_users = collection_store_otp.find_one({"user_id": user_id})

    status = True

    if otp_sent_users is None:
        print(f"No OTP found for user: {user_id}")
        status = False
        raise HTTPException(status_code=404, detail="No OTP found for this user")

    if otp_sent_users["OTP"] != otp:
        print(f"Invalid OTP for user: {user_id}. Expected: {otp_sent_users['OTP']}, Received: {otp}")
        status = False
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if datetime.now() - otp_sent_users["datetime"] > OTP_EXPIRY_TIME:
        print(f"OTP expired for user: {user_id}")
        status = False
        raise HTTPException(status_code=400, detail="OTP expired")

    print(f"OTP verified successfully for user: {user_id}")

    #save log
    time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
    document = {
        "user_id" : user_id,
        "meeting_id": meeting_id,
        "OTP": otp,
        "STATUS" : status,
        "datetime" : datetime.now()
    }
    time_stamp_collection.insert_one(document)
    print(f"Saved verification log for user: {user_id}")

    return {"message": "OTP verified successfully"}
