from firebase_admin import credentials, initialize_app, storage
import firebase_admin
from firebase_admin import db

cred = credentials.Certificate("D:\VScode\capstone\serviceAccountKey2.json")
firebase_admin.initialize_app(cred,{
    'databaseURL':"https://capstone-facerecogniton-default-rtdb.asia-southeast1.firebasedatabase.app/",
    'storageBucket': 'capstone-facerecogniton.appspot.com'
})

# Put your local file path 
fileName = "img_file\d00001.jpg"
bucket = storage.bucket()
blob = bucket.blob(fileName)
blob.upload_from_filename(fileName)

# Opt : if you want to make public access from the URL
blob.make_public()
print("your file url", blob.public_url)