#import numpy as np
import logging
from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile
from pymongo import MongoClient
from gridfs import GridFS
# Initialize MongoDB client
client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
collection_name = db["profiles"]
fs = GridFS(db)


router = APIRouter(
    prefix="/user",
    tags=['User'],
    responses={404:{
        'message': "User not found"
    }}
)



class User(BaseModel):
    id : int
    name : str
    nickname : str
    email: str
    phone_number:str
    lineID :str





@router.get("/")
def read_root():
    try:
        # Your code here
        return {"message": "Success"}
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise



@router.get('/{id}')
def user_by_id(id:int):
    x = collection_name.find_one({},{"id":str(id)})
    return x["id"] 

@router.post("/")
def create_user(user:User):
    x = 
    collection_name.insert_one(user)
    return collection_name.find_one(user)

@router.delete("/{id}")
def delete_user (id:int):
    my_query = {"id":str(id)}
    collection_name.delete_one(my_query)
    result = {'msg',f"{id} was delete!!" }
    return result

@router.put("/{id}")
def update_user(id:int,field_update: str, to_new_value: str):
    x = collection_name.find_one({},{"id":str(id)})
    #search old value
    for y in collection_name.find({"_id": x["_id"]}, {"_id": 0, field_update : 1}):
     y
    
    update_operation = {"$set": {"field_to_update": to_new_value}}
    collection_name.update_one({"_id": x["_id"]}, update_operation)

    result = {'msg': f" {y} Update successful! to {to_new_value}"}
    return result

@router.put("/{id}/upload_file")
async def upload_file(file: UploadFile):
    # Ensure file is not empty
    if not file:
        return {"message": "No file uploaded"}

    # Read file contents
    contents = await file.read()

    # Upload file to GridFS
    file_id = fs.put(contents, filename=file.filename)
    return {"message": "File uploaded successfully"}

