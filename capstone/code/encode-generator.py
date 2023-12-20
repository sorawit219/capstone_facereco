import cv2
import face_recognition
import pickle
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

cred = credentials.Certificate("D:\VScode\capstone\serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL': "https://capstone-facerecogniton-default-rtdb.asia-southeast1.firebasedatabase.app/" ,
    'storageBucket' : "capstone-facerecogniton.appspot.com"
})




foldermodepath = 'D:\VScode\capstone\img_'
pathlis = os.listdir(foldermodepath)
print(pathlis)
imgLIst = []
studentIds = []
for path in pathlis:
    imgLIst.append(cv2.imread(os.path.join(foldermodepath,path)))
    print(path)
    studentIds.append(os.path.splitext(path)[0])
    fileName = os.path.join(foldermodepath,path)
    bucket = storage.bucket()
    blob = bucket.blob(fileName)
    blob.upload_from_file(fileName)


    #print(path)
    #print(os.path.splitext(path)[0])
print(studentIds)



def findEncodeing(imgLIst):
    encodeList=[]
    for img in imgLIst:
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)

    return encodeList

print("Encoding Started...")
encodeListKnow = findEncodeing(imgLIst)
encodeLIstKnowWithIds = [encodeListKnow,studentIds]
print("Encode Complete")

file = open("EncodeFile.p",'wb')
pickle.dump(encodeLIstKnowWithIds,file)
file.close()