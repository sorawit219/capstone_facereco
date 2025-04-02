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
timestamp_collection_name = os.getenv('COLLECTION_TIME_STAMP')

print(f"MongoDB URL: {mongo_url}")
print(f"Database Name: {db_name}")
print(f"User Collection: {collection_name}")
print(f"Timestamp Collection: {timestamp_collection_name}")

try:
    client = MongoClient(mongo_url)
    db = client[db_name]
    collection = db[collection_name]
    timestamp_collection = db[timestamp_collection_name]
    
    # Check connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
    # Check user records
    user_count = collection.count_documents({})
    print(f"\nTotal user records: {user_count}")
    
    if user_count > 0:
        # Get sample user
        sample_user = collection.find_one()
        print("\nSample user record:")
        print(json.dumps(json.loads(json_util.dumps(sample_user)), indent=2))
        
        # Check if user has name field and its type
        if "name" in sample_user:
            print(f"\nName field exists with type: {type(sample_user['name'])}")
            print(f"Name value: {sample_user['name']}")
        else:
            print("\nName field doesn't exist in sample user record")
        
        # Check text field for QR code
        if "text" in sample_user:
            print(f"\nText field exists with type: {type(sample_user['text'])}")
            print(f"Text value: {sample_user['text']}")
        else:
            print("\nText field doesn't exist in sample user record")
            
        # Check user_id field
        if "user_id" in sample_user:
            print(f"\nuser_id field exists with type: {type(sample_user['user_id'])}")
            print(f"user_id value: {sample_user['user_id']}")
        else:
            print("\nuser_id field doesn't exist in sample user record")
    
    # Check timestamp records
    timestamp_count = timestamp_collection.count_documents({})
    print(f"\nTotal timestamp records: {timestamp_count}")
    
    if timestamp_count > 0:
        sample_timestamp = timestamp_collection.find_one()
        print("\nSample timestamp record:")
        print(json.dumps(json.loads(json_util.dumps(sample_timestamp)), indent=2))

except Exception as e:
    print(f"MongoDB connection error: {str(e)}") 