import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def init_db():
    """Инициализирует базу данных и создаёт таблицы, если их нет."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей (ДОБАВЛЕНО freeze_days)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            nickname TEXT,
            topic_id INTEGER UNIQUE,
            current_streak INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            freeze_days INTEGER DEFAULT 0,
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

def save_daily_stats(user_topic_id, exercises_dict, points, day_completed):
    """Сохраняет ежедневную статистику пользователя."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id FROM users WHERE topic_id = ?', (user_topic_id,))
        user = cursor.fetchone()
        
        if not user:
            logger.error(f"Пользователь с topic_id {user_topic_id} не найден")
            return False
        
        user_id = user[0]
        today = datetime.now().date()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats 
            (user_id, date, pushups, squats, abs, burpees, pullups, total_points, day_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, today,
            exercises_dict.get('отжимания', 0),
            exercises_dict.get('приседания', 0),
            exercises_dict.get('пресс', 0),
            exercises_dict.get('берпи', 0),  # ТОЛЬКО берпи, без сложения
            exercises_dict.get('подтягивания', 0),
            points,
            1 if day_completed else 0
        ))
        
        if day_completed:
            cursor.execute('''
                UPDATE users 
                SET current_streak = current_streak + 1,
                    total_points = total_points + ?
                WHERE id = ?
            ''', (points, user_id))
        else:
            cursor.execute('UPDATE users SET current_streak = 0 WHERE id = ?', (user_id,))
        
        conn.commit()
        logger.info(f"Сохранена статистика для user_id {user_id}: {points} очков")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")
        return False
    finally:
        conn.close()

def get_today_rating():
    """Возвращает рейтинг за сегодняшний день."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    cursor.execute('''
        SELECT u.name, u.nickname, u.current_streak, ds.total_points,
               ds.pushups, ds.squats, ds.abs, ds.burpees, ds.pullups
        FROM users u
        LEFT JOIN daily_stats ds ON u.id = ds.user_id AND ds.date = ?
        WHERE u.is_active = 1
        ORDER BY ds.total_points DESC, u.current_streak DESC
    ''', (today,))
    
    rating = cursor.fetchall()
    conn.close()
    return rating

def get_user_by_topic(topic_id):
    """Возвращает информацию о пользователе по ID темы."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, nickname, current_streak, total_points, freeze_days
        FROM users WHERE topic_id = ?
    ''', (topic_id,))
    
    user = cursor.fetchone()
    conn.close()
    return user

def use_freeze_day(user_topic_id):
    """Использовать один день заморозки."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE users 
            SET freeze_days = freeze_days - 1,
                current_streak = current_streak + 1
            WHERE topic_id = ? AND freeze_days > 0
        ''', (user_topic_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        
        # Создаём запись в daily_stats о использовании заморозки
        if success:
            cursor.execute('SELECT id FROM users WHERE topic_id = ?', (user_topic_id,))
            user = cursor.fetchone()
            if user:
                user_id = user[0]
                today = datetime.now().date()
                cursor.execute('''
                    INSERT OR IGNORE INTO daily_stats 
                    (user_id, date, day_completed)
                    VALUES (?, ?, 1)
                ''', (user_id, today))
                conn.commit()
        
        conn.close()
        return success
        
    except Exception as e:
        logger.error(f"Ошибка использования заморозки: {e}")
        conn.close()
        return False

def buy_freeze_day(user_topic_id, cost_points):
    """Купить день заморозки за очки."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        # Проверяем, хватает ли очков
        cursor.execute('SELECT total_points FROM users WHERE topic_id = ?', (user_topic_id,))
        user = cursor.fetchone()
        
        if not user or user[0] < cost_points:
            return False
        
        # Списываем очки и добавляем день заморозки
        cursor.execute('''
            UPDATE users 
            SET total_points = total_points - ?,
                freeze_days = freeze_days + 1
            WHERE topic_id = ?
        ''', (cost_points, user_topic_id))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
        
    except Exception as e:
        logger.error(f"Ошибка покупки заморозки: {e}")
        conn.close()
        return False

def get_all_users():
    """Возвращает всех пользователей."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT name, nickname, topic_id, current_streak, total_points, freeze_days
        FROM users WHERE is_active = 1
        ORDER BY name
    ''')
    
    users = cursor.fetchall()
    conn.close()
    return users

def reset_all_stats():
    """Сбрасывает всю статистику."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET current_streak = 0, total_points = 0, freeze_days = 0')
        cursor.execute('DELETE FROM daily_stats')
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка сброса статистики: {e}")
        return False
    finally:
        conn.close()

def reset_today_stats():
    """Сбрасывает сегодняшнюю статистику."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        today = datetime.now().date()
        cursor.execute('DELETE FROM daily_stats WHERE date = ?', (today,))
        cursor.execute('UPDATE users SET current_streak = 0')
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Ошибка сброса сегодняшней статистики: {e}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    print("База данных создана. Добавьте пользователей командой /add_user")
