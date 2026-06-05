# 🌤 PogodaMood Bot — @pogoda_mood_bot

Telegram бот с ежедневным прогнозом погоды, партнёрскими ссылками и двуязычным интерфейсом (RU/EN).

## Функции
- 📅 Прогноз на день / неделю / 14 дней
- 🕖 Автоматическая рассылка каждый день в 7:00
- 🏙 Любой город мира
- 🌍 Русский + English
- 🚗 Партнёрские ссылки по контексту погоды
- 💾 SQLite база данных

## Деплой на Railway

1. Создай аккаунт на https://railway.app
2. New Project → Deploy from GitHub (или загрузи папку)
3. Добавь переменные окружения:
   - BOT_TOKEN=твой_токен
   - WEATHER_API_KEY=твой_ключ
4. Railway автоматически запустит `worker: python bot.py`

## Партнёрские ссылки (заменить на реальные)

В файле bot.py найди раздел AFFILIATE и замени URL на свои реферальные ссылки:
- Bolt: https://partners.bolt.eu
- inDrive: https://partners.indrive.com
- Wolt: https://partnership.wolt.com
- Glovo: https://glovoapp.com/partners
- Lamoda: через admitad.com

## Команды бота
- /start — главное меню
- /city — установить город
- /weather — прогноз прямо сейчас
- /settings — настройки
- /help — помощь
