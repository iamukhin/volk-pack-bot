import logging
import os
import re
import random
from datetime import datetime, time
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update

from config import BOT_TOKEN, FORUM_CHAT_ID, RATING_TOPIC_ID, ADMIN_IDS, EXERCISES, TIMEZONE
import database

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем базу данных
database.init_db()

# ---------- КОМАНДЫ ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f'Бот "Стая Волков" запущен! Привет, {user.first_name}! 🐺\nПиши отчёты в свою тему!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Используем topic_id как временный telegram_id
    success = database.add_user(topic_id, name, nickname, topic_id)
    
    if success:
        await update.message.reply_text(f"✅ Участник {name} ({nickname}) добавлен!")
    else:
        await update.message.reply_text("❌ Ошибка при добавлении.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику пользователя."""
    if not update.message or not update.message.message_thread_id:
        await update.message.reply_text("Эта команда работает только в личных темах.")
        return
    
    topic_id = update.message.message_thread_id
    user = database.get_user_by_topic(topic_id)
    
    if not user:
        await update.message.reply_text("❌ Вы не зарегистрированы. Обратитесь к админу.")
        return
    
    name, nickname, streak, total_points = user
    response = (
        f"📊 *Статистика {name} ({nickname})*\n"
        f"🔥 Серия дней: {streak}\n"
        f"🏆 Всего очков: {total_points}\n"
        f"🐺 Держись, братишка!"
    )
    await update.message.reply_text(response, parse_mode='Markdown')

# ---------- ПАРСИНГ И СОХРАНЕНИЕ ОТЧЁТОВ ----------
def parse_report(text: str):
    text = text.lower().replace('день', '').replace(':', ' ').replace(',', ' ')
    
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
    if not update.message or not update.message.message_thread_id:
        return
    
    topic_id = update.message.message_thread_id
    text = update.message.text
    
    if not text:
        return
    
    exercises = parse_report(text)
    if not exercises:
        return
    
    points, day_completed, failed = calculate_points(exercises)
    
    # Сохраняем в БД
    database.save_daily_stats(topic_id, exercises, points, day_completed)
    
    # Формируем ответ
    if day_completed:
        praise = [
            "🔥 Отлично, братишка! День засчитан!",
            "🐺 Стая гордится тобой! Так держать!",
            "💪 Мощно! Очки твои, серия растёт!",
            "🏔️ Царь горы! Продолжай в том же духе!",
            "🎯 В яблочко! Ты сегодня - анаконда!"
        ]
        response = f"✅ *Отчёт принят!*\n"
        for ex, count in exercises.items():
            response += f"• {ex}: {count}\n"
        response += f"\n🎯 *Очки за день:* {points:.1f}\n"
        response += f"📈 *{random.choice(praise)}*"
    else:
        response = f"⚠️ *Есть недобор!*\n"
        for ex, count, minimum in failed:
            response += f"• {ex}: {count} из {minimum}\n"
        response += "\n📢 *Дополни до минимума до 23:59!*"
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ---------- РАСПИСАНИЕ (исправлено для вебхука) ----------
async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет утреннее сообщение в 8:00 МСК = 4:00 NSK."""
    morning_phrases = [
        "☀️ Доброе утро, стая! Просыпайтесь, львы! Сегодня день новых побед!",
        "🐺 Эй, волки! Солнце встало, пора показывать зубы! Кто сегодня король горы?",
        "💪 Утро, братишки! Сегодняшний день принадлежит сильнейшим! За работу!",
        "🏔️ Стая, подъём! Горы не ждут. Кто сделает первые 100 отжиманий?"
    ]
    
    phrase = random.choice(morning_phrases)
    
    try:
        await context.bot.send_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=RATING_TOPIC_ID,
            text=f"*{phrase}*",
            parse_mode='Markdown'
        )
        logger.info("Утреннее сообщение отправлено (8:00 МСК = 4:00 NSK)")
    except Exception as e:
        logger.error(f"Ошибка отправки утреннего сообщения: {e}")

async def send_fact(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет факт в 12:00 МСК = 8:00 NSK."""
    facts = [
        "💡 Факт: 20 отжиманий сжигают примерно 10 калорий. 100 отжиманий = 50 калорий = 1 яблоко!",
        "🐺 Факт: Волки в стае могут пробежать до 200 км за сутки. А ты сколько приседаний сделаешь?",
        "💪 Факт: Мышцы начинают 'гореть' из-за молочной кислоты. Это знак роста!",
        "🏔️ Факт: Самая длинная серия отжиманий — 10,507 раз за 24 часа. Но мы скромнее — 100 в день!",
        "🔥 Факт: После тренировки метаболзм остаётся повышенным до 48 часов. Качаешься даже во сне!"
    ]
    
    fact = random.choice(facts)
    
    try:
        await context.bot.send_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=RATING_TOPIC_ID,
            text=f"*📚 ФАКТ ДНЯ*\n\n{fact}",
            parse_mode='Markdown'
        )
        logger.info("Факт отправлен (12:00 МСК = 8:00 NSK)")
    except Exception as e:
        logger.error(f"Ошибка отправки факта: {e}")

async def send_rating(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет рейтинг в 10:00 МСК = 6:00 NSK."""
    rating = database.get_today_rating()
    
    if not rating:
        text = "📊 *Рейтинг за сегодня*\n\nПока никто не отчитался. Стая, вы где? 🐺"
    else:
        text = "🏔️ *ВЕРШИНА СИЛЫ | Рейтинг за сегодня*\n\n"
        for i, (name, nickname, streak, points, push, squat, abs_cnt, burp, pull) in enumerate(rating, 1):
            text += f"{i}. *{name} {nickname}*"
            if streak > 0:
                text += f" [Серия: {str(streak)+'🔥' if streak >= 3 else streak}]\n"
            else:
                text += "\n"
            
            if points:
                text += f"   Очки: {points:.1f} | "
                if push: text += f"Отж: {push} "
                if squat: text += f"Прис: {squat} "
                if abs_cnt: text += f"Пр: {abs_cnt} "
                if burp: text += f"Бер: {burp} "
                if pull: text += f"Под: {pull}"
                text += "\n"
            else:
                text += "   Ещё не отчитался\n"
    
    try:
        await context.bot.send_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=RATING_TOPIC_ID,
            text=text,
            parse_mode='Markdown'
        )
        logger.info("Рейтинг отправлен (10:00 МСК = 6:00 NSK)")
    except Exception as e:
        logger.error(f"Ошибка отправки рейтинга: {e}")

async def send_evening_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вечернее напоминание в 21:00 МСК = 17:00 NSK."""
    evening_phrases = [
        "🌙 Эй, стая! Не забыли про тренировку? До 23:59 осталось мало времени!",
        "🐺 Вечер, братишки! Кто ещё не отчитался? Пора показывать результат!",
        "💀 Волки, время поджимает! Не дайте серии сгореть!",
        "🏆 Вечерняя проверка! Кто сегодня в топе? Отчитывайтесь!"
    ]
    
    phrase = random.choice(evening_phrases)
    
    try:
        await context.bot.send_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=RATING_TOPIC_ID,
            text=f"*{phrase}*",
            parse_mode='Markdown'
        )
        logger.info("Вечернее напоминание отправлено (21:00 МСК = 17:00 NSK)")
    except Exception as e:
        logger.error(f"Ошибка отправки вечернего напоминания: {e}")

async def send_night_check(context: ContextTypes.DEFAULT_TYPE):
    """Проверка в 23:59 МСК = 19:59 NSK и троллинг тех, кто не отчитался."""
    from datetime import date
    
    conn = database.sqlite3.connect('volk_bot.db')
    cursor = conn.cursor()
    
    today = date.today()
    
    # Находим всех активных пользователей
    cursor.execute('''
        SELECT u.topic_id, u.name, u.nickname, u.current_streak, 
               COALESCE(ds.day_completed, 0) as completed
        FROM users u
        LEFT JOIN daily_stats ds ON u.id = ds.user_id AND ds.date = ?
        WHERE u.is_active = 1
    ''', (today,))
    
    users = cursor.fetchall()
    conn.close()
    
    troll_messages = [
        "💀 {name} {nickname}! Стая не прощает слабину! Серия из {streak} дней сгорела!",
        "🐺 Эх, {name}... Волк должен быть голодным каждый день! {streak} дней в помойке!",
        "🏔️ {name} {nickname} сорвался с горы! {streak} дней полетели в тартары!",
        "🔥 Пламя погасло! {name} не отчитался! {streak}-дневная серия уничтожена!"
    ]
    
    no_fails_message = "🎉 *Стая в полном составе!* Все львы отчитались сегодня! 🦁"
    
    fails_exist = False
    fail_text = "🪦 *КОГО СТАЯ ПОТЕРЯЛА*\n\n"
    
    for topic_id, name, nickname, streak, completed in users:
        if not completed:  # Не отчитался
            fails_exist = True
            # Сбрасываем серию в БД
            database.sqlite3.connect('volk_bot.db').execute(
                'UPDATE users SET current_streak = 0 WHERE topic_id = ?',
                (topic_id,)
            ).connection.commit()
            
            # Формируем сообщение троллинга
            troll_msg = random.choice(troll_messages).format(
                name=name, nickname=nickname, streak=streak
            )
            fail_text += f"• {troll_msg}\n"
            
            # Отправляем троллинг в личную тему
            try:
                app = Application.builder().token(BOT_TOKEN).build()
                await app.bot.send_message(
                    chat_id=FORUM_CHAT_ID,
                    message_thread_id=topic_id,
                    text=f"*{troll_msg}*\n\nЗавтра исправляйся! 💪",
                    parse_mode='Markdown'
                )
                await app.shutdown()
                logger.info(f"Троллинг отправлен {name} в тему {topic_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки троллинга {name}: {e}")
    
    # Отправляем итог в общую тему
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        if fails_exist:
            await app.bot.send_message(
                chat_id=FORUM_CHAT_ID,
                message_thread_id=RATING_TOPIC_ID,
                text=fail_text,
                parse_mode='Markdown'
            )
        else:
            await app.bot.send_message(
                chat_id=FORUM_CHAT_ID,
                message_thread_id=RATING_TOPIC_ID,
                text=no_fails_message,
                parse_mode='Markdown'
            )
        await app.shutdown()
        logger.info("Ночная проверка завершена")
    except Exception as e:
        logger.error(f"Ошибка ночной проверки: {e}")

def setup_job_queue(application: Application):
    """Настраивает планировщик задач."""
    job_queue = application.job_queue
    
    # Сервер в Новосибирске (UTC+7), Москва (UTC+3) = разница -4 часа
    # 8:00 МСК = 4:00 NSK - утро
    job_queue.run_daily(send_morning_message, time=time(hour=4, minute=0, second=0))
    
    # 10:00 МСК = 6:00 NSK - рейтинг
    job_queue.run_daily(send_rating, time=time(hour=6, minute=0, second=0))
    
    # 12:00 МСК = 8:00 NSK - факт
    job_queue.run_daily(send_fact, time=time(hour=8, minute=0, second=0))
    
    # 21:00 МСК = 17:00 NSK - вечер
    job_queue.run_daily(send_evening_reminder, time=time(hour=17, minute=0, second=0))
    
    # 23:59 МСК = 19:59 NSK - ночная проверка
    job_queue.run_daily(send_night_check, time=time(hour=19, minute=59, second=0))
    
    logger.info("Планировщик задач настроен (время сервера NSK UTC+7)")

# ---------- ОСНОВНАЯ ФУНКЦИЯ ----------
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_user", add_user_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчик отчётов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report))
    
    # Настраиваем расписание
    setup_job_queue(application)
    
    # Запускаем
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
        logger.info("Запуск в режиме polling...")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
