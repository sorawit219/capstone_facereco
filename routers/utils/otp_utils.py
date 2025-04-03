import math
import random
import requests
from datetime import datetime
from pymongo import MongoClient
import os
from fastapi import HTTPException

# Generate a random 6-digit OTP
def generate_otp():
    """
    Generate a random 6-digit OTP.
    
    Returns:
        str: A 6-digit OTP string
    """
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(f"Generated OTP: {six_digits}")
    return six_digits

# Send OTP via SMS and store it in the database
async def send_otp_sms(user_id: str, db: MongoClient, api_key: str):
    """
    Send an OTP via SMS to the user and store it in the database.
    
    Args:
        user_id (str): The user ID to send the OTP to
        db (MongoClient): MongoDB client instance
        api_key (str): The SMS API key
        
    Returns:
        dict: Response message with status
    """
    print(f"Sending OTP for user ID: {user_id}")
    url = "https://api-v2.thaibulksms.com/sms"
    collection_name = db["profiles"]
    user_profile = collection_name.find_one({"id": str(user_id)})
    
    if not user_profile:
        print(f"User profile not found for ID: {user_id}")
        raise HTTPException(status_code=404, detail="User profile not found")
        
    otp = generate_otp()
    message = f"Your OTP is {otp}"
    
    payload = {
        "msisdn": user_profile["phone_number"],
        "message": message,
        "sender": "FaceTicket",
        "force": "corporate",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
        "authorization": api_key
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        print(f"SMS API Response: {response.text}")
        
        collection = db["OTP_user"]
        current_time = datetime.now()
        document = {
            "user_id": user_id,
            "OTP": otp,
            "datetime": current_time
        }
        check = collection.insert_one(document)
        
        if check:
            print(f"OTP saved to database for user: {user_id}")
            return {
                "success": True,
                "message": "OTP has been sent to your phone number and is valid for 3 minutes"
            }
        else:
            print(f"Failed to save OTP to database for user: {user_id}")
            return {
                "success": False,
                "message": "Failed to store OTP in database"
            }
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Verify the OTP submitted by the user
async def verify_otp(user_id: str, otp: str, meeting_id: str, db: MongoClient, collection_name: str, timestamp_collection: str):
    """
    Verify the OTP submitted by the user.
    
    Args:
        user_id (str): The user ID
        otp (str): The OTP submitted by the user
        meeting_id (str): The meeting ID
        db (MongoClient): MongoDB client instance
        collection_name (str): The name of the collection storing OTPs
        timestamp_collection (str): The name of the collection storing timestamps
        
    Returns:
        dict: Response with verification status
    """
    from datetime import timedelta
    
    # Validate collection names are strings
    if not collection_name or not isinstance(collection_name, str):
        raise HTTPException(status_code=500, detail="Invalid OTP collection name configuration")
    
    if not timestamp_collection or not isinstance(timestamp_collection, str):
        raise HTTPException(status_code=500, detail="Invalid timestamp collection name configuration")
    
    OTP_EXPIRY_TIME = timedelta(minutes=5)
    collection_store_otp = db[collection_name]
    
    # Find the most recent OTP for the user
    otp_sent_users = collection_store_otp.find({"user_id": user_id}).sort("datetime", -1).limit(1)
    otp_sent_users = list(otp_sent_users)
    
    if not otp_sent_users:
        print(f"No OTP found for user: {user_id}")
        raise HTTPException(status_code=404, detail="No OTP found for this user")
    
    otp_record = otp_sent_users[0]
    current_time = datetime.now()
    
    # Check if OTP is expired
    if current_time - otp_record["datetime"] > OTP_EXPIRY_TIME:
        print(f"OTP expired for user: {user_id}. Sent at: {otp_record['datetime']}")
        raise HTTPException(status_code=400, detail="OTP expired")
    
    # Check if OTP matches
    if otp_record["OTP"] != otp:
        print(f"Invalid OTP for user: {user_id}. Expected: {otp_record['OTP']}, Received: {otp}")
        raise HTTPException(status_code=400, detail="Invalid OTP")

    print(f"OTP verified successfully for user: {user_id}")

    # Save verification log
    time_stamp_collection = db[timestamp_collection]
    document = {
        "user_id": user_id,
        "meeting_id": meeting_id,
        "OTP": otp,
        "STATUS": True,
        "datetime": current_time
    }
    time_stamp_collection.insert_one(document)
    print(f"Saved verification log for user: {user_id}")

    return {"success": True, "message": "OTP verified successfully"} 