from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pickle
import numpy as np

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db['user_enrollments']

# Get valid user IDs from database
valid_user_ids = set(collection.distinct("user_id"))
print(f"Valid user IDs in database: {valid_user_ids}")

try:
    # Load the current EncodeFile
    with open('EncodeFile.p', 'rb') as file:
        encodeListKnowWithIds = pickle.load(file)
        encodeListKnow, UserId = encodeListKnowWithIds
    
    print(f"\nOriginal number of encoded faces: {len(encodeListKnow)}")
    print(f"Original number of user IDs: {len(UserId)}")
    
    # Create lists to store valid data
    valid_encodings = []
    valid_ids = []
    seen_ids = set()  # Track seen IDs to handle duplicates
    
    # Filter out invalid users and duplicates
    for encoding, user_id in zip(encodeListKnow, UserId):
        if user_id in valid_user_ids and user_id not in seen_ids:
            valid_encodings.append(encoding)
            valid_ids.append(user_id)
            seen_ids.add(user_id)
    
    # Convert lists to numpy arrays
    valid_encodings = np.array(valid_encodings)
    valid_ids = np.array(valid_ids)
    
    # Save the cleaned data
    with open('EncodeFile_cleaned.p', 'wb') as file:
        pickle.dump([valid_encodings, valid_ids], file)
    
    print(f"\nCleaned number of encoded faces: {len(valid_encodings)}")
    print(f"Cleaned number of user IDs: {len(valid_ids)}")
    print(f"Cleaned user IDs: {valid_ids}")
    
    # Backup the original file
    import shutil
    shutil.copy2('EncodeFile.p', 'EncodeFile_backup.p')
    print("\nOriginal file backed up as 'EncodeFile_backup.p'")
    
    # Replace the original file with the cleaned version
    shutil.copy2('EncodeFile_cleaned.p', 'EncodeFile.p')
    print("Original file replaced with cleaned version")
    
    # Remove the temporary cleaned file
    os.remove('EncodeFile_cleaned.p')
    print("Temporary cleaned file removed")

except FileNotFoundError:
    print("EncodeFile.p not found")
except Exception as e:
    print(f"Error processing EncodeFile: {str(e)}")
finally:
    client.close() 