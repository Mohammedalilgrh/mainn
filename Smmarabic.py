# -*- coding: utf-8 -*-
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

import telebot
from telebot import types
import sqlite3

TOKEN = '8149279921:AAFoNP5M-9mn_GpgHM244X1ETqFWtBNCFnQ'
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6831120113
DETAILS_CHANNEL = '@IQ3lu'
FORCE_CHANNELS = ['@Mboost99', '@s111sgrh']

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        phone TEXT,
        invites INTEGER DEFAULT 0
    )
''')
conn.commit()

def is_subscribed(user_id):
    for ch in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    existing_user = cursor.fetchone()

    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id and not existing_user:
            cursor.execute("UPDATE users SET invites = invites + 1 WHERE id=?", (referrer_id,))
            conn.commit()

    if not existing_user:
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in FORCE_CHANNELS:
            markup.add(types.InlineKeyboardButton(f"اشترك في {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ تم الاشتراك", callback_data='check_join'))
        bot.send_message(user_id, "الرجاء الاشتراك بجميع القنوات المطلوبة لاستخدام البوت:", reply_markup=markup)
    else:
        ask_phone(message)

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    if is_subscribed(call.from_user.id):
        ask_phone(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ لم يتم التحقق من الاشتراك بعد!", show_alert=True)

def ask_phone(message):
    bot.send_message(message.chat.id, "أرسل رقم هاتفك:")
    bot.register_next_step_handler(message, save_user_info)

def save_user_info(message):
    phone = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    cursor.execute("UPDATE users SET username=?, phone=? WHERE id=?", (username, phone, user_id))
    conn.commit()
    send_main_menu(message.chat.id)

def send_main_menu(chat_id):
    cursor.execute("SELECT username, phone, invites FROM users WHERE id=?", (chat_id,))
    user = cursor.fetchone()
    if user:
        points = user[2] * 5
        msg = f"اسم المستخدم: @{user[0]}\nرقم الهاتف: {user[1]}\nالنقاط: {points}\nدعوات الأصدقاء: {user[2]}\n\nكل دعوة صديق = 5 نقاط. كل 200 نقطة يمكنك الضغط على الزر للحصول على اشتراك مجاني."
    else:
        msg = "لم يتم العثور على المستخدم."

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("انستغرام", "تيك توك")
    markup.row("فيسبوك", "تيليجرام")
    markup.row("رابط الدعوة", "نقاطي")
    markup.row("الحصول على اشتراك مجاني")
    bot.send_message(chat_id, msg, reply_markup=markup)

print("Bot is running...")
bot.infinity_polling()