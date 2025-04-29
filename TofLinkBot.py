import json
import os
import time
import threading
from flask import Flask, request
import requests

TOKEN = "7679592392:AAHi7YBXB3wmCdsrzTnyURwyljDRvMckoVY"
API_URL = f"https://api.telegram.org/bot{TOKEN}"
ADMIN_IDS = [5459406429, 6387942633, 7189616405]
FORWARD_CHANNEL = "@hottof"
DATA_FILE = "settings/statistics.json"
CHANNELS_FILE = "settings/settings.json"
app = Flask(__name__)

if not os.path.exists("settings"):
    os.makedirs("settings")

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"daily": {}, "weekly": {}, "monthly": {}, "channels": {}}, f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def check_membership(user_id):
    required_channels = load_json(CHANNELS_FILE).get("tof_checker", [])
    not_joined = []
    for ch in required_channels:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": ch["id"], "user_id": user_id}).json()
        if r.get("result", {}).get("status") not in ["member", "creator", "administrator"]:
            not_joined.append(ch)
    return not_joined

def record_stats(user_id, channels):
    stats = load_json(DATA_FILE)
    ts = time.time()
    for period in ["daily", "weekly", "monthly"]:
        if str(user_id) not in stats[period]:
            stats[period][str(user_id)] = ts
    for ch in channels:
        stats["channels"].setdefault(ch["id"], 0)
        stats["channels"][ch["id"]] += 1
    save_json(DATA_FILE, stats)

def delete_later(chat_id, message_ids, delay=15):
    def job():
        time.sleep(delay)
        for mid in message_ids:
            requests.post(f"{API_URL}/deleteMessage", data={"chat_id": chat_id, "message_id": mid})
    threading.Thread(target=job).start()

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if text.startswith("/start"):
            args = text.split()
            if len(args) == 2:
                file_id = args[1]
                not_joined = check_membership(chat_id)
                if not_joined:
                    btns = [[{"text": ch["name"], "url": f"https://t.me/{ch['id'].lstrip('@')}"}] for ch in not_joined]
                    btns.append([{"text": "عضو شدم", "callback_data": f"check_{file_id}"}])
                    msg = requests.post(f"{API_URL}/sendMessage", json={
                        "chat_id": chat_id,
                        "text": "برای دریافت فایل، لطفاً ابتدا در کانال‌های زیر عضو شوید:",
                        "reply_markup": {"inline_keyboard": btns}
                    }).json()
                    delete_later(chat_id, [msg["result"]["message_id"]], 60)
                else:
                    requests.post(f"{API_URL}/sendVideo", json={
                        "chat_id": chat_id,
                        "video": file_id,
                        "caption": "@hottof | تُفِ داغ"
                    })
                    record_stats(chat_id, load_json(CHANNELS_FILE).get("tof_checker", []))

    elif "callback_query" in update:
        q = update["callback_query"]
        data = q["data"]
        chat_id = q["message"]["chat"]["id"]
        message_id = q["message"]["message_id"]
        if data.startswith("check_"):
            file_id = data.replace("check_", "")
            not_joined = check_membership(chat_id)
            requests.post(f"{API_URL}/deleteMessage", data={"chat_id": chat_id, "message_id": message_id})
            if not_joined:
                btns = [[{"text": ch["name"], "url": f"https://t.me/{ch['id'].lstrip('@')}"}] for ch in not_joined]
                btns.append([{"text": "عضو شدم", "callback_data": f"check_{file_id}"}])
                msg = requests.post(f"{API_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "هنوز عضو برخی کانال‌ها نشده‌اید:",
                    "reply_markup": {"inline_keyboard": btns}
                }).json()
                delete_later(chat_id, [msg["result"]["message_id"]], 60)
            else:
                requests.post(f"{API_URL}/sendVideo", json={
                    "chat_id": chat_id,
                    "video": file_id,
                    "caption": "@hottof | تُفِ داغ"
                })
                record_stats(chat_id, load_json(CHANNELS_FILE).get("tof_checker", []))

    return "OK"
