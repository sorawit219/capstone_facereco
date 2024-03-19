import cv2
import pickle
import face_recognition
import numpy as np




async def face_reco():
    cap = cv2.VideoCapture(0)
    cap.set(3,1280)
    cap.set(4,720)

    print("Loading Encoding file..")
    try:
        with open("D:/VScode/capstone/code/EncodeFile.p", 'rb') as file:
            encodeListKnowWithIds = pickle.load(file)
            encodeListKnow, studentIds = encodeListKnowWithIds
        print("Encoding file Loaded")
    except FileNotFoundError:
        print("Error: Encoding file not found.")
        return

    while True:
        success, img = cap.read()
        if not success:
            print("Error: Unable to access webcam.")
            break

        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnow, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnow, encodeFace)
            matchIndex = np.argmin(faceDis)
            face_percent = 1 - faceDis[matchIndex]

            if matches[matchIndex]:
                id = studentIds[matchIndex]
                print("Known Face Detected - ID:", id)

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                bbox = x1, y2-175, x2-x1, y2-y1
                cv2.rectangle(img, bbox, (0, 255, 0), 2)
                cv2.putText(img, str(id), (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

        _, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()
    cv2.destroyAllWindows()

