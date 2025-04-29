from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import threading
import json
import os
import time
import requests

TOKEN_UPLOADER = "7920918778:AAFM8JNgk4cUhn0_P81hkB1Y0cYifjdSt-M"
TOKEN_CHECKER = "7679592392:AAHi7YBXB3wmCdsrzTnyURwyljDRvMckoVY"

bot_uploader = Bot(token=TOKEN_UPLOADER)
bot_checker = Bot(token=TOKEN_CHECKER)

app = Flask(__name__)

dispatcher_uploader = Dispatcher(bot_uploader, None, workers=4)
dispatcher_checker = Dispatcher(bot_checker, None, workers=4)

ADMIN_IDS = [5459406429, 6387942633, 7189616405]
sessions = {}

STATE_NONE = 'none'
STATE_POST_FORWARD = 'post_forward'
STATE_POST_CAPTION = 'post_caption'
STATE_SUPER_VIDEO = 'super_video'
STATE_SUPER_COVER = 'super_cover'
STATE_SUPER_CAPTION = 'super_caption'
STATE_DELAY_INPUT = 'delay_input'

API_URL = f'https://api.telegram.org/bot{TOKEN_UPLOADER}'
CHANNEL_USERNAME = '@hottof'
CHANNEL_TAG = '@hottof | تُفِ داغ'

def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    return requests.post(f'{API_URL}/sendMessage', data=payload)

def send_photo(chat_id, photo, caption=None, reply_markup=None):
    payload = {'chat_id': chat_id, 'photo': photo, 'caption': caption, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    return requests.post(f'{API_URL}/sendPhoto', data=payload)

def send_video(chat_id, video, caption=None, thumb=None):
    payload = {'chat_id': chat_id, 'video': video, 'caption': caption, 'parse_mode': 'HTML'}
    if thumb:
        payload['thumb'] = thumb
    return requests.post(f'{API_URL}/sendVideo', data=payload)

def forward_message(to_chat_id, from_chat_id, message_id):
    return requests.post(f'{API_URL}/forwardMessage', data={
        'chat_id': to_chat_id,
        'from_chat_id': from_chat_id,
        'message_id': message_id
    })

def delete_message(chat_id, message_id):
    return requests.post(f'{API_URL}/deleteMessage', data={
        'chat_id': chat_id,
        'message_id': message_id
    })

def main_panel():
    return {'keyboard': [[{'text': 'پست'}, {'text': 'سوپر'}]], 'resize_keyboard': True}

def confirm_panel():
    return {'keyboard': [[{'text': 'ارسال همین حالا'}, {'text': 'ارسال تاخیری'}], [{'text': 'بازگشت به پنل اصلی'}]], 'resize_keyboard': True}

def no_cover_inline():
    return {'inline_keyboard': [[{'text': 'ندارم', 'callback_data': 'no_cover'}]]}

def schedule_send(func, delay_minutes):
    threading.Thread(target=lambda: (time.sleep(delay_minutes * 60), func())).start()

def handle_send(user_id, chat_id):
    data = sessions.get(user_id, {})
    if data.get('type') == 'post':
        forward_message(CHANNEL_USERNAME, data['forward_chat_id'], data['message_id'])
    elif data.get('type') == 'super':
        send_video(CHANNEL_USERNAME, data['video_id'], data['caption'], data.get('cover_id'))
    sessions[user_id] = {'state': STATE_NONE}
    send_message(chat_id, 'با موفقیت ارسال شد.', reply_markup=main_panel())

def handle_uploader(update: Update, context):
    message = update.message
    if not message:
        return
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text or ''
    if user_id not in ADMIN_IDS:
        return
    state = sessions.get(user_id, {}).get('state', STATE_NONE)

    if text in ['/start', '/panel']:
        sessions[user_id] = {'state': STATE_NONE}
        send_message(chat_id, 'خوش آمدید به پنل مدیریت', reply_markup=main_panel())

    elif text == 'پست':
        sessions[user_id] = {'state': STATE_POST_FORWARD}
        send_message(chat_id, 'لطفا یک پست (عکس یا ویدیو) فوروارد کنید:')

    elif text == 'سوپر':
        sessions[user_id] = {'state': STATE_SUPER_VIDEO}
        send_message(chat_id, 'لطفا ویدیوی خود را ارسال کنید:')

    elif text == 'ارسال همین حالا':
        handle_send(user_id, chat_id)

    elif text == 'ارسال تاخیری':
        sessions[user_id]['state'] = STATE_DELAY_INPUT
        send_message(chat_id, 'چند دقیقه بعد ارسال شود؟')

    elif text == 'بازگشت به پنل اصلی':
        sessions[user_id] = {'state': STATE_NONE}
        send_message(chat_id, 'بازگشت به پنل اصلی', reply_markup=main_panel())

    elif state == STATE_POST_FORWARD and message.forward_from:
        sessions[user_id] = {
            'state': STATE_POST_CAPTION,
            'type': 'post',
            'forward_chat_id': message.forward_from.id,
            'message_id': message.message_id
        }
        send_message(chat_id, 'لطفا کپشن را وارد کنید:')

    elif state == STATE_SUPER_VIDEO and message.video:
        sessions[user_id] = {
            'state': STATE_SUPER_COVER,
            'type': 'super',
            'video_id': message.video.file_id
        }
        send_message(chat_id, 'در صورت داشتن کاور، ارسال کنید یا دکمه زیر را بزنید:', reply_markup=no_cover_inline())

    elif state == STATE_SUPER_COVER and message.photo:
        sessions[user_id]['cover_id'] = message.photo[-1].file_id
        sessions[user_id]['state'] = STATE_SUPER_CAPTION
        send_message(chat_id, 'لطفا کپشن را وارد کنید:')

    elif state == STATE_SUPER_CAPTION:
        sessions[user_id]['caption'] = text
        send_message(chat_id, 'پیش‌نمایش آماده است. انتخاب کنید:', reply_markup=confirm_panel())

    elif state == STATE_POST_CAPTION:
        sessions[user_id]['caption'] = text
        send_message(chat_id, 'پیش‌نمایش آماده است. انتخاب کنید:', reply_markup=confirm_panel())

    elif state == STATE_DELAY_INPUT:
        try:
            minutes = int(''.join(filter(str.isdigit, text)))
            schedule_send(lambda: handle_send(user_id, CHANNEL_USERNAME), minutes)
            send_message(chat_id, f'محتوا {minutes} دقیقه دیگر ارسال خواهد شد.', reply_markup=main_panel())
            sessions[user_id] = {'state': STATE_NONE}
        except:
            send_message(chat_id, 'عدد معتبر وارد کنید.')

def callback_handler(update: Update, context):
    query = update.callback_query
    if not query:
        return
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    if query.data == 'no_cover':
        delete_message(chat_id, query.message.message_id)
        sessions[user_id]['state'] = STATE_SUPER_CAPTION
        send_message(chat_id, 'لطفا کپشن را وارد کنید:')

dispatcher_uploader.add_handler(CallbackQueryHandler(callback_handler))
dispatcher_uploader.add_handler(MessageHandler(Filters.all, handle_uploader))

@app.route(f"/{TOKEN_UPLOADER}", methods=["POST"])
def webhook_uploader():
    update = Update.de_json(request.get_json(force=True), bot_uploader)
    dispatcher_uploader.process_update(update)
    return 'ok'

@app.route(f"/{TOKEN_CHECKER}", methods=["POST"])
def webhook_checker():
    update = Update.de_json(request.get_json(force=True), bot_checker)
    dispatcher_checker.process_update(update)
    return 'ok'

@app.route('/')
def home():
    return 'Bot is alive!'

def set_webhooks():
    bot_uploader.set_webhook("https://three-ta-bot.onrender.com/" + TOKEN_UPLOADER)
    bot_checker.set_webhook("https://three-ta-bot.onrender.com/" + TOKEN_CHECKER)

if __name__ == "__main__":
    set_webhooks()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
