from pymongo import MongoClient
from dotenv import load_dotenv
import os
import pickle
import numpy as np
import cv2
import face_recognition
import re

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db['user_enrollments']

# Get valid user IDs from database
valid_user_ids = set(collection.distinct("user_id"))
print(f"Valid user IDs in database: {valid_user_ids}")

# Regular expression to identify MongoDB ObjectID-like strings
object_id_pattern = re.compile(r'^[0-9a-f]{24}$')

try:
    # Load the current EncodeFile
    with open('EncodeFile.p', 'rb') as file:
        loaded_data = pickle.load(file)
    
    # Check the format of the loaded data
    if isinstance(loaded_data, tuple) and len(loaded_data) == 2:
        # Format: (encodeListKnow, UserId)
        encodeListKnow, UserId = loaded_data
        print(f"\nOriginal number of encoded faces: {len(encodeListKnow)}")
        print(f"Original number of user IDs: {len(UserId)}")
        
        # Create lists to store valid data
        valid_encodings = []
        valid_ids = []
        seen_ids = set()  # Track seen IDs to handle duplicates
        invalid_ids = []  # Track invalid IDs for reporting
        
        # Filter out invalid users and duplicates
        for encoding, user_id in zip(encodeListKnow, UserId):
            if user_id in valid_user_ids and user_id not in seen_ids:
                valid_encodings.append(encoding)
                valid_ids.append(user_id)
                seen_ids.add(user_id)
            else:
                invalid_ids.append(user_id)
        
        # Report on invalid IDs
        if invalid_ids:
            print(f"\nFound {len(invalid_ids)} invalid or duplicate user IDs to remove:")
            for invalid_id in invalid_ids:
                if object_id_pattern.match(str(invalid_id)):
                    print(f"Removing ObjectID-like user ID: {invalid_id}")
                else:
                    print(f"Removing invalid user ID: {invalid_id}")
        
        # Convert lists to numpy arrays
        valid_encodings = np.array(valid_encodings)
        valid_ids = np.array(valid_ids)
        
        # Save the cleaned data
        with open('EncodeFile_cleaned.p', 'wb') as file:
            pickle.dump([valid_encodings, valid_ids], file)
        
        print(f"\nCleaned number of encoded faces: {len(valid_encodings)}")
        print(f"Cleaned number of user IDs: {len(valid_ids)}")
        print(f"Cleaned user IDs: {valid_ids}")
        
    else:
        # Format: just a list of encodings
        encodeListKnow = loaded_data
        print(f"\nOriginal number of encoded faces: {len(encodeListKnow)}")
        
        # Get all image files from the directory
        img_dir = 'lall_img/img_file'
        if not os.path.exists(img_dir):
            print(f"Image directory {img_dir} not found")
            raise FileNotFoundError(f"Image directory {img_dir} not found")
            
        img_files = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        print(f"Found {len(img_files)} image files in {img_dir}")
        
        # Create a mapping of user IDs to their face encodings
        user_encodings = {}
        invalid_ids = []  # Track invalid IDs for reporting
        
        # Process each image file
        for img_file in img_files:
            # Extract user ID from filename (assuming format: userID.jpg)
            user_id = os.path.splitext(img_file)[0]
            
            # Skip if user ID is not valid
            if user_id not in valid_user_ids:
                invalid_ids.append(user_id)
                continue
                
            # Load and process the image
            img_path = os.path.join(img_dir, img_file)
            img = cv2.imread(img_path)
            if img is None:
                print(f"Failed to read image: {img_path}")
                continue
                
            # Convert to RGB for face_recognition
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = face_recognition.face_locations(img_rgb)
            if not face_locations:
                print(f"No face detected in image: {img_path}")
                continue
                
            # Get face encodings
            face_encodings = face_recognition.face_encodings(img_rgb, face_locations)
            if not face_encodings:
                print(f"Could not encode face in image: {img_path}")
                continue
                
            # Store the first face encoding for this user
            user_encodings[user_id] = face_encodings[0]
            print(f"Processed valid user: {user_id}")
        
        # Report on invalid IDs
        if invalid_ids:
            print(f"\nFound {len(invalid_ids)} invalid user IDs to remove:")
            for invalid_id in invalid_ids:
                if object_id_pattern.match(str(invalid_id)):
                    print(f"Removing ObjectID-like user ID: {invalid_id}")
                else:
                    print(f"Removing invalid user ID: {invalid_id}")
        
        # Create new lists for valid encodings and IDs
        valid_encodings = []
        valid_ids = []
        
        # Add only valid user encodings
        for user_id in valid_user_ids:
            if user_id in user_encodings:
                valid_encodings.append(user_encodings[user_id])
                valid_ids.append(user_id)
        
        # Convert lists to numpy arrays
        valid_encodings = np.array(valid_encodings)
        valid_ids = np.array(valid_ids)
        
        # Save the cleaned data with user IDs
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

except FileNotFoundError as e:
    print(f"Error: {str(e)}")
except Exception as e:
    print(f"Error processing EncodeFile: {str(e)}")
finally:
    client.close() 