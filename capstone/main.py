import cv2
from fastapi.responses import StreamingResponse
from fastapi import FastAPI
from routers import face_detection_recogniton_copy as users

app = FastAPI()

@app.get("/")
def root ():
    return {"Hello":"Capstone FaceReco"}

def config_rounter():
    app.include_router(users.router)

config_rounter()
