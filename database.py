import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    """Инициализирует базу данных и создаёт таблицы, если их нет."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            nickname TEXT,
            topic_id INTEGER UNIQUE,
            current_streak INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Таблица ежедневной статистики
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            pushups INTEGER DEFAULT 0,
            squats INTEGER DEFAULT 0,
            abs INTEGER DEFAULT 0,
            burpees INTEGER DEFAULT 0,
            pullups INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            day_completed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица фраз
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            text TEXT,
            media_path TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def add_user(telegram_id, name, nickname, topic_id):
    """Добавляет нового пользователя в базу."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO users (telegram_id, name, nickname, topic_id)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, name, nickname, topic_id))
        conn.commit()
        logger.info(f"Добавлен пользователь: {name} ({nickname})")
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("База данных создана. Добавьте пользователей командой /add_user")
