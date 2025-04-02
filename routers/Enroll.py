#import numpy as np
import logging
from fastapi import APIRouter,HTTPException
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pymongo import MongoClient
# Initialize MongoDB client
from datetime import datetime
import smtplib
import ssl
from email.message import EmailMessage
import pyqrcode
import random
import math
import hashlib
from io import BytesIO
from bson import ObjectId
import os
from dotenv import load_dotenv
load_dotenv()
from bson import Binary
import base64



smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')
smtp_username = os.getenv('SMTP_USERNAME')
smtp_password = os.getenv('SMTP_PASSWORD')

from_email = 'capstone.FaceRec@gmail.com'
subject = 'Here is QR-code'
body = 'Thank for using FACETICKET'


client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection_name = db["user_enrollments"]

 

router = APIRouter(
    prefix="/enrollment",
    tags=['Enroll'],
    responses={404:{
        'message': "User not found"
    }}
)



class Enroll(BaseModel):
    meet_id :str
    user_id : str
    date_time : datetime
    qrcode : bytes
    text : str

class Qr_otp(BaseModel):
    meet_id :str
    user_id : str
    date_time : datetime
    rand : str
    qrcode : bytes
    text: str

def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits

def generate_qr(name):
    try:
        x = rand_num()  # generate number
        qr_data = f"{x}_{name}"  # Combining random number and name
        shuffled_data = ''.join(random.sample(qr_data.strip(" "), len(qr_data)))  # Shuffle the data after removing whitespace
        
        # Create QR code
        qr = pyqrcode.create(shuffled_data)
        
        # Create PNG in memory
        png_content = BytesIO()
        qr.png(png_content, scale=6)  # Remove the module_drawer parameter
        png_content.seek(0)
        
        return shuffled_data, png_content
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Required package 'pypng' is not installed. Please install it using: pip install pypng"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code: {str(e)}"
        )


# @router.get("/")
# def read_root():
#     try:
#         # Your code here
#         return {"message": "Success"}
#     except Exception as e:
#         logging.error(f"An error occurred: {str(e)}")
#         raise



# @router.get('/{u_id}')
# def search_enrollment(u_id: str):
#     result = []
#     # for post in Enroll.find({"id":str(u_id)}):
#     for post in collection_name.find({"user_id": str(u_id)}):
#         result.append(post)
#     return result
@router.get('/{id}')
def search_enrollment(id: str):
    try:
        # Try to find by ObjectId
        results = list(collection_name.find({"user_id": ObjectId(id)}))
    except:
        # If ObjectId doesn't work, try as a string
        results = list(collection_name.find({"user_id": id}))
    
    for result in results:
        # Convert _id to string for the response
        result["_id"] = str(result["_id"])

        # Check and decode the QR code data
        if "qrcode" in result:
            qrcode_data = result["qrcode"]
            
            # If the qrcode is stored as Binary data (BinData in MongoDB)
            if isinstance(qrcode_data, Binary):
                # Convert the binary data to a base64-encoded string
                result["qrcode"] = base64.b64encode(qrcode_data).decode('utf-8')
            else:
                result["qrcode"] = "Invalid format for qrcode"
                
    return results

@router.get("/u_id/{creator_id}")
async def get_enrollments_by_creator(creator_id: str):
    try:
        # Find all enrollments where user_id matches the creator_id
        result = []
        enrollments = collection_name.find({"user_id": creator_id})
        
        # Convert MongoDB documents to JSON serializable format
        for enrollment in enrollments:
            # Convert ObjectId to string and binary data to base64 if needed
            enrollment["_id"] = str(enrollment["_id"])
            if "qrcode" in enrollment and isinstance(enrollment["qrcode"], bytes):
                enrollment["qrcode"] = "binary_data"  # Replace binary data with placeholder
            
            result.append(enrollment)
            
        return result
    except Exception as e:
        logging.error(f"Error fetching enrollments for creator {creator_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch enrollments: {str(e)}")

@router.post("/{id}")
async def create_enrollment(id: str, meet_id: str, choice: int):  # face+otp =1 , face+qr=2, qr+top = 3
    try:
        # Check if the meeting exists
        collec = db["meeting"]
        meet_object = ObjectId(meet_id)
        meeting = collec.find_one({"_id": meet_object})
        if meeting:
            # Add the user ID to the list of enrolled users
            collec.update_one({"_id": meet_object}, {"$push": {"enrolled_users": id}})
        else:
            raise HTTPException(status_code=404, detail="Meeting not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enroll in meeting: {e}")

    try:
        # Retrieve user data
        criteria = {"id": id}
        collection_name = db["profiles"]
        result = collection_name.find_one(criteria, {"name": 1, "email": 1})
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
            
        name = result["name"]
        email = result.get("email")
        
        # Generate QR code
        shuffled_data, png_content = generate_qr(name)
        
        # Create hash
        sha256 = hashlib.sha256()
        sha256.update(shuffled_data.encode('utf-8'))
        string_hash = sha256.hexdigest()
        
        # Create enrollment document
        enrollment = Enroll(
            meet_id=str(meet_id),
            user_id=str(id),
            date_time=datetime.now(),
            text=string_hash,
            qrcode=png_content.getvalue()
        )
        
        # Insert enrollment data
        result_insert = db["user_enrollments"].insert_one(enrollment.model_dump())
        
        if not result_insert:
            raise HTTPException(status_code=500, detail="Failed to insert enrollment data")
            
        # Send email if not face-only option
        if choice != 1:
            if not email:
                raise HTTPException(status_code=400, detail="User's email not found")
                
            try:
                em = EmailMessage()
                em['From'] = from_email
                em['To'] = email
                em['Subject'] = subject
                em.set_content(body)
                em.add_attachment(png_content.getvalue(), maintype='image', subtype='png', filename='QR_code.png')
                
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, int(smtp_port), context=context) as smtp:
                    smtp.login(smtp_username, smtp_password)
                    smtp.send_message(em)
                    
                return {"msg": "Enrollment created and email sent successfully!"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
        else:
            return {"msg": "Enrollment created successfully!"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create enrollment: {str(e)}")

@router.delete("/{id}")
async def delete_enrollment(id: str, meet_id: str):
    try:
        query = {"user_id": id, "meet_id": meet_id}
        result = collection_name.delete_one(query)

        if result.deleted_count == 1:
            collec = db["meeting"]
            meeting = ObjectId(meet_id)
            collec.update_one({"_id":meeting}, {"$pull": {"enrolled_users": {"$in": [id]}}})
            return {"msg": f"{id} was deleted"}
        else:
            raise HTTPException(status_code=404, detail="Enrollment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete enrollment: {e}")