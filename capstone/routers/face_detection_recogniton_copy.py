import cv2
import pickle
import face_recognition
import numpy as np
import cvzone
import logging
from typing import Union
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(
    prefix="/user",
    tags=['User'],
    responses={404:{
        'message': "User not found"
    }}
)

user_db = {

}


class User(BaseModel):
    first_name : str
    last_name : str
    nickname : str
    #e-mail: str
    phone_number:int
    line_id :str



def face_reco(user_id):
    #Load the encodding file
    cap = cv2.VideoCapture(0)
    cap.set(3,1280)
    cap.set(4,720)
    print("Loading Encode file..")
    file = open("D:\VScode\capstone\code\EncodeFile.p",'rb')
    encodeListKnowWithIds = pickle.load(file)
    file.close()
    encodeListKnow,studentIds = encodeListKnowWithIds
    #print(studentIds)
    print("Encode file Loaded")

    while True:
        succcess, img = cap.read()
        if not succcess:
            break
        imgS = cv2.resize(img,(0,0),None,0.25,0.25)
    
        imgS = cv2.cvtColor(imgS,cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS,faceCurFrame)

        for encodeFace,faceLoc in zip(encodeCurFrame,faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnow,encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnow,encodeFace)

            #print("matches",matches)
            #print("faceDis",faceDis)

            matchIndex = np.argmin(faceDis)
            #print("Match Index",matchIndex)
            face_percent = 1-faceDis[matchIndex]

            #if face_percent >= 0.5:
            #name = 

            if matches[matchIndex]:
                #print("Known Face Detected")            
                #print(studentIds[matchIndex])
                y1,x2,y2,x1 = faceLoc
                y1,x2,y2,x1 = y1*4,x2*4,y2*4,x1
                start_point = (x1,y2-175)
                end_point = (x2+x1,y2+y1)
                cv2.rectangle(img,start_point,end_point,color=(0,0,255),thickness=2)
                id = studentIds[matchIndex]
                print(id)
                if (user_id == id): return True
                else: return False
    
        #img_array = np.array(img)
        #print(img_array.shape)

        #cv2.imshow("Face Attandance",img)
        #cv2.waitKey(1)
        #if cv2.waitKey(1) & 0xFF == ord("q"):
        #    break

        #cap.release()
        #cv2.destroyAllWindows()
        _, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

logging.basicConfig(level=logging.DEBUG)

@router.get("/")
def read_root():
    try:
        # Your code here
        return {"message": "Success"}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise


@router.get('/user/{id}')
def user_by_id(id:int):
    user = user_db[id-1]
    return user

@router.post("/user")
def create_user(user:User):
    user = user_db.append(user)
    return user_db[-1]

@router.delete("/user/{id}")
def delete_user (id:int):
    user = user_db[id-1]
    user_db.pop(id-1)
    result = {'msg',f"{user['name']} was delete!!" }
    return result

#@router.put("/user/{id}")
#def update_user(id: int,user :User):
#    user_db[id-1].update(**user.dict[])
#    result = {'msg': f"Coffee id {id} Update successful!"}
#    return result

@router.get("/user/{id}/video")
def camera_face(id:int,user:User):

    return StreamingResponse(face_reco(id), media_type="multipart/x-mixed-replace; boundary=frame")
