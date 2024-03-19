from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from test_face import face_reco  # Import your face recognition function

router = APIRouter()

@router.get("/video")
async def stream_video(background_tasks: BackgroundTasks):
    background_tasks.add_task(face_reco)
    return StreamingResponse(face_reco(), media_type="multipart/x-mixed-replace; boundary=frame")