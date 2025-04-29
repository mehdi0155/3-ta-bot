import os
import json
import time
import threading
import re
from flask import Flask, request
import requests

BOT_TOKEN = '7920918778:AAFM8JNgk4cUhn0_P81hkB1Y0cYifjdSt-M'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
ADMIN_IDS = [5459406429, 6387942633, 7189616405]
CHANNEL_USERNAME = '@hottof'
CHANNEL_TAG = '@hottof | تُفِ داغ'

app = Flask(__name__)
sessions = {}

# States
STATE_NONE = 'none'
STATE_POST_FORWARD = 'post_forward'
STATE_POST_CAPTION = 'post_caption'
STATE_SUPER_VIDEO = 'super_video'
STATE_SUPER_COVER = 'super_cover'
STATE_SUPER_CAPTION = 'super_caption'
STATE_DELAY_INPUT = 'delay_input'

# Send message

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
    payload = {'chat_id': to_chat_id, 'from_chat_id': from_chat_id, 'message_id': message_id}
    return requests.post(f'{API_URL}/forwardMessage', data=payload)

def delete_message(chat_id, message_id):
    return requests.post(f'{API_URL}/deleteMessage', data={'chat_id': chat_id, 'message_id': message_id})

# Panels

def main_panel():
    return {'keyboard': [[{'text': 'پست'}, {'text': 'سوپر'}]], 'resize_keyboard': True}

def confirm_panel():
    return {'keyboard': [[{'text': 'ارسال همین حالا'}, {'text': 'ارسال تاخیری'}], [{'text': 'بازگشت به پنل اصلی'}]], 'resize_keyboard': True}

def no_cover_inline():
    return {'inline_keyboard': [[{'text': 'ندارم', 'callback_data': 'no_cover'}]]}

# Delay handler

def schedule_send(func, delay_minutes):
    threading.Thread(target=lambda: (time.sleep(delay_minutes * 60), func())).start()

# Webhook
@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    update = request.get_json()

    if 'message' in update:
        message = update['message']
        user_id = message['from']['id']
        chat_id = message['chat']['id']
        text = message.get('text', '')

        if user_id not in ADMIN_IDS:
            return 'ok'

        if text == '/start' or text == '/panel':
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

        elif sessions.get(user_id, {}).get('state') == STATE_POST_FORWARD and 'forward_from' in message:
            sessions[user_id] = {
                'state': STATE_POST_CAPTION,
                'type': 'post',
                'forward_chat_id': message['forward_from']['id'],
                'message_id': message['message_id']
            }
            send_message(chat_id, 'لطفا کپشن را وارد کنید:')

        elif sessions.get(user_id, {}).get('state') == STATE_SUPER_VIDEO and 'video' in message:
            sessions[user_id] = {
                'state': STATE_SUPER_COVER,
                'type': 'super',
                'video_id': message['video']['file_id']
            }
            send_message(chat_id, 'در صورت داشتن کاور، ارسال کنید یا دکمه زیر را بزنید:', reply_markup=no_cover_inline())

        elif sessions.get(user_id, {}).get('state') == STATE_SUPER_COVER and 'photo' in message:
            sessions[user_id]['cover_id'] = message['photo'][-1]['file_id']
            sessions[user_id]['state'] = STATE_SUPER_CAPTION
            send_message(chat_id, 'لطفا کپشن را وارد کنید:')

        elif sessions.get(user_id, {}).get('state') == STATE_SUPER_CAPTION:
            sessions[user_id]['caption'] = message['text']
            send_message(chat_id, 'پیش‌نمایش آماده است. انتخاب کنید:', reply_markup=confirm_panel())

        elif sessions.get(user_id, {}).get('state') == STATE_POST_CAPTION:
            sessions[user_id]['caption'] = message['text']
            send_message(chat_id, 'پیش‌نمایش آماده است. انتخاب کنید:', reply_markup=confirm_panel())

        elif sessions.get(user_id, {}).get('state') == STATE_DELAY_INPUT:
            minutes = int(re.findall(r'\d+', text)[0])
            schedule_send(lambda: handle_send(user_id, CHANNEL_USERNAME), minutes)
            send_message(chat_id, f'محتوا {minutes} دقیقه دیگر ارسال خواهد شد.', reply_markup=main_panel())
            sessions[user_id] = {'state': STATE_NONE}

    elif 'callback_query' in update:
        query = update['callback_query']
        user_id = query['from']['id']
        chat_id = query['message']['chat']['id']

        if query['data'] == 'no_cover':
            delete_message(chat_id, query['message']['message_id'])
            sessions[user_id]['state'] = STATE_SUPER_CAPTION
            send_message(chat_id, 'لطفا کپشن را وارد کنید:')
