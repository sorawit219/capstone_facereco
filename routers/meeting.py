#import numpy as np
from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pymongo import MongoClient
from gridfs import GridFS
from typing import List
from datetime import datetime
import os

# Initialize MongoDB client
client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
collection_name = db["meeting"]
fs = GridFS(db)


router = APIRouter(
    prefix="/meeting",
    tags=['Meeting'],
    responses={404:{
        'message': "User not found"
    }}
)



class Meeting(BaseModel):
    name : str
    user_create: str
    description :str
    start_datetime:datetime
    end_datetime:datetime
    place_id :str
    enrolled_users: List[str] = []
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@router.post("/{id}")
async def create_meeting(meeting: Meeting,place:str):
    try:
        new_meeting = Meeting(
            name=meeting.name,
            user_create=meeting.user_create,
            description=meeting.description,
            place_id=place,
            start_datetime=meeting.start_datetime,
            end_datetime=meeting.end_datetime,
            enrolled_users= meeting.enrolled_users
        )
        result = collection_name.insert_one(new_meeting.dict())
        inserted_id = result.inserted_id
        if result.inserted_id:
            return {"msg": "Create Meeting Complete", "ID": str(inserted_id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create place")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create place: {e}")
    
@router.get("/")
async def get_meeting_id_from_name(name: str):
    try:
        result = await collection_name.find_one({"name": name}, {"_id": 1})
        if result:
            obj_id = result["_id"]
            return {"msg": "Found Object!!", "ID": str(obj_id)}
        else:
            raise HTTPException(status_code=404, detail="No document found with the specified name")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get object ID: {e}")

@router.post("/{meet_id}/upload")
async def upload_meeting_picture(meet_id:str,files : List[UploadFile]=File(...)):
    try:
        collection = db["meeting_picture"]
        file_data = []
        for file in files:
            picture_contents = await file.read()
            file_data.append({
                "place_id": meet_id,
                "filename": file.filename,
                "image_data": picture_contents
            })
        result = await collection.insert_many(file_data)
        if result:
            return {"msg": "Upload Complete", "count": len(result.inserted_ids)}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload pictures")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload pictures: {e}")

@router.get("/{meet_id}/getImage")
async def download_meeting_picture(meet_id: str):
    try:
        collection = db["meeting_picture"]
        image_documents = await collection.find({"place": meet_id}).to_list(None)
        if not image_documents:
            raise HTTPException(status_code=404, detail="No images found for the specified place ID")

        foldermodepath = 'D:\VScode\capstone\place_img'
        if not os.path.exists(foldermodepath):
            os.makedirs(foldermodepath)

        file_paths = []
        for image_document in image_documents:
            image_name = image_document["filename"]
            image_data = image_document["image_data"]
            file_path = os.path.join(foldermodepath, f"{meet_id}_{image_name}.png")
            with open(file_path, "wb") as f:
                f.write(image_data)
            file_paths.append(file_path)

        # Return file response
        return [FileResponse(file_path) for file_path in file_paths]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download images: {e}")