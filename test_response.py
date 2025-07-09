#!/usr/bin/env python3
"""
Тестирование времени отклика Habit Bot
"""

import asyncio
import time
from datetime import datetime
from telegram import Bot

# Токен бота
TOKEN = '7742690883:AAFClrtlv4YYlKzFTI5oID6yWkTqke0SBV4'

# Ваш user ID для теста (замените на свой)
TEST_USER_ID = 1149449580  # Замените на свой ID

async def test_response_time():
    """Тестирует время отклика бота"""
    bot = Bot(token=TOKEN)
    
    print(f"🧪 Тестирование отклика бота - {datetime.now()}")
    
    try:
        # Тест 1: Проверка подключения к API
        start_time = time.time()
        me = await bot.get_me()
        api_time = time.time() - start_time
        
        print(f"✅ API подключение: {api_time:.3f}s (@{me.username})")
        
        # Тест 2: Отправка сообщения
        start_time = time.time()
        message = await bot.send_message(
            chat_id=TEST_USER_ID,
            text="🧪 Тест отклика бота"
        )
        send_time = time.time() - start_time
        
        print(f"✅ Отправка сообщения: {send_time:.3f}s")
        
        # Тест 3: Получение обновлений
        start_time = time.time()
        updates = await bot.get_updates(limit=1)
        updates_time = time.time() - start_time
        
        print(f"✅ Получение обновлений: {updates_time:.3f}s")
        
        # Удаляем тестовое сообщение
        try:
            await bot.delete_message(chat_id=TEST_USER_ID, message_id=message.message_id)
            print("🗑️  Тестовое сообщение удалено")
        except:
            pass
        
        # Общее время
        total_time = api_time + send_time + updates_time
        print(f"\n⏱️  Общее время: {total_time:.3f}s")
        
        if total_time < 1.0:
            print("🚀 Отличная скорость отклика!")
        elif total_time < 2.0:
            print("✅ Хорошая скорость отклика")
        elif total_time < 5.0:
            print("⚠️  Медленная скорость отклика")
        else:
            print("❌ Очень медленная скорость отклика")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")

async def main():
    """Основная функция"""
    await test_response_time()

if __name__ == "__main__":
    asyncio.run(main()) 