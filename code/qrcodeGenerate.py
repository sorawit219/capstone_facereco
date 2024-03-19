import pyqrcode
import random
import math
import firebase_admin
from firebase_admin import credentials

def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits



cred = credentials.Certificate("D:\VScode\capstone\serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL':"https://capstone-facerecogniton-default-rtdb.asia-southeast1.firebasedatabase.app/",
    'storageBucket':"capstone-facerecogniton.appspot.com"
})


def generate_qr():
    #first_info = db.reference('User/'+id+'first_name').get()#get first name from firebase
    #last_info = db.reference('User/'+id+'last_name').get()#getlast name from firebase
    x = rand_num()
    link = x+"sorawitkuhakasemsin"#+id+first_info+last_info
    pngname = x+"_"+str(1234)
    qr = ''.join(random.sample(link,len(link)))# shuffle
    url = pyqrcode.create(qr) #string to qrcode picture
    url.png(pngname+'.png',scale=6) #name it to file.png



