from pymongo import MongoClient
from dotenv import load_dotenv
import os
import hashlib

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
    
    # Get a sample QR code hash from the database
    sample_record = collection.find_one({"text": {"$exists": True}})
    
    if sample_record:
        qr_hash = sample_record["text"]
        user_id = sample_record["user_id"]
        
        print(f"Found QR code hash: {qr_hash}")
        print(f"Associated user ID: {user_id}")
        
        # Simulate the QR code lookup process from the websocket endpoint
        print("\nSimulating QR code lookup process...")
        result = collection.find_one({"text": qr_hash})
        
        if result:
            print("✅ QR code found in database")
            print(f"Retrieved user ID: {result['user_id']}")
            
            # Verify the user exists
            user_data = collection.find_one({"user_id": result["user_id"]})
            if user_data:
                print("✅ User found in database")
                
                # Check the name field
                if "name" in user_data:
                    print(f"User name: {user_data['name']} (type: {type(user_data['name']).__name__})")
                    
                    # Test string conversion to ensure no errors
                    try:
                        name_str = str(user_data["name"])
                        print(f"String conversion test: {name_str} (type: {type(name_str).__name__})")
                    except Exception as e:
                        print(f"❌ Error converting name to string: {str(e)}")
                else:
                    print("❌ Name field not found in user data")
            else:
                print(f"❌ User with ID {result['user_id']} not found in database")
        else:
            print("❌ QR code not found in database")
            
        # Test with a non-existent QR code
        fake_hash = "nonexistentqrcodehash1234567890"
        print("\nTesting with non-existent QR code hash...")
        fake_result = collection.find_one({"text": fake_hash})
        
        if fake_result:
            print("Found (unexpected)")
        else:
            print("✅ Non-existent QR code properly returns None")
            
    else:
        print("No QR code records found in the database")

except Exception as e:
    print(f"Error: {str(e)}") 