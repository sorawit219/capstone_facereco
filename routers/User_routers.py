import logging
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import UploadFile,File,HTTPException
from fastapi.responses import Response
from pymongo import MongoClient
from gridfs import GridFS
import os
import random
import math
import cv2
import pickle
import face_recognition
from bson.binary import Binary
from dotenv import load_dotenv
load_dotenv()


# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection_name = db[os.getenv('COLLECTION_PROFILE')]
fs = GridFS(db)


router = APIRouter(
    prefix="/user",
    tags=['User'],
    responses={404:{
        'message': "User not found"
    }}
)



class User(BaseModel):
    id : str
    name : str
    nickname : str
    email: str
    phone_number:str
    lineID :str
    

def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits



@router.get("/")
def read_root():
    try:
        # Your code here
        return {"message": "Success"}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise



@router.get('/{id}')
async def getObjID_by_id(id:str):
    x = collection_name.find_one({"id":str(id)})
    return x["name"] 

@router.post("/")
async def create_user(user:User):
    x = str(rand_num())
    #check the same id
    while collection_name.find_one({"id": str(x)}):
        x = str(rand_num())
    user_with_picture = User(id=x,name=user.name, nickname=user.nickname,phone_number=user.phone_number,lineID=user.lineID,email=user.email)
    result = collection_name.insert_one(user_with_picture.model_dump())
    if result.acknowledged:
        return {"message": "User created successfully", "user_id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=500, detail="Failed to create user with picture")

@router.delete("/{id}")
async def delete_user (id:str):
    my_query = {"id":str(id)}
    collection_name.delete_one(my_query)
    result = {'msg',f"{id} was delete!!" }
    return result

@router.put("/{id}")
async def update_user(id:str,field_update: str, to_new_value: str):
    x = collection_name.find_one({},{"id":str(id)})
    #search old value
    if x:
    # Retrieve the old value
        old_value_document = collection_name.find_one({"_id": x["_id"]}, {field_update: 1})
        old_value = old_value_document.get(field_update) if old_value_document else None

    # Perform the update
        update_operation = {"$set": {field_update: to_new_value}}
        collection_name.update_one({"_id": x["_id"]}, update_operation)

        result = {'msg': f"Old value: {old_value}. Update successful! New value: {to_new_value}"}
    else:
        result = {'msg': "Document not found."}
    return result


@router.post("/{id}/upload")
async def upload_user_picture(id:str,file : UploadFile=File()):
    try:
        picture_contents = await file.read() #read file
        file_name, file_extension = os.path.splitext(file.filename)
        new_filename = f"{id}{file_extension}"
        with open(new_filename, "wb") as new_file:
            new_file.write(picture_contents)
        collection_user_picture = db[os.getenv('COLLECTION_USER_PICTURE')]
        image_document = {
            "user_id": id,
            "filename": new_filename,
            "file_extension": file_extension,
            "image_data": Binary(picture_contents)
        }
        collection_user_picture.insert_one(image_document)
        new_file.close
        encode_pickel()
        return {"msg":"Upload and Encode Complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")


@router.get("/{id}/getImage")
async def download_user_picture(id:str):
    collection_user_picture = db[os.getenv('COLLECTION_USER_PICTURE')]
    image_document = collection_user_picture.find_one({"user_id": id})
    if image_document:
        return Response(content=image_document["image_data"], media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Image not found")

'''
def findEncodeing(imgLIst):
    encodeList= []
    for img in imgLIst:
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)
        if encode:  # If at least one face encoding is found
            encodeList.append(encode[0])
        else:
            print("⚠️ Warning: No face detected in one image. Skipping.")
    return encodeList


def encode_pickel():
    #import img to the list
    foldermodepath = 'lall_img\img_file'
    pathlis = os.listdir(foldermodepath)
    print(pathlis)
    imgLIst_a = [] #array of img
    studentIds = []
    collection = db["user_picture"]
    image_documents = collection.find()
    for image_document in image_documents:
        filename = image_document["filename"]
        image_data = image_document["image_data"]
        with open(os.path.join(foldermodepath, filename), "wb") as f:
            f.write(image_data)
            imgLIst_a.append(cv2.imread(os.path.join(foldermodepath,filename)))
            studentIds.append(os.path.splitext(filename)[0])#print list numberpath

    f.close()
        
    print(studentIds) #img name not png
    print("Encoding Started...")
    encodeListKnow = findEncodeing(imgLIst_a)
    encodeLIstKnowWithIds = [encodeListKnow,studentIds]
    print("Encode Complete")

    file = open("EncodeFile.p",'wb')
    pickle.dump(encodeLIstKnowWithIds,file)
    file.close()
'''
def findEncodeing(imgLIst, studentIds):
    encodeList = []
    validStudentIds = []  # Store only IDs with valid face encodings

    for img, student_id in zip(imgLIst, studentIds):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)

        if encode:  # If at least one face encoding is found
            encodeList.append(encode[0])
            validStudentIds.append(student_id)  # Only keep IDs for images with faces
        else:
            print(f"⚠️ Warning: No face detected in {student_id}. Skipping.")

    return encodeList, validStudentIds


def encode_pickel():
    # Import images to the list
    foldermodepath = "lall_img/img_file"
    pathlis = os.listdir(foldermodepath)
    print(pathlis)

    imgLIst_a = []  # Array of images
    studentIds = []
    collection = db[os.getenv('COLLECTION_USER_PICTURE')]
    image_documents = collection.find()

    for image_document in image_documents:
        filename = image_document["filename"]
        image_data = image_document["image_data"]
        
        img_path = os.path.join(foldermodepath, filename)
        
        # Save the image from database
        with open(img_path, "wb") as f:
            f.write(image_data)

        # Load the saved image
        img = cv2.imread(img_path)
        if img is None:
            print(f"⚠️ Warning: Unable to read {filename}. Skipping.")
            continue  # Skip this image

        imgLIst_a.append(img)
        studentIds.append(os.path.splitext(filename)[0])  # Extract name without extension

    print(studentIds)  # Print image names
    print("Encoding Started...")

    # Encode images
    encodeListKnow, validStudentIds = findEncodeing(imgLIst_a, studentIds)
    encodeLIstKnowWithIds = [encodeListKnow, validStudentIds]

    print("Encode Complete")

    # Save encodings to file
    with open("EncodeFile.p", "wb") as file:
        pickle.dump(encodeLIstKnowWithIds, file)