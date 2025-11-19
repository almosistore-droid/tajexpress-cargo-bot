import os
import telebot
from telebot import types
from flask import Flask, request
from telebot.apihelper import ApiTelegramException

# --- 1. КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ И ТОКЕНА ---
TOKEN = "8596817855:AAFQibbgPc-JnGjT5zyBLpR1Bvjd-B8Bupc"

# --- ИСПРАВЛЕННАЯ КОНФИГУРАЦИЯ WEBHOOK ---
WEBHOOK_HOST = 'https://tajexpress-cargo-bot.onrender.com'
# 🚨 ИСПРАВЛЕНО: Используем простой путь вместо токена
WEBHOOK_ROUTE = '/webhook'
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_ROUTE

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ СОСТОЯНИЯ ---
user_data = {}
DELIVERY_GROUP_ID = -5077729823

# --- ТЕКСТЫ КНОПОК ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

# --- 2. УСТАНОВКА WEBHOOK ПРИ ЗАПУСКЕ ---
def set_webhook():
    """Устанавливает Webhook для бота."""
    try:
        bot.remove_webhook()
        # 🚨 ИСПРАВЛЕНО: Устанавливаем на простой путь /webhook
        success = bot.set_webhook(url=WEBHOOK_URL)
        if success:
            print(f"✅ WEBHOOK SET: Установлен на {WEBHOOK_URL}")
            return True
        else:
            print("❌ WEBHOOK SET ERROR: Не удалось установить Webhook")
            return False
    except Exception as e:
        print(f"❌ WEBHOOK SET CRITICAL ERROR: {e}")
        return False

# --- 3. FLASK ROUTES ---

@app.route('/')
def index():
    """Проверка работоспособности сервера"""
    return "🤖 Telegram Bot is running! Use /start in Telegram."

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    """Обрабатывает входящие обновления Telegram через Webhook."""
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            
            # Логируем входящее сообщение
            if update.message:
                print(f"📨 Received message from {update.message.chat.id}. Text: {update.message.text}")
            
            # Обработка обновления
            bot.process_new_updates([update])
            print("✅ Successfully processed update")
            return 'ok', 200
            
        except Exception as e:
            print(f"❌ FLASK ERROR: {e}")
            return 'error', 500
    else:
        return 'Not JSON', 403

# --- 4. ОБРАБОТЧИКИ БОТА ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Отправляет приветственное сообщение и основное меню."""
    chat_id = message.chat.id
    print(f"🎯 HANDLER: /start from {chat_id}")
    
    try:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
        markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
        markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
        markup.row(types.KeyboardButton(BUTTON_CONTACT))

        bot.send_message(
            chat_id,
            "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:",
            reply_markup=markup
        )
        print(f"✅ Sent welcome message to {chat_id}")
        
    except Exception as e:
        print(f"❌ ERROR in send_welcome: {e}")

# Остальные обработчики остаются без изменений...

@bot.message_handler(func=lambda message: message.text == BUTTON_GET_ADDRESS)
def get_full_address(message):
    """Начинает процесс получения полного адреса склада в Китае."""
    print(f"🎯 HANDLER: {BUTTON_GET_ADDRESS}")
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_for_address)

def get_name_for_address(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, get_phone_for_address)

def get_phone_for_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    
    name = user_data[chat_id]["name"]
    phone = user_data[chat_id]["phone"]
    final_address = (
        f"Amin 17590820846 浙江省金华市义乌市 "
        f"福田三小区80栋二单元305室 {name} {phone}"
    )
    bot.send_message(chat_id, final_address)
    # Возвращаем меню
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == BUTTON_DELIVERY)
def start_delivery(message):
    """Начинает процесс оформления заявки на доставку."""
    print(f"🎯 HANDLER: {BUTTON_DELIVERY}")
    msg = bot.send_message(message.chat.id, "Введите ваше имя для заявки на доставку:")
    bot.register_next_step_handler(msg, get_delivery_name)

def get_delivery_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"delivery_name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш адрес для доставки:")
    bot.register_next_step_handler(msg, get_delivery_address)

def get_delivery_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["delivery_address"] = message.text
    
    delivery_name = user_data[chat_id]["delivery_name"]
    delivery_address = user_data[chat_id]["delivery_address"]
    
    delivery_text = (
        "📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n\n"
        f"👤 Имя: {delivery_name}\n"
        f"📍 Адрес: {delivery_address}\n"
        f"От пользователя: @{message.from_user.username or message.from_user.id}"
    )
    
    try:
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        bot.send_message(chat_id, "Ваша заявка на доставку отправлена! ✅")
        bot.send_message(
            chat_id,
            "Доставка ⏳ Мӯҳлати доставка аз *18 то 25 рӯз*, "
            "вале мо одатан *пеш аз муҳлат* мерасонем 🚀✨",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка отправки заявки: {e}")
        print(f"❌ DELIVERY ERROR: {e}")
    
    send_welcome(message)

# Добавьте остальные обработчики здесь...

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработчик для любых других текстовых сообщений."""
    print(f"❓ UNKNOWN COMMAND: {message.text} from {message.chat.id}")
    bot.reply_to(message, "Извините, я не понял эту команду. Пожалуйста, используйте кнопки меню или команду /start.")

# --- 5. ЗАПУСК ПРИЛОЖЕНИЯ ---
if __name__ == '__main__':
    print("🚀 Starting application...")
    # Устанавливаем вебхук только при прямом запуске
    set_webhook()
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
else:
    # При запуске через Gunicorn (Render) вебхук установится при первом запросе
    print("📦 Application loaded by Gunicorn")
