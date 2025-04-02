import cv2
from pyzbar.pyzbar import decode
import hashlib
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import numpy as np
from bson import ObjectId
import base64
import io
from datetime import datetime

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URL'))
db = client[os.getenv('DATABASE_NAME')]
collection = db[os.getenv('COLLECTION_USER_ENROLLMENT')]  # For storing user QR codes
qr_collection = db["user_enrollments"]  # Collection for QR code pictures

def register_qr_code():
    print("=== QR Code Registration Tool ===")
    print("Press 'q' to quit, 's' to save a detected QR code")
    print("Press 'd' to display existing QR codes from database")
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    qr_detected = False
    qr_code_text = None
    qr_hash = None
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break
        
        # Look for QR codes
        decoded_objects = decode(frame)
        
        # If QR code is found
        if decoded_objects:
            for obj in decoded_objects:
                # Get QR code data
                qr_code_text = obj.data.decode("utf-8")
                
                # Compute hash
                sha256 = hashlib.sha256()
                sha256.update(qr_code_text.encode("utf-8"))
                qr_hash = sha256.hexdigest()
                
                # Draw rectangle around QR code
                points = obj.polygon
                if len(points) > 4:
                    hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                    cv2.polylines(frame, [hull], True, (0, 255, 0), 3)
                else:
                    pts = np.array([point for point in points], dtype=np.int32)
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
                
                # Add text
                cv2.putText(frame, f"QR: {qr_code_text[:15]}...", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Press 's' to save", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                qr_detected = True
        else:
            qr_detected = False
            qr_code_text = None
            qr_hash = None
            
        # Display the frame
        cv2.imshow("QR Code Registration", frame)
        
        # Check for key presses
        key = cv2.waitKey(1) & 0xFF
        
        # 'q' to quit
        if key == ord('q'):
            break
            
        # 'd' to display QR codes from database
        if key == ord('d'):
            display_db_qr_codes()
            
        # 's' to save if QR code is detected
        if key == ord('s') and qr_detected:
            # Ask for user ID and meeting ID
            cap.release()  # Temporarily release camera to allow console input
            user_id = input("Enter user ID to associate with this QR code: ")
            meet_id = input("Enter meeting ID to associate with this QR code: ")
            
            # Save to database
            try:
                # First check if QR code already exists
                existing = collection.find_one({"text": qr_hash})
                if existing:
                    print(f"This QR code is already registered to user ID: {existing['user_id']}")
                else:
                    # Save QR code image
                    # Crop the QR code region if possible
                    if len(points) >= 4:
                        x_coords = [p.x for p in points]
                        y_coords = [p.y for p in points]
                        min_x, max_x = min(x_coords), max(x_coords)
                        min_y, max_y = min(y_coords), max(y_coords)
                        
                        # Add padding
                        padding = 10
                        min_x = max(0, min_x - padding)
                        min_y = max(0, min_y - padding)
                        max_x = min(frame.shape[1], max_x + padding)
                        max_y = min(frame.shape[0], max_y + padding)
                        
                        qr_image = frame[min_y:max_y, min_x:max_x]
                    else:
                        qr_image = frame
                    
                    # Convert image to binary
                    _, buffer = cv2.imencode('.png', qr_image)
                    binary_image = buffer.tobytes()
                    
                    # Convert binary to base64 string for MongoDB storage
                    base64_str = base64.b64encode(binary_image).decode('utf-8')
                    
                    # Get current timestamp
                    current_time = datetime.now()
                    
                    # Create QR code document in the requested format
                    qr_doc = {
                        "meet_id": meet_id,
                        "user_id": user_id,
                        "date_time": current_time,
                        "qrcode": {
                            "$binary": {
                                "base64": base64_str,
                                "subType": "00"
                            }
                        },
                        "text": qr_hash
                    }
                    qr_result = qr_collection.insert_one(qr_doc)
                    
                    print(f"QR code registered successfully!")
                    print(f"QR Text: {qr_code_text}")
                    print(f"Hash: {qr_hash}")
                    print(f"Associated with user ID: {user_id}")
                    print(f"Associated with meeting ID: {meet_id}")
                    print(f"Document ID: {qr_result.inserted_id}")
            except Exception as e:
                print(f"Error saving to database: {e}")
                
            # Re-open camera
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Error: Could not reopen camera.")
                break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()

def display_db_qr_codes():
    """Display QR codes from the database for verification"""
    qr_docs = qr_collection.find().limit(10)
    
    print("Displaying QR codes from database...")
    
    for doc in qr_docs:
        try:
            # Get the binary image data
            binary_data = doc.get("qrcode", {}).get("$binary", {}).get("base64")
            
            if binary_data:
                # Convert base64 to binary
                binary_data = base64.b64decode(binary_data)
                
                # Convert binary to NumPy array
                nparr = np.frombuffer(binary_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None:
                    # Get user and meeting info
                    user_id = doc.get("user_id", "Unknown")
                    meet_id = doc.get("meet_id", "Unknown")
                    qr_hash = doc.get("text", "Unknown")
                    
                    # Try to detect QR code in the stored image
                    decoded = decode(img)
                    qr_text = "Not detected"
                    if decoded:
                        qr_text = decoded[0].data.decode("utf-8")
                    
                    # Add info to the image
                    cv2.putText(img, f"User: {user_id[:10]}...", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(img, f"Meeting: {meet_id[:10]}...", (10, 60), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(img, f"Hash: {qr_hash[:10]}...", (10, 90), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Show image
                    cv2.imshow(f"QR from DB: {str(doc['_id'])}", img)
                    cv2.waitKey(0)  # Wait for key press
                    cv2.destroyWindow(f"QR from DB: {str(doc['_id'])}")
                else:
                    print(f"Could not decode image for document {doc['_id']}")
            else:
                print(f"No image data found for document {doc['_id']}")
        except Exception as e:
            print(f"Error displaying QR code {doc['_id']}: {e}")
    
    print("Finished displaying QR codes")

if __name__ == "__main__":
    register_qr_code() 