from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
from bson import json_util

# Load environment variables
load_dotenv()

# Connect to MongoDB
print("Connecting to MongoDB...")
mongo_url = os.getenv('MONGODB_URL')
db_name = os.getenv('DATABASE_NAME')
collection_name = os.getenv('COLLECTION_USER_ENROLLMENT')

print(f"MongoDB URL: {mongo_url}")
print(f"Database Name: {db_name}")
print(f"User Collection: {collection_name}")

try:
    client = MongoClient(mongo_url)
    db = client[db_name]
    collection = db[collection_name]
    
    # Check connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
    # Check for records with 'text' field (QR code hash)
    qr_records = collection.find({"text": {"$exists": True}})
    qr_count = collection.count_documents({"text": {"$exists": True}})
    
    print(f"\nFound {qr_count} records with QR code hashes")
    
    if qr_count > 0:
        # Show all QR code hashes with their associated user_ids
        print("\nQR code hashes and their associated user IDs:")
        print("-" * 60)
        print(f"{'User ID':<15} | {'QR Code Hash'}")
        print("-" * 60)
        
        for record in qr_records:
            user_id = record.get("user_id", "Unknown")
            text_hash = record.get("text", "Missing")
            print(f"{user_id:<15} | {text_hash[:50]}...")
            
        # Check if any record has user_id 1234 (from our previous sample)
        target_user = "1234"
        user_record = collection.find_one({"user_id": target_user})
        
        if user_record:
            print(f"\nRecord for user_id '{target_user}':")
            if "text" in user_record:
                print(f"QR code hash: {user_record['text']}")
            else:
                print("No QR code hash found for this user.")
                print("Available fields:", list(user_record.keys()))
        else:
            print(f"\nNo record found for user_id '{target_user}'")
    else:
        print("\nNo QR codes found in the database!")
        print("\nChecking for alternative QR code storage...")
        
        # Check if QR codes might be stored in 'qrcode' field as binary
        bin_qr_count = collection.count_documents({"qrcode": {"$exists": True}})
        print(f"Found {bin_qr_count} records with 'qrcode' field")
        
        if bin_qr_count > 0:
            sample = collection.find_one({"qrcode": {"$exists": True}})
            print(f"Sample record with 'qrcode' field - user_id: {sample.get('user_id', 'Unknown')}")
            print("You may need to verify the QR code data structure.")

except Exception as e:
    print(f"MongoDB connection error: {str(e)}") 