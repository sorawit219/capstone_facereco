#import numpy as np

from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import StreamingResponse
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
from typing import List
import os
from dotenv import load_dotenv
load_dotenv()



# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection_name = db[os.getenv('COLLECTION_PLACE')]
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
        result = collection_name.insert_one(place.model_dump())
        inserted_id = result.inserted_id
        if result.inserted_id:
            return {"msg": "Create Place Complete", "ID": str(inserted_id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create place")
    except Exception as e:
        # Properly format the error message to be string-friendly
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to create place: {error_msg}")
    
@router.get("/")
async def get_place_id_from_name(name: str):
    try:
        # Fixed query syntax - was incorrectly using {}, {"name": name}
        result = collection_name.find_one({"name": name}, {"_id": 1})
        if result:
            return {"msg": "Found Place!", "ID": str(result["_id"])}
        else:
            raise HTTPException(status_code=404, detail="No place found with the specified name")
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to get place ID: {error_msg}")

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
        # Validate place_id format
        if not ObjectId.is_valid(place_id):
            raise HTTPException(status_code=400, detail="Invalid place ID format")
            
        collection = db["place_picture"]
        image_documents = list(collection.find({"place_id": place_id}))
        
        if not image_documents:
            raise HTTPException(status_code=404, detail="No images found for the specified place ID")
        
        foldermodepath = 'all_img/place_img'
        if not os.path.exists(foldermodepath):
            os.makedirs(foldermodepath)

        file_paths = []
        for image_document in image_documents:
            image_name = image_document["filename"]
            image_data = image_document["image_data"]
            file_path = os.path.join(foldermodepath, f"{place_id}_{image_name}")
            with open(file_path, "wb") as f:
                f.write(image_data)
            file_paths.append(file_path)

        # Return file response for the first image if there are any
        if file_paths:
            return StreamingResponse(open(file_paths[0], "rb"), media_type="image/*")
        else:
            raise HTTPException(status_code=404, detail="No images found after processing")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to download images: {error_msg}")