from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pickle

# Load environment variables
load_dotenv()

# Check database connection
print("Checking database connection...")
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db['user_enrollments']

# Get all unique user IDs from database
db_user_ids = collection.distinct("user_id")
print(f"\nUser IDs in database: {db_user_ids}")

# Check EncodeFile
print("\nChecking EncodeFile.p...")
try:
    with open('EncodeFile.p', 'rb') as file:
        encodeListKnowWithIds = pickle.load(file)
        encodeListKnow, UserId = encodeListKnowWithIds
        print(f"User IDs in EncodeFile: {UserId}")
        print(f"Number of encoded faces: {len(encodeListKnow)}")
        print(f"Number of user IDs: {len(UserId)}")
        
        # Check for mismatches
        db_set = set(db_user_ids)
        encode_set = set(UserId)
        missing_in_db = encode_set - db_set
        missing_in_encode = db_set - encode_set
        
        if missing_in_db:
            print(f"\nWarning: These user IDs are in EncodeFile but not in database: {missing_in_db}")
        if missing_in_encode:
            print(f"Warning: These user IDs are in database but not in EncodeFile: {missing_in_encode}")
            
except FileNotFoundError:
    print("EncodeFile.p not found")
except Exception as e:
    print(f"Error reading EncodeFile.p: {str(e)}")

# Close database connection
client.close() 