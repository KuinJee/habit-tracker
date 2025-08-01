# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY habit_tracker_bot.py .

# Создаем пользователя для безопасности
RUN adduser --disabled-password --gecos '' botuser && chown -R botuser:botuser /app
USER botuser

# Открываем порт (не используется, но для совместимости)
EXPOSE 8000

# Команда запуска
CMD ["python", "habit_tracker_bot.py"] 