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
        result = collection_name.insert_one(place.model_dump())
        inserted_id = result.inserted_id
        if result.inserted_id:
            return {"msg": "Create Place Complete", "ID": str(inserted_id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create place")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create place: {e}")
    
@router.get("/")
async def get_place_id_from_name(name: str):
    try:
        
        #obj_id = ObjectId(_id)
        result = collection_name.find_one({},{"name": name})
        if result:
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
        if not ObjectId.is_valid(place_id):
            raise HTTPException(status_code=404, detail="No images found for the specified place ID")
        collection = db["place_picture"]
        files = collection.find({"place_id": place_id})
        
        if files.count() == 0:
              raise HTTPException(status_code=404, detail="No files found for this place_id")
        
        async def stream_files():
            for file in files:
                yield file["image_data"]

        # Return a StreamingResponse with the streamed files
        return StreamingResponse(stream_files(), media_type="application/octet-stream")


        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download images: {e}")