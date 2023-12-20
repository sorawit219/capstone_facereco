
import requests
otp =1234
user_id = 'sorawitkuha'
token = 'f5fFYBa1nzPxa2YgDbwLRZxkhtqUp2DuoiVh2wRxOAT'
url = 'https://notify-bot.line.me/oauth/token'

headers = {'Content-Type':'application/x-www-form-urlencoded'}
message = {'client_id': user_id,'message':'Here is the OTP code '+str(otp)}
session = requests.Session()
session.post(url,headers=headers,json=message)
