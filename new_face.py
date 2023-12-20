import cv2
import face_recognition
import pickle
import numpy as np
import cvzone
from typing import Union
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

def generate_frames():
    cap = cv2.VideoCapture(0)  # 0 is the default webcam

    while True:
        success, frame = cap.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def face_reco():
    # Load the encoding file
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)
    print("Loading Encode file..")
    file = open("D:\VScode\capstone\code\EncodeFile.p", 'rb')
    encodeListKnowWithIds = pickle.load(file)
    file.close()
    encodeListKnow, studentIds = encodeListKnowWithIds
    print("Encode file Loaded")

    while True:
        success, img = cap.read()
        if not success:
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
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = x1, y2 - 175, x2 - x1, y2 - y1
                cv2.rectangle(img, bbox, 0)
                id = studentIds[matchIndex]
                print(id)

        _, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/")
def read_root():
    return StreamingResponse(face_reco(), media_type="multipart/x-mixed-replace; boundary=frame")
