# 📂 Настройка GitHub репозитория для Habit Tracker Bot

## Подготовка файлов

Убедитесь что у вас есть все необходимые файлы:

```
Habit Bot/
├── habit_tracker_bot.py    # ✅ Основной файл бота
├── requirements.txt        # ✅ Зависимости Python
├── Procfile               # ✅ Команда запуска для Railway
├── railway.json           # ✅ Конфигурация Railway
├── runtime.txt            # ✅ Версия Python
├── env.example            # ✅ Пример переменных окружения
├── .gitignore             # ✅ Игнорируемые файлы
├── README.md              # ✅ Документация
├── DEPLOY.md              # ✅ Инструкции по деплою
└── GITHUB_SETUP.md        # ✅ Этот файл
```

## Команды для Git

### 1. Инициализация репозитория (если нужно)
```bash
cd "Habit Bot"
git init
```

### 2. Добавление файлов
```bash
# Добавляем все файлы
git add .

# Или добавляем по отдельности
git add habit_tracker_bot.py
git add requirements.txt
git add Procfile
git add railway.json
git add runtime.txt
git add env.example
git add .gitignore
git add README.md
git add DEPLOY.md
git add GITHUB_SETUP.md
```

### 3. Первый коммит
```bash
git commit -m "🚀 Initial commit: Habit Tracker Bot ready for Railway deployment

- ✅ Main bot file with all features
- ✅ Railway deployment configuration
- ✅ Complete documentation
- ✅ Environment variables setup
- ✅ Python 3.11 runtime
- ✅ Optimized for cloud deployment"
```

### 4. Подключение к GitHub
```bash
# Замените YOUR_USERNAME на ваш GitHub username
git remote add origin https://github.com/YOUR_USERNAME/habit-tracker.git

# Или используйте SSH (если настроен)
git remote add origin git@github.com:YOUR_USERNAME/habit-tracker.git
```

### 5. Отправка в GitHub
```bash
git branch -M main
git push -u origin main
```

## Создание GitHub репозитория

### Через веб-интерфейс:
1. Перейдите на [GitHub](https://github.com)
2. Нажмите "New repository"
3. Название: `habit-tracker`
4. Описание: `🤖 Telegram bot for habit tracking with reminders and statistics`
5. Выберите "Public" для возможности деплоя на Railway
6. НЕ добавляйте README, .gitignore, license (у нас уже есть)
7. Нажмите "Create repository"

### Через GitHub CLI:
```bash
gh repo create habit-tracker --public --description "🤖 Telegram bot for habit tracking with reminders and statistics"
```

## Проверка репозитория

После push проверьте что все файлы на месте:
- https://github.com/YOUR_USERNAME/habit-tracker

Должны быть видны:
- ✅ Все файлы проекта
- ✅ README.md отображается корректно
- ✅ Зеленая кнопка "Code" для клонирования

## Настройка Railway

После создания репозитория:

1. Перейдите на [Railway](https://railway.app)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите репозиторий `habit-tracker`
5. Railway автоматически определит Python проект

## Переменные окружения в Railway

В разделе "Variables" добавьте:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
RAILWAY_ENVIRONMENT=production
```

## Обновление проекта

Для обновления бота:
```bash
# Внесите изменения в код
git add .
git commit -m "🔧 Update: описание изменений"
git push
```

Railway автоматически пересоберет проект.

## Полезные команды

### Проверка статуса
```bash
git status
```

### Просмотр истории
```bash
git log --oneline
```

### Создание новой ветки
```bash
git checkout -b feature/new-feature
```

### Слияние изменений
```bash
git checkout main
git merge feature/new-feature
```

## Troubleshooting

### Ошибка при push
```
error: failed to push some refs to 'github.com:username/habit-tracker.git'
```

**Решение:**
```bash
git pull origin main --rebase
git push origin main
```

### Большие файлы
Если Git жалуется на большие файлы, проверьте .gitignore:
```bash
# Удалите большие файлы из индекса
git rm --cached filename
git commit -m "Remove large file"
```

### Изменение remote URL
```bash
git remote set-url origin https://github.com/NEW_USERNAME/habit-tracker.git
```

## Следующие шаги

1. ✅ Создайте GitHub репозиторий
2. ✅ Загрузите код
3. ✅ Подключите к Railway
4. ✅ Настройте переменные окружения
5. ✅ Проверьте работу бота

Готово! Ваш бот готов к работе на Railway! 🚀 