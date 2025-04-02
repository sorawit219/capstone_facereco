import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import os

async def test_qr_endpoint():
    """Test the QR+OTP endpoint"""
    print("Testing QR+OTP endpoint...")
    uri = "ws://localhost:8000/qr+otp?meeting=test_meeting"
    try:
        async with websockets.connect(uri) as websocket:
            # Sample QR code data (replace with your actual QR code data)
            test_qr_data = "test_qr_code_data"
            clean_qr_data = test_qr_data.strip()
            if not clean_qr_data or clean_qr_data == "null" or clean_qr_data == "undefined":
                # Skip empty frames that don't contain QR code data
                return
            await websocket.send(clean_qr_data)
            response = await websocket.recv()
            print(f"Response: {response}")
            parsed = json.loads(response)
            print(f"Status: {parsed.get('status')}")
            print(f"Message: {parsed.get('msg')}")
            print(f"Timestamp: {parsed.get('timestamp')}")
    except Exception as e:
        print(f"Error connecting to QR endpoint: {str(e)}")

async def test_face_recognition_endpoint():
    """Test the face recognition+OTP endpoint"""
    print("\nTesting face_reco+otp endpoint...")
    uri = "ws://localhost:8000/face_reco+otp"
    try:
        # Load a test image
        img_path = "test_face.jpg"  # Replace with a path to a test image
        if not os.path.exists(img_path):
            print(f"Test image {img_path} not found. Skipping face recognition test.")
            return
            
        img = cv2.imread(img_path)
        if img is None:
            print(f"Could not read image {img_path}. Skipping face recognition test.")
            return
            
        # Encode image to base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        img_data = f"data:image/jpeg;base64,{img_base64}"
        
        async with websockets.connect(uri) as websocket:
            await websocket.send(img_data)
            response = await websocket.recv()
            print(f"Response: {response}")
            parsed = json.loads(response)
            print(f"Status: {parsed.get('status')}")
            print(f"Message: {parsed.get('message', 'No message')}")
    except Exception as e:
        print(f"Error testing face recognition endpoint: {str(e)}")

async def main():
    """Run all tests"""
    await test_qr_endpoint()
    await test_face_recognition_endpoint()

if __name__ == "__main__":
    asyncio.run(main()) 