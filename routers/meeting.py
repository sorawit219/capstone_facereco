#import numpy as np
from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pymongo import MongoClient
from gridfs import GridFS
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()
# from typing import Optional
# from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
# from bson import ObjectId

# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
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
    name: str
    user_create: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    place_id: str
    enrolled_users: List[str] = []
    image: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MeetingResponse(BaseModel):
    id: str
    name: str
    user_create: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    place_id: str
    enrolled_users: List[str] = []
    image: Optional[str] = None


class PaginatedMeetingResponse(BaseModel):
    total: int
    page: int
    page_size: int
    meetings: List[MeetingResponse]


@router.post("/{place_id}")
async def create_meeting(place_id: str, meeting: Meeting):
    try:
        # Set the place_id from the path parameter
        meeting_dict = meeting.dict()
        meeting_dict["place_id"] = place_id
        
        # Insert the meeting document
        result = collection_name.insert_one(meeting_dict)
        inserted_id = result.inserted_id
        
        if result.inserted_id:
            return {"msg": "Create Meeting Complete", "ID": str(inserted_id)}
        else:
            raise HTTPException(status_code=500, detail="Failed to create meeting")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create meeting: {e}")
    
@router.get("/")
async def get_meeting_id_from_name(name: str):
    try:
        result = collection_name.find_one({"name": name}, {"_id": 1})
        if result:
            obj_id = result["_id"]
            return {"msg": "Found Meeting!", "ID": str(obj_id)}
        else:
            raise HTTPException(status_code=404, detail="No meeting found with the specified name")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get meeting ID: {e}")


@router.get("/page/{page}", response_model=PaginatedMeetingResponse)
async def get_paginated_meetings(page: int = 1, page_size: int = 20):
    """
    Get a paginated list of meetings.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of meetings per page
        
    Returns:
        A paginated response with a list of meetings
    """
    try:
        # Ensure page is at least 1
        if page < 1:
            page = 1
            
        # Calculate skip value (how many documents to skip)
        skip = (page - 1) * page_size
        
        # Get total count of meetings
        total_meetings = collection_name.count_documents({})
        
        # Fetch meetings with pagination
        cursor = collection_name.find({}).skip(skip).limit(page_size)
        
        # Convert MongoDB documents to MeetingResponse objects
        meetings = []
        for doc in cursor:
            try:
                # Convert ObjectId to string
                doc["id"] = str(doc.pop("_id"))
                
                # Ensure all required fields exist
                for field in ["name", "user_create", "description", "start_datetime", "end_datetime", "place_id"]:
                    if field not in doc:
                        print(f"Missing required field '{field}' in meeting document: {doc}")
                        # Provide default values for missing fields
                        if field in ["name", "user_create", "description", "place_id"]:
                            doc[field] = ""
                        elif field in ["start_datetime", "end_datetime"]:
                            doc[field] = datetime.now()
                
                meetings.append(MeetingResponse(**doc))
            except Exception as doc_error:
                print(f"Error processing document: {doc}")
                print(f"Error details: {doc_error}")
                # Skip this document and continue with others
                continue
        
        # Return paginated response
        return PaginatedMeetingResponse(
            total=total_meetings,
            page=page,
            page_size=page_size,
            meetings=meetings
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in get_paginated_meetings: {e}")
        print(f"Traceback: {error_traceback}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve paginated meetings: {str(e)}")


@router.post("/{meet_id}/upload")
async def upload_meeting_picture(meet_id: str, files: List[UploadFile]=File(...)):
    try:
        collection = db["meeting_picture"]
        file_data = []
        for file in files:
            picture_contents = await file.read()
            file_data.append({
                "meeting_id": meet_id,
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

@router.get("/{meet_id}/getImage")
async def download_meeting_picture(meet_id: str):
    try:
        collection = db["meeting_picture"]
        image_documents = collection.find({"meeting_id": meet_id})
        
        if not image_documents:
            raise HTTPException(status_code=404, detail="No images found for the specified meeting ID")

        foldermodepath = 'all_img/meeting_img'
        if not os.path.exists(foldermodepath):
            os.makedirs(foldermodepath)

        file_paths = []
        for image_document in image_documents:
            image_name = image_document["filename"]
            image_data = image_document["image_data"]
            file_path = os.path.join(foldermodepath, f"{meet_id}_{image_name}")
            with open(file_path, "wb") as f:
                f.write(image_data)
            file_paths.append(file_path)

        # Return file response for the first image if there are any
        if file_paths:
            return FileResponse(file_paths[0])
        else:
            raise HTTPException(status_code=404, detail="No images found after processing")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download images: {e}")

@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_by_id(meeting_id: str):
    """
    Get detailed information about a specific meeting by its ID.
    
    Args:
        meeting_id: The unique identifier of the meeting
        
    Returns:
        MeetingResponse: The meeting details
    """
    try:
        from bson.objectid import ObjectId
        
        # Try to convert the meeting_id to ObjectId
        try:
            obj_id = ObjectId(meeting_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid meeting ID format")
        
        # Query the database for the meeting
        meeting = collection_name.find_one({"_id": obj_id})
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Convert the _id field to a string for the response
        meeting["id"] = str(meeting.pop("_id"))
        
        # Return the meeting details
        return MeetingResponse(**meeting)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve meeting details: {e}")
    
@router.get("/get_meeting_ids_from_user_id/{user_id}")
async def get_meeting_ids_from_user_id(user_id: str):
    try:
        # ค้นหา meeting ทั้งหมดที่สร้างโดย user นี้
        results = collection_name.find({"user_create_id": user_id})
        
        meeting_list = []
        async for doc in results:
            meeting_list.append({
                "id": str(doc["_id"]),
                "name": doc.get("name", ""),
                "start_datetime": doc.get("start_datetime"),
                "end_datetime": doc.get("end_datetime"),
            })

        if meeting_list:
            return {"msg": f"Found {len(meeting_list)} meetings", "meetings": meeting_list}
        else:
            raise HTTPException(status_code=404, detail="No meetings found for the specified user")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get meetings: {e}")
