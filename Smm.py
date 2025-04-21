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
from flask import Flask, request
import keep_alive 

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
            markup.add(types.InlineKeyboardButton(f"Join {ch} / Ø§Ø´ØªØ±Ùƒ ÙÙŠ {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("âœ… I've Joined / ØªÙ… Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ", callback_data='check_join'))
        bot.send_message(user_id, "Please join all required channels / Ø§Ù„Ø±Ø¬Ø§Ø¡ Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ Ø¨Ø¬Ù…ÙŠØ¹ Ø§Ù„Ù‚Ù†ÙˆØ§Øª Ø§Ù„Ù…Ø·Ù„ÙˆØ¨Ø© Ù„Ø§Ø³ØªØ®Ø¯Ø§Ù… Ø§Ù„Ø¨ÙˆØª:", reply_markup=markup)
    else:
        ask_phone(message)

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    if is_subscribed(call.from_user.id):
        ask_phone(call.message)
    else:
        bot.answer_callback_query(call.id, "âŒ Ù„Ù… ÙŠØªÙ… Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„Ø§Ø´ØªØ±Ø§Ùƒ Ø¨Ø¹Ø¯!", show_alert=True)

def ask_phone(message):
    bot.send_message(message.chat.id, "Send your phone number / Ø£Ø±Ø³Ù„ Ø±Ù‚Ù… Ù‡Ø§ØªÙÙƒ:")
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
        msg = f"Username / Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: @{user[0]}\nPhone / Ø±Ù‚Ù… Ø§Ù„Ù‡Ø§ØªÙ: {user[1]}\nPoints / Ø§Ù„Ù†Ù‚Ø§Ø·: {points}\nInvites / Ø¯Ø¹ÙˆØ§Øª Ø§Ù„Ø£ØµØ¯Ù‚Ø§Ø¡: {user[2]}\n\nÙƒÙ„ Ø¯Ø¹ÙˆØ© ØµØ¯ÙŠÙ‚ = 5 Ù†Ù‚Ø§Ø·. ÙƒÙ„ 200 Ù†Ù‚Ø·Ø© ÙŠÙ…ÙƒÙ†Ùƒ Ø§Ù„Ø¶ØºØ· Ø¹Ù„Ù‰ Ø§Ù„Ø²Ø± Ù„Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ø´ØªØ±Ø§Ùƒ Ù…Ø¬Ø§Ù†ÙŠ."
    else:
        msg = "User not found / Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…."

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Instagram / Ø§Ù†Ø³ØªØºØ±Ø§Ù…", "TikTok / ØªÙŠÙƒ ØªÙˆÙƒ")
    markup.row("Facebook / ÙÙŠØ³Ø¨ÙˆÙƒ", "Telegram / ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…")
    markup.row("Referral Link / Ø±Ø§Ø¨Ø· Ø§Ù„Ø¯Ø¹ÙˆØ©", "Ù†Ù‚Ø§Ø·ÙŠ")
    markup.row("Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ø´ØªØ±Ø§Ùƒ Ù…Ø¬Ø§Ù†ÙŠ")
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text in ["Instagram / Ø§Ù†Ø³ØªØºØ±Ø§Ù…", "TikTok / ØªÙŠÙƒ ØªÙˆÙƒ", "Facebook / ÙÙŠØ³Ø¨ÙˆÙƒ", "Telegram / ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…"])
def handle_platform(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Followers / Ù…ØªØ§Ø¨Ø¹ÙŠÙ†", "Likes / Ø¥Ø¹Ø¬Ø§Ø¨Ø§Øª", "Views / Ù…Ø´Ø§Ù‡Ø¯Ø§Øª")
    markup.row("â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹")
    bot.send_message(msg.chat.id, f"Ø§Ø®ØªØ± Ø§Ù„Ø®Ø¯Ù…Ø© Ù„Ù€ {msg.text}:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["Followers / Ù…ØªØ§Ø¨Ø¹ÙŠÙ†", "Likes / Ø¥Ø¹Ø¬Ø§Ø¨Ø§Øª", "Views / Ù…Ø´Ø§Ù‡Ø¯Ø§Øª"])
def handle_service(msg):
    if msg.text == "â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹":
        send_main_menu(msg.chat.id)
        return
    note = "ÙŠØ¬Ø¨ Ø¹Ù„ÙŠÙƒ Ø§Ø±ÙØ§Ù‚ Ø±ØµÙŠØ¯ Ù„Ø£ØªÙ…Ø§Ù… Ø§Ù„Ø¹Ù…Ù„ÙŠØ© ÙÙˆØ±Ø§Ù‹"
    prices = {
        "Followers / Ù…ØªØ§Ø¨Ø¹ÙŠÙ†": [
            "1000 Ù…ØªØ§Ø¨Ø¹ = Ø±ØµÙŠØ¯ Ø£Ø¨Ùˆ Ø§Ù„2",
            "3000 Ù…ØªØ§Ø¨Ø¹ = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„5",
            "6000 Ù…ØªØ§Ø¨Ø¹ = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„10"
        ],
        "Likes / Ø¥Ø¹Ø¬Ø§Ø¨Ø§Øª": [
            "3000 Ø¥Ø¹Ø¬Ø§Ø¨ = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ 2",
            "8000 Ø¥Ø¹Ø¬Ø§Ø¨ = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„5",
            "15000 Ø¥Ø¹Ø¬Ø§Ø¨ = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„10"
        ],
        "Views / Ù…Ø´Ø§Ù‡Ø¯Ø§Øª": [
            "3000 Ù…Ø´Ø§Ù‡Ø¯Ø© = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ 2",
            "8000 Ù…Ø´Ø§Ù‡Ø¯Ø© = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„5",
            "15000 Ù…Ø´Ø§Ù‡Ø¯Ø© = Ø±ØµÙŠØ¯ Ø§Ø¨Ùˆ Ø§Ù„10"
        ]
    }
    services = prices.get(msg.text, [])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services:
        markup.add(service)
    markup.row("â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹")
    bot.send_message(msg.chat.id, f"Ø§Ø®ØªØ± Ø§Ù„Ø®Ø¯Ù…Ø© Ø§Ù„ØªÙŠ ØªØ±ÙŠØ¯Ù‡Ø§ Ù„Ù€ {msg.text}:\n{note}", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: ask_link(m, msg.text))

def ask_link(message, service):
    if message.text == "â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹":
        send_main_menu(message.chat.id)
        return
    message.chat.service = service  # Ø­ÙØ¸ Ù†ÙˆØ¹ Ø§Ù„Ø®Ø¯Ù…Ø©
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹")
    bot.send_message(message.chat.id, "Ø£Ø±Ø³Ù„ Ø±Ø§Ø¨Ø· Ø§Ù„ØµÙØ­Ø© Ø£Ùˆ   Ø§Ù„Ù…Ù†Ø´ÙˆØ± Ø§Ù„Ù…Ø±Ø§Ø¯ Ø±Ø´Ù‚Ù‡:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: ask_code(m, service, m.text))

def ask_code(message, service, page_link):
    if message.text == "â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹":
        send_main_menu(message.chat.id)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹")
    bot.send_message(message.chat.id, f"Ø±Ø§Ø¨Ø·Ùƒ:\n{page_link}\n\nØ§Ù„Ø¢Ù†  Ø£Ø±Ø³Ù„ Ø±Ù…Ø² ÙƒØ§Ø±Øª Ø²ÙŠÙ† Ø£Ùˆ Ø¢Ø³ÙŠØ§ Ø³ÙŠÙ„ âš ï¸Ø³ÙˆÙ ÙŠØªÙ… Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø±Ù‚Ù… Ø§Ù„Ø±ØµÙŠØ¯ Ø§Ù„Ù…Ø±ÙÙ‚ ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: send_to_admin(m, service, page_link))

def send_to_admin(message, service, page_link):
    if message.text == "â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹":
        send_main_menu(message.chat.id)
        return
    code = message.text.strip()
    user = message.from_user
    cursor.execute("SELECT phone FROM users WHERE id=?", (user.id,))
    phone_result = cursor.fetchone()
    phone = phone_result[0] if phone_result else "ØºÙŠØ± Ù…Ø¹Ø±ÙˆÙ"
    text = f"ðŸ›’ Ø·Ù„Ø¨ Ø¬Ø¯ÙŠØ¯\n\nðŸ‘¤ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: @{user.username} ({user.id})\nðŸ“ž Ø±Ù‚Ù… Ø§Ù„Ù‡Ø§ØªÙ: {phone}\nðŸ“¦ Ø§Ù„Ø®Ø¯Ù…Ø©: {service}\nðŸ”— Ø§Ù„Ø±Ø§Ø¨Ø·: {page_link}\nðŸ’³ Ø§Ù„ÙƒÙˆØ¯: {code}\nâ³ ÙŠØªÙ… Ø§Ù„ØªØ­Ù‚ÙŠÙ‚ ÙÙŠ Ø§Ù„Ø·Ù„Ø¨ ... Ø³ÙˆÙ ÙŠØªÙ… Ø§Ù„Ø±Ø´Ù‚ Ø®Ù„Ø§Ù„ 24 Ø³Ø§Ø¹Ø© ÙÙ‚Ø·"
    
    # Send the code again in a new message for easy copying
    bot.send_message(DETAILS_CHANNEL, text, parse_mode="Markdown")
    bot.send_message(DETAILS_CHANNEL, f"  {code}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("âœ… Ù‚Ø¨ÙˆÙ„", callback_data=f"accept_{user.id}"),
        types.InlineKeyboardButton("âŒ Ø±ÙØ¶", callback_data=f"reject_{user.id}")
    )
    bot.send_message(user.id, "ÙŠØªÙ… Ø§Ù„ØªØ­Ù‚Ù‚.. Ø³ÙˆÙ ÙŠØªÙ… Ø§Ù„Ø±Ø´Ù‚ Ø®Ù„Ø§Ù„ 24 Ø³Ø§Ø¹Ø© ÙÙ‚Ø·.")
    bot.send_message(DETAILS_CHANNEL, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_response(call):
    user_id = int(call.data.split("_")[1])
    if call.data.startswith("accept"):
        bot.send_message(user_id, "âœ… ØªÙ… Ù‚Ø¨ÙˆÙ„ ÙƒÙˆØ¯Ùƒ. Ø³ÙŠØªÙ… ØªÙ†ÙÙŠØ° Ø§Ù„Ø¹Ù…Ù„ÙŠØ© Ø®Ù„Ø§Ù„ 24 Ø³Ø§Ø¹Ø© ÙÙ‚Ø·.")
    else:
        bot.send_message(user_id, "âŒ ØªÙ… Ø±ÙØ¶ ÙƒÙˆØ¯Ùƒ. Ø­Ø§ÙˆÙ„ Ù…Ø±Ø© Ø£Ø®Ø±Ù‰.")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(func=lambda msg: msg.text == "â¬…ï¸ Back / Ø±Ø¬ÙˆØ¹")
def go_back(msg):
    send_main_menu(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "Referral Link / Ø±Ø§Ø¨Ø· Ø§Ù„Ø¯Ø¹ÙˆØ©")
def send_ref_link(msg):
    user_id = msg.from_user.id
    link = f"[https://t.me/{bot.get_me().username}?start={user_id}](https://t.me/{bot.get_me().username}?start={user_id})"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ðŸ“‹ Ø§Ù†Ø³Ø® Ø§Ù„Ø±Ø§Ø¨Ø·", switch_inline_query=link))
    bot.send_message(msg.chat.id, f"Ø§Ù†Ø³Ø® ÙˆØ´Ø§Ø±Ùƒ Ù‡Ø°Ø§ Ø§Ù„Ø±Ø§Ø¨Ø· Ù„Ø¯Ø¹ÙˆØ© Ø£ØµØ¯Ù‚Ø§Ø¦Ùƒ:\n\n`{link}`", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ø´ØªØ±Ø§Ùƒ Ù…Ø¬Ø§Ù†ÙŠ")
def check_free_subscription(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
    invites = cursor.fetchone()
    if invites and invites[0] * 5 >= 200:
        bot.send_message(DETAILS_CHANNEL, f"âœ… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… @{msg.from_user.username} ({user_id}) ÙˆØµÙ„ Ø¥Ù„Ù‰ 200 Ù†Ù‚Ø·Ø© ÙˆÙŠØ³ØªØ­Ù‚ Ø§Ø´ØªØ±Ø§Ùƒ Ù…Ø¬Ø§Ù†ÙŠ!")
        bot.send_message(user_id, "ØªÙ‡Ø§Ù†ÙŠÙ†Ø§! ØªÙ… Ø¥Ø´Ø¹Ø§Ø± Ø§Ù„Ø¥Ø¯Ø§Ø±Ø© Ù„Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ø´ØªØ±Ø§Ùƒ Ù…Ø¬Ø§Ù†ÙŠ.")
    else:
        bot.send_message(user_id, "âŒ Ù„Ù… ØªØµÙ„ Ø¥Ù„Ù‰ 200 Ù†Ù‚Ø·Ø© Ø¨Ø¹Ø¯. ÙƒÙ„ Ø¯Ø¹ÙˆØ© ØµØ¯ÙŠÙ‚ = 5 Ù†Ù‚Ø§Ø·.")

@bot.message_handler(func=lambda msg: msg.text == "Ù†Ù‚Ø§Ø·ÙŠ")
def show_points(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
    invites = cursor.fetchone()
    if invites:
        points = invites[0] * 5
        bot.send_message(user_id, f"Ù†Ù‚Ø§Ø·Ùƒ Ø§Ù„Ø­Ø§Ù„ÙŠØ©: {points} Ù†Ù‚Ø·Ø© (Ø¹Ø¯Ø¯ Ø§Ù„Ø¯Ø¹ÙˆØ§Øª: {invites[0]})")
    else:
        bot.send_message(user_id, "Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ù†Ù‚Ø§Ø·Ùƒ.")
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

# Start the server in a thread
t = Thread(target=run)
t.start()
print("Bot is running...")
from keep_alive import keep_alive
keep_alive()
bot.infinity_polling()
