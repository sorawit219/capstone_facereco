from fastapi import FastAPI
from routers import User_routers as users
#from routers import face_reco_routers
from routers.face_reco_router2 import router as face_reco_router
from routers import Enroll as enroll
from routers import place,meeting,OTPViaSMS
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
def root ():
    return {"Hello":"Capstone FaceReco"}

def config_rounter():
    app.include_router(users.router)
    app.include_router(face_reco_router)
    app.include_router(enroll.router)
    app.include_router(place.router)
    app.include_router(meeting.router)
    app.include_router(OTPViaSMS.router)



config_rounter()
