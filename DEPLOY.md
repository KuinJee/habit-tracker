# 🚀 Деплой Habit Tracker Bot на Railway

## Подготовка к деплою

### 1. Подготовка GitHub репозитория

1. Форкните репозиторий или создайте новый
2. Убедитесь что все файлы на месте:
   - `habit_tracker_bot.py` - основной файл бота
   - `requirements.txt` - зависимости
   - `Procfile` - команда запуска для Railway
   - `railway.json` - конфигурация Railway
   - `runtime.txt` - версия Python
   - `env.example` - пример переменных окружения

### 2. Получение токена бота

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Введите имя бота (например: "My Habit Tracker")
4. Введите username бота (например: "my_habit_tracker_bot")
5. Скопируйте полученный токен

## Деплой на Railway

### Способ 1: Через GitHub (рекомендуется)

1. Перейдите на [Railway](https://railway.app)
2. Войдите через GitHub
3. Нажмите "New Project"
4. Выберите "Deploy from GitHub repo"
5. Выберите ваш репозиторий с ботом
6. Railway автоматически определит Python проект

### Способ 2: Через Railway CLI

```bash
# Установите Railway CLI
npm install -g @railway/cli

# Войдите в аккаунт
railway login

# Инициализируйте проект
railway init

# Деплой
railway up
```

## Настройка переменных окружения

1. В панели Railway перейдите в раздел "Variables"
2. Добавьте переменную:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
3. Сохраните изменения

## Проверка деплоя

1. В разделе "Deployments" проверьте статус деплоя
2. В разделе "Logs" посмотрите логи запуска
3. Если бот запустился успешно, вы увидите сообщение "Bot started successfully"

## Настройка домена (опционально)

1. В разделе "Settings" найдите "Domains"
2. Нажмите "Generate Domain" для получения публичного URL
3. Или подключите свой домен

## Мониторинг

### Логи
- Перейдите в раздел "Logs" для просмотра логов в реальном времени
- Фильтруйте по уровню: Info, Warning, Error

### Метрики
- В разделе "Metrics" доступны:
  - Использование CPU
  - Использование памяти
  - Сетевая активность

## Обновление бота

1. Внесите изменения в код
2. Сделайте commit и push в GitHub
3. Railway автоматически пересоберет и задеплоит новую версию

## Устранение проблем

### Бот не запускается

1. Проверьте логи в разделе "Logs"
2. Убедитесь что токен бота правильный
3. Проверьте что все зависимости в `requirements.txt`

### Ошибки в логах

```
ModuleNotFoundError: No module named 'telegram'
```
**Решение**: Проверьте `requirements.txt`, добавьте недостающие зависимости

```
telegram.error.InvalidToken: Invalid token
```
**Решение**: Проверьте переменную окружения `TELEGRAM_BOT_TOKEN`

### Бот не отвечает

1. Проверьте что бот запущен (статус в Railway)
2. Убедитесь что токен активен
3. Проверьте что бот не заблокирован в Telegram

## Резервное копирование

### Данные бота
Бот сохраняет данные в `habits.json`. Для production рекомендуется:

1. Подключить Railway PostgreSQL:
   ```bash
   railway add postgresql
   ```

2. Изменить код для работы с базой данных

### Код
Весь код хранится в GitHub, что обеспечивает версионность и резервное копирование.

## Стоимость

Railway предоставляет:
- $5 в месяц бесплатно для новых пользователей
- Оплата по факту использования
- Автоматическое масштабирование

## Альтернативы Railway

Если Railway не подходит, можно использовать:
- Heroku
- DigitalOcean App Platform
- Google Cloud Run
- AWS Lambda

## Поддержка

При возникновении проблем:
1. Проверьте [документацию Railway](https://docs.railway.app)
2. Создайте Issue в GitHub репозитории
3. Обратитесь в [поддержку Railway](https://railway.app/help) 