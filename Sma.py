from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time

TOKEN = '8149279921:AAFoNP5M-9mn_GpgHM244X1ETqFWtBNCFnQ'
bot = telebot.TeleBot(TOKEN, threaded=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Invalid content type", 403

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Bot settings
ADMIN_ID = 6831120113
DETAILS_CHANNEL = '@IQ3lu'
FORCE_CHANNELS = ['@Mboost99', '@s111sgrh']

# Database setup
conn = sqlite3.connect('users.db', check_same_thread=False, timeout=10)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        invites INTEGER DEFAULT 0,
        last_active INTEGER
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
    current_time = int(time.time())
    
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    existing_user = cursor.fetchone()

    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id and not existing_user:
            cursor.execute("UPDATE users SET invites = invites + 1 WHERE id=?", (referrer_id,))
            conn.commit()

    if not existing_user:
        cursor.execute("INSERT OR IGNORE INTO users (id, username, last_active) VALUES (?, ?, ?)", 
                      (user_id, username, current_time))
    else:
        cursor.execute("UPDATE users SET last_active = ? WHERE id = ?", (current_time, user_id))
    conn.commit()

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in FORCE_CHANNELS:
            markup.add(types.InlineKeyboardButton(f"Join {ch} / اشترك في {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ I've Joined / تم الاشتراك", callback_data='check_join'))
        bot.send_message(user_id, "Please join all required channels / الرجاء الاشتراك بجميع القنوات المطلوبة لاستخدام البوت:", reply_markup=markup)
    else:
        send_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    if is_subscribed(call.from_user.id):
        # Directly show the free subscription section
        user_id = call.from_user.id
        cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
        invites = cursor.fetchone()
        
        if invites and invites[0] * 5 >= 200:
            msg = "🎉 تهانينا! لقد وصلت إلى 200 نقطة وتستحق الحصول على اشتراك مجاني!\n\nاضغط على الزر أدناه للحصول على اشتراكك المجاني:"
        else:
            needed = 40 - invites[0] if invites else 40
            msg = f"🔍 أنت بحاجة إلى {needed} دعوة أخرى للحصول على اشتراك مجاني (كل دعوة = 5 نقاط).\n\nيمكنك دعوة الأصدقاء باستخدام زر 'رابط الدعوة' في القائمة الرئيسية."
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("Instagram / انستغرام", "TikTok / تيك توك")
        markup.row("Facebook / فيسبوك", "Telegram / تيليجرام")
        markup.row("Referral Link / رابط الدعوة", "نقاطي")
        markup.row(types.KeyboardButton("✨ الحصول على اشتراك مجاني ✨"))
        
        bot.send_message(call.from_user.id, msg, reply_markup=markup)
        send_main_menu(call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ الرجاء الاشتراك بجميع القنوات المطلوبة لاستخدام البوت!", show_alert=True)

def send_main_menu(chat_id):
    cursor.execute("SELECT username, invites FROM users WHERE id=?", (chat_id,))
    user = cursor.fetchone()
    if user:
        points = user[1] * 5
        msg = f"👤 @{user[0]}\n⭐ النقاط: {points}\n📌 الدعوات: {user[1]}\n\nكل دعوة صديق = 5 نقاط. كل 200 نقطة يمكنك الحصول على اشتراك مجاني."
    else:
        msg = "User not found / لم يتم العثور على المستخدم."

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Instagram / انستغرام", "TikTok / تيك توك")
    markup.row("Facebook / فيسبوك", "Telegram / تيليجرام")
    markup.row("Referral Link / رابط الدعوة", "نقاطي")
    markup.row("الحصول على اشتراك مجاني")
    bot.send_message(chat_id, msg, reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["Instagram / انستغرام", "TikTok / تيك توك", "Facebook / فيسبوك", "Telegram / تيليجرام"])
def handle_platform(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات")
    markup.row("⬅️ Back / رجوع")
    bot.send_message(msg.chat.id, f"اختر الخدمة لـ {msg.text}:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات"])
def handle_service(msg):
    if msg.text == "⬅️ Back / رجوع":
        send_main_menu(msg.chat.id)
        return
    
    note = "يجب عليك ارفاق رصيد لأتمام العملية فوراً"
    prices = {
        "Followers / متابعين": [
            "1000 متابع = رصيد أبو ال2",
            "3000 متابع = رصيد ابو ال5",
            "6000 متابع = رصيد ابو ال10"
        ],
        "Likes / إعجابات": [
            "3000 إعجاب = رصيد ابو 2",
            "8000 إعجاب = رصيد ابو ال5",
            "15000 إعجاب = رصيد ابو ال10"
        ],
        "Views / مشاهدات": [
            "3000 مشاهدة = رصيد ابو 2",
            "8000 مشاهدة = رصيد ابو ال5",
            "15000 مشاهدة = رصيد ابو ال10"
        ]
    }
    
    services = prices.get(msg.text, [])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for service in services:
        markup.add(service)
    markup.row("⬅️ Back / رجوع")
    bot.send_message(msg.chat.id, f"اختر الخدمة التي تريدها لـ {msg.text}:\n{note}", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: ask_link(m, msg.text))

def ask_link(message, service):
    if message.text == "⬅️ Back / رجوع":
        send_main_menu(message.chat.id)
        return
    
    message.chat.service = service
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⬅️ Back / رجوع")
    bot.send_message(message.chat.id, "أرسل رابط الصفحة أو المنشور المراد رشقه:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: ask_code(m, service, m.text))

def ask_code(message, service, page_link):
    if message.text == "⬅️ Back / رجوع":
        send_main_menu(message.chat.id)
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⬅️ Back / رجوع")
    bot.send_message(message.chat.id, f"رابطك:\n{page_link}\n\nالآن أرسل رمز كارت زين أو آسيا سيل ⚠️ سيتم التحقق تلقائيًا:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: send_to_admin(m, service, page_link))

def send_to_admin(message, service, page_link):
    if message.text == "⬅️ Back / رجوع":
        send_main_menu(message.chat.id)
        return
    
    code = message.text.strip()
    user = message.from_user
    text = f"🛒 طلب جديد\n\n👤 المستخدم: @{user.username} ({user.id})\n📦 الخدمة: {service}\n🔗 الرابط: {page_link}\n💳 الكود: {code}\n⏳ يتم التحقق من الطلب... خلال 24 ساعة فقط"
    
    bot.send_message(DETAILS_CHANNEL, text, parse_mode="Markdown")
    bot.send_message(DETAILS_CHANNEL, f"{code}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user.id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
    )
    
    bot.send_message(user.id, "يتم التحقق.. سيتم الرشق خلال 24 ساعة.")
    bot.send_message(DETAILS_CHANNEL, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_response(call):
    user_id = int(call.data.split("_")[1])
    if call.data.startswith("accept"):
        bot.send_message(user_id, "✅ تم قبول كودك. سيتم تنفيذ العملية خلال 24 ساعة فقط.")
    else:
        bot.send_message(user_id, "❌ تم رفض كودك. حاول مرة أخرى.")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Back / رجوع")
def go_back(msg):
    send_main_menu(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "Referral Link / رابط الدعوة")
def send_ref_link(msg):
    user_id = msg.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 انسخ الرابط", switch_inline_query=link))
    bot.send_message(msg.chat.id, f"انسخ وشارك هذا الرابط لدعوة أصدقائك:\n\n`{link}`", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["الحصول على اشتراك مجاني", "✨ الحصول على اشتراك مجاني ✨"])
def check_free_subscription(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
    invites = cursor.fetchone()
    
    if invites and invites[0] * 5 >= 200:
        bot.send_message(DETAILS_CHANNEL, f"✅ المستخدم @{msg.from_user.username} ({user_id}) وصل إلى 200 نقطة ويستحق اشتراك مجاني!")
        bot.send_message(user_id, "تهانينا! تم إشعار الإدارة للحصول على اشتراك مجاني.")
    else:
        needed = 40 - invites[0] if invites else 40
        bot.send_message(user_id, f"❌ لم تصل إلى 200 نقطة بعد. تحتاج إلى {needed} دعوة أخرى (كل دعوة صديق = 5 نقاط).")

@bot.message_handler(func=lambda msg: msg.text == "نقاطي")
def show_points(msg):
    user_id = msg.from_user.id
    cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
    invites = cursor.fetchone()
    
    if invites:
        points = invites[0] * 5
        bot.send_message(user_id, f"نقاطك الحالية: {points} نقطة (عدد الدعوات: {invites[0]})")
    else:
        bot.send_message(user_id, "لم يتم العثور على نقاطك.")

if __name__ == '__main__':
    print("Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://mainn-7th7.onrender.com/' + TOKEN)
