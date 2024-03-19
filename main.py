from fastapi import FastAPI
from routers import User_routers as users
#from routers import face_reco_routers
from routers.face_reco_router2 import router as face_reco_router


app = FastAPI()





@app.get("/")
def root ():
    return {"Hello":"Capstone FaceReco"}

def config_rounter():
    app.include_router(users.router)
    app.include_router(face_reco_router)



config_rounter()
