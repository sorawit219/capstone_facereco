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
timestamp_collection_name = os.getenv('COLLECTION_TIME_STAMP')

print(f"MongoDB URL: {mongo_url}")
print(f"Database Name: {db_name}")
print(f"Timestamp Collection: {timestamp_collection_name}")

try:
    client = MongoClient(mongo_url)
    db = client[db_name]
    timestamp_collection = db[timestamp_collection_name]
    
    # Check connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
    # Check timestamp records
    timestamp_count = timestamp_collection.count_documents({})
    print(f"\nTotal timestamp records: {timestamp_count}")
    
    if timestamp_count > 0:
        # Get recent timestamp records
        recent_records = list(timestamp_collection.find().sort("datetime", -1).limit(3))
        print("\nMost recent timestamp records:")
        for record in recent_records:
            print("-" * 60)
            record_json = json.loads(json_util.dumps(record))
            print(f"User ID: {record.get('user_id', 'Unknown')}")
            print(f"Name: {record.get('name', 'Unknown')}")
            print(f"Meeting ID: {record.get('meeting_id', 'Unknown')}")
            print(f"Status: {record.get('STATUS', False)}")
            print(f"Date/Time: {record_json.get('datetime', {}).get('$date', 'Unknown')}")
    else:
        print("\nNo timestamp records found in the database!")
        
    # Check buffer in code
    print(f"\nCurrent buffer size in code: {len(client['__main__'].get_collection('buffer').estimated_document_count() if client['__main__'].list_collection_names() else 0)}")
    

except Exception as e:
    print(f"MongoDB connection error: {str(e)}") 