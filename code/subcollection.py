import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate('D:\VScode\capstone\serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Define the data for the sub-collection
subcollection_data = {
    "document_1": {
        "field1": "value1",
        "field2": "value2"
    },
    "document_2": {
        "field1": "value3",
        "field2": "value4"
    }
}

# Add a document with a nested sub-collection
doc_ref = db.collection("main_collection").document("document_id")
doc_ref.set({
    "subcollection": subcollection_data
})