from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage
)

from User_routers import rand_num

# Initialize LineBotApi with your channel access token
YOUR_CHANNEL_ACCESS_TOKEN = 'rwMyEJHwq0gBBjad+93n0SnYeoMJxBrHshBlTqenDSuN6SfH/z4RC/kxMV7F4MOmBq9qEmgnLRYPXJscnPaHJ3fUUB9eFVaqNZCUPRs8A1CsYFazP7Z/ExHdpguMkrb7hZDyo4uenvGzlyemc8EUmAdB04t89/1O/w1cDnyilFU='
YOUR_CHANNEL_SECRET = 'dd8cb9bf8bae39065490fd22707052dc'

app = Flask(__name__)

line_bot_api = Configuration(access_token=YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

def send_otp_via_line(user_id, otp):
    line_bot_api.push_message(user_id, TextSendMessage(text=f'Your OTP is: {otp}'))



@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    otp = rand_num()
    send_otp_via_line(user_id, otp)

if __name__ == "__main__":
    app.run(debug=True)