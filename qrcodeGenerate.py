import pyqrcode
import random
import math
from io import BytesIO

def rand_num():#random number
    num = "0123456789"
    six_digits = ""
    for i in range(6):
        six_digits = six_digits + num[math.floor(random.random()*10)]
    print(six_digits)
    return six_digits


def generate_qr(name):
    x = rand_num()#generate number
    qr_data = f"{x}_{name}"  # Combining random number and name
    shuffled_data = ''.join(random.sample(qr_data.strip(), len(qr_data)))  # Shuffle the data after removing whitespace
    qr = pyqrcode.create(shuffled_data) #create qrcode
    png_content = BytesIO()
    qr.png(png_content, scale=6)
    png_content.seek(0)
    return shuffled_data, png_content#return name of qrcode and qrcode data
    



