from flask import Flask, request
from threading import Thread, Lock
import telebot
from telebot import types
import sqlite3
import time
import logging
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = '8149279921:AAFoNP5M-9mn_GpgHM244X1ETqFWtBNCFnQ'
bot = telebot.TeleBot(TOKEN, threaded=True)
app = Flask(__name__)

# Task queue for better load management
task_queue = Queue()
db_lock = Lock()

# Improved database connection
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            invites INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        task_queue.put(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def process_updates():
    while True:
        try:
            update = task_queue.get()
            bot.process_new_updates([update])
            task_queue.task_done()
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            time.sleep(1)

def run_flask():
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        logger.error(f"Flask run error: {e}")
        time.sleep(5)
        run_flask()

# Improved subscription check with retry
def is_subscribed(user_id):
    for attempt in range(3):  # 3 attempts with delay
        try:
            for ch in ['@Mboost99', '@s111sgrh']:
                try:
                    member = bot.get_chat_member(ch, user_id)
                    if member.status in ['left', 'kicked']:
                        return False
                except Exception as e:
                    logger.error(f"Error checking channel {ch}: {e}")
                    if attempt == 2:  # Last attempt
                        return False
            return True
        except Exception as e:
            logger.error(f"Subscription check error: {e}")
            if attempt == 2:
                return False
            time.sleep(1)

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check existing user
            cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
            existing_user = cursor.fetchone()

            # Handle referral
            args = message.text.split()
            if len(args) > 1:
                referrer_id = args[1]
                if referrer_id.isdigit() and int(referrer_id) != user_id and not existing_user:
                    cursor.execute("UPDATE users SET invites = invites + 1 WHERE id=?", (referrer_id,))
                    conn.commit()

            # Register new user
            if not existing_user:
                cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user_id, username))
                conn.commit()

            # Check subscription
            if not is_subscribed(user_id):
                markup = types.InlineKeyboardMarkup()
                for ch in ['@Mboost99', '@s111sgrh']:
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
                    "Please join all required channels / الرجاء الاشتراك بجميع القنوات المطلوبة لاستخدام البوت:",
                    reply_markup=markup
                )
            else:
                send_main_menu(user_id)
                
            conn.close()
                
    except Exception as e:
        logger.error(f"Start handler error: {e}")
        try:
            bot.send_message(user_id, "حدث خطأ، يرجى المحاولة لاحقاً")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    try:
        # Hide loading indicator
        bot.answer_callback_query(call.id)
        
        # Check subscription with retry
        subscribed = False
        for attempt in range(3):
            subscribed = is_subscribed(call.from_user.id)
            if subscribed:
                break
            time.sleep(1)
        
        if subscribed:
            # Delete old message
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            # Show main menu directly
            send_main_menu(call.from_user.id)
        else:
            # Show error alert
            bot.answer_callback_query(
                call.id,
                "❌ الرجاء الاشتراك بجميع القنوات المطلوبة أولاً!",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Check join error: {e}")
        bot.answer_callback_query(
            call.id,
            "حدث خطأ أثناء التحقق، يرجى المحاولة مرة أخرى",
            show_alert=True
        )

def send_main_menu(chat_id):
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT username, invites FROM users WHERE id=?", (chat_id,))
            user = cursor.fetchone()
            conn.close()

        if user:
            points = user[1] * 5
            msg = (
                f"Username / اسم المستخدم: @{user[0]}\n"
                f"Points / النقاط: {points}\n"
                f"Invites / دعوات الأصدقاء: {user[1]}\n\n"
                "كل دعوة صديق = 5 نقاط. كل 200 نقطة يمكنك الضغط على الزر للحصول على اشتراك مجاني."
            )
        else:
            msg = "User not found / لم يتم العثور على المستخدم."

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("Instagram / انستغرام", "TikTok / تيك توك")
        markup.row("Facebook / فيسبوك", "Telegram / تيليجرام")
        markup.row("Referral Link / رابط الدعوة", "نقاطي")
        markup.row("الحصول على اشتراك مجاني")
        
        bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Send main menu error: {e}")

@bot.message_handler(func=lambda msg: msg.text in ["Instagram / انستغرام", "TikTok / تيك توك", "Facebook / فيسبوك", "Telegram / تيليجرام"])
def handle_platform(msg):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات")
        markup.row("⬅️ Back / رجوع")
        
        bot.send_message(
            msg.chat.id, 
            f"اختر الخدمة لـ {msg.text}:", 
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Platform handler error: {e}")

@bot.message_handler(func=lambda msg: msg.text in ["Followers / متابعين", "Likes / إعجابات", "Views / مشاهدات"])
def handle_service(msg):
    try:
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
        
        bot.send_message(
            msg.chat.id,
            f"اختر الخدمة التي تريدها لـ {msg.text}:\n{note}",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, lambda m: ask_link(m, msg.text))
        
    except Exception as e:
        logger.error(f"Service handler error: {e}")

def ask_link(message, service):
    try:
        if message.text == "⬅️ Back / رجوع":
            send_main_menu(message.chat.id)
            return
            
        message.chat.service = service
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⬅️ Back / رجوع")
        
        bot.send_message(
            message.chat.id,
            "أرسل رابط الصفحة أو المنشور المراد رشقه:",
            reply_markup=markup
        )
        bot.register_next_step_handler(
            message, 
            lambda m: ask_code(m, service, m.text)
        )
    except Exception as e:
        logger.error(f"Ask link error: {e}")

def ask_code(message, service, page_link):
    try:
        if message.text == "⬅️ Back / رجوع":
            send_main_menu(message.chat.id)
            return
            
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⬅️ Back / رجوع")
        
        bot.send_message(
            message.chat.id,
            f"رابطك:\n{page_link}\n\nالآن أرسل رمز كارت زين أو آسيا سيل ⚠️ سيتم التحقق تلقائيًا:",
            reply_markup=markup
        )
        bot.register_next_step_handler(
            message,
            lambda m: send_to_admin(m, service, page_link)
        )
    except Exception as e:
        logger.error(f"Ask code error: {e}")

def send_to_admin(message, service, page_link):
    try:
        if message.text == "⬅️ Back / رجوع":
            send_main_menu(message.chat.id)
            return
            
        code = message.text.strip()
        user = message.from_user
        
        text = (
            f"🛒 طلب جديد\n\n"
            f"👤 المستخدم: @{user.username} ({user.id})\n"
            f"📦 الخدمة: {service}\n"
            f"🔗 الرابط: {page_link}\n"
            f"💳 الكود: {code}\n"
            f"⏳ يتم التحقق من الطلب... خلال 24 ساعة فقط"
        )
        
        bot.send_message(DETAILS_CHANNEL, text, parse_mode="Markdown")
        bot.send_message(DETAILS_CHANNEL, f"{code}")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user.id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
        )
        
        bot.send_message(
            user.id,
            "يتم التحقق.. سيتم الرشق خلال 24 ساعة."
        )
        bot.send_message(
            DETAILS_CHANNEL,
            text,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Send to admin error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_response(call):
    try:
        user_id = int(call.data.split("_")[1])
        
        if call.data.startswith("accept"):
            bot.send_message(
                user_id,
                "✅ تم قبول كودك. سيتم تنفيذ العملية خلال 24 ساعة فقط."
            )
        else:
            bot.send_message(
                user_id,
                "❌ تم رفض كودك. حاول مرة أخرى."
            )
            
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Admin response error: {e}")

@bot.message_handler(func=lambda msg: msg.text == "⬅️ Back / رجوع")
def go_back(msg):
    try:
        send_main_menu(msg.chat.id)
    except Exception as e:
        logger.error(f"Go back error: {e}")

@bot.message_handler(func=lambda msg: msg.text == "Referral Link / رابط الدعوة")
def send_ref_link(msg):
    try:
        user_id = msg.from_user.id
        link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📋 انسخ الرابط",
                switch_inline_query=link
            )
        )
        
        bot.send_message(
            msg.chat.id,
            f"انسخ وشارك هذا الرابط لدعوة أصدقائك:\n\n`{link}`",
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Referral link error: {e}")

@bot.message_handler(func=lambda msg: msg.text == "الحصول على اشتراك مجاني")
def check_free_subscription(msg):
    try:
        user_id = msg.from_user.id
        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
            invites = cursor.fetchone()
            conn.close()

        if invites and invites[0] * 5 >= 200:
            bot.send_message(
                DETAILS_CHANNEL,
                f"✅ المستخدم @{msg.from_user.username} ({user_id}) وصل إلى 200 نقطة ويستحق اشتراك مجاني!"
            )
            bot.send_message(
                user_id,
                "تهانينا! تم إشعار الإدارة للحصول على اشتراك مجاني."
            )
        else:
            bot.send_message(
                user_id,
                "❌ لم تصل إلى 200 نقطة بعد. كل دعوة صديق = 5 نقاط."
            )
    except Exception as e:
        logger.error(f"Free subscription error: {e}")

@bot.message_handler(func=lambda msg: msg.text == "نقاطي")
def show_points(msg):
    try:
        user_id = msg.from_user.id
        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT invites FROM users WHERE id=?", (user_id,))
            invites = cursor.fetchone()
            conn.close()

        if invites:
            points = invites[0] * 5
            bot.send_message(
                user_id,
                f"نقاطك الحالية: {points} نقطة (عدد الدعوات: {invites[0]})"
            )
        else:
            bot.send_message(
                user_id,
                "لم يتم العثور على نقاطك."
            )
    except Exception as e:
        logger.error(f"Show points error: {e}")

def main():
    try:
        # Start update processing thread
        Thread(target=process_updates, daemon=True).start()
        
        # Start Flask in main thread
        run_flask()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        time.sleep(5)
        main()

if __name__ == '__main__':
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(
            url='https://mainn-7th7.onrender.com/' + TOKEN,
            max_connections=100
        )
        main()
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")
