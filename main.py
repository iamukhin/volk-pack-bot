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
    user = update.effective_user
    await update.message.reply_text(f'Бот "Стая Волков" запущен! Привет, {user.first_name}! 🐺\nПиши мне отчёты в свою тему!')

async def help_command(update, context):
    """Отправляет сообщение при получении команды /help."""
    help_text = (
        "Формат отчёта:\n"
        "отжимания 100, приседания 200, пресс 50\n"
        "Или: день 5, берпи 60, подтягивания 30"
    )
    await update.message.reply_text(help_text)

def main():
    """Запускает бота."""
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # На Bothost всегда используем вебхук
    # Определяем URL вебхука (адрес, куда Telegram будет слать сообщения)
    # Bothost обычно предоставляет домен вида: ваш-бот-12345.bothost.app
    # Нужно узнать ваш домен на Bothost
    webhook_host = os.environ.get('BOTHOST_HOST', '')  # Bothost может установить эту переменную
    port = int(os.environ.get('PORT', 8080))
    
    if webhook_host:
        # Если хост известен, используем вебхук
        webhook_url = f"https://{webhook_host}/{BOT_TOKEN}"
        logger.info(f"Запуск с вебхуком: {webhook_url}")
        
        # Запускаем вебхук
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        # Если хост неизвестен, запускаем в режиме polling (для отладки)
        # Bothost может не передавать переменную, поэтому добавим fallback
        logger.info("Переменная BOTHOST_HOST не найдена. Запуск в режиме polling...")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
