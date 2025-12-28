def save_daily_stats(user_topic_id, exercises_dict, points, day_completed):
    """Сохраняет ежедневную статистику пользователя."""
    conn = sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    try:
        # Находим ID пользователя по topic_id
        cursor.execute('SELECT id FROM users WHERE topic_id = ?', (user_topic_id,))
        user = cursor.fetchone()
        
        if not user:
            logger.error(f"Пользователь с topic_id {user_topic_id} не найден")
            return False
        
        user_id = user[0]
        today = datetime.now().date()
        
        # Обновляем или вставляем запись за сегодня
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats 
            (user_id, date, pushups, squats, abs, burpees, pullups, total_points, day_completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, today,
            exercises_dict.get('отжимания', 0),
            exercises_dict.get('приседания', 0),
            exercises_dict.get('пресс', 0),
            exercises_dict.get('берпи', 0) + exercises_dict.get('бурпи', 0),
            exercises_dict.get('подтягивания', 0),
            points,
            1 if day_completed else 0
        ))
        
        # Если день засчитан, обновляем streak и total_points пользователя
        if day_completed:
            cursor.execute('''
                UPDATE users 
                SET current_streak = current_streak + 1,
                    total_points = total_points + ?
                WHERE id = ?
            ''', (points, user_id))
        else:
            # Если день не засчитан, сбрасываем серию
            cursor.execute('''
                UPDATE users SET current_streak = 0 WHERE id = ?
            ''', (user_id,))
        
        conn.commit()
        logger.info(f"Сохранена статистика для user_id {user_id}: {points} очков")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")
        return False
    finally:
        conn.close()
