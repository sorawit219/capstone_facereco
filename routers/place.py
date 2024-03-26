#import numpy as np

from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
from typing import List
import os

# Initialize MongoDB client
client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
collection_name = db["place"]
fs = GridFS(db)


router = APIRouter(
    prefix="/place",
    tags=['Place'],
    responses={404:{
        'message': "User not found"
    }}
)



class Place(BaseModel):
    name : str
    user_create: str
    Description :str

@router.post("/")
async def create_place(place: Place):
    try:
        result = collection_name.insert_one(place.dict())
        inserted_id = result.inserted_id
        if result.inserted_id:
            return {"msg": "Create Place Complete", "ID": str(inserted_id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create place")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create place: {e}")
    
@router.get("/")
async def get_place_id(_id: str):
    try:
        
        obj_id = ObjectId(_id)
        result = collection_name.find_one({"_id": obj_id})
        if result:
            result["_id"] = str(result["_id"])
            return {"msg": result}
        else:
            raise HTTPException(status_code=404, detail="No document found with the specified name")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get object ID: {e}")

@router.post("/{place_id}/upload")
async def upload_place_picture(place_id:str,files : List[UploadFile]=File(...)):
    try:
        collection = db["place_picture"]
        file_data = []
        for file in files:
            picture_contents = await file.read()
            file_data.append({
                "place_id": place_id,
                "filename": file.filename,
                "image_data": picture_contents
            })
        result = collection.insert_many(file_data)
        if result:
            return {"msg": "Upload Complete", "count": len(result.inserted_ids)}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload pictures")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload pictures: {e}")

@router.get("/{place_id}/getImage")
async def download_place_picture(place_id: str):
    try:
        collection = db["place_picture"]
        cursor = collection.find({"place_id": place_id})
        image_documents = []
        async for document in cursor:
            image_documents.append(document)
        
        if not image_documents:
            raise HTTPException(status_code=404, detail="No images found for the specified place ID")

        foldermodepath = 'D:\\VScode\\capstone\\place_img'
        if not os.path.exists(foldermodepath):
            os.makedirs(foldermodepath)

        file_paths = []
        for image_document in image_documents:
            image_name = image_document["filename"]
            image_data = image_document["image_data"]
            file_path = os.path.join(foldermodepath, f"{place_id}_{image_name}.png")
            with open(file_path, "wb") as f:
                f.write(image_data)
            file_paths.append(file_path)
        # Return file responses
        return [FileResponse(file_path) for file_path in file_paths]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download images: {e}")