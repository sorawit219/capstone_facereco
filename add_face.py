import cv2
import face_recognition
import pickle
import numpy as np
from pymongo import MongoClient
from dotenv import load_dotenv
import os

def add_face_encoding(user_id):
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return False
    
    print("\nPress 'c' to capture image when ready")
    print("Press 'q' to quit without capturing")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break
            
        # Display the frame
        cv2.imshow('Capture Face', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\nQuitting without capture")
            break
        elif key == ord('c'):
            # Try to detect and encode face
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                print("\nNo face detected. Please try again.")
                continue
                
            if len(face_locations) > 1:
                print("\nMultiple faces detected. Please ensure only one face is in frame.")
                continue
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
            
            # Load existing encodings
            try:
                with open('EncodeFile.p', 'rb') as file:
                    encodeListKnowWithIds = pickle.load(file)
                    encodeListKnow, UserId = encodeListKnowWithIds
            except FileNotFoundError:
                encodeListKnow = np.array([])
                UserId = np.array([])
            
            # Add new encoding
            if len(encodeListKnow) == 0:
                encodeListKnow = np.array([face_encoding])
                UserId = np.array([user_id])
            else:
                encodeListKnow = np.vstack([encodeListKnow, face_encoding])
                UserId = np.append(UserId, user_id)
            
            # Save updated encodings
            with open('EncodeFile.p', 'wb') as file:
                pickle.dump([encodeListKnow, UserId], file)
            
            print(f"\nFace encoded and saved for user {user_id}")
            break
    
    # Release webcam and close windows
    cap.release()
    cv2.destroyAllWindows()
    return True

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Connect to MongoDB
    client = MongoClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('DATABASE_NAME')]
    collection = db['user_enrollments']
    
    # Get user IDs from database
    valid_user_ids = set(collection.distinct("user_id"))
    
    # Load current EncodeFile
    try:
        with open('EncodeFile.p', 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            _, UserId = encodeListKnowWithIds
            encoded_ids = set(UserId)
    except FileNotFoundError:
        encoded_ids = set()
    
    # Find users without face encodings
    missing_users = valid_user_ids - encoded_ids
    
    if not missing_users:
        print("All users in database already have face encodings")
    else:
        print("\nUsers missing face encodings:")
        for user_id in missing_users:
            print(f"- {user_id}")
        
        for user_id in missing_users:
            print(f"\nProcessing user: {user_id}")
            if add_face_encoding(user_id):
                print(f"Successfully added face encoding for {user_id}")
            else:
                print(f"Failed to add face encoding for {user_id}")
    
    client.close() 