import logging
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pymongo import MongoClient
from gridfs import GridFS
import os
import random
import math
import cv2
import pickle
import face_recognition
from dotenv import load_dotenv
import base64
from bson.binary import Binary
load_dotenv()
import uuid
import logging
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection_name = db[os.getenv('COLLECTION_PROFILE')]
fs = GridFS(db)


router = APIRouter(
    prefix="/user",
    tags=['User'],
    responses={404:{
        'message': "User not found"
    }}
)



class User(BaseModel):
    id : str
    name : str
    nickname : str
    email: str
    phone_number:str
    lineID :str

class UserCreate(BaseModel):
    id: str
    name : str
    nickname : str
    email: str
    phone_number:str
    lineID :str
    

class ImageUpload(BaseModel):
    image: str  # base64 string





@router.get("/")
def read_root():
    try:
        # Your code here
        return {"message": "Success"}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise



@router.get('/{id}')
async def getObjID_by_id(id:str):
    x = collection_name.find_one({"id":str(id)})
    return x["name"] 

@router.post("/")
async def create_user(user: UserCreate):
    #check if id already exists
    if collection_name.find_one({"id": user.id}):
        raise HTTPException(status_code=400, detail="User ID already exists")
    
    user_with_picture = User(id=user.id, name=user.name, nickname=user.nickname, phone_number=user.phone_number, lineID=user.lineID, email=user.email)
    result = collection_name.insert_one(user_with_picture.model_dump())
    if result.acknowledged:
        return {"message": "User created successfully", "user_id": user.id}
    else:
        raise HTTPException(status_code=500, detail="Failed to create user with picture")

@router.delete("/{id}")
async def delete_user (id:str):
    my_query = {"id":str(id)}
    collection_name.delete_one(my_query)
    result = {'msg',f"{id} was delete!!" }
    return result

@router.put("/{id}")
async def update_user(id:str,field_update: str, to_new_value: str):
    x = collection_name.find_one({},{"id":str(id)})
    #search old value
    if x:
    # Retrieve the old value
        old_value_document = collection_name.find_one({"_id": x["_id"]}, {field_update: 1})
        old_value = old_value_document.get(field_update) if old_value_document else None

    # Perform the update
        update_operation = {"$set": {field_update: to_new_value}}
        collection_name.update_one({"_id": x["_id"]}, update_operation)

        result = {'msg': f"Old value: {old_value}. Update successful! New value: {to_new_value}"}
    else:
        result = {'msg': "Document not found."}
    return result


@router.post("/{id}/upload")
async def upload_user_picture(id: str, file: UploadFile = File(...)):
    try:
        # Read file contents
        picture_contents = await file.read()
        
        # Get file extension safely
        file_name, file_extension = os.path.splitext(file.filename)
        if not file_name:
            raise ValueError("Filename extraction failed. Check file format.")

        new_filename = f"{id}{file_extension}"
        
        # Ensure directory exists
        foldermodepath = os.getenv('IMAGE_UPLOAD_PATH', 'lall_img/img_file')
        os.makedirs(foldermodepath, exist_ok=True)
        
        # Save file
        filepath = os.path.join(foldermodepath, new_filename)
        with open(filepath, "wb") as new_file:
            new_file.write(picture_contents)
        
        # Verify image can be read and contains a face
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError("Invalid image file")
            
        # Convert to RGB for face detection
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(img_rgb)
        
        if not face_locations:
            raise ValueError("No face detected in the image")
        
        # Store in MongoDB
        image_document = {
            "user_id": id,
            "filename": new_filename,
            "file_extension": file_extension,
            "image_data": Binary(picture_contents)
        }
        collection_user_upload = db["user_picture"]
        collection_user_upload.insert_one(image_document)
        
        # Update face encodings
        encode_pickel()
        
        return {"msg": "Upload and Encode Complete"}
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.get("/{id}/getImage")
async def download_user_picture(id:str):
    collection = db["user_picture"]
    image_document = collection.find_one({"user_id": id})
    image_name = image_document["filename"]
    image_data = image_document["image_data"]
    foldermodepath = 'lall_img\img_file'
    path = f"{foldermodepath}\{image_name}"
    return FileResponse(path)

def findEncodeing(imgLIst):
    encodeList = []
    for img in imgLIst:
        try:
            # Convert to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Find face locations first
            face_locations = face_recognition.face_locations(img)
            
            if not face_locations:
                logger.warning("No face detected in image")
                continue
                
            # Get face encodings
            face_encodings = face_recognition.face_encodings(img, face_locations)
            
            if not face_encodings:
                logger.warning("Could not encode face in image")
                continue
                
            # Use the first face encoding
            encodeList.append(face_encodings[0])
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            continue
            
    return encodeList


def encode_pickel():
    try:
        #import img to the list
        foldermodepath = 'lall_img/img_file'
        pathlis = os.listdir(foldermodepath)
        print(pathlis)
        imgLIst_a = [] #array of img
        studentIds = []
        collection = db["user_picture"]
        image_documents = collection.find()
        
        for image_document in image_documents:
            try:
                filename = image_document["filename"]
                image_data = image_document["image_data"]
                
                # Save image to file
                filepath = os.path.join(foldermodepath, filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                
                # Read image with OpenCV
                img = cv2.imread(filepath)
                if img is None:
                    logger.error(f"Failed to read image: {filename}")
                    continue
                    
                imgLIst_a.append(img)
                studentIds.append(os.path.splitext(filename)[0])
                
            except Exception as e:
                logger.error(f"Error processing document {filename}: {str(e)}")
                continue
        
        if not imgLIst_a:
            logger.warning("No valid images found to encode")
            return
            
        print(studentIds)
        print("Encoding Started...")
        encodeListKnow = findEncodeing(imgLIst_a)
        
        if not encodeListKnow:
            logger.warning("No face encodings were generated")
            return
            
        encodeLIstKnowWithIds = [encodeListKnow, studentIds]
        print("Encode Complete")

        # Save encodings
        with open("EncodeFile.p", 'wb') as file:
            pickle.dump(encodeLIstKnowWithIds, file)
            
    except Exception as e:
        logger.error(f"Error in encode_pickel: {str(e)}")
        raise
