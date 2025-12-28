import logging
import os
import re
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from config import BOT_TOKEN, FORUM_CHAT_ID, RATING_TOPIC_ID, ADMIN_IDS, EXERCISES, TIMEZONE
import database

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем базу данных при запуске
database.init_db()

# ---------- КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение при получении команды /start."""
    user = update.effective_user
    await update.message.reply_text(f'Бот "Стая Волков" запущен! Привет, {user.first_name}! 🐺\nПиши отчёты в свою тему!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение при получении команды /help."""
    help_text = (
        "📋 *Формат отчёта:*\n"
        "`отжимания 100, приседания 200, пресс 50`\n"
        "Или: `день 5, берпи 60, подтягивания 30`\n\n"
        "📊 *Минимумы для зачёта:*\n"
        "• Отжимания: 100\n"
        "• Приседания: 100\n"
        "• Пресс: 50\n"
        "• Бёрпи: 50\n"
        "• Подтягивания: 30\n\n"
        "⚠️ Упражнения *не суммируются*! По каждому своя норма."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет нового участника (только для админов)."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Только админы могут добавлять участников.")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "Формат: /add_user @username Имя Прозвище topic_id\n"
            "Пример: /add_user @is_Yasha Яша ЦАРЬ_ХАЧАПУРИ 14"
        )
        return
    
    telegram_username = context.args[0].replace('@', '')
    name = context.args[1]
    nickname = context.args[2]
    try:
        topic_id = int(context.args[3])
    except ValueError:
        await update.message.reply_text("❌ topic_id должен быть числом.")
        return
    
    # Здесь нужно получить telegram_id по username (упрощённо)
    # В реальности нужно хранить telegram_id при добавлении
    # Пока используем topic_id как временный идентификатор
    success = database.add_user(topic_id, name, nickname, topic_id)
    
    if success:
        await update.message.reply_text(f"✅ Участник {name} ({nickname}) добавлен!")
    else:
        await update.message.reply_text("❌ Ошибка при добавлении.")

# ---------- ПАРСИНГ ОТЧЁТОВ ----------
def parse_report(text: str):
    """Парсит текст отчёта и возвращает словарь с упражнениями."""
    text = text.lower().replace('день', '').replace(':', ' ').replace(',', ' ')
    
    # Шаблоны для поиска: "отжимания 100" или "100 отжиманий"
    patterns = {
        'отжимания': r'(?:отжимания|отжиманий|отжим)\s*(\d+)',
        'приседания': r'(?:приседания|приседаний|присед)\s*(\d+)',
        'пресс': r'(?:пресс|пресса)\s*(\d+)',
        'берпи': r'(?:берпи|бурпи|бёрпи)\s*(\d+)',
        'бурпи': r'(?:берпи|бурпи|бёрпи)\s*(\d+)',
        'подтягивания': r'(?:подтягивания|подтягиваний|подтяг)\s*(\d+)',
    }
    
    result = {}
    for exercise, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[exercise] = int(match.group(1))
    
    return result

def calculate_points(exercises_dict):
    """Рассчитывает очки и проверяет минимумы."""
    total_points = 0
    day_completed = True
    failed_exercises = []
    
    for exercise, count in exercises_dict.items():
        if exercise in EXERCISES:
            points_per_rep, minimum = EXERCISES[exercise]
            points = count * points_per_rep
            
            if count >= minimum:
                total_points += points
            else:
                day_completed = False
                failed_exercises.append((exercise, count, minimum))
    
    return total_points, day_completed, failed_exercises

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает отчёт пользователя."""
    # Проверяем, что сообщение из темы форума
    if not update.message or not update.message.message_thread_id:
        return
    
    topic_id = update.message.message_thread_id
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return
    
    # Парсим отчёт
    exercises = parse_report(text)
    if not exercises:
        # Не похоже на отчёт
        return
    
    # Рассчитываем очки
    points, day_completed, failed = calculate_points(exercises)
    
    # Формируем ответ
    if day_completed:
        response = f"✅ *Отчёт принят!*\n"
        for ex, count in exercises.items():
            response += f"• {ex}: {count}\n"
        response += f"\n🎯 *Очки за день:* {points:.1f}\n"
        response += "🔥 *День засчитан!* Так держать, братишка! 🐺"
    else:
        response = f"⚠️ *Есть недобор!*\n"
        for ex, count, minimum in failed:
            response += f"• {ex}: {count} из {minimum}\n"
        response += "\n📢 *Дополни до минимума до 23:59!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ---------- ОСНОВНАЯ ФУНКЦИЯ ----------
def main():
    """Запускает бота."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_user", add_user_command))
    
    # Обработчик текстовых сообщений (для отчётов)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report))
    
    # На Bothost всегда используем вебхук
    webhook_host = os.environ.get('BOTHOST_HOST', '')
    port = int(os.environ.get('PORT', 8080))
    
    if webhook_host:
        webhook_url = f"https://{webhook_host}/{BOT_TOKEN}"
        logger.info(f"Запуск с вебхуком: {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        logger.info("Переменная BOTHOST_HOST не найдена. Запуск в режиме polling...")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
