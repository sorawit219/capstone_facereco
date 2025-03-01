import requests
from fastapi import APIRouter
from pymongo import MongoClient
from datetime import datetime,timedelta
import random
import math

router = APIRouter(
    prefix="/otp",
    tags=['OTP'],
    responses={404:{
        'message': "User not found"
    }}
)

client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]


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

@router.get("/receive")
async def receive_otp(id:str,otp:str,meeting:str):
    collection = db["OTP_user"]
    check = collection.find_one({"user_id": id,"OTP":otp})
    if check is not None:
        current_time = datetime.now()
        previous_time = check["datetime"]
        time_difference = current_time - previous_time
        three_minutes = timedelta(minutes=3)
        if time_difference >= three_minutes:
            collection2 = db["time_stamps"]
            document = {
                "user_id" : id,
                "meeting_id":meeting,
                "OTP": otp,
                "STATUS" : False,
                "datetime" :current_time
            }
            collection2.insert_one(document)
            return {"msg":"Your OTP now is Invalid"}
        else:
            collection2 = db["time_stamps"]
            document = {
                "user_id" : id,
                "meeting_id":meeting,
                "OTP": otp,
                "STATUS" : True,
                "datetime" :current_time
            }
            collection2.insert_one(document)
            return {"msg":"Your OTP is Pass , Thank You!!!"}
    else : return {"msg": "Not found Your OTP.Please put OTP again or send OTP again"}
