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
import httpx
from routers.utils.qr_utils import process_qr_data
# install

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]
time_stamp_collection = db[os.getenv('COLLECTION_TIME_STAMP')]  # Use consistent environment variable

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
    print("QR+OTP WebSocket connected!")
    
    # Get meeting from query parameters
    meeting = websocket.query_params.get("meeting", "default_meeting")
    print(f"Meeting ID: {meeting}")
    
    string_hash = None
    otp_sent_users = set()
    
    try:
        while True:
            base64_data = await websocket.receive_text()  # Receive base64 image data without header
            
            # Log the start of processing a new frame
            print(f"Received frame data: length={len(base64_data)}")
            
            if not base64_data or base64_data in ["null", "undefined"]:
                await websocket.send_json({"error": "Empty image data received"})
                continue
            
            # Try to convert Base64 to OpenCV Image
            try:
                # The frontend already removed the header, so we don't need to split
                # Add padding if needed (base64 needs to be divisible by 4)
                padded_data = base64_data
                padding_needed = len(padded_data) % 4
                if padding_needed:
                    padded_data += '=' * (4 - padding_needed)
                    print(f"Added {4 - padding_needed} '=' padding characters")
                
                # Try to decode the base64 image
                try:
                    img_data = base64.b64decode(padded_data)
                    print(f"Successfully decoded base64 data: {len(img_data)} bytes")
                except Exception as e:
                    print(f"Base64 decode error: {e}")
                    # Try adding the header and see if that helps
                    try:
                        padded_data_with_header = "data:image/jpeg;base64," + padded_data
                        img_data = base64.b64decode(padded_data.split(",", 1)[1] if "," in padded_data_with_header else padded_data)
                        print("Successfully decoded after header manipulation")
                    except Exception as inner_e:
                        print(f"Second decode attempt failed: {inner_e}")
                        await websocket.send_json({"error": f"Invalid base64 data: {str(e)}"})
                        continue
                
                np_arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if img is None:
                    print("Failed to decode image from binary data")
                    await websocket.send_json({"error": "Could not decode image data"})
                    continue
                
                print(f"Successfully decoded image: {img.shape}")
                
                # Decode QR codes from the image
                decoded_objects = decode(img)
                
                if not decoded_objects:
                    # No QR code found in the image
                    print("No QR codes detected in the image")
                    await websocket.send_json({"msg": "No QR code detected", "status": False})
                    continue
                
                print(f"Found {len(decoded_objects)} QR codes in image")
                
                # Process the decoded QR code content (not the image data)
                qr_code_text = decoded_objects[0].data.decode('utf-8')
                current_time = datetime.now()
                
                print(f"Decoded QR Text: {qr_code_text[:30]}...")
                
                # Process using our utility function
                string_hash = process_qr_data(qr_code_text)
                
                # Log the hash for debugging
                print(f"SHA256 Hash: {string_hash}")
                
                # Search the database for the QR code hash
                print(f"Searching for QR hash: {string_hash}")
                result = collection.find_one({"text": string_hash})
                
                # Debug: If not found, check some samples
                if result is None:
                    print(f"Hash not found. Checking for similar hashes in database...")
                    sample_entries = list(collection.find({}, {"text": 1}).limit(3))
                    for entry in sample_entries:
                        if "text" in entry:
                            print(f"Sample hash in DB: {entry['text']}")
                    
                    sample_qr_entries = list(collection.find({"text": {"$exists": True}}).limit(5))
                    print(f"Found {len(sample_qr_entries)} entries with 'text' field")
                else:
                    print(f"Found matching hash in database for user ID: {result['user_id']}")
                
                # Process the result
                if result is None:
                    status = False
                    user_id = None
                    name = "Unknown"
                    msg = "QR Code not found in database"
                else:
                    user_id = str(result["user_id"])  # Convert user_id to string
                    user_data = collection.find_one({"user_id": user_id})
                    if user_data and "name" in user_data:
                        # Ensure name is a string type
                        name = str(user_data["name"]) if user_data["name"] is not None else "Unknown"
                    else:
                        name = "Unknown"
                    
                    status = True
                    msg = f"OTP sent to user {user_id}"
                    
                    if user_id not in otp_sent_users:
                        otp_sent_users.add(user_id)
                        print(f"Sending OTP to user {user_id}")
                        otp = await send_otp(user_id)  # ส่ง OTP
                        if otp:
                            print("OTP sent successfully")
                        else:
                            print("Failed to send OTP")
                
                # Record timestamp
                document = {
                    "user_id": user_id if user_id else "Unknown",
                    "name": name,
                    "meeting_id": meeting,
                    "OTP": True if user_id else False,
                    "STATUS": status,
                    "datetime": current_time
                }

                if status:
                    # Insert individual record immediately rather than buffering
                    time_stamp_collection.insert_one(document)
                    print(f"Recorded timestamp for user {user_id}")

                # Add to buffer for batch processing if needed for analytics
                buffer_doc = document.copy()  # Create a copy for the buffer
                buffer.append(buffer_doc)

                if len(buffer) >= BUFFER_LIMIT:
                    try:
                        # Use the helper function to safely flush buffer
                        inserted_count = flush_buffer_to_db(buffer)
                        print(f"Flushed {inserted_count} records to database")
                        buffer.clear()  # Clear buffer after flushing
                    except Exception as e:
                        print(f"Error flushing buffer: {e}")
                        buffer.clear()  # Clear buffer even if insert fails
                
                # Create a JSON-safe copy of the document with datetime as a string
                json_safe_document = document.copy()
                json_safe_document["datetime"] = document["datetime"].isoformat()

                # Convert the document to a JSON-serializable format using json_util
                serializable_timestamp = json.loads(json_util.dumps(json_safe_document))
                
                print(f"Sending response to client: status={status}, msg={msg}")
                await websocket.send_json({"msg": msg, "status": status, "timestamp": serializable_timestamp})
                
            except Exception as e:
                print(f"Error processing image: {str(e)}")
                print(f"Error details: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                await websocket.send_json({"error": f"Error processing image: {str(e)}"})

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await websocket.send_json({"error": str(e)})
    finally:
        print("WebSocket connection closed")
        await websocket.close()

# async def read_qr(websocket: WebSocket):
#     string_hash = None
#     await websocket.accept()
#     otp_sent_users = set()
#     try:
#         while True:
#             qr_data = await websocket.receive_text()  # รับข้อมูล QR Code
#             sha256 = hashlib.sha256()
#             sha256.update(qr_data.encode('utf-8'))
#             string_hash = sha256.hexdigest()

#             # ค้นหา QR Code ในฐานข้อมูล
#             result = collection.find_one({"text": string_hash})
#             if result:
#                 user_id = result["user_id"]                
#                 if user_id not in otp_sent_users:
#                     otp_sent_users.add(user_id)
#                     otp = send_otp(user_id)  # ส่ง OTP
#                     await websocket.send_json({"msg":"OTP sent to user {user_id}","status":True})
#             else:
#                 await websocket.send_json({"msg":"QR Code not found in database","status":False})

#     except WebSocketDisconnect:
#         print("WebSocket Disconnected")
#     except Exception as e:
#         print(f"Error: {e}")
#         await websocket.send_json({"error": str(e)})
#     finally:
#         await websocket.close()
# async def read_qr(websocket: WebSocket):
#     await websocket.accept()
#     # Skip the verification step until we get the connection working
#     # if not await verify_connection(websocket):
#     #     await websocket.close(code=1008)  # Policy Violation
#     #     return
    
#     # Get meeting from query parameters
#     meeting = websocket.query_params.get("meeting", "default_meeting")
    
#     string_hash = None
#     otp_sent_users = set()
#     try:
#         while True:
#             qr_data = await websocket.receive_text()  # รับข้อมูล QR Code
#             current_time = datetime.now()
#             sha256 = hashlib.sha256()
#             sha256.update(qr_data.encode('utf-8'))
#             string_hash = sha256.hexdigest()

#             # ค้นหา QR Code ในฐานข้อมูล
#             result = collection.find_one({"text": string_hash})
#             status = False
#             user_id = None
#             name = "Unknown"
#             msg = "QR Code not found in database"
            
#             if result:
#                 user_id = result["user_id"]
#                 user_data = collection.find_one({"user_id": user_id})
#                 if user_data and "name" in user_data:
#                     name = user_data["name"]
                
#                 status = True
#                 msg = f"OTP sent to user {user_id}"
                
#                 if user_id not in otp_sent_users:
#                     otp_sent_users.add(user_id)
#                     otp = await send_otp(user_id)  # ส่ง OTP
            
#             # Record timestamp
#             document = {
#                 "user_id": user_id if user_id else "Unknown",
#                 "name": name,
#                 "meeting_id": meeting,
#                 "OTP": True if user_id else False,
#                 "STATUS": status,
#                 "datetime": current_time
#             }

#             # Save to database
#             if status:
#                 time_stamp_collection.insert_one(document)

#             global buffer
#             buffer.append(document)

#             if len(buffer) >= BUFFER_LIMIT:
#                 time_stamp_collection.insert_many(buffer)
#                 buffer.clear()
            
#             await websocket.send_json({
#                 "msg": msg, 
#                 "status": status, 
#                 "timestamp": document,
#                 "user": {
#                     "id": user_id,
#                     "name": name
#                 } if user_id else None
#             })

#     except WebSocketDisconnect:
#         print("WebSocket Disconnected")
#     except Exception as e:
#         print(f"Error: {e}")
#         await websocket.send_json({"error": str(e)})
#     finally:
#         await websocket.close()


#read face-recognition and sent otp
@router.websocket("/face_reco+otp")
async def face_reco(websocket: WebSocket):    
    await websocket.accept()
    print("WebSocket Connected!")

    # Get meeting from query parameters
    meeting = websocket.query_params.get("meeting", "default_meeting")
    print(f"Face+OTP WebSocket connected for meeting: {meeting}")

    global encodeListKnow
    otp_sent_users = set()  # Track users who've received OTPs
        
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
            current_time = datetime.now()  # Add current time for timestamp
            
            # Convert Base64 to OpenCV Image
            try:
                header, encoded = frame_data.split(",", 1)            
                img_data = base64.b64decode(encoded)
                np_arr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            except Exception as e:
                await websocket.send_json({"error": "Invalid image data", "details": str(e)})
                continue

            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_json({
                    "status": "no_face",
                    "message": "No face detected",
                    "action": "continue"
                })
                continue
                
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)
            if not encodeCurFrame:
                await websocket.send_json({
                    "status": "no_encoding",
                    "message": "Could not extract face features",
                    "action": "continue"
                })
                continue

            status = False
            recognized_id = None
            name = "Unknown"
            
            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                if not any(matches):
                    await websocket.send_json({
                        "status": "unrecognized",
                        "message": "Face not recognized",
                        "action": "continue"
                    })
                    continue

                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    user_data = collection.find_one({"user_id": recognized_id})
                    if not user_data:
                        await websocket.send_json({
                            "status": "error",
                            "message": "User data not found",
                            "action": "continue"
                        })
                        continue
                        
                    name = str(user_data["name"]) if user_data and "name" in user_data else "Unknown"
                    status = True
                    
                    # Draw face rectangle
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    
                    # Record timestamp when face is recognized
                    document = {
                        "user_id": recognized_id,
                        "name": name,
                        "meeting_id": meeting,
                        "OTP": False,  # OTP not yet verified
                        "STATUS": status,
                        "datetime": current_time
                    }
                    
                    # Insert individual record immediately
                    try:
                        time_stamp_collection.insert_one(document)
                        print(f"Recorded face recognition timestamp for user {recognized_id}")
                    except Exception as e:
                        print(f"Error recording timestamp: {e}")
                    
                    # Add to buffer for batch processing if needed
                    global buffer
                    buffer_doc = document.copy()
                    buffer.append(buffer_doc)
                    
                    if len(buffer) >= BUFFER_LIMIT:
                        try:
                            # Use the helper function to safely flush buffer
                            inserted_count = flush_buffer_to_db(buffer)
                            print(f"Flushed {inserted_count} records to database")
                            buffer.clear()  # Clear buffer after flushing
                        except Exception as e:
                            print(f"Error flushing buffer: {e}")
                            buffer.clear()  # Clear buffer even if insert fails
                    
                    # Handle OTP
                    if recognized_id not in otp_sent_users:
                        otp = await send_otp(recognized_id)
                        if otp:  # If OTP was successfully sent
                            otp_sent_users.add(recognized_id)
                            await websocket.send_json({
                                "status": "otp_sent",
                                "message": f"OTP sent to user {recognized_id}",
                                "user_id": recognized_id,
                                "name": name,
                                "action": "verify_otp"
                            })
                        else:
                            await websocket.send_json({
                                "status": "error",
                                "message": "Failed to send OTP",
                                "action": "continue"
                            })
                    else:
                        await websocket.send_json({
                            "status": "pending_verification",
                            "message": f"OTP already sent to {name}",
                            "user_id": recognized_id,
                            "action": "verify_otp"
                        })

    except WebSocketDisconnect:
        print("WebSocket Disconnected")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await websocket.send_json({
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e)
        })
    finally:
        print("Face+OTP WebSocket connection closed")
        await websocket.close()

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
            # Only log and process if QR codes were actually found
            if decoded_objects:
                for obj in decoded_objects:
                    qr_code_text = obj.data.decode("utf-8")
                    string_hash = process_qr_data(qr_code_text)
                    # Log the hash only when a QR code is detected
                    print(f"SHA256 Hash: {string_hash}")
                    break  # Just use the first QR code detected
            
            status = False
            
            #ตรวจจับใบหน้า
            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
            face_location = face_recognition.face_locations(imgS)
            if not face_location:
                await websocket.send_json({"msg": "No face detected", "status": status})
                continue
            encodeCurFrame = face_recognition.face_encodings(imgS, face_location)

            recognized_id = None
            name = "Unknown"
            for encodeFace, faceLoc in zip(encodeCurFrame, face_location):
                matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
                if not any(matches):  # ไม่มีใบหน้าตรงกัน
                    await websocket.send_json({"msg": "Face not match in ListKnow", "status": status})
                    continue
                faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
                matchIndex = np.argmin(faceDis)

                if matches[matchIndex]:
                    recognized_id = UserId[matchIndex]
                    print(f"Known Face Detected - ID:{recognized_id}")
                    user_data = collection.find_one({"user_id": recognized_id})
                    name = str(user_data["name"]) if user_data and "name" in user_data else "Unknown"
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
                try:
                    text_id = result["user_id"]
                    if text_id == recognized_id:
                        status = True
                        msg = f" User {recognized_id} found you have enroll this meeting Please Check in"
                    else:
                        msg = " QR Code not match User Or not enroll in this meeting "
                except:
                    msg = "QR Code not found in database"
            elif recognized_id:
                msg = f"User {recognized_id} Pass! But not have QR-code.Plase scan QR-code"

            document = {
                "user_id": recognized_id if recognized_id else "Unknown",
                "name": name,
                "meeting_id": meeting,
                "OTP": None,
                "STATUS": status,
                "datetime": current_time
            }

            if status:
                # Insert individual record immediately
                time_stamp_collection.insert_one(document)
                print(f"Recorded timestamp for user {recognized_id}")

            # Add to buffer for batch processing if needed for analytics
            buffer_doc = document.copy()  # Create a copy for the buffer
            buffer.append(buffer_doc)

            if len(buffer) >= BUFFER_LIMIT:
                try:
                    # Use the helper function to safely flush buffer
                    inserted_count = flush_buffer_to_db(buffer)
                    print(f"Flushed {inserted_count} records to database")
                    buffer.clear()  # Clear buffer after flushing
                except Exception as e:
                    print(f"Error flushing buffer: {e}")
                    buffer.clear()  # Clear buffer even if insert fails
            
            # Create a JSON-safe copy of the document with datetime as a string
            json_safe_document = document.copy()
            json_safe_document["datetime"] = document["datetime"].isoformat()
            
            #ส่งผลลัพธ์กลับไปยัง Frontend
            await websocket.send_json({
                "msg": msg, 
                "status": status,
                "user": {
                    "id": recognized_id,
                    "name": name
                } if recognized_id else None
            })

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
    try:
        # Make HTTP request to OTPViaSMS endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://localhost:8000/otp/send", params={"id": id})
            if response.status_code == 200:
                print(f"OTP sent successfully to user {id}")
                return True
            else:
                print(f"Failed to send OTP to user {id}. Status code: {response.status_code}")
                return False
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        return False
    # url = "https://api-v2.thaibulksms.com/sms"
    # collection_name = db["profiles"]
    # user_profile = collection_name.find_one({"id":str(id)})
    # rand = rand_num()
    # message = "Your OTP is "+str(rand)
    # payload = {
    #     "msisdn": user_profile["phone_number"] ,
    #     "message": message,
    #     "sender": "Demo",
    #     # FaceTicket
    #     # "force" : "corporate",
    # }
    # headers = {
    #     "accept": "application/json",
    #     "content-type": "application/x-www-form-urlencoded",
    #     "authorization": os.getenv('API_KEY')
    # }

    # #have 3 user token free per api key for this api therefore can sent 3 time use carefully if want to sent more pay it

    # response = requests.post(url, data=payload, headers=headers)
    # collection_store_otp = db[os.getenv('COLLECTION_USER_OTP')]
    # x = datetime.now()
    # document = {
    #     "user_id" : id,
    #     "OTP" : str(rand),
    #     "datetime" : x
    # }
    # check = collection_store_otp.insert_one(document) #save otp to database
    # print(response.text)
    # return check

# Helper function to safely flush buffer to database
def flush_buffer_to_db(buffer_data):
    """
    Safely flush buffer data to MongoDB, handling any potential duplicate key errors.
    
    Args:
        buffer_data: List of documents to insert
    
    Returns:
        int: Number of successfully inserted documents
    """
    if not buffer_data:
        return 0
        
    # Make copies to avoid modifying the original data
    docs_to_insert = []
    for doc in buffer_data:
        doc_copy = doc.copy()
        # Remove _id if present to let MongoDB generate a new one
        if '_id' in doc_copy:
            del doc_copy['_id']
        docs_to_insert.append(doc_copy)
    
    try:
        # Try bulk insert
        result = time_stamp_collection.insert_many(docs_to_insert)
        return len(result.inserted_ids)
    except Exception as e:
        print(f"Bulk insert failed: {e}")
        
        # If bulk insert fails, try one by one
        success_count = 0
        for doc in docs_to_insert:
            try:
                time_stamp_collection.insert_one(doc)
                success_count += 1
            except Exception as inner_e:
                print(f"Individual insert failed: {inner_e}")
        
        return success_count
