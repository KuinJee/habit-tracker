#!/usr/bin/env python3
"""
Watchdog для автоматического перезапуска бота при изменениях в коде
Использование: python watchdog.py
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

def start_bot():
    """Запускает бота"""
    print("🚀 Запускаю Habit Bot...")
    try:
        # Активируем виртуальное окружение и запускаем бота
        cmd = [
            sys.executable, 
            "habit_tracker_bot.py"
        ]
        return subprocess.Popen(cmd, cwd=os.getcwd())
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return None

def stop_bot(process):
    """Останавливает бота"""
    if process and process.poll() is None:
        print("🛑 Останавливаю бота...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️ Принудительное завершение...")
            process.kill()
            process.wait()

def main():
    """Основная функция watchdog"""
    print("👀 Watchdog запущен - отслеживаю изменения в коде...")
    print("Нажмите Ctrl+C для остановки")
    
    bot_process = None
    last_modified = 0
    
    try:
        while True:
            # Проверяем изменения в основных файлах
            files_to_watch = [
                "habit_tracker_bot.py",
                "habits.json",
                "requirements.txt"
            ]
            
            current_modified = 0
            for file_path in files_to_watch:
                if os.path.exists(file_path):
                    current_modified = max(current_modified, os.path.getmtime(file_path))
            
            # Если файлы изменились, перезапускаем бота
            if current_modified > last_modified:
                print(f"📝 Обнаружены изменения в {time.ctime(current_modified)}")
                
                if bot_process:
                    stop_bot(bot_process)
                
                bot_process = start_bot()
                last_modified = current_modified
            
            time.sleep(1)  # Проверяем каждую секунду
            
    except KeyboardInterrupt:
        print("\n👋 Останавливаю watchdog...")
        if bot_process:
            stop_bot(bot_process)
        print("✅ Watchdog остановлен")

if __name__ == "__main__":
    main() 