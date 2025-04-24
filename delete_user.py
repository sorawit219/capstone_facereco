import os
import pickle
import cv2
import face_recognition
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize MongoDB client
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection_name = db[os.getenv('COLLECTION_PROFILE')]
user_picture_collection = db["user_picture"]

def delete_user(user_id):
    try:
        # 1. Delete from main user collection
        result = collection_name.delete_one({"id": str(user_id)})
        if result.deleted_count == 0:
            logger.warning(f"User {user_id} not found in main collection")
        
        # 2. Delete from user_picture collection
        picture_result = user_picture_collection.delete_one({"user_id": str(user_id)})
        if picture_result.deleted_count == 0:
            logger.warning(f"User {user_id} not found in picture collection")
        
        # 3. Delete the image file if it exists
        image_path = os.path.join('lall_img', 'img_file', f"{user_id}.jpg")
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Deleted image file: {image_path}")
        
        # 4. Update face encodings
        update_face_encodings()
        
        return True, "User deleted successfully"
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return False, str(e)

def update_face_encodings():
    try:
        # Get all images from the directory
        foldermodepath = 'lall_img/img_file'
        if not os.path.exists(foldermodepath):
            os.makedirs(foldermodepath)
            
        pathlist = os.listdir(foldermodepath)
        imgList = []
        studentIds = []
        
        # Process each image
        for path in pathlist:
            imgPath = os.path.join(foldermodepath, path)
            img = cv2.imread(imgPath)
            if img is not None:
                imgList.append(img)
                studentIds.append(os.path.splitext(path)[0])
        
        # Find encodings
        encodeList = []
        for img in imgList:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(img)
            if face_locations:
                face_encodings = face_recognition.face_encodings(img, face_locations)
                if face_encodings:
                    encodeList.append(face_encodings[0])
        
        # Save updated encodings
        with open('EncodeFile.p', 'wb') as f:
            pickle.dump(encodeList, f)
            
        logger.info("Face encodings updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating face encodings: {str(e)}")
        raise

if __name__ == "__main__":
    user_id = "k3hCWwwICRWUlnkoKu4TBT8m2lp2"
    success, message = delete_user(user_id)
    print(message) 