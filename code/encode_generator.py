import cv2
import pickle
import os
import face_recognition
from pymongo import MongoClient


client = MongoClient("mongodb+srv://admin2:el3OOhw4nt8bH2qa@cluster0.aq1yq2n.mongodb.net/")
db = client["face_ticket"]
collection = db["user_picture"]

def findEncodeing(imgLIst):
    encodeList= []
    for img in imgLIst:
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList


def encode_pickel():
    #import img to the list
    foldermodepath = 'D:\VScode\capstone\img_'
    pathlis = os.listdir(foldermodepath)
    print(pathlis)
    imgLIst_a = [] #array of img
    studentIds = []

    image_documents = collection.find()
    for image_document in image_documents:
        filename = image_document["filename"]
        image_data = image_document["image_data"]
        with open(os.path.join(foldermodepath, filename), "wb") as f:
            f.write(image_data)

    for path in pathlis:
    
        imgLIst_a.append(cv2.imread(os.path.join(foldermodepath,path)))
        studentIds.append(os.path.splitext(path)[0])#print list numberpath

    print(studentIds) #img name not png
    print("Encoding Started...")
    encodeListKnow = findEncodeing(imgLIst_a)
    encodeLIstKnowWithIds = [encodeListKnow,studentIds]
    print("Encode Complete")

    file = open("EncodeFile.p",'wb')
    pickle.dump(encodeLIstKnowWithIds,file)
    file.close()
    
    for filename in os.listdir(foldermodepath):
        file_path = os.path.join(foldermodepath, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)