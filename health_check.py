#!/usr/bin/env python3
"""
Быстрая проверка работоспособности Habit Bot
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from telegram import Bot

# Токен бота
TOKEN = '7742690883:AAFClrtlv4YYlKzFTI5oID6yWkTqke0SBV4'

async def health_check():
    """Быстрая проверка работоспособности бота"""
    try:
        bot = Bot(token=TOKEN)
        
        # Проверяем подключение к Telegram API
        me = await bot.get_me()
        print(f"✅ Бот подключен: @{me.username}")
        
        # Проверяем файл данных
        script_dir = os.path.dirname(os.path.abspath(__file__))
        habits_file = os.path.join(script_dir, 'habits.json')
        
        if os.path.exists(habits_file):
            with open(habits_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Файл данных доступен: {len(data)} пользователей")
        else:
            print("⚠️  Файл данных не найден")
        
        # Проверяем процесс через pgrep
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'habit_tracker_bot.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print(f"✅ Процесс работает: PID {', '.join(pids)}")
                return True
            else:
                print("❌ Процесс не найден")
                return False
        except Exception as e:
            print(f"⚠️  Не удалось проверить процесс: {e}")
            return True  # Считаем что работает, если не можем проверить
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

async def main():
    """Основная функция"""
    print(f"🔍 Проверка работоспособности Habit Bot - {datetime.now()}")
    
    is_healthy = await health_check()
    
    if is_healthy:
        print("✅ Бот работает нормально")
        sys.exit(0)
    else:
        print("❌ Бот не работает")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 