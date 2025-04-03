from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from routers.utils.otp_utils import generate_otp, send_otp_sms, verify_otp

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

@router.post("/send")
async def send_otp(id:str):
    print(f"Received OTP send request for user ID: {id}")
    try:
        result = await send_otp_sms(id, db, os.getenv('API_KEY'))
        return {"msg": result["message"]}
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/verify_otp")
@router.post("/verify_otp")
async def verify_otp_endpoint(user_id: str, meeting_id: str, otp: str):
    print(f"Received OTP verification request - User: {user_id}, Meeting: {meeting_id}")
    try:
        # Get collection names with defaults if env vars not set
        otp_collection = os.getenv('COLLECTION_USER_OTP', 'OTP_user')
        timestamp_collection = os.getenv('COLLECTION_TIME_STAMPS', 'time_stamps')
        
        result = await verify_otp(
            user_id=user_id,
            otp=otp,
            meeting_id=meeting_id,
            db=db,
            collection_name=otp_collection,
            timestamp_collection=timestamp_collection
        )
        return {"message": result["message"]}
    except HTTPException as e:
        # Re-raise FastAPI HTTP exceptions
        raise e
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
