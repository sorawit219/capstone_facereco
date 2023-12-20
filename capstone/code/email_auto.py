import os
import smtplib
from email.message import EmailMessage
import ssl

smtp_server = 'smtp.gmail.com'
smtp_port = 465
smtp_username = 'capstone.facerec@gmail.com'
smtp_password = 'qjvz izcl ehtr bwlw'

from_email = 'capstone.FaceRec@gmail.com'
from_password = 'o7xPXkdSDcnVCcn'
to_email = 'sorawit.pat@gmail.com'
subject = 'Hello, world!'
body = 'This is a test email.'

em = EmailMessage()
em['From'] = from_email
em['To'] = to_email
em['Subject'] = subject
em.set_content(body)
context = ssl.create_default_context()
#message = f'Subject: {subject}\n\n{body}'

with smtplib.SMTP_SSL(smtp_server, smtp_port,context=context) as smtp:
    smtp.login(smtp_username, smtp_password)
    smtp.sendmail(from_email, to_email, em.as_string())

