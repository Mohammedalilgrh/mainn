from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time

TOKEN = '8149279921:AAFoNP5M-9mn_GpgHM244X1ETqFWtBNCFnQ'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Bot Settings
ADMIN_ID = 6831120113
DETAILS_CHANNEL = '@IQ3lu'
FORCE_CHANNELS = ['@Mboost99', '@s111sgrh']

# Database Setup
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        invites INTEGER DEFAULT 0,
        last_sub_request INTEGER DEFAULT 0
    )''')
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
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    existing_user = cursor.fetchone()
    
    # Handle referral
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id and not existing_user:
            cursor.execute("UPDATE users SET invites = invites + 1 WHERE id=?", (referrer_id,))
            conn.commit()
    
    # Register new user if not exists
    if not existing_user:
        cursor.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
    
    # Check channel subscription
    if not is_subscribed(user_id):
        show_subscription_request(user_id)
    else:
        send_main_menu(user_id)

def show_subscription_request(user_id):
    markup = types.InlineKeyboardMarkup()
    for ch in FORCE_CHANNELS:
        markup.add(types.InlineKeyboardButton(
            f"Join {ch} / اشترك في {ch}", 
            url=f"https://t.me/{ch[1:]}"
        ))
    markup.add(types.InlineKeyboardButton(
        "✅ I've Joined / تم الاشتراك", 
        callback_data='check_join'
    ))
    bot.send_message(
        user_id,
        "Please join all required channels / الرجاء الاشتراك بجميع القنوات المطلوبة:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    if is_subscribed(call.from_user.id):
        send_main_menu(call.from_user.id)
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Please join all channels / الرجاء الاشتراك بجميع القنوات!",
            show_alert=True
        )

def send_main_menu(chat_id):
    cursor.execute("SELECT username, invites FROM users WHERE id=?", (chat_id,))
    user = cursor.fetchone()
    
    if user:
        username, invites = user
        points = invites * 5
        msg = (
            f"Username / اسم المستخدم: @{username}\n"
            f"Points / النقاط: {points}\n"
            f"Invites / دعوات الأصدقاء: {invites}\n\n"
            "Each invite = 5 points / كل دعوة صديق = 5 نقاط\n"
            "200 points = Free subscription / 200 نقطة = اشتراك مجاني"
        )
    else:
        msg = "Welcome / مرحباً بك!"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Instagram / انستغرام", "TikTok / تيك توك")
    markup.row("Facebook / فيسبوك", "Telegram / تيليجرام")
    markup.row("Referral Link / رابط الدعوة", "My Points / نقاطي")
    markup.row("Free Subscription / اشتراك مجاني")
    bot.send_message(chat_id, msg, reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "Referral Link / رابط الدعوة")
def send_ref_link(msg):
    user_id = msg.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "Copy / انسخ الرابط", 
        switch_inline_query=link
    ))
    bot.send_message(
        msg.chat.id,
        f"Share this link / شارك هذا الرابط:\n\n`{link}`",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text == "My Points / نقاطي")
def show_points(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
    invites = cursor.fetchone()
    points = invites[0] * 5 if invites else 0
    bot.send_message(
        user_id,
        f"Your points / نقاطك: {points}\n"
        f"Your invites / دعواتك: {invites[0] if invites else 0}"
    )

@bot.message_handler(func=lambda msg: msg.text == "Free Subscription / اشتراك مجاني")
def handle_free_sub(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites, last_sub_request FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        bot.send_message(user_id, "Error / خطأ في البيانات")
        return
    
    invites, last_request = result
    points = invites * 5
    current_time = int(time.time())
    
    if points >= 200:
        if current_time - last_request >= 86400:  # 24 hours
            cursor.execute(
                "UPDATE users SET invites = invites - 40, last_sub_request = ? WHERE id = ?",
                (current_time, user_id)
            )
            conn.commit()
            bot.send_message(
                DETAILS_CHANNEL,
                f"🎉 New free sub request from @{msg.from_user.username} ({user_id})"
            )
            bot.send_message(
                user_id,
                "✅ Request approved / تم قبول طلبك! Will be activated within 24h / سيتم التنفيذ خلال 24 ساعة"
            )
        else:
            remaining = 86400 - (current_time - last_request)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            bot.send_message(
                user_id,
                f"⏳ Please wait / يرجى الانتظار {hours}h {minutes}m"
            )
    else:
        needed = 200 - points
        bot.send_message(
            user_id,
            f"❌ You need / تحتاج {needed} more points / نقاط إضافية"
        )

# Service Handlers
@bot.message_handler(func=lambda msg: msg.text in [
    "Instagram / انستغرام", "TikTok / تيك توك",
    "Facebook / فيسبوك", "Telegram / تيليجرام"
])
def handle_platform(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات")
    markup.row("⬅️ Back / رجوع")
    bot.send_message(
        msg.chat.id,
        f"Choose service for / اختر خدمة لـ {msg.text.split('/')[0].strip()}:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda msg: msg.text in [
    "Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات"
])
def handle_service(msg):
    if msg.text == "⬅️ Back / رجوع":
        send_main_menu(msg.chat.id)
        return
    
    service_prices = {
        "Followers / متابعين": [
            "1000 followers / 1000 متابع = 2$",
            "3000 followers / 3000 متابع = 5$",
            "6000 followers / 6000 متابع = 10$"
        ],
        "Likes / إعجابات": [
            "3000 likes / 3000 إعجاب = 2$",
            "8000 likes / 8000 إعجاب = 5$",
            "15000 likes / 15000 إعجاب = 10$"
        ],
        "Views / مشاهدات": [
            "3000 views / 3000 مشاهدة = 2$",
            "8000 views / 8000 مشاهدة = 5$",
            "15000 views / 15000 مشاهدة = 10$"
        ]
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for price in service_prices.get(msg.text, []):
        markup.add(price)
    markup.row("⬅️ Back / رجوع")
    
    bot.send_message(
        msg.chat.id,
        "Choose package / اختر الباقة:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, lambda m: get_link(m, msg.text))

def get_link(message, service_type):
    if message.text == "⬅️ Back / رجوع":
        send_main_menu(message.chat.id)
        return
    
    bot.send_message(
        message.chat.id,
        "Send your link / أرسل الرابط الخاص بك:"
    )
    bot.register_next_step_handler(
        message, 
        lambda m: process_order(m, service_type, message.text)
    )

def process_order(message, service_type, package):
    if message.text == "⬅️ Back / رجوع":
        send_main_menu(message.chat.id)
        return
    
    link = message.text
    user = message.from_user
    
    order_msg = (
        f"🛒 New Order / طلب جديد\n\n"
        f"👤 User / مستخدم: @{user.username}\n"
        f"📦 Service / خدمة: {service_type.split('/')[0].strip()}\n"
        f"📝 Package / باقة: {package.split('=')[0].strip()}\n"
        f"🔗 Link / رابط: {link}"
    )
    
    bot.send_message(DETAILS_CHANNEL, order_msg)
    bot.send_message(
        message.chat.id,
        "✅ Order received / تم استلام طلبك! Processing in 24h / جاري التنفيذ خلال 24 ساعة"
    )

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Back / رجوع")
def go_back(msg):
    send_main_menu(msg.chat.id)

# Set webhook
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url='https://mainn-7th7.onrender.com/8149279921:AAFoNP5M-9mn_GpgHM244X1ETqFWtBNCFnQ')
