import os
import smtplib
from email.message import EmailMessage
import ssl
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('D:\VScode\capstone\serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()
email = db.collection("user").document('LA').collection("321576").e-mail()
print (email)



"""""
smtp_server = 'smtp.gmail.com'
smtp_port = 465
smtp_username = 'capstone.facerec@gmail.com'
smtp_password = 'qjvz izcl ehtr bwlw'

from_email = 'capstone.FaceRec@gmail.com'
from_password = 'o7xPXkdSDcnVCcn'
to_email = 'sorawit.pat@gmail.com'
subject = 'Here is QR-code'
body = 'Thank for use FACETICKET'

path = r'D:\VScode\capstone\Qrcode_img\123456.png'
em = EmailMessage()
em['From'] = from_email
em['To'] = to_email
em['Subject'] = subject
em.set_content(body)
context = ssl.create_default_context()
#message = f'Subject: {subject}\n\n{body}'

with open(path, "rb") as image_file:
    image_data = image_file.read()
    em.add_attachment(image_data, maintype='image', subtype='jpg', filename=os.path.basename(path))

with smtplib.SMTP_SSL(smtp_server, smtp_port,context=context) as smtp:
    smtp.login(smtp_username, smtp_password)
    smtp.sendmail(from_email, to_email, em.as_string())

"""