# 🚨 Быстрое исправление ошибки Railway

## Проблема
```
Error deploying Repo
There was an issue deploying KuinJee/habit-tracker
```

## ✅ Решение (уже применено)

### 1. Исправлен Procfile
```bash
# Было: web: python habit_tracker_bot.py
# Стало: worker: bash start.sh
```

### 2. Убран хардкодированный токен
```python
# Теперь токен берется только из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

### 3. Добавлена конфигурация nixpacks.toml
```toml
[variables]
NIXPACKS_PYTHON_VERSION = "3.11"

[start]
cmd = "python habit_tracker_bot.py"
```

## 🔧 Что нужно сделать в Railway

### 1. Переменные окружения
В Railway панели → Variables → Add Variable:
```
TELEGRAM_BOT_TOKEN = ваш_токен_бота
RAILWAY_ENVIRONMENT = production
```

### 2. Redeploy
1. Перейдите в Deployments
2. Нажмите "Redeploy"
3. Дождитесь завершения сборки

## 📋 Проверка

### Логи должны показать:
```
🚀 Запуск Habit Tracker Bot на Railway...
✅ Токен бота найден
🤖 Запускаем бота...
[INIT] Бот запущен с часовым поясом: Europe/Moscow
[INIT] Начинаем поллинг...
```

### Статус деплоя: "Active" ✅

## 🆘 Если не работает

1. Проверьте токен бота у @BotFather
2. Убедитесь что переменная `TELEGRAM_BOT_TOKEN` установлена в Railway
3. Посмотрите логи в Railway → Logs
4. Попробуйте Redeploy еще раз

## 📞 Альтернативы

Если Railway не работает:
- Heroku (платно)
- DigitalOcean App Platform
- Google Cloud Run
- Собственный VPS

---

**Статус**: Исправления применены ✅  
**Репозиторий**: https://github.com/KuinJee/habit-tracker  
**Последнее обновление**: Сейчас 