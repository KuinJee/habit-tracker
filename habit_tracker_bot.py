import os
import json
import asyncio
from datetime import datetime, time, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, BotCommand
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue, ConversationHandler, MessageHandler, filters
)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7742690883:AAFClrtlv4YYlKzFTI5oID6yWkTqke0SBV4')

# Состояния для ConversationHandler
SETTING_REMINDER_TIME = 0
SETTING_CUSTOM_GLOBAL_TIME = 1
SELECT_PERIOD, SELECT_HABIT_FOR_STATS = 2, 3
RENAMING_HABIT = 4

def load_data():
    try:
        # Получаем абсолютный путь к папке, где находится скрипт
        script_dir = os.path.dirname(os.path.abspath(__file__))
        habits_file = os.path.join(script_dir, 'habits.json')
        if os.path.exists(habits_file):
            with open(habits_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        return {}
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return {}

def save_data(data):
    try:
        # Получаем абсолютный путь к папке, где находится скрипт
        script_dir = os.path.dirname(os.path.abspath(__file__))
        habits_file = os.path.join(script_dir, 'habits.json')
        with open(habits_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def get_user_data(user_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"habits": {}}
    return data[str(user_id)]

def update_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

def _create_habit_list_message(user_id):
    """Создает текст и кнопки для списка привычек."""
    user_data = get_user_data(user_id)
    habits = user_data.get('habits', {})

    if not habits:
        return {
            "text": "📝 У тебя пока нет привычек. Добавь новую, просто написав мне ее название.",
            "reply_markup": None,
            "parse_mode": 'Markdown'
        }

    today = datetime.now().strftime('%Y-%m-%d')
    list_text = "📋 **Твои привычки**\n\n"
    
    for habit_name, habit_info in habits.items():
        if isinstance(habit_info, dict):
            dates = habit_info.get('dates', [])
        else:
            dates = habit_info
        
        is_done_today = today in dates
        status_emoji = "✅" if is_done_today else "⏳"
        
        list_text += f"{status_emoji} **{habit_name}**\n\n"

    buttons = [
        [
            InlineKeyboardButton("✅ Выполнение", callback_data="menu_today"),
            InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")
        ],
        [
            InlineKeyboardButton("✍️ Изменение", callback_data="menu_manage"),
            InlineKeyboardButton("⏰ Напоминания", callback_data="menu_reminder")
        ],
        [
            InlineKeyboardButton("➕ Добавить", callback_data="menu_add")
        ]
    ]
    
    return {
        "text": list_text,
        "reply_markup": InlineKeyboardMarkup(buttons),
        "parse_mode": 'Markdown'
    }

async def _send_habit_list(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет обновленный список привычек."""
    if hasattr(query_or_update, 'from_user'):
        user_id = query_or_update.from_user.id
    elif hasattr(query_or_update, 'effective_user'):
        user_id = query_or_update.effective_user.id
    else:
        # Fallback для других типов объектов
        user_id = query_or_update.from_user.id if hasattr(query_or_update, 'from_user') else None
    
    message_data = _create_habit_list_message(user_id)
    
    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(**message_data)
    else:
        await query_or_update.message.reply_text(**message_data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await setup_commands(context.application)
        
        # Восстанавливаем напоминания при первом запуске /start - АСИНХРОННО
        if not hasattr(context.application, '_reminders_restored'):
            print("[INIT] Восстанавливаем напоминания при первом запуске...")
            await restore_reminders_async(context)
            context.application._reminders_restored = True
        
        welcome_text = """
🤖 **Привет! Я бот для отслеживания привычек**

Я помогу тебе развить полезные привычки и следить за своим прогрессом. Просто напиши мне название привычки, чтобы добавить ее.

Ниже твой текущий список привычек.
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await list_habits(update, context)
    except Exception as e:
        print(f"Ошибка в функции start: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def list_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_data = _create_habit_list_message(user_id)
    await update.message.reply_text(**message_data)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await list_habits(update, context)

# ===== ПРОСТАЯ СИСТЕМА ДОБАВЛЕНИЯ ПРИВЫЧЕК =====

async def add_habit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для добавления привычек."""
    habit = update.message.text.strip()
    if not habit:
        return

    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    if habit in user_data.get('habits', {}):
        await update.message.reply_text(f"Привычка «{habit}» уже есть.")
        return

    user_data.setdefault('habits', {})[habit] = {
        "dates": [],
        "reminder_time": None
    }
    update_user_data(user_id, user_data)
    
    # Сохраняем привычку в контексте для возможной установки напоминания
    context.user_data['new_habit'] = habit
    
    buttons = [
        [InlineKeyboardButton("Да, установить время", callback_data="new_habit_set_time")],
        [InlineKeyboardButton("Нет, пропустить", callback_data="new_habit_skip")]
    ]
    await update.message.reply_text(
        f"Привычка «{habit}» добавлена! Хотите установить время напоминания?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ===== НОВАЯ СИСТЕМА НАПОМИНАНИЙ =====

async def handle_new_habit_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка установки напоминания для новой привычки."""
    query = update.callback_query
    await query.answer()
    
    habit = context.user_data.get('new_habit')
    if not habit:
        await query.edit_message_text("Ошибка: привычка не найдена.")
        return ConversationHandler.END
    
    if query.data == "new_habit_skip":
        await query.edit_message_text(f"✅ Привычка «{habit}» добавлена без напоминания!")
        context.user_data.pop('new_habit', None)
        # Убираем sleep - показываем список сразу
        await _send_habit_list(query, context)
        return ConversationHandler.END
    
    # Устанавливаем состояние для ввода времени
    context.user_data['setting_time_for'] = habit
    
    buttons = [
        [InlineKeyboardButton("🌅 Утро (09:00)", callback_data="time_09:00")],
        [InlineKeyboardButton("🌙 Вечер (23:00)", callback_data="time_23:00")],
        [InlineKeyboardButton("⏰ Другое время", callback_data="time_custom")],
        [InlineKeyboardButton("❌ Отмена", callback_data="time_cancel")]
    ]
    
    await query.edit_message_text(
        "Выберите время напоминания:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return SETTING_REMINDER_TIME

async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени напоминания."""
    query = update.callback_query
    await query.answer()
    
    habit = context.user_data.get('setting_time_for') or context.user_data.get('new_habit')
    if not habit:
        await query.edit_message_text("Ошибка: привычка не найдена.")
        return ConversationHandler.END
    
    if query.data == "time_cancel":
        await query.edit_message_text(f"✅ Привычка «{habit}» добавлена без напоминания!")
        context.user_data.pop('new_habit', None)
        context.user_data.pop('setting_time_for', None)
        # Убираем sleep - показываем список сразу
        await _send_habit_list(query, context)
        return ConversationHandler.END
    
    if query.data == "time_custom":
        await query.edit_message_text(
            "⏰ **Введите время напоминания**\n\n"
            "Формат: ЧЧ:ММ (например, 14:30)\n"
            "Время должно быть в 24-часовом формате.\n\n"
            "Введите время или нажмите /cancel для отмены:",
            parse_mode='Markdown'
        )
        return SETTING_REMINDER_TIME
    
    # Обработка предустановленного времени
    if query.data.startswith("time_"):
        time_str = query.data.replace("time_", "")
        if time_str == "disable":
            await disable_habit_reminder(query, context, habit)
        else:
            await save_habit_reminder_time(query, context, habit, time_str)
        return ConversationHandler.END

async def handle_custom_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода произвольного времени."""
    time_str = update.message.text.strip()
    habit = context.user_data.get('setting_time_for') or context.user_data.get('new_habit')
    
    if not habit:
        await update.message.reply_text("❌ Ошибка: привычка не найдена.")
        return ConversationHandler.END
    
    try:
        time_obj = datetime.strptime(time_str, '%H:%M').time()
        time_str = time_obj.strftime('%H:%M')
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 09:00)\n"
            "Попробуйте еще раз или нажмите /cancel для отмены."
        )
        return SETTING_REMINDER_TIME
    
    await save_habit_reminder_time(update, context, habit, time_str)
    return ConversationHandler.END

async def save_habit_reminder_time(query_or_update, context: ContextTypes.DEFAULT_TYPE, habit: str, time_str: str):
    """Сохраняет время напоминания для привычки."""
    if hasattr(query_or_update, 'from_user'):
        user_id = query_or_update.from_user.id
    elif hasattr(query_or_update, 'effective_user'):
        user_id = query_or_update.effective_user.id
    else:
        user_id = None
    
    user_data = get_user_data(user_id)
    
    if habit in user_data.get('habits', {}):
        if isinstance(user_data['habits'][habit], dict):
            user_data['habits'][habit]['reminder_time'] = time_str
        else:
            user_data['habits'][habit] = {
                'dates': user_data['habits'][habit],
                'reminder_time': time_str
            }
        
        update_user_data(user_id, user_data)
        
        # Планируем напоминание и проверяем результат
        if schedule_reminder(context, user_id, habit, time_str):
            message = f"✅ Напоминание для привычки «{habit}» установлено на {time_str}!"
        else:
            message = f"⚠️ Напоминание установлено, но возможны проблемы с планировщиком для «{habit}» на {time_str}."
        
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(message)
        else:
            await query_or_update.message.reply_text(message)
        
        context.user_data.pop('new_habit', None)
        context.user_data.pop('setting_time_for', None)
        
        # Убираем sleep - показываем список сразу
        await _send_habit_list(query_or_update, context)
    else:
        # Обработка случая, когда привычка не найдена
        error_message = f"❌ Ошибка: привычка «{habit}» не найдена."
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(error_message)
        else:
            await query_or_update.message.reply_text(error_message)
        
        context.user_data.pop('new_habit', None)
        context.user_data.pop('setting_time_for', None)
        await _send_habit_list(query_or_update, context)

async def disable_habit_reminder(query, context, habit):
    """Отключает напоминание для привычки"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if habit in user_data.get('habits', {}):
        # Удаляем запланированное напоминание
        job_name = f"reminder_{user_id}_{habit}"
        for job in context.application.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        
        # Убираем время напоминания из данных
        if isinstance(user_data['habits'][habit], dict):
            user_data['habits'][habit]['reminder_time'] = None
        else:
            user_data['habits'][habit] = {
                'dates': user_data['habits'][habit],
                'reminder_time': None
            }
        
        update_user_data(user_id, user_data)
        
        await query.edit_message_text(f"🔕 Напоминание для привычки «{habit}» отключено.")
        
        context.user_data.pop('new_habit', None)
        context.user_data.pop('setting_time_for', None)
        
        # Убираем sleep - показываем список сразу
        await _send_habit_list(query, context)
    else:
        await query.edit_message_text(f"❌ Ошибка: привычка «{habit}» не найдена.")
        await _send_habit_list(query, context)

async def cancel_reminder_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена настройки напоминания."""
    habit = context.user_data.get('setting_time_for') or context.user_data.get('new_habit')
    
    if habit:
        await update.message.reply_text(f"✅ Привычка «{habit}» добавлена без напоминания!")
    else:
        await update.message.reply_text("❌ Настройка напоминания отменена.")
    
    context.user_data.pop('new_habit', None)
    context.user_data.pop('setting_time_for', None)
    await list_habits(update, context)
    return ConversationHandler.END

def schedule_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, habit: str, time_str: str):
    """Планирует напоминание для привычки"""
    try:
        # Проверяем формат времени
        if ':' not in time_str:
            print(f"[REMINDER] Неверный формат времени: {time_str}")
            return False
            
        hour, minute = map(int, time_str.split(':'))
        
        # Проверяем валидность времени
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            print(f"[REMINDER] Неверное время: {hour}:{minute}")
            return False
            
        # Используем московское время явно
        moscow_tz = ZoneInfo('Europe/Moscow')
        reminder_time = time(hour, minute, tzinfo=moscow_tz)
        job_name = f"reminder_{user_id}_{habit}"
        
        # Удаляем существующие задания с таким же именем
        for job in context.job_queue.jobs():
            if job.name == job_name:
                job.schedule_removal()
                print(f"[REMINDER] Удалено старое напоминание: {job_name}")
        
        # Создаем новое напоминание
        job = context.job_queue.run_daily(
            send_reminder,
            reminder_time,
            data={'user_id': user_id, 'habit': habit},
            name=job_name
        )
        
        print(f"[REMINDER] Напоминание запланировано на {time_str} (MSK) для пользователя {user_id}, привычка '{habit}'")
        try:
            next_run = job.next_run_time
            print(f"[REMINDER] Job ID: {job.name}, следующий запуск: {next_run}")
        except AttributeError:
            print(f"[REMINDER] Job ID: {job.name}, следующий запуск: (неизвестно)")
        return True
    except Exception as e:
        print(f"[REMINDER] Ошибка при планировании напоминания: {e}")
        import traceback
        print(f"[REMINDER] Traceback: {traceback.format_exc()}")
        return False

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет напоминание пользователю"""
    job = context.job
    user_id = job.data['user_id']
    habit = job.data['habit']
    
    now = datetime.now()
    moscow_now = datetime.now(ZoneInfo('Europe/Moscow'))
    
    print(f"[REMINDER] ⏰ Отправка напоминания: пользователь {user_id}, привычка '{habit}'")
    print(f"[REMINDER] Время: UTC {now}, MSK {moscow_now}")
    
    try:
        user_data = get_user_data(user_id)
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Проверяем, что привычка существует
        if habit not in user_data.get('habits', {}):
            print(f"[REMINDER] ❌ Привычка '{habit}' больше не существует для пользователя {user_id}")
            return
        
        habit_info = user_data['habits'][habit]
        if isinstance(habit_info, dict):
            dates = habit_info.get('dates', [])
        else:
            dates = habit_info
        
        # Проверяем, выполнена ли привычка сегодня
        if today in dates:
            print(f"[REMINDER] ✅ Привычка '{habit}' уже выполнена сегодня для пользователя {user_id}")
            return
        
        print(f"[REMINDER] 📨 Отправляю напоминание пользователю {user_id} о привычке '{habit}'")
        
        buttons = [[
            InlineKeyboardButton("✅ Выполнено", callback_data=f"reminder_done|{habit}"),
            InlineKeyboardButton("Пропустить", callback_data="reminder_skip")
        ]]
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ Пора выполнить привычку «{habit}»!",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        print(f"[REMINDER] ✅ Напоминание успешно отправлено пользователю {user_id}")
        
    except Exception as e:
        print(f"[REMINDER] ❌ Ошибка при отправке напоминания: {e}")
        import traceback
        print(f"[REMINDER] Traceback: {traceback.format_exc()}")

async def restore_reminders_async(context):
    """Асинхронно восстанавливает все активные напоминания при запуске бота"""
    print("[REMINDER] Начинаем асинхронное восстановление напоминаний...")
    
    try:
        data = load_data()
        restored_count = 0
        
        for user_id, user_data in data.items():
            habits = user_data.get('habits', {})
            
            for habit_name, habit_info in habits.items():
                if isinstance(habit_info, dict):
                    reminder_time = habit_info.get('reminder_time')
                    if reminder_time:
                        print(f"[REMINDER] Восстанавливаю напоминание: пользователь {user_id}, привычка '{habit_name}', время {reminder_time}")
                        if schedule_reminder(context, int(user_id), habit_name, reminder_time):
                            restored_count += 1
                        else:
                            print(f"[REMINDER] Не удалось восстановить напоминание для {user_id}:{habit_name}")
        
        print(f"[REMINDER] Восстановлено {restored_count} напоминаний")
        
        # Показываем активные задания
        print(f"[REMINDER] Активные задания в очереди:")
        for job in context.job_queue.jobs():
            if job.name and job.name.startswith('reminder_'):
                try:
                    next_run = job.next_run_time
                    print(f"[REMINDER]   - {job.name}: следующий запуск {next_run}")
                except AttributeError:
                    print(f"[REMINDER]   - {job.name}: следующий запуск (неизвестно)")
        
    except Exception as e:
        print(f"[REMINDER] Ошибка при восстановлении напоминаний: {e}")
        import traceback
        print(f"[REMINDER] Traceback: {traceback.format_exc()}")

# Оставляем синхронную версию для обратной совместимости
def restore_reminders(context):
    """Синхронная версия для обратной совместимости"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(restore_reminders_async(context))
    except RuntimeError:
        # Если нет активного event loop, используем старую синхронную версию
        print("[REMINDER] Fallback к синхронному восстановлению напоминаний...")
        try:
            data = load_data()
            restored_count = 0
            
            for user_id, user_data in data.items():
                habits = user_data.get('habits', {})
                
                for habit_name, habit_info in habits.items():
                    if isinstance(habit_info, dict):
                        reminder_time = habit_info.get('reminder_time')
                        if reminder_time:
                            if schedule_reminder(context, int(user_id), habit_name, reminder_time):
                                restored_count += 1
            
            print(f"[REMINDER] Восстановлено {restored_count} напоминаний (синхронно)")
            
        except Exception as e:
            print(f"[REMINDER] Ошибка при синхронном восстановлении: {e}")

# ===== ОБРАБОТЧИК КНОПОК =====

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # Обработка меню
        if query.data.startswith('menu_'):
            action = query.data.split('_', 1)[1]
            if action == 'add':
                await query.edit_message_text("Просто введите название новой привычки:")
            elif action == 'list':
                await _send_habit_list(query, context)
            elif action == 'today':
                await handle_today_menu(query, context)
            elif action == 'stats':
                await stats_entry(query, context)
            elif action == 'reminder':
                await reminder_menu(query, context)
            elif action == 'manage':
                await manage_menu(query, context)
            elif action == 'undo':
                await show_undo_menu(query, context)

        # Обработка статистики
        elif query.data.startswith('stats_'):
            period = query.data.split('_', 1)[1]
            await show_stats(query, context, period)
            
        # Обработка очистки статистики
        elif query.data == 'clear_stats_menu':
            await clear_stats_menu(query, context)
            
        elif query.data.startswith('clear_habit|'):
            habit_name = query.data.split('|', 1)[1]
            await clear_habit_confirm(query, context, habit_name)
            
        elif query.data.startswith('confirm_clear_habit|'):
            habit_name = query.data.split('|', 1)[1]
            await confirm_clear_habit(query, context, habit_name)
            
        elif query.data == 'clear_all_habits':
            await clear_all_habits_confirm(query, context)
            
        elif query.data == 'confirm_clear_all':
            await confirm_clear_all(query, context)
            
        # Обработка управления привычками
        elif query.data.startswith('edit_habit|'):
            habit_name = query.data.split('|', 1)[1]
            await edit_habit_menu(query, context, habit_name)
            
        elif query.data.startswith('delete_habit|'):
            habit_name = query.data.split('|', 1)[1]
            await delete_habit_confirm(query, context, habit_name)
            
        elif query.data.startswith('confirm_delete|'):
            habit_name = query.data.split('|', 1)[1]
            await confirm_delete_habit(query, context, habit_name)

        # Обработка переименования привычек
        elif query.data.startswith('rename_habit|'):
            # Эта кнопка обрабатывается в ConversationHandler
            pass
            
        # Обработка изменения напоминаний
        elif query.data.startswith('change_reminder|'):
            # Эта кнопка обрабатывается в ConversationHandler
            pass
            
        # Обработка установки напоминаний
        elif query.data.startswith('set_reminder|'):
            # Эта кнопка обрабатывается в ConversationHandler
            pass

        # Кнопки времени вне ConversationHandler (возврат в меню)
        elif query.data.startswith('time_') and query.data.endswith('_back'):
            action = query.data.replace('time_', '').replace('_back', '')
            if action == 'cancel':
                await _send_habit_list(query, context)

        # Отметка выполнения
        elif query.data.startswith("done|"):
            habit_name = query.data.split('|')[1]
            await mark_habit_done(query, context, habit_name)
            
        # Отмена выполнения
        elif query.data.startswith("undo|"):
            habit_name = query.data.split('|')[1]
            await mark_habit_undone(query, context, habit_name)
            
        # Напоминания
        elif query.data.startswith("reminder_done|"):
            habit = query.data.split('|', 1)[1]
            await mark_habit_done(query, context, habit)
            
        elif query.data == "reminder_skip":
            await query.edit_message_text("Хорошо, в следующий раз!")

    except Exception as e:
        import traceback
        print(f"Ошибка в обработчике кнопок: {e}")
        print(f"Callback data: {query.data}")
        print(f"Traceback: {traceback.format_exc()}")
        try:
            await query.edit_message_text(f"❌ Произошла ошибка при обработке команды. Попробуйте снова.")
        except Exception as edit_error:
            print(f"Не удалось отредактировать сообщение: {edit_error}")
            try:
                await query.message.reply_text(f"❌ Произошла ошибка при обработке команды. Попробуйте снова.")
            except Exception as reply_error:
                print(f"Не удалось отправить сообщение об ошибке: {reply_error}")

async def handle_today_menu(query, context):
    """Обработка меню сегодняшних привычек"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text("Нет привычек. Добавьте через меню.")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    uncompleted_habits = []
    completed_habits = []
    
    for habit_name, habit_info in habits.items():
        dates = habit_info.get('dates', []) if isinstance(habit_info, dict) else habit_info
        if today not in dates:
            uncompleted_habits.append(habit_name)
        else:
            completed_habits.append(habit_name)

    if not uncompleted_habits:
        message = "🎉 Все привычки уже выполнены сегодня!"
    else:
        message = "Выберите привычку для отметки выполнения:"
    
    buttons = []
    for habit in uncompleted_habits:
        buttons.append([InlineKeyboardButton(habit, callback_data=f"done|{habit}")])
    
    if completed_habits:
        buttons.append([InlineKeyboardButton("❌ Отменить выполнение", callback_data="menu_undo")])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_list")])
    
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(buttons))

async def mark_habit_done(query, context, habit_name):
    """Отмечает привычку как выполненную"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if habit_name in user_data['habits']:
        today = datetime.now().strftime('%Y-%m-%d')
        habit_info = user_data['habits'][habit_name]
        
        if isinstance(habit_info, dict):
            if today not in habit_info.get('dates', []):
                habit_info.setdefault('dates', []).append(today)
                update_user_data(user_id, user_data)
        else:
            if today not in habit_info:
                habit_info.append(today)
                update_user_data(user_id, user_data)
    
    await _send_habit_list(query, context)

async def mark_habit_undone(query, context, habit_name):
    """Отменяет выполнение привычки"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if habit_name in user_data['habits']:
        today = datetime.now().strftime('%Y-%m-%d')
        habit_info = user_data['habits'][habit_name]
        
        if isinstance(habit_info, dict):
            if today in habit_info.get('dates', []):
                habit_info['dates'].remove(today)
                update_user_data(user_id, user_data)
        else:
            if today in habit_info:
                habit_info.remove(today)
                update_user_data(user_id, user_data)
    
    await _send_habit_list(query, context)

# ===== ОСТАЛЬНЫЕ ФУНКЦИИ =====

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_today_menu(update, context)

async def debug_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для диагностики напоминаний (только для отладки)"""
    user_id = update.effective_user.id
    
    # Проверяем активные напоминания для пользователя
    user_reminders = []
    all_jobs = []
    
    for job in context.application.job_queue.jobs():
        all_jobs.append(f"Job: {job.name}, next_run: {job.next_run_time}")
        if job.name and job.name.startswith(f'reminder_{user_id}_'):
            habit_name = job.name.replace(f'reminder_{user_id}_', '')
            user_reminders.append(f"• {habit_name}: {job.next_run_time}")
    
    # Проверяем напоминания в базе данных
    user_data = get_user_data(user_id)
    db_reminders = []
    
    for habit_name, habit_info in user_data.get('habits', {}).items():
        if isinstance(habit_info, dict) and habit_info.get('reminder_time'):
            db_reminders.append(f"• {habit_name}: {habit_info['reminder_time']}")
    
    # Добавляем информацию о времени
    now_utc = datetime.now()
    now_moscow = datetime.now(ZoneInfo('Europe/Moscow'))
    
    message = f"🔧 **Диагностика напоминаний**\n\n"
    message += f"**Текущее время:**\n"
    message += f"• UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"• MSK: {now_moscow.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    message += f"**Активные напоминания в планировщике:**\n"
    if user_reminders:
        message += "\n".join(user_reminders)
    else:
        message += "Нет активных напоминаний"
    
    message += f"\n\n**Напоминания в базе данных:**\n"
    if db_reminders:
        message += "\n".join(db_reminders)
    else:
        message += "Нет настроенных напоминаний"
    
    message += f"\n\n**Всего заданий в планировщике:** {len(all_jobs)}"
    message += f"\n**Ваш ID:** {user_id}"
    message += f"\n**Timezone бота:** {context.application.timezone}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для тестирования напоминаний - отправляет тестовое напоминание через 1 минуту"""
    user_id = update.effective_user.id
    
    try:
        # Планируем тестовое напоминание через 1 минуту
        test_time = datetime.now() + timedelta(minutes=1)
        
        job = context.job_queue.run_once(
            send_test_reminder,
            when=test_time,
            data={'user_id': user_id},
            name=f"test_reminder_{user_id}"
        )
        
        await update.message.reply_text(
            f"🧪 **Тестовое напоминание запланировано**\n\n"
            f"Вы получите тестовое сообщение через 1 минуту.\n"
            f"Время отправки: {test_time.strftime('%H:%M:%S')}\n\n"
            f"Если напоминание не придет, значит есть проблемы с системой уведомлений.",
            parse_mode='Markdown'
        )
        
        print(f"[TEST] Тестовое напоминание запланировано для пользователя {user_id} на {test_time}")
        
    except Exception as e:
        print(f"[TEST] Ошибка при планировании тестового напоминания: {e}")
        await update.message.reply_text(
            "❌ Ошибка при планировании тестового напоминания. Проверьте логи."
        )

async def test_immediate_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает напоминание на ближайшую минуту для тестирования"""
    user_id = update.effective_user.id
    
    try:
        # Получаем текущее время в MSK
        now = datetime.now(ZoneInfo('Europe/Moscow'))
        print(f"[TEST] Текущее время MSK: {now}")
        
        # Планируем напоминание на следующую минуту
        next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        hour = next_minute.hour
        minute = next_minute.minute
        
        print(f"[TEST] Планируем тестовое напоминание на {hour:02d}:{minute:02d}")
        
        # Создаем тестовую привычку
        test_habit = f"Тест_{hour:02d}:{minute:02d}"
        
        # Планируем напоминание
        if schedule_reminder(context, user_id, test_habit, f"{hour:02d}:{minute:02d}"):
            await update.message.reply_text(
                f"🧪 **Тестовое напоминание создано**\n\n"
                f"Привычка: {test_habit}\n"
                f"Время: {hour:02d}:{minute:02d} MSK\n"
                f"Сейчас: {now.strftime('%H:%M:%S')}\n\n"
                f"Напоминание должно прийти через ~{60 - now.second} секунд",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка при создании тестового напоминания")
        
    except Exception as e:
        print(f"[TEST] Ошибка: {e}")
        import traceback
        print(f"[TEST] Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def send_test_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет тестовое напоминание"""
    job = context.job
    user_id = job.data['user_id']
    
    try:
        print(f"[TEST] Отправляю тестовое напоминание пользователю {user_id}")
        
        await context.bot.send_message(
            chat_id=user_id,
            text="🧪 **Тестовое напоминание**\n\nЕсли вы получили это сообщение, система напоминаний работает корректно! ✅",
            parse_mode='Markdown'
        )
        
        print(f"[TEST] Тестовое напоминание успешно отправлено пользователю {user_id}")
        
    except Exception as e:
        print(f"[TEST] Ошибка при отправке тестового напоминания: {e}")
        import traceback
        print(f"[TEST] Traceback: {traceback.format_exc()}")

async def stats_entry(query, context):
    """Главное меню статистики"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text(
            "📊 У вас пока нет привычек для анализа статистики.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_list")]])
        )
        return

    buttons = [
        [InlineKeyboardButton("📈 За неделю", callback_data="stats_week")],
        [InlineKeyboardButton("📊 За месяц", callback_data="stats_month")],
        [InlineKeyboardButton("📉 За все время", callback_data="stats_all")],
        [InlineKeyboardButton("🗑 Очистить статистику", callback_data="clear_stats_menu")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_list")]
    ]
    
    message = "📊 **Статистика привычек**\n\nВыберите период для анализа:"
    
    await query.edit_message_text(
        message, 
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def show_stats(query, context, period):
    """Показывает статистику за выбранный период"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if period == "week":
        days_back = 7
        period_name = "неделю"
    elif period == "month":
        days_back = 30
        period_name = "месяц"
    else:  # all
        days_back = 365
        period_name = "все время"
    
    today = datetime.now()
    start_date = today - timedelta(days=days_back)
    
    stats_text = f"📊 **Статистика за {period_name}**\n\n"
    
    for habit_name, habit_info in habits.items():
        if isinstance(habit_info, dict):
            dates = habit_info.get('dates', [])
        else:
            dates = habit_info
        
        # Считаем выполнения в периоде
        completed_in_period = 0
        for date_str in dates:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if date_obj >= start_date:
                    completed_in_period += 1
            except ValueError:
                continue
        
        if period == "all":
            # Для всего времени считаем дни с первого выполнения
            if dates:
                first_date = min(dates)
                try:
                    first_date_obj = datetime.strptime(first_date, '%Y-%m-%d')
                    days_since_start = (today - first_date_obj).days + 1
                    possible_days = min(days_since_start, days_back)
                except ValueError:
                    possible_days = days_back
            else:
                possible_days = 0
        else:
            possible_days = days_back
        
        if possible_days > 0:
            percentage = (completed_in_period / possible_days) * 100
            stats_text += f"**{habit_name}**\n"
            stats_text += f"  ✅ {completed_in_period}/{possible_days} дней ({percentage:.1f}%)\n\n"
    
    if not habits:
        stats_text += "Нет данных за выбранный период."
    
    buttons = [
        [InlineKeyboardButton("🔙 К выбору периода", callback_data="menu_stats")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_list")]
    ]
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def manage_menu(query, context):
    """Меню управления привычками"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text(
            "✍️ У вас пока нет привычек для управления.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_list")]])
        )
        return
    
    buttons = []
    for habit_name in habits.keys():
        buttons.append([InlineKeyboardButton(f"✏️ {habit_name}", callback_data=f"edit_habit|{habit_name}")])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_list")])
    
    await query.edit_message_text(
        "✍️ **Управление привычками**\n\nВыберите привычку для изменения:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def edit_habit_menu(query, context, habit_name):
    """Меню редактирования конкретной привычки"""
    user_data = get_user_data(query.from_user.id)
    habit_info = user_data['habits'].get(habit_name, {})
    
    reminder_text = ""
    if isinstance(habit_info, dict):
        reminder_time = habit_info.get('reminder_time')
        if reminder_time:
            reminder_text = f"\n⏰ Напоминание: {reminder_time}"
        else:
            reminder_text = "\n⏰ Напоминание: не установлено"
    
    buttons = [
        [InlineKeyboardButton("✏️ Изменить название", callback_data=f"rename_habit|{habit_name}")],
        [InlineKeyboardButton("⏰ Изменить напоминание", callback_data=f"change_reminder|{habit_name}")],
        [InlineKeyboardButton("🗑 Удалить привычку", callback_data=f"delete_habit|{habit_name}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_manage")]
    ]
    
    await query.edit_message_text(
        f"✏️ **Редактирование привычки**\n\n**{habit_name}**{reminder_text}",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def delete_habit_confirm(query, context, habit_name):
    """Подтверждение удаления привычки"""
    buttons = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete|{habit_name}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_habit|{habit_name}")
        ]
    ]
    
    await query.edit_message_text(
        f"🗑 **Удаление привычки**\n\nВы уверены, что хотите удалить привычку **{habit_name}**?\n\nВся история выполнения будет потеряна!",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def confirm_delete_habit(query, context, habit_name):
    """Окончательное удаление привычки"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if habit_name in user_data['habits']:
        # Удаляем напоминание, если есть
        job_name = f"reminder_{user_id}_{habit_name}"
        for job in context.application.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        
        # Удаляем привычку
        del user_data['habits'][habit_name]
        update_user_data(user_id, user_data)
        
        await query.edit_message_text(
            f"✅ Привычка **{habit_name}** удалена.",
            parse_mode='Markdown'
        )
        
        # Убираем sleep - показываем список сразу
        await _send_habit_list(query, context)
    else:
        await query.edit_message_text("❌ Привычка не найдена.")

async def reminder_menu(query, context):
    """Меню напоминаний"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text(
            "⏰ У вас пока нет привычек для настройки напоминаний.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_list")]])
        )
        return

    message = "⏰ **Управление напоминаниями**\n\n"
    buttons = []
    
    for habit_name, habit_info in habits.items():
        if isinstance(habit_info, dict):
            reminder_time = habit_info.get('reminder_time')
            if reminder_time:
                status = f"🔔 {reminder_time}"
            else:
                status = "🔕 не установлено"
        else:
            status = "🔕 не установлено"
        
        message += f"**{habit_name}**: {status}\n"
        buttons.append([InlineKeyboardButton(f"⚙️ {habit_name}", callback_data=f"set_reminder|{habit_name}")])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_list")])
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def show_undo_menu(query, context):
    """Показывает меню отмены выполнения привычек"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text("Нет привычек.")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    completed_habits = []
    
    for habit_name, habit_info in habits.items():
        dates = habit_info.get('dates', []) if isinstance(habit_info, dict) else habit_info
        if today in dates:
            completed_habits.append(habit_name)

    if not completed_habits:
        await query.edit_message_text(
            "❌ Сегодня нет выполненных привычек для отмены.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_list")]])
        )
        return
    
    buttons = []
    for habit in completed_habits:
        buttons.append([InlineKeyboardButton(f"❌ {habit}", callback_data=f"undo|{habit}")])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_today")])
    
    await query.edit_message_text(
        "Выберите привычку для отмены выполнения:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def change_reminder_for_habit(update, context):
    """Изменение напоминания для конкретной привычки"""
    query = update.callback_query
    await query.answer()
    habit_name = query.data.split('|', 1)[1]
    context.user_data['setting_time_for'] = habit_name
    
    buttons = [
        [
            InlineKeyboardButton("🌅 09:00", callback_data="time_09:00"),
            InlineKeyboardButton("🌄 12:00", callback_data="time_12:00")
        ],
        [
            InlineKeyboardButton("🌇 18:00", callback_data="time_18:00"),
            InlineKeyboardButton("🌃 21:00", callback_data="time_21:00")
        ],
        [
            InlineKeyboardButton("⏰ Свое время", callback_data="time_custom"),
            InlineKeyboardButton("🔕 Отключить", callback_data="time_disable")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_habit|{habit_name}")]
    ]
    
    await query.edit_message_text(
        f"⏰ **Напоминание для «{habit_name}»**\n\nВыберите время:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )
    
    return SETTING_REMINDER_TIME

async def set_reminder_for_habit(update, context):
    """Установка напоминания для привычки из меню напоминаний"""
    query = update.callback_query
    await query.answer()
    habit_name = query.data.split('|', 1)[1]
    context.user_data['setting_time_for'] = habit_name
    
    buttons = [
        [
            InlineKeyboardButton("🌅 09:00", callback_data="time_09:00"),
            InlineKeyboardButton("🌄 12:00", callback_data="time_12:00")
        ],
        [
            InlineKeyboardButton("🌇 18:00", callback_data="time_18:00"),
            InlineKeyboardButton("🌃 21:00", callback_data="time_21:00")
        ],
        [
            InlineKeyboardButton("⏰ Свое время", callback_data="time_custom"),
            InlineKeyboardButton("🔕 Отключить", callback_data="time_disable")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_reminder")]
    ]
    
    await query.edit_message_text(
        f"⏰ **Напоминание для «{habit_name}»**\n\nВыберите время:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )
    
    return SETTING_REMINDER_TIME

async def rename_habit_start(update, context):
    """Начало процесса переименования привычки"""
    query = update.callback_query
    await query.answer()
    habit_name = query.data.split('|', 1)[1]
    context.user_data['renaming_habit'] = habit_name
    
    await query.edit_message_text(
        f"✏️ **Переименование привычки**\n\n"
        f"Текущее название: **{habit_name}**\n\n"
        f"Введите новое название привычки или нажмите /cancel для отмены:",
        parse_mode='Markdown'
    )
    
    return RENAMING_HABIT

async def handle_habit_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового названия привычки"""
    new_name = update.message.text.strip()
    old_name = context.user_data.get('renaming_habit')
    
    if not old_name:
        await update.message.reply_text("❌ Ошибка: привычка не найдена.")
        return ConversationHandler.END
    
    if not new_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Попробуйте еще раз или нажмите /cancel для отмены."
        )
        return RENAMING_HABIT
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    # Проверяем, не существует ли уже привычка с таким названием
    if new_name in user_data.get('habits', {}) and new_name != old_name:
        await update.message.reply_text(
            f"❌ Привычка с названием «{new_name}» уже существует. "
            f"Попробуйте другое название или нажмите /cancel для отмены."
        )
        return RENAMING_HABIT
    
    # Переименовываем привычку
    if old_name in user_data.get('habits', {}):
        habit_data = user_data['habits'][old_name]
        del user_data['habits'][old_name]
        user_data['habits'][new_name] = habit_data
        
        # Обновляем напоминания
        if isinstance(habit_data, dict) and habit_data.get('reminder_time'):
            # Удаляем старое напоминание
            old_job_name = f"reminder_{user_id}_{old_name}"
            for job in context.application.job_queue.get_jobs_by_name(old_job_name):
                job.schedule_removal()
            
            # Создаем новое напоминание
            schedule_reminder(context, user_id, new_name, habit_data['reminder_time'])
        
        update_user_data(user_id, user_data)
        
        await update.message.reply_text(f"✅ Привычка переименована: «{old_name}» → «{new_name}»")
        
        context.user_data.pop('renaming_habit', None)
        
        # Убираем sleep - показываем список сразу
        await list_habits(update, context)
    else:
        await update.message.reply_text("❌ Привычка не найдена.")
    
    return ConversationHandler.END

async def cancel_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена переименования привычки"""
    habit_name = context.user_data.get('renaming_habit')
    
    if habit_name:
        await update.message.reply_text(f"❌ Переименование привычки «{habit_name}» отменено.")
    else:
        await update.message.reply_text("❌ Переименование отменено.")
    
    context.user_data.pop('renaming_habit', None)
    await list_habits(update, context)
    return ConversationHandler.END

async def setup_commands(application: Application):
    try:
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("menu", "Показать меню действий"),
            BotCommand("debug", "Диагностика напоминаний"),
            BotCommand("test", "Тестовое напоминание"),
            BotCommand("testquick", "Быстрый тест напоминания"),
            BotCommand("cancel", "Отменить текущее действие")
        ]
        await application.bot.set_my_commands(commands)
        print("Команды успешно установлены")
    except Exception as e:
        print(f"Ошибка при установке команд: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Произошла ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )

async def clear_stats_menu(query, context):
    """Меню очистки статистики"""
    user_data = get_user_data(query.from_user.id)
    habits = user_data.get('habits', {})
    
    if not habits:
        await query.edit_message_text(
            "🗑 У вас пока нет привычек для очистки статистики.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_stats")]])
        )
        return

    buttons = []
    # Добавляем кнопки для каждой привычки
    for habit_name in habits.keys():
        buttons.append([InlineKeyboardButton(f"🗑 {habit_name}", callback_data=f"clear_habit|{habit_name}")])
    
    # Добавляем опцию очистки всех привычек
    buttons.append([InlineKeyboardButton("🗑 Очистить все привычки", callback_data="clear_all_habits")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_stats")])
    
    await query.edit_message_text(
        "🗑 **Очистка статистики**\n\nВыберите привычку для очистки истории выполнения:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def clear_habit_confirm(query, context, habit_name):
    """Подтверждение очистки статистики одной привычки"""
    buttons = [
        [
            InlineKeyboardButton("✅ Да, очистить", callback_data=f"confirm_clear_habit|{habit_name}"),
            InlineKeyboardButton("❌ Отмена", callback_data="clear_stats_menu")
        ]
    ]
    
    await query.edit_message_text(
        f"🗑 **Очистка статистики**\n\nВы уверены, что хотите очистить всю историю выполнения для привычки **{habit_name}**?\n\nВся статистика будет потеряна!",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def clear_all_habits_confirm(query, context):
    """Подтверждение очистки статистики всех привычек"""
    buttons = [
        [
            InlineKeyboardButton("✅ Да, очистить все", callback_data="confirm_clear_all"),
            InlineKeyboardButton("❌ Отмена", callback_data="clear_stats_menu")
        ]
    ]
    
    await query.edit_message_text(
        "🗑 **Очистка всей статистики**\n\nВы уверены, что хотите очистить историю выполнения **всех привычек**?\n\nВся статистика будет потеряна навсегда!",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode='Markdown'
    )

async def confirm_clear_habit(query, context, habit_name):
    """Очистка статистики одной привычки"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if habit_name in user_data['habits']:
        habit_info = user_data['habits'][habit_name]
        
        if isinstance(habit_info, dict):
            # Очищаем только даты, оставляем время напоминания
            user_data['habits'][habit_name]['dates'] = []
        else:
            # Старый формат - заменяем на новый с пустыми датами
            user_data['habits'][habit_name] = {
                'dates': [],
                'reminder_time': None
            }
        
        update_user_data(user_id, user_data)
        
        await query.edit_message_text(
            f"✅ Статистика для привычки **{habit_name}** очищена.",
            parse_mode='Markdown'
        )
        
        # Убираем sleep - показываем меню сразу
        await clear_stats_menu(query, context)
    else:
        await query.edit_message_text("❌ Привычка не найдена.")

async def confirm_clear_all(query, context):
    """Очистка статистики всех привычек"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    habits_cleared = 0
    for habit_name, habit_info in user_data['habits'].items():
        if isinstance(habit_info, dict):
            # Очищаем только даты, оставляем время напоминания
            user_data['habits'][habit_name]['dates'] = []
        else:
            # Старый формат - заменяем на новый с пустыми датами
            user_data['habits'][habit_name] = {
                'dates': [],
                'reminder_time': None
            }
        habits_cleared += 1
    
    update_user_data(user_id, user_data)
    
    await query.edit_message_text(
        f"✅ Статистика очищена для {habits_cleared} привычек.",
        parse_mode='Markdown'
    )
    
    # Убираем sleep - показываем меню сразу
    await stats_entry(query, context)

def main():
    # Проверяем наличие токена
    if not TOKEN:
        print("❌ ОШИБКА: Не установлен TELEGRAM_BOT_TOKEN")
        print("Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return
    
    # Проверяем среду выполнения
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    if is_railway:
        print("🚂 Запуск на Railway")
    else:
        print("💻 Локальный запуск")
    
    # Используем местное время для приложения
    try:
        app_timezone = ZoneInfo('Europe/Moscow')  # Московское время
    except Exception:
        app_timezone = ZoneInfo('UTC')  # Fallback на UTC
    
    # Создаем приложение с сетевыми настройками
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30 if is_railway else 10)
        .read_timeout(30 if is_railway else 10)
        .write_timeout(30 if is_railway else 10)
        .pool_timeout(30 if is_railway else 10)
        .build()
    )
    application.timezone = app_timezone
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("debug", debug_reminders))
    application.add_handler(CommandHandler("test", test_reminder))
    application.add_handler(CommandHandler("testquick", test_immediate_reminder))
    
    # ConversationHandler для установки времени напоминания
    reminder_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_new_habit_reminder, pattern="^new_habit_set_time$"),
            CallbackQueryHandler(handle_new_habit_reminder, pattern="^new_habit_skip$"),
            CallbackQueryHandler(change_reminder_for_habit, pattern="^change_reminder\\|"),
            CallbackQueryHandler(set_reminder_for_habit, pattern="^set_reminder\\|")
        ],
        states={
            SETTING_REMINDER_TIME: [
                CallbackQueryHandler(handle_time_selection, pattern="^time_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_time_input)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_reminder_setup)
        ],
        per_chat=True,
        per_message=False,
        allow_reentry=True
    )
    application.add_handler(reminder_handler)
    
    # ConversationHandler для переименования привычек
    rename_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(rename_habit_start, pattern="^rename_habit\\|")
        ],
        states={
            RENAMING_HABIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_habit_rename)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_rename)
        ],
        per_chat=True,
        per_message=False,
        allow_reentry=True
    )
    application.add_handler(rename_handler)
    
    # Обработчик кнопок (должен быть после ConversationHandler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_text))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    print(f"[INIT] Бот запущен с часовым поясом: {app_timezone}")
    print("[INIT] Начинаем поллинг...")
    
    try:
        # Напоминания восстанавливаются при первом вызове /start
        
        # Запускаем бота с оптимизированными параметрами
        application.run_polling(
            drop_pending_updates=True,
            poll_interval=1.0 if is_railway else 0.1,  # Более длинный интервал для Railway
            timeout=20 if is_railway else 10          # Больший таймаут для Railway
        )
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        print("🔄 Бот остановлен")

if __name__ == '__main__':
    main() 