from flask import Flask, request
from threading import Thread
from telegram import Update, Bot
from telegram.ext import Dispatcher
import os

TOKEN_UPLOADER = "7920918778:AAFM8JNgk4cUhn0_P81hkB1Y0cYifjdSt-M"
TOKEN_CHECKER = "7679592392:AAHi7YBXB3wmCdsrzTnyURwyljDRvMckoVY"

bot_uploader = Bot(token=TOKEN_UPLOADER)
bot_checker = Bot(token=TOKEN_CHECKER)

app = Flask(__name__)

dispatcher_uploader = Dispatcher(bot_uploader, None, workers=4)
dispatcher_checker = Dispatcher(bot_checker, None, workers=4)

# اینجا باید هندلرها رو به dispatcher_uploader و dispatcher_checker اضافه کنی
# مثلاً: dispatcher_uploader.add_handler(CommandHandler(...))

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
    bot_uploader.set_webhook(f"https://your-render-url/{TOKEN_UPLOADER}")
    bot_checker.set_webhook(f"https://your-render-url/{TOKEN_CHECKER}")

if __name__ == "__main__":
    set_webhooks()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
