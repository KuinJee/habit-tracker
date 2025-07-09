# 🔧 Устранение проблем с деплоем на Railway

## Основные исправления

### 1. ✅ Исправлен тип процесса
**Проблема**: Railway пытался запустить бота как веб-приложение  
**Решение**: Изменен `Procfile` с `web:` на `worker:`

```
# Было:
web: python habit_tracker_bot.py

# Стало:
worker: bash start.sh
```

### 2. ✅ Убран хардкодированный токен
**Проблема**: Токен был захардкожен в коде как fallback  
**Решение**: Теперь токен берется только из переменных окружения

```python
# Было:
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7742690883:AAF...')

# Стало:
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

### 3. ✅ Добавлена конфигурация nixpacks
**Проблема**: Railway не понимал, как собрать проект  
**Решение**: Создан файл `nixpacks.toml` с точными настройками

### 4. ✅ Создан скрипт запуска
**Проблема**: Нет диагностики при запуске  
**Решение**: Создан `start.sh` с проверками

## Проверка деплоя

### 1. Переменные окружения
В Railway панели добавьте:
```
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
RAILWAY_ENVIRONMENT=production
```

### 2. Проверка логов
В разделе "Logs" должны появиться сообщения:
```
🚀 Запуск Habit Tracker Bot на Railway...
✅ Токен бота найден
🐍 Версия Python: Python 3.11.x
🤖 Запускаем бота...
[INIT] Бот запущен с часовым поясом: Europe/Moscow
[INIT] Начинаем поллинг...
```

### 3. Статус деплоя
В разделе "Deployments" статус должен быть "Active"

## Возможные проблемы

### ❌ "Build failed"
**Причина**: Ошибка в зависимостях  
**Решение**: Проверьте `requirements.txt`, все пакеты должны быть доступны

### ❌ "Invalid token"
**Причина**: Неправильный токен бота  
**Решение**: 
1. Получите новый токен у @BotFather
2. Обновите переменную `TELEGRAM_BOT_TOKEN` в Railway

### ❌ "Application crashed"
**Причина**: Ошибка в коде или отсутствие токена  
**Решение**: Проверьте логи в Railway, найдите строку с ошибкой

### ❌ "Module not found"
**Причина**: Отсутствует зависимость  
**Решение**: Добавьте пакет в `requirements.txt` и пересоберите

## Команды для тестирования

### Локальное тестирование
```bash
# Установите токен
export TELEGRAM_BOT_TOKEN="your_token_here"

# Запустите бота
python habit_tracker_bot.py
```

### Проверка зависимостей
```bash
pip install -r requirements.txt
python -c "import telegram; print('✅ telegram-bot OK')"
python -c "import apscheduler; print('✅ APScheduler OK')"
```

## Альтернативные решения

Если Railway не работает, попробуйте:

### 1. Heroku
```bash
# Создайте Heroku app
heroku create your-habit-bot

# Установите переменные
heroku config:set TELEGRAM_BOT_TOKEN=your_token

# Деплой
git push heroku main
```

### 2. DigitalOcean App Platform
1. Подключите GitHub репозиторий
2. Выберите тип "Worker"
3. Установите переменные окружения
4. Деплой

### 3. Google Cloud Run
```bash
# Создайте Dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "habit_tracker_bot.py"]

# Деплой
gcloud run deploy habit-bot --source .
```

## Мониторинг

### Проверка работы бота
1. Отправьте `/start` боту в Telegram
2. Проверьте ответ
3. Добавьте тестовую привычку

### Логи в Railway
- Перейдите в раздел "Logs"
- Фильтруйте по уровню: Info, Error
- Следите за сообщениями о напоминаниях

### Метрики
- CPU usage должно быть < 50%
- Memory usage должно быть < 100MB
- Restart count должен быть минимальным

## Контакты

При возникновении проблем:
1. Проверьте этот файл
2. Посмотрите логи в Railway
3. Создайте Issue в GitHub репозитории

---

**Последнее обновление**: Исправления для Railway деплоя применены ✅ 