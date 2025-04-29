from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackContext
import json
import threading
import time

TOKEN_CHECKER = "7679592392:AAHi7YBXB3wmCdsrzTnyURwyljDRvMckoVY"
CHANNELS_FILE = "settings/settings.json"
bot_checker = None  # از main.py مقداردهی می‌شود

dispatcher_checker = Dispatcher(bot_checker, None, workers=4)

# خواندن کانال‌های اجباری
def load_channels():
    try:
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f).get("checker", [])
    except:
        return []

# بررسی عضویت کاربر
def is_user_member(bot, user_id, channel_username):
    try:
        status = bot.get_chat_member(channel_username, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

# حذف خودکار پیام
def delete_after_delay(bot, chat_id, message_id, delay=15):
    def job():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass
    threading.Thread(target=job).start()

# دکمه بررسی مجدد عضویت
def generate_check_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("بررسی عضویت", callback_data="check_membership")]])

# دکمه کانال‌ها
def generate_channel_buttons(channels):
    buttons = [[InlineKeyboardButton(ch['name'], url=f"https://t.me/{ch['id'].lstrip('@')}")] for ch in channels]
    buttons.append([InlineKeyboardButton("بررسی عضویت", callback_data="check_membership")])
    return InlineKeyboardMarkup(buttons)

# هندلر پیام‌ها
def checker_message_handler(update: Update, context: CallbackContext):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat_id
    text = message.text

    # لینک‌ها به صورت tof://file_id
    if text and text.startswith("tof://"):
        file_id = text.split("tof://")[1]
        channels = load_channels()
        not_joined = [ch for ch in channels if not is_user_member(bot_checker, user_id, ch['id'])]

        if not_joined:
            msg = "برای دریافت فایل ابتدا در کانال‌های زیر عضو شوید:"
            reply = message.reply_text(msg, reply_markup=generate_channel_buttons(not_joined))
            delete_after_delay(bot_checker, reply.chat_id, reply.message_id)
            delete_after_delay(bot_checker, message.chat_id, message.message_id)
        else:
            sent = bot_checker.send_video(chat_id, file_id)
            info = message.reply_text("لینک ارسال شد و بعد از ۱۵ ثانیه حذف می‌شود.")
            delete_after_delay(bot_checker, sent.chat_id, sent.message_id)
            delete_after_delay(bot_checker, info.chat_id, info.message_id)
            delete_after_delay(bot_checker, message.chat_id, message.message_id)

# هندلر Callback
def checker_callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    channels = load_channels()
    not_joined = [ch for ch in channels if not is_user_member(bot_checker, user_id, ch['id'])]

    if not_joined:
        query.message.edit_text("هنوز در همه‌ی کانال‌ها عضو نشده‌اید:", reply_markup=generate_channel_buttons(not_joined))
    else:
        query.message.edit_text("عضویت تایید شد. دوباره روی لینک فایل بزنید.")

# ثبت هندلرها
dispatcher_checker.add_handler(MessageHandler(Filters.text & (~Filters.command), checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.caption, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.forwarded, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.video, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.all, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.reply, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.status_update, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.photo, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.command, checker_message_handler))
dispatcher_checker.add_handler(MessageHandler(Filters.reply, checker_message_handler))

# برای کال‌بک‌ها
from telegram.ext import CallbackQueryHandler
dispatcher_checker.add_handler(CallbackQueryHandler(checker_callback_handler))
