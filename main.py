from fastapi import FastAPI, WebSocket
from routers import User_routers as users
#from routers import face_reco_router2
from routers.face_reco_router2 import router as face_reco_router
from routers import Enroll as enroll
from routers import place,meeting,OTPViaSMS,dashboard
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include your router
app.include_router(face_reco_router, prefix="")

# If you have an API proxy, add a route for it
@app.post("/api/websocket-proxy/{path:path}")
async def websocket_proxy(path: str):
    return {"message": f"This endpoint should redirect to WebSocket /{path}"}

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
    app.include_router(dashboard.router)

# Add a health check endpoint
@app.get("/health-check")
def health_check():
    return {"status": "healthy"}

# Optional debugging endpoint to check WebSocket routing
@app.websocket("/test-ws")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Connected successfully!")
    await websocket.close()

config_rounter()
