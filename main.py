import logging
from config import BOT_TOKEN, FORUM_CHAT_ID, RATING_TOPIC_ID, MY_TOPIC_ID, ADMIN_IDS

# Настраиваем логирование, чтобы видеть ошибки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота."""
    from telegram.ext import Application
    
    # Создаём приложение бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Здесь позже будут команды и обработчики
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=[])

if __name__ == '__main__':
    main()
