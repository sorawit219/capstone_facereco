from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId
import asyncio

router = APIRouter()

@router.post("/{meet_id}/upload")
async def upload_meeting_picture(
    meet_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Upload multiple pictures for a meeting using GridFS for better performance
    Returns: {"msg": str, "count": int, "file_ids": List[str]}
    """
    try:
        # Validate meeting ID format
        try:
            meeting_obj_id = ObjectId(meet_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid meeting ID format")

        # Initialize GridFS bucket
        fs = AsyncIOMotorGridFSBucket(db)
        
        uploaded_ids = []
        
        # Process files concurrently
        upload_tasks = []
        for file in files:
            # Read file content asynchronously
            content = await file.read()
            
            # Create upload task
            upload_tasks.append(
                fs.upload_from_stream(
                    filename=file.filename,
                    source=content,
                    metadata={
                        "meeting_id": meet_id,
                        "content_type": file.content_type
                    }
                )
            )
        
        # Execute all uploads concurrently
        results = await asyncio.gather(*upload_tasks)
        uploaded_ids = [str(file_id) for file_id in results]
        
        return {
            "msg": "Upload Complete",
            "count": len(uploaded_ids),
            "file_ids": uploaded_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload pictures: {str(e)}"
        )