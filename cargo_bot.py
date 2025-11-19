import os
import telebot
from telebot import types
from flask import Flask, request
from telebot.apihelper import ApiTelegramException

# --- 1. КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ И ТОКЕНА ---
# Токен прописан жестко для гарантии инициализации.
TOKEN = "8596817855:AAFQibbgPc-JnGjT5zyBLpR1Bvjd-B8Bupc"

# --- КОНФИГУРАЦИЯ WEBHOOK (КРИТИЧЕСКИ ВАЖНО) ---
# 🚨 ВНИМАНИЕ: ЗАМЕНИТЕ ЭТОТ АДРЕС НА ВАШ РЕАЛЬНЫЙ АДРЕС НА RENDER/PYTHONANYWHERE!
WEBHOOK_HOST = 'https://tajexpress-bot.onrender.com' # <-- ПРИМЕР: Замените на свой домен!
WEBHOOK_ROUTE = '/' + TOKEN
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_ROUTE

app = Flask(__name__) 
bot = telebot.TeleBot(TOKEN, use_class_middlewares=True)

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ СОСТОЯНИЯ (Для многошаговых сценариев) ---
# ВНИМАНИЕ: В ПРОДАКШЕНЕ НА GUNICORN/FLASK ЭТОТ СЛОВАРЬ user_data 
# МОЖЕТ ТЕРЯТЬ ДАННЫЕ. ИСПОЛЬЗУЙТЕ ЕГО ТОЛЬКО ДЛЯ ТЕСТИРОВАНИЯ.
user_data = {} 

# ID группы или чата, куда будут отправляться заявки на доставку. 
DELIVERY_GROUP_ID = -5077729823

# --- 2. ФУНКЦИЯ УСТАНОВКИ WEBHOOK (Для WSGI и запуска) ---
def set_webhook():
    """Устанавливает или сбрасывает Webhook для бота."""
    try:
        # Удаляем старый Webhook, если он был
        bot.remove_webhook()
        # Устанавливаем новый Webhook
        if bot.set_webhook(url=WEBHOOK_URL):
            print(f"WEBHOOK SET: Установлен на {WEBHOOK_URL}")
            return True
        else:
            print("WEBHOOK SET ERROR: Не удалось установить Webhook.")
            return False
    except Exception as e:
        print(f"WEBHOOK SET CRITICAL ERROR: {e}")
        return False


# --- 3. КОНФИГУРАЦИЯ FLASK/WEBHOOK ---

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    """Обрабатывает входящие обновления Telegram через Webhook."""
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            
            if update.message:
                print(f"WEBHOOK DEBUG: Received message from {update.message.chat.id}. Text: {update.message.text}")
            else:
                print(f"WEBHOOK DEBUG: Received other update type: {update.update_id}")

            bot.process_new_updates([update])
            return 'ok', 200
        except Exception as e:
            print(f"CRITICAL FLASK ERROR: Failed to process update: {e}")
            return 'error', 500
    else:
        return 'Not JSON', 403

# --- 4. ОБРАБОТЧИКИ БОТА (Логика) ---

# --- ТЕКСТЫ КНОПОК ---
BUTTON_GET_ADDRESS = "🏠 🇨🇳 Гирифтани адрес ва код"
BUTTON_DELIVERY = "🚚 Доставка"
BUTTON_CALC = "📦 Нархнома"
BUTTON_TRACK = "🔍 Проверка трек-кода"
BUTTON_CONTACT = "📞 Контакты"
BUTTON_TAJIK_ADDR = "🇹🇯 Адрес Душанбе"
BUTTON_PROHIBITED = "Молхои манъшуда"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Отправляет приветственное сообщение и основное меню."""
    print(f"HANDLER LOG: Handler for /start started from chat {message.chat.id}")
    try:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        
        markup.row(types.KeyboardButton(BUTTON_GET_ADDRESS), types.KeyboardButton(BUTTON_DELIVERY))
        markup.row(types.KeyboardButton(BUTTON_CALC), types.KeyboardButton(BUTTON_TRACK))
        markup.row(types.KeyboardButton(BUTTON_TAJIK_ADDR), types.KeyboardButton(BUTTON_PROHIBITED))
        markup.row(types.KeyboardButton(BUTTON_CONTACT))

        bot.send_message(
            message.chat.id,
            "Добро пожаловать в TAJ-EXPRESS! 🚚\nВыберите пункт меню:",
            reply_markup=markup
        )
        print(f"HANDLER LOG: Successfully sent welcome message to {message.chat.id}")
    except ApiTelegramException as e:
        print(f"HANDLER ERROR: Failed to send welcome message to {message.chat.id}. Telegram API Error: {e}") 
    except Exception as e:
        print(f"HANDLER ERROR: Unknown error in send_welcome: {e}")


# -----------------------------------------------------
# ФУНКЦИОНАЛ: Гирифтани адрес ва код
# -----------------------------------------------------
@bot.message_handler(func=lambda message: message.text == BUTTON_GET_ADDRESS)
def get_full_address(message):
    """Начинает процесс получения полного адреса склада в Китае."""
    print(f"HANDLER LOG: Matched button {BUTTON_GET_ADDRESS}")
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, get_name_for_address)

def get_name_for_address(message):
    """Получает имя пользователя для адреса."""
    chat_id = message.chat.id
    user_data[chat_id] = {"name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш номер телефона:")
    bot.register_next_step_handler(msg, get_phone_for_address)

def get_phone_for_address(message):
    """Получает номер телефона пользователя для адреса."""
    chat_id = message.chat.id
    user_data[chat_id]["phone"] = message.text
    send_address(chat_id)

def send_address(chat_id):
    """Формирует и отправляет полный адрес склада."""
    name = user_data[chat_id]["name"]
    phone = user_data[chat_id]["phone"]
    # Ваш предоставленный формат адреса
    final_address = (
        f"Amin 17590820846 浙江省金华市义乌市 "
        f"福田三小区80栋二单元305室 {name} {phone}"
    )
    bot.send_message(chat_id, final_address)
    send_welcome(bot.get_chat(chat_id)) # Возвращаем меню

# -----------------------------------------------------
# ФУНКЦИОНАЛ: Доставка — отправка в группу
# -----------------------------------------------------
@bot.message_handler(func=lambda message: message.text == BUTTON_DELIVERY)
def start_delivery(message):
    """Начинает процесс оформления заявки на доставку."""
    print(f"HANDLER LOG: Matched button {BUTTON_DELIVERY}")
    msg = bot.send_message(message.chat.id, "Введите ваше имя для заявки на доставку:")
    bot.register_next_step_handler(msg, get_delivery_name)

def get_delivery_name(message):
    """Получает имя для заявки."""
    chat_id = message.chat.id
    user_data[chat_id] = {"delivery_name": message.text}
    msg = bot.send_message(chat_id, "Введите ваш адрес для доставки:")
    bot.register_next_step_handler(msg, get_delivery_address)

def get_delivery_address(message):
    """Получает адрес доставки, отправляет в группу и подтверждает пользователю."""
    chat_id = message.chat.id
    user_data[chat_id]["delivery_address"] = message.text
    
    delivery_name = user_data[chat_id]["delivery_name"]
    delivery_address = user_data[chat_id]["delivery_address"]
    
    # Сообщение для группы
    delivery_text = (
        "📦 *НОВАЯ ЗАЯВКА НА ДОСТАВКУ*\n\n"
        f"👤 Имя: {delivery_name}\n"
        f"📍 Адрес: {delivery_address}\n"
        f"От пользователя: @{message.from_user.username or message.from_user.id}"
    )
    
    try:
        # Отправка заявки в группу
        bot.send_message(DELIVERY_GROUP_ID, delivery_text, parse_mode="Markdown")
        
        # Подтверждение пользователю
        bot.send_message(chat_id, "Ваша заявка на доставку отправлена! ✅")
        
        # Информация о сроках доставки (ОБНОВЛЕНО)
        bot.send_message(
            chat_id,
            "Доставка ⏳ Мӯҳлати доставка аз *18 то 25 рӯз*, "
            "вале мо одатан *пеш аз муҳлат* мерасонем 🚀✨",
            parse_mode="Markdown"
        )
    except ApiTelegramException as e:
         bot.send_message(chat_id, f"Ошибка отправки заявки: проверьте ID группы (`{DELIVERY_GROUP_ID}`) и права бота в ней. {e}")
         print(f"DELIVERY ERROR: Failed to send message to group {DELIVERY_GROUP_ID}. Error: {e}")
    
    send_welcome(message) # Возвращаем меню

# -----------------------------------------------------
# ФУНКЦИОНАЛ: Расчет, Трекинг, Контакты, Адреса
# -----------------------------------------------------

@bot.message_handler(func=lambda message: message.text == BUTTON_CALC)
def request_calculation(message):
    """Начинает процесс расчета стоимости."""
    print(f"HANDLER LOG: Matched button {BUTTON_CALC}")
    msg = bot.send_message(message.chat.id, "Пожалуйста, введите вес вашего груза в кг:")
    bot.register_next_step_handler(msg, process_weight_step)

def process_weight_step(message):
    """Обрабатывает введенный вес."""
    try:
        weight = float(message.text.replace(',', '.').strip())
        if weight <= 0:
            raise ValueError
        
        # Переход к следующему шагу
        msg = bot.send_message(message.chat.id, "Теперь введите город отправления:")
        bot.register_next_step_handler(msg, process_departure_city_step, weight)
        
    except ValueError:
        msg = bot.send_message(message.chat.id, "Неверный формат. Пожалуйста, введите вес цифрами (например, 10.5).")
        bot.register_next_step_handler(msg, process_weight_step)

def process_departure_city_step(message, weight):
    """Обрабатывает город отправления и запрашивает город назначения."""
    departure_city = message.text.strip()
    
    msg = bot.send_message(message.chat.id, "Спасибо. Теперь введите город назначения:")
    bot.register_next_step_handler(msg, process_arrival_city_step, weight, departure_city)

def process_arrival_city_step(message, weight, departure_city):
    """Обрабатывает город назначения и выдает результат."""
    arrival_city = message.text.strip()
    
    # --- ЛОГИКА РАСЧЕТА СТОИМОСТИ (ПРИМЕР) ---
    price_per_kg = 100
    base_fee = 500
    total_cost = (weight * price_per_kg) + base_fee
    
    response = (
        f"✅ **Расчет готов!**\n\n"
        f"➡️ **Отправление:** {departure_city}\n"
        f"⬅️ **Назначение:** {arrival_city}\n"
        f"⚖️ **Вес груза:** {weight} кг\n"
        f"💰 **Примерная стоимость:** {total_cost:.2f} руб.\n\n"
        f"_Обратите внимание: это предварительный расчет. Для точной стоимости, пожалуйста, свяжитесь с нашим менеджером._"
    )
    
    bot.send_message(message.chat.id, response, parse_mode='Markdown')
    send_welcome(message) # Возвращаем пользователя в главное меню

@bot.message_handler(func=lambda message: message.text == BUTTON_TRACK)
def track_cargo(message):
    """Запрашивает номер для отслеживания."""
    print(f"HANDLER LOG: Matched button {BUTTON_TRACK}")
    msg = bot.send_message(message.chat.id, "Пожалуйста, введите номер для отслеживания вашего груза (например, TAJ12345):")
    bot.register_next_step_handler(msg, process_tracking_number)

def process_tracking_number(message):
    """Обрабатывает номер для отслеживания и выдает статус."""
    tracking_number = message.text.strip().upper()
    
    # --- ЛОГИКА ОТСЛЕЖИВАНИЯ (ПРИМЕР) ---
    statuses = {
        "TAJ12345": "В пути, прибытие 25.11.2025.",
        "TAJ67890": "На складе в Москве, готовится к отправке.",
        "TAJ11223": "Доставлен и вручен получателю 15.11.2025."
    }
    
    status = statuses.get(tracking_number, "❌ К сожалению, груз с этим номером не найден. Проверьте правильность ввода или свяжитесь с нами.")
    
    bot.send_message(message.chat.id, f"**Статус груза {tracking_number}:**\n{status}", parse_mode='Markdown')
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == BUTTON_CONTACT)
def contact_us(message):
    """Предоставляет контактную информацию."""
    print(f"HANDLER LOG: Matched button {BUTTON_CONTACT}")
    contact_info = (
        "📞 **Наши контакты:**\n\n"
        "Служба поддержки: `+7 495 123 45 67`\n"
        "Email: `support@tajexpress.com`\n"
        "Менеджер: `@TajExpressManager`\n"
    )
    bot.send_message(message.chat.id, contact_info, parse_mode='Markdown')
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == BUTTON_TAJIK_ADDR)
def send_dushanbe_address(message):
    """Предоставляет адрес офиса в Душанбе."""
    print(f"HANDLER LOG: Matched button {BUTTON_TAJIK_ADDR}")
    address_info = (
        "🇹🇯 **Адрес офиса в Душанбе:**\n\n"
        "**Компания:** TAJ-EXPRESS\n"
        "**Адрес:** пр. Рудаки 123, Бизнес-центр 'Азия'\n"
        "**Телефон:** +992 900 12 34 56"
    )
    bot.send_message(message.chat.id, address_info, parse_mode='Markdown')
    send_welcome(message)

@bot.message_handler(func=lambda message: message.text == BUTTON_PROHIBITED)
def send_prohibited_list(message):
    """Предоставляет список запрещенных к перевозке товаров."""
    print(f"HANDLER LOG: Matched button {BUTTON_PROHIBITED}")
    prohibited_info = (
        "🚫 **Молҳои манъшуда (Запрещенные товары):**\n\n"
        "Список товаров, запрещенных к перевозке:\n"
        "1. Оружие и боеприпасы.\n"
        "2. Взрывчатые, легковоспламеняющиеся и радиоактивные вещества.\n"
        "3. Наркотические средства, психотропные вещества.\n"
        "4. Яды и сильнодействующие токсичные вещества.\n"
        "5. Деньги, банковские карты, ценные бумаги.\n"
        "6. Изделия и вещества, которые могут представлять опасность для других грузов или работников.\n"
        "\n"
        "_Для получения полного и актуального списка, пожалуйста, свяжитесь с нашим менеджером._"
    )
    bot.send_message(message.chat.id, prohibited_info, parse_mode='Markdown')
    send_welcome(message)


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработчик для любых других текстовых сообщений."""
    bot.reply_to(message, "Извините, я не понял эту команду. Пожалуйста, используйте кнопки меню или команду /start.")

# --- 5. ЗАПУСК ДЛЯ WEBHOOK (ПРИМЕНЕНИЕ) ---
if __name__ == '__main__':
    # При локальном запуске (не Gunicorn/Render) устанавливаем Webhook
    set_webhook()
    print("Приложение запущено локально (если не используется gunicorn)")
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
