import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import firestore

cred = credentials.Certificate("D:\VScode\capstone\serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()




data = {
    
        "first_name" : "Sorawit",
        "last_name" : " Kuhakasemsin",
        "nickname" : "Pat",
        "last_Attendance_time" : "2023-11-11 09:00:00",
        "total_Attendance" : "2",
        "e-mail":"sorawti.pat@gmail.com"
    
}


subcollection_data = {
        "place" : "Mahidol_University",
        "meeting_id": "000435",
        "date" : "2023-11-11",
        "time": "09:00:00",
        "absent":"false"
}


doc_ref = db.collection("user").document("321578")
doc_ref.update({
    "Meeting": subcollection_data
})

#db.collection("user").document("321578").set(data)

print("Document successfully written!")
