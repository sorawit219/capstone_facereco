from fastapi import APIRouter,WebSocket,WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.security import APIKeyHeader
import pickle
import cv2
import face_recognition
import numpy as np
from pymongo import MongoClient
from pyzbar.pyzbar import decode
import hashlib
from datetime import datetime
import requests
import math
import random
from dotenv import load_dotenv
import os
import base64
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from fastapi.responses import JSONResponse
from bson import json_util
import json

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]

# Global variable to track if the camera is running
buffer = []
BUFFER_LIMIT = 5

#qr code+otp
#face_reco + otp
#face_reco + qr code

# Add CORS origins and API key handling
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Update your router definition to include tags
router = APIRouter(tags=["Face Recognition"])

# Add a dependency function to verify API key or origin
async def verify_connection(websocket: WebSocket):
    # Temporarily allow all connections for troubleshooting
    return True
    
    # The rest of your verification logic can stay commented out for now
    # origin = websocket.headers.get("origin", "")
    # allowed_origins = ["http://localhost:4200", "https://yourfrontend.com", "*"]
    # ...

#read qr-code and sent otp        
@router.websocket("/qr+otp")
async def read_qr(websocket: WebSocket):
    await websocket.accept()
    # Skip the verification step until we get the connection working
    # if not await verify_connection(websocket):
    #     await websocket.close(code=1008)  # Policy Violation
    #     return
    
    # Get meeting from query parameters
    meeting = websocket.query_params.get("meeting", "default_meeting")
    
    string_hash = None
    otp_sent_users = set()
    try:
        while True:
            qr_data = await websocket.receive_text()  # รับข้อมูล QR Code
            if not qr_data:
                await websocket.send_json({"error": "Empty QR code data received"})
                continue
            print(f"Raw QR Data: {qr_data}")
            clean_qr_data = qr_data.strip()
            current_time = datetime.now()
            sha256 = hashlib.sha256()
            sha256.update(clean_qr_data.encode('utf-8'))
            string_hash = sha256.hexdigest()
            print(f"SHA256 Hash: {string_hash}") #เอา hash string ไป check ใน db

            # ค้นหา QR Code ในฐานข้อมูล
            result = collection.find_one({"text": string_hash})
            if result is None:
                status = False
                user_id = None
                name = "Unknown"
                msg = "QR Code not found in database"
            
            if result:
                user_id = result["user_id"]
                user_data = collection.find_one({"user_id": user_id})
                if user_data and "name" in user_data:
                    name = user_data["name"]
                
                status = True
                msg = f"OTP sent to user {user_id}"
                
                if user_id not in otp_sent_users:
                    otp_sent_users.add(user_id)
                    otp = await send_otp(user_id)  # ส่ง OTP
            
            # Record timestamp
            document = {
                "user_id": user_id if user_id else "Unknown",
                "name": name,
                "meeting_id": meeting,
                "OTP": True if user_id else False,
                "STATUS": status,
                "datetime": current_time
            }

            # Save to database
            time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
            if status:
                time_stamp_collection.insert_one(document)

            global buffer
            buffer.append(document)

            if len(buffer) >= BUFFER_LIMIT:
                time_stamp_collection.insert_many(buffer)
                buffer.clear()
            
            await websocket.send_json({"msg": msg, "status": status, "timestamp": document})

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


#read face-recognition and sent otp
@router.websocket("/face_reco+otp")
async def face_reco(websocket:WebSocket):    
    await websocket.accept()
    print("WebSocket Connected!")

    # Get meeting from query parameters
    meeting = websocket.query_params.get("meeting", "default_meeting")

    global encodeListKnow
    otp_sent_users = set()
        
    try:
        with open("EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, UserId = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")
            await websocket.send_json({"error": "Face encoding data not available"})
            await websocket.close()
            return
    
    try:
        while True:
            frame_data = await websocket.receive_text()
            current_time = datetime.now()
            
            # แปลง Base64 เป็น OpenCV Image
            try:
                header, encoded = frame_data.split(",", 1)            
                img_data = base64.b64decode(encoded)
                np_arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            except Exception as e:
                await websocket.send_json({"error": "Invalid image data","status":False})
                continue

            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_json({"msg":"No Face Detect","status":False})
                continue
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            status = False
            recognized_id = None
            name = "Unknown"
            msg = "Face not recognized"

            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                if not any(matches):  # ไม่มีใบหน้าตรงกัน
                    continue

                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    user_data = collection.find_one({"user_id": recognized_id})
                    name = user_data["name"] if user_data and "name" in user_data else "Unknown"
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    
                    status = True
                    msg = f"OTP sent to user {recognized_id}"
                    
                    if recognized_id not in otp_sent_users:
                        otp_sent_users.add(recognized_id)
                        otp = await send_otp(recognized_id)  # ส่ง OTP
            
            # Record timestamp
            document = {
                "user_id": recognized_id if recognized_id else "Unknown",
                "name": name,
                "meeting_id": meeting,
                "OTP": True if recognized_id and status else False,
                "STATUS": status,
                "datetime": current_time
            }

            # Save to database
            time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
            if status:
                time_stamp_collection.insert_one(document)

            global buffer
            buffer.append(document)

            if len(buffer) >= BUFFER_LIMIT:
                time_stamp_collection.insert_many(buffer)
                buffer.clear()
                
            await websocket.send_json({"msg": msg, "status": status, "timestamp": document})
            
    except WebSocketDisconnect:
        print("WebSocket Disconnected")       
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_json({"error": str(e)})


#read face-recognition and qr-code
@router.websocket("/face_reco+qr")
async def face_reco_qr(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket Connected!")
    
    try:
        # Get meeting from query parameters
        meeting = websocket.query_params.get("meeting", "default_meeting")
        
        global encodeListKnow
        try:
            with open("EncodeFile.p", 'rb') as file:
                encodeListKnowWithIds = pickle.load(file)
                encodeListKnow, UserId = encodeListKnowWithIds
            print("Encoding file Loaded")
        except FileNotFoundError:
            print("Error: Encoding file not found.")
            await websocket.send_json({"error": "Face encoding data not available"})
            await websocket.close()
            return
        
        while True:
            frame_data = await websocket.receive_text()
            # แปลง Base64 เป็น OpenCV Image
            try:
                header, encoded = frame_data.split(",", 1)
                img_data = base64.b64decode(encoded)
                np_arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception as e:
                await websocket.send_json({"error": "Invalid image data"})
                continue
            
            current_time = datetime.now()
            string_hash = None

            #ตรวจจับ QR Code
            qr_code_text = None
            decoded_objects = decode(img)
            for obj in decoded_objects:
                qr_code_text = obj.data.decode("utf-8")
                sha256 = hashlib.sha256()
                sha256.update(qr_code_text.encode("utf-8"))
                string_hash = sha256.hexdigest()
            
            status = False
            print(string_hash)

            #ตรวจจับใบหน้า
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_json({"msg": "No face detected", "status": status})
                continue
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                if not any(matches):  # ไม่มีใบหน้าตรงกัน
                    await websocket.send_json({"msg": "Face not match in ListKnow", "status": status})
                    continue
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                recognized_id = None
                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    print(f"Known Face Detected - ID:{recognized_id}")
                    user_data = collection.find_one({"user_id": recognized_id})
                    name = user_data["name"]
                    if name is None:
                        name = "Unknown"
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                    bbox = x1, y2-175, x2-x1, y2-y1
                    cv2.rectangle(img, bbox, (0, 255, 0), 2)
                    cv2.putText(img, name, (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                else:
                    await websocket.send_json({"msg": "Face not recognized", "status": status})
            
            msg = "Authentication failed"

            if recognized_id and string_hash:
                result = collection.find_one({"text": string_hash})
                text_id = result["user_id"]
                if text_id == recognized_id:
                    status = True
                    msg = f" User {recognized_id} found you have enroll this meeting Please Check in"
                else:
                    msg = " QR Code not match User Or not enroll in this meeting "
            elif recognized_id:
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
        await websocket.send_json({"error": str(e)})


def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits

# Add the timestamp search functionality
@router.get("/timestamps/meeting/{meeting_id}")
async def get_timestamps_by_meeting(meeting_id: str, 
                                  limit: Optional[int] = Query(100, ge=1, le=1000),
                                  skip: Optional[int] = Query(0, ge=0),
                                  status: Optional[bool] = None,
                                  sort_by: Optional[str] = Query("datetime", regex="^(datetime|user_id|name)$"),
                                  sort_order: Optional[int] = Query(-1, ge=-1, le=1)):
    """
    Retrieve timestamp records for a specific meeting.
    
    Parameters:
    - meeting_id: ID of the meeting to search for
    - limit: Maximum number of records to return (default: 100, max: 1000)
    - skip: Number of records to skip (for pagination)
    - status: Filter by authentication status (optional)
    - sort_by: Field to sort by (datetime, user_id, or name)
    - sort_order: Sort order (1 for ascending, -1 for descending)
    
    Returns:
    - List of timestamp records for the meeting
    """
    try:
        # Create the filter
        query_filter = {"meeting_id": meeting_id}
        if status is not None:
            query_filter["STATUS"] = status
        
        # Get the collection
        time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
        
        # Execute the query with sorting and pagination
        cursor = time_stamp_collection.find(query_filter)\
                                   .sort(sort_by, sort_order)\
                                   .skip(skip)\
                                   .limit(limit)
        
        # Count total records for this meeting
        total_records = time_stamp_collection.count_documents(query_filter)
        
        # Convert MongoDB cursor to a list
        records = list(cursor)
        
        # Convert ObjectId and datetime to string for JSON serialization
        parsed_records = json.loads(json_util.dumps(records))
        
        # Return the results
        return {
            "total": total_records,
            "records": parsed_records,
            "limit": limit,
            "skip": skip,
            "has_more": (skip + limit) < total_records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving timestamps: {str(e)}")

@router.get("/timestamps/user/{user_id}")
async def get_timestamps_by_user(user_id: str,
                               meeting_id: Optional[str] = None,
                               limit: Optional[int] = Query(100, ge=1, le=1000),
                               skip: Optional[int] = Query(0, ge=0),
                               status: Optional[bool] = None,
                               sort_by: Optional[str] = Query("datetime", regex="^(datetime|meeting_id|name)$"),
                               sort_order: Optional[int] = Query(-1, ge=-1, le=1)):
    """
    Retrieve timestamp records for a specific user.
    
    Parameters:
    - user_id: ID of the user to search for
    - meeting_id: Optional filter for specific meeting
    - limit: Maximum number of records to return (default: 100, max: 1000)
    - skip: Number of records to skip (for pagination)
    - status: Filter by authentication status (optional)
    - sort_by: Field to sort by (datetime, meeting_id, or name)
    - sort_order: Sort order (1 for ascending, -1 for descending)
    
    Returns:
    - List of timestamp records for the user
    """
    try:
        # Create the filter
        query_filter = {"user_id": user_id}
        if meeting_id:
            query_filter["meeting_id"] = meeting_id
        if status is not None:
            query_filter["STATUS"] = status
        
        # Get the collection
        time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
        
        # Execute the query with sorting and pagination
        cursor = time_stamp_collection.find(query_filter)\
                                   .sort(sort_by, sort_order)\
                                   .skip(skip)\
                                   .limit(limit)
        
        # Count total records for this user
        total_records = time_stamp_collection.count_documents(query_filter)
        
        # Convert MongoDB cursor to a list
        records = list(cursor)
        
        # Convert ObjectId and datetime to string for JSON serialization
        parsed_records = json.loads(json_util.dumps(records))
        
        # Return the results
        return {
            "total": total_records,
            "records": parsed_records,
            "limit": limit,
            "skip": skip,
            "has_more": (skip + limit) < total_records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving timestamps: {str(e)}")

@router.get("/meetings")
async def get_meetings_list():
    """
    Get a list of all meetings with statistics.
    
    Returns:
    - List of meetings with stats like total check-ins and unique users
    """
    try:
        time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMPS')]
        
        # Use aggregation to group by meeting_id and get statistics
        pipeline = [
            # Group by meeting_id and calculate statistics
            {
                "$group": {
                    "_id": "$meeting_id",
                    "total_check_ins": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"},
                    "successful_check_ins": {"$sum": {"$cond": [{"$eq": ["$STATUS", True]}, 1, 0]}},
                    "latest_check_in": {"$max": "$datetime"},
                    "earliest_check_in": {"$min": "$datetime"}
                }
            },
            # Project to reshape the output
            {
                "$project": {
                    "meeting_id": "$_id",
                    "total_check_ins": 1,
                    "unique_users_count": {"$size": "$unique_users"},
                    "successful_check_ins": 1,
                    "latest_check_in": 1,
                    "earliest_check_in": 1,
                    "_id": 0
                }
            },
            # Sort by latest check-in
            {
                "$sort": {"latest_check_in": -1}
            }
        ]
        
        # Execute the aggregation
        result = list(time_stamp_collection.aggregate(pipeline))
        
        # Convert to JSON
        parsed_result = json.loads(json_util.dumps(result))
        
        return {
            "total": len(parsed_result),
            "meetings": parsed_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving meetings: {str(e)}")

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
