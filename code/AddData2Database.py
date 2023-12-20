import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("D:\VScode\capstone\serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL':"https://capstone-facerecogniton-default-rtdb.asia-southeast1.firebasedatabase.app/",
    'storageBucket' : "capstone-facerecogniton.appspot.com"
})

ref = db.reference('User')

data = {
    "321568" :{
        "first_name" : "Sorawit",
        "last_name" : " Kuhakasemsin",
        "nickname" : "Pat",
        "last_Attendance_time" : "2023-11-11 09:00:00",
        "total_Attendance" : "2",
        "e-mail":"sorawti.pat@gmail.com"
    }
}

for key,value in data.items():
    ref.child(key).set(value)