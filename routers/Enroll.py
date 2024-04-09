#import numpy as np
import logging
from fastapi import APIRouter,HTTPException
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pymongo import MongoClient
# Initialize MongoDB client
import datetime
import smtplib
import ssl
from email.message import EmailMessage
import pyqrcode
import random
import math
import hashlib
from io import BytesIO
from bson import ObjectId


smtp_server = 'smtp.gmail.com'
smtp_port = 465
smtp_username = 'capstone.facerec@gmail.com'
smtp_password = 'qjvz izcl ehtr bwlw'

from_email = 'capstone.FaceRec@gmail.com'
subject = 'Here is QR-code'
body = 'Thank for using FACETICKET'


client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
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
    date_time : datetime.datetime
    qrcode : bytes
    text : str

class Qr_otp(BaseModel):
    meet_id :str
    user_id : str
    date_time : datetime.datetime
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
    x = rand_num()#generate number
    qr_data = f"{x}_{name}"  # Combining random number and name
    qr_data = qr_data.strip
    shuffled_data = ''.join(random.sample(qr_data.strip(), len(qr_data)))  # Shuffle the data after removing whitespace
    qr = pyqrcode.create(shuffled_data) #create qrcode
    png_content = BytesIO()
    qr.png(png_content, scale=6)
    png_content.seek(0)
    return shuffled_data, png_content #return name of qrcode and qrcode data
    


@router.get("/")
def read_root():
    try:
        # Your code here
        return {"message": "Success"}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise



@router.get('/{id}')
def search_enrollment(user_id:str):
    result = []
    for post in Enroll.find({"id":str(user_id)}):
        result.append(post)
    return result

@router.post("/{id}")
async def create_enrollment(id:str,meet_id:str,choice:int):#face+otp =1 , face+qr=2, qr+top = 3
    
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

    try:# sent qr code
        # Retrieve user data
        criteria = {"id": id}
        collection_name = db["profiles"]
        result = collection_name.find_one(criteria, {"name": 1, "email": 1})
        if result:
            name = result.get("name", "").strip()  # Remove leading and trailing whitespace from the name
            shuffled_data, png_content = generate_qr(name)
            sha256 = hashlib.sha256()
            print(shuffled_data)
            sha256.update(shuffled_data.encode('utf-8'))
            string_hash = sha256.hexdigest()
            #print("hash complete")
            enrollment = Enroll(meet_id=str(meet_id), user_id=str(id), date_time=datetime.now(), text=string_hash, qrcode=png_content.getvalue())
            # Insert enrollment data into the database
            result_insert = db["enrollments"].insert_one(enrollment.model_dump())
            if result_insert:
                # Send email with QR code
                to_email = result.get("email", "")
                if to_email:
                    
                    em = EmailMessage()
                    em['From'] = 'capstone.FaceRec@gmail.com'
                    em['To'] = to_email
                    em['Subject'] = 'Here is QR-code'
                    em.set_content(body)
                    em.add_attachment(png_content.getvalue(), maintype='image', subtype='png', filename='QR_code.png')
                    
                    context = ssl.create_default_context()
                    smtp_server = "smtp.gmail.com"
                    smtp_port = 465
                    smtp_username = "capstone.facerec@gmail.com"
                    smtp_password = "qjvz izcl ehtr bwlw"
                    
                    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
                        smtp.login(smtp_username, smtp_password)
                        smtp.send_message(em)
                    print("Email sent successfully!")
                else:
                    return {"error": "User's email not found"}
            else:
                return {"error": "Failed to insert enrollment data into the database"}
        else:
            return {"error": "User not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create enrollment: {e}")

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