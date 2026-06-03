# Telegram‑бот для управления Google Календарём через Gemini API

## 📖 Описание проекта
Этот проект представляет собой Telegram‑бота, который использует Gemini API (через OpenAI‑совместимый интерфейс) и Google Calendar API для создания и чтения событий календаря.  
Пользователь пишет боту обычным текстом, а модель автоматически определяет, нужно ли создать событие, получить список дел или просто ответить текстом.  
Бот работает только для пользователей, указанных в `settings.ini`.

---

## 🚀 Возможности
- Создание событий в Google Calendar  
- Получение списка событий за любой период  
- Автоматическое понимание естественного языка  
- Интеграция с Gemini API  
- Поддержка function calling  
- Авторизация через Google OAuth  
- Ограничение доступа по списку пользователей  

---

## 📂 Структура проекта
project/
│
├── settings.ini          # Конфигурация бота
├── credentials.json      # OAuth-креды Google (не хранить публично)
├── token.json            # Создаётся автоматически после авторизации
├── main.py                # Основной код бота
└── README.md             # Документация


---

## ⚙️ Установка и настройка

### 1. Установка зависимостей
```bash
pip install pyTelegramBotAPI google-auth google-auth-oauthlib google-api-python-client openai
```

## Создание файла settings.ini
```Пример:
Code
[General]
token = 123456789:ABCDEF...
allowed_users = 11111111,22222222
gemini_key = YOUR_GEMINI_API_KEY
model_name = gemini-2.5-flash
```
## 3. Настройка Google Calendar API
Открыть Google Cloud Console
Включить Google Calendar API
Создать OAuth Client ID
Скачать credentials.json
Поместить в корень проекта
При первом запуске бот откроет браузер для авторизации и создаст token.json.
