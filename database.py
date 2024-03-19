#import numpy as np
import logging
from fastapi import APIRouter
#from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi import UploadFile
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
# Initialize MongoDB client
client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
collection_name = db["profiles"]
fs = GridFS(db)
x = {
  "id": 1234,
  "name": "Sorawit Kuhakasemsin",
  "nickname": "Pat",
  "email": "sorawit.pat@gmail.com",
  "phone_number": "0910039624",
  "lineID": "sorawitkuha"
}
#collection_name.insert_one(x)
object_id_to_find = ObjectId("65f85ca872f1d9e1a64621c7")
print(collection_name.find_one({"_id":object_id_to_find}))
