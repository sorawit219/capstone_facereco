from pymongo import MongoClient
from dotenv import load_dotenv
import os
import hashlib
import json

load_dotenv()

def debug_qr_scan(qr_text: str):
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('DATABASE_NAME')]
    collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]
    
    # Create hash of QR code text
    sha256 = hashlib.sha256()
    sha256.update(qr_text.encode('utf-8'))
    qr_hash = sha256.hexdigest()
    
    print("\n=== QR Code Scan Debug Information ===")
    print(f"Input QR Text: {qr_text}")
    print(f"Generated Hash: {qr_hash}")
    
    # Check if QR code exists in database
    result = collection.find_one({"text": qr_hash})
    if result:
        print("\nQR Code Found in Database:")
        print(f"User ID: {result.get('user_id', 'N/A')}")
        print(f"Meeting ID: {result.get('meeting_id', 'N/A')}")
        print(f"Enrolled At: {result.get('enrolled_at', 'N/A')}")
    else:
        print("\nQR Code Not Found in Database")
        print("Possible reasons:")
        print("1. QR code not enrolled")
        print("2. QR code text mismatch")
        print("3. Different hash algorithm used")
        
        # Show similar hashes for debugging
        print("\nSimilar QR Codes in Database:")
        similar_codes = collection.find({"text": {"$regex": qr_hash[:8]}})
        for code in similar_codes:
            print(f"Similar Hash: {code.get('text', 'N/A')}")
            print(f"User ID: {code.get('user_id', 'N/A')}")
            print("-" * 30)

if __name__ == "__main__":
    qr_text = input("Enter QR code text to debug: ")
    debug_qr_scan(qr_text) 