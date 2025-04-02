from pymongo import MongoClient
from dotenv import load_dotenv
import os
import hashlib
from datetime import datetime

load_dotenv()

def enroll_qr_code(user_id: str, meeting_id: str, qr_text: str):
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('DATABASE_NAME')]
    collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]
    
    # Create hash of QR code text
    sha256 = hashlib.sha256()
    sha256.update(qr_text.encode('utf-8'))
    qr_hash = sha256.hexdigest()
    
    # Create enrollment document
    enrollment = {
        "user_id": user_id,
        "meeting_id": meeting_id,
        "text": qr_hash,
        "enrolled_at": datetime.now()
    }
    
    # Check if QR code already exists
    existing = collection.find_one({"text": qr_hash})
    if existing:
        print(f"QR Code already enrolled for user {existing['user_id']}")
        return False
    
    # Insert new enrollment
    result = collection.insert_one(enrollment)
    if result.inserted_id:
        print(f"Successfully enrolled QR code for user {user_id}")
        print(f"QR Code Hash: {qr_hash}")
        return True
    else:
        print("Failed to enroll QR code")
        return False

if __name__ == "__main__":
    # Example usage
    user_id = input("Enter user ID: ")
    meeting_id = input("Enter meeting ID: ")
    qr_text = input("Enter QR code text: ")
    
    enroll_qr_code(user_id, meeting_id, qr_text) 