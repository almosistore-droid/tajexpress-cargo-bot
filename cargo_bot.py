import os
import telebot
from telebot import types
from flask import Flask, request
from telebot.apihelper import ApiTelegramException

# --- 1. КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ И ТОКЕНА ---
# Токен читается из переменной окружения (установлен на Render)
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    # В среде Render это должно быть видно в логах, если токен не установлен
    print("FATAL ERROR: TELEGRAM TOKEN IS NOT SET IN ENVIRONMENT!")

# Инициализация Flask-приложения (КРИТИЧЕСКИ ВАЖНО: ПЕРЕД @app.route)
# Flask должен быть готов принимать Webhook
app = Flask(__name__) 

# Инициализация бота
bot = telebot.TeleBot(TOKEN, use_class_middlewares=True)

# --- 2. КОНФИГУРАЦИЯ WEBHOOK ---
# На Render URL сервиса будет другой, но маршрут остается /TOKEN
# WEBHOOK_ROUTE должен использовать TOKEN, который уже определен.
WEBHOOK_ROUTE = '/' + TOKEN

# Примечание: Render автоматически обнаружит порт (обычно $PORT или 10000)
# и перенаправит трафик на него.

@app.route(WEBHOOK_ROUTE, methods=['POST'])
def webhook():
    """Обрабатывает входящие обновления Telegram через Webhook."""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'ok', 200
    else:
        return 'Not JSON', 403

def set_webhook(webhook_url):
    """Устанавливает или удаляет Webhook. Вызывается после получения URL от Render."""
    try:
        # Сначала удаляем старый Webhook 
        bot.delete_webhook(drop_pending_updates=True)
        print("WEBHOOK: Старый Webhook удален.")

        # Устанавливаем новый Webhook, используя URL, предоставленный Render
        bot.set_webhook(url=webhook_url + TOKEN)
        print(f"WEBHOOK: Новый Webhook установлен на: {webhook_url + TOKEN}")
    except ApiTelegramException as e:
        print(f"WEBHOOK Ошибка Telegram API: {e}")
    except Exception as e:
        print(f"WEBHOOK Неизвестная ошибка: {e}")

# --- 3. ОБРАБОТЧИКИ БОТА (Логика остается той же) ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Отправляет приветственное сообщение и основное меню."""
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    btn1 = types.KeyboardButton("Рассчитать стоимость")
    btn2 = types.KeyboardButton("Отследить груз")
    btn3 = types.KeyboardButton("Связаться с нами")
    markup.add(btn1, btn2, btn3)

    bot.send_message(
        message.chat.id,
        "Привет! Я бот компании TAJ-EXPRESS. Как я могу вам помочь сегодня?",
        reply_markup=markup
    )

@bot.message_handler(commands=['test'])
def send_test_message(message):
    """Тестовая команда для проверки работоспособности."""
    bot.send_message(message.chat.id, "Бот работает. Токен получен, Webhook активен.")

@bot.message_handler(func=lambda message: message.text == "Рассчитать стоимость")
def request_calculation(message):
    """Начинает процесс расчета стоимости."""
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

@bot.message_handler(func=lambda message: message.text == "Отследить груз")
def track_cargo(message):
    """Запрашивает номер для отслеживания."""
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

@bot.message_handler(func=lambda message: message.text == "Связаться с нами")
def contact_us(message):
    """Предоставляет контактную информацию."""
    contact_info = (
        "📞 **Наши контакты:**\n\n"
        "Служба поддержки: `+7 495 123 45 67`\n"
        "Email: `support@tajexpress.com`\n"
        "Менеджер: `@TajExpressManager`\n"
    )
    bot.send_message(message.chat.id, contact_info, parse_mode='Markdown')
    send_welcome(message)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Обработчик для любых других текстовых сообщений."""
    bot.reply_to(message, "Извините, я не понял эту команду. Пожалуйста, используйте кнопки меню или команду /start.")

# --- 4. ЗАПУСК ДЛЯ WEBHOOK (ПРИМЕНЕНИЕ) ---
if __name__ == '__main__':
    # Эта часть не выполняется на Render, так как запускает gunicorn, но оставляем для полноты.
    print("Приложение запущено локально (если не используется gunicorn)")
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 5000))
