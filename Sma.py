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
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=5)
app = Flask(__name__)

# Task queue for better load management
task_queue = Queue()
db_lock = Lock()

# Improved database connection with pooling
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=-10000')  # 10MB cache
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            channel TEXT,
            status TEXT,
            last_checked TIMESTAMP,
            PRIMARY KEY (user_id, channel)
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

# Cached subscription status with auto-refresh
subscription_cache = {}

def is_subscribed(user_id):
    try:
        # Check cache first
        if user_id in subscription_cache:
            cached_status, last_check = subscription_cache[user_id]
            if time.time() - last_check < 300:  # 5 minute cache
                return cached_status
        
        # Check database cache
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT channel, status FROM subscriptions 
            WHERE user_id=? AND last_checked > datetime('now', '-5 minutes')
        ''', (user_id,))
        cached_channels = {row[0]: row[1] for row in cursor.fetchall()}
        
        all_subscribed = True
        for ch in ['@Mboost99', '@s111sgrh']:
            if ch in cached_channels:
                if cached_channels[ch] != 'member':
                    all_subscribed = False
                    break
                continue
                
            # Live check with retry
            for attempt in range(3):
                try:
                    member = bot.get_chat_member(ch, user_id)
                    status = member.status
                    cursor.execute('''
                        INSERT OR REPLACE INTO subscriptions 
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (user_id, ch, status))
                    conn.commit()
                    
                    if status not in ['member', 'administrator', 'creator']:
                        all_subscribed = False
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Failed to check channel {ch} for user {user_id}: {e}")
                        all_subscribed = False
                    time.sleep(1)
        
        conn.close()
        
        # Update cache
        subscription_cache[user_id] = (all_subscribed, time.time())
        return all_subscribed
        
    except Exception as e:
        logger.error(f"Error in is_subscribed: {e}")
        return False

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

            # Update last active
            cursor.execute("UPDATE users SET last_active=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
            conn.commit()
            conn.close()

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
                "Please join all required channels / الرجاء الاشتراك بجميع القنوات المطلوبة:",
                reply_markup=markup
            )
        else:
            send_main_menu(user_id)
            
    except Exception as e:
        logger.error(f"Start handler error: {e}")
        try:
            bot.send_message(user_id, "حدث خطأ، يرجى المحاولة لاحقاً / Error occurred, please try again")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def check_join(call):
    try:
        # Immediate response to prevent timeout
        bot.answer_callback_query(call.id, "جاري التحقق... / Verifying...")
        
        # Check subscription with retry
        subscribed = False
        for attempt in range(3):
            subscribed = is_subscribed(call.from_user.id)
            if subscribed:
                break
            time.sleep(1)  # Wait between attempts
        
        if subscribed:
            # Delete old message
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            # Send main menu directly
            send_main_menu(call.from_user.id)
        else:
            # Update the message with retry button
            markup = types.InlineKeyboardMarkup()
            for ch in ['@Mboost99', '@s111sgrh']:
                markup.add(types.InlineKeyboardButton(
                    f"Join {ch} / اشترك في {ch}", 
                    url=f"https://t.me/{ch[1:]}"
                ))
            markup.add(types.InlineKeyboardButton(
                "🔄 Try Again / حاول مرة أخرى", 
                callback_data='check_join'
            ))
            
            try:
                bot.edit_message_text(
                    "❌ لم تشترك بعد في جميع القنوات / Not subscribed to all channels",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=markup
                )
            except:
                pass
            
            bot.answer_callback_query(
                call.id,
                "❌ الرجاء الانضمام لجميع القنوات أولاً / Please join all channels first",
                show_alert=True
            )
            
    except Exception as e:
        logger.error(f"Check join error: {e}")
        try:
            bot.answer_callback_query(
                call.id,
                "حدث خطأ / Error occurred",
                show_alert=True
            )
        except:
            pass

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
            msg = f"""
👤 المستخدم / Username: @{user[0]}
⭐ النقاط / Points: {points}
📌 الدعوات / Invites: {user[1]}

كل دعوة صديق = 5 نقاط / Each invite = 5 points
200 نقطة = اشتراك مجاني / 200 points = Free subscription
            """
        else:
            msg = "User not found / لم يتم العثور على المستخدم"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("Instagram / انستغرام", "TikTok / تيك توك")
        markup.row("Facebook / فيسبوك", "Telegram / تيليجرام")
        markup.row("Referral Link / رابط الدعوة", "نقاطي / My Points")
        markup.row("اشتراك مجاني / Free Subscription")
        
        bot.send_message(
            chat_id,
            msg.strip(),
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Send main menu error: {e}")
        try:
            bot.send_message(chat_id, "Error loading menu / خطأ في تحميل القائمة")
        except:
            pass

# [Keep all other handlers exactly as in your original code but add similar error handling]

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
            max_connections=100,
            allowed_updates=["message", "callback_query"]
        )
        main()
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")
