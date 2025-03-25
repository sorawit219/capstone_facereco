from fastapi import FastAPI
from routers import User_routers as users
#from routers import face_reco_router2
from routers.face_reco_router2 import router as face_reco_router
from routers import Enroll as enroll
from routers import place,meeting,OTPViaSMS
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # ใส่ URL ของ Angular App
    allow_credentials=True,
    allow_methods=["*"],  # อนุญาตทุก Methods เช่น GET, POST
    allow_headers=["*"],  # อนุญาตทุก Headers
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
