from pymongo import MongoClient
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

def check_qr_codes():
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('DATABASE_NAME')]
    collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]
    
    # Find all documents with QR codes
    qr_entries = collection.find({'text': {'$exists': True}})
    
    print("\n=== Existing QR Code Entries ===")
    for entry in qr_entries:
        print(f"\nUser ID: {entry.get('user_id', 'N/A')}")
        print(f"QR Code Hash: {entry.get('text', 'N/A')}")
        print(f"Meeting ID: {entry.get('meeting_id', 'N/A')}")
        print("-" * 50)
    
    # Count total entries
    total_entries = collection.count_documents({'text': {'$exists': True}})
    print(f"\nTotal QR Code Entries: {total_entries}")

if __name__ == "__main__":
    check_qr_codes() 