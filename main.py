import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN, FORUM_CHAT_ID, RATING_TOPIC_ID, ADMIN_IDS, EXERCISES, TIMEZONE

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Простая команда для проверки
async def start(update, context):
    """Отправляет сообщение при получении команды /start."""
    await update.message.reply_text('Бот "Стая Волков" запущен! 🐺\nПиши мне отчёты в свою тему!')

async def help_command(update, context):
    """Отправляет сообщение при получении команды /help."""
    await update.message.reply_text('Формат отчёта: "отжимания 100, приседания 200"')

def main():
    """Запускает бота."""
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем вебхук (нужно для Bothost)
    port = int(os.environ.get('PORT', 8080))
    webhook_url = os.environ.get('BOTHOST_URL', '') + "/" + BOT_TOKEN
    
    if webhook_url:
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url
        )
    else:
        # Локальный запуск для отладки
        logger.info("Запуск в режиме polling (локально)...")
        application.run_polling()

if __name__ == '__main__':
    main()
