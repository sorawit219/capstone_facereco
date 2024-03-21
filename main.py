from fastapi import FastAPI
from routers import User_routers as users
#from routers import face_reco_routers
from routers.face_reco_router2 import router as face_reco_router
from routers import Enroll as enroll
from routers import place,meeting

app = FastAPI()





@app.get("/")
def root ():
    return {"Hello":"Capstone FaceReco"}

def config_rounter():
    app.include_router(users.router)
    app.include_router(face_reco_router)
    app.include_router(enroll.router)
    app.include_router(place.router)
    app.include_router(meeting.router)


config_rounter()
