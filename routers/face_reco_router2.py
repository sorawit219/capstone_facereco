from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
import pickle
import cv2
import face_recognition
import numpy as np
import asyncio
router = APIRouter()

# Global variable to track if the camera is running
camera_running = False

async def face_reco():
    global camera_running
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)
    try:
        with open("D:/VScode/capstone/code/EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, studentIds = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
            print("Error: Encoding file not found.")


    while camera_running:
        success, img = cap.read()
        if not success:
            print("Error: Unable to access webcam.")
            break
        

        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
            matchIndex = np.argmin(faceDis)
            face_percent = 1 - faceDis[matchIndex]

            if matches[matchIndex]:
                id = studentIds[matchIndex]
                print("Known Face Detected - ID:", id)
                print(camera_running)

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                bbox = x1, y2-175, x2-x1, y2-y1
                cv2.rectangle(img, bbox, (0, 255, 0), 2)
                cv2.putText(img, str(id), (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            if not camera_running:
                break

        _, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        await asyncio.sleep(0.2)

    cap.release()
    cv2.destroyAllWindows()




@router.get("/video")
async def read_root(background_tasks: BackgroundTasks):
    global camera_running
    if not camera_running:
        camera_running = True
        background_tasks.add_task(face_reco)
    return StreamingResponse(face_reco(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/stop")
async def stop_video():
    global camera_running
    camera_running = False
    return {"message": "Video stream stopped"}
