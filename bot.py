import asyncio
import logging
import aiohttp
import aiosqlite
from datetime import datetime
import pytz
import random
import os

def now_local():
    return datetime.now(pytz.timezone("Europe/Chisinau"))

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ── QUOTES ───────────────────────────────────────────────────────────────────
QUOTES = {
    "sun": [
        {"ru": "☀️ «Каждое утро — это шанс начать заново.» — Неизвестный автор", "en": "☀️ 'Every morning is a chance to begin again.' — Unknown"},
        {"ru": "🌅 «Не жди подходящего момента — создавай его.» — Джордж Бернард Шоу", "en": "🌅 'Don't wait for the right moment. Create it.' — G.B. Shaw"},
        {"ru": "✨ «Жизнь прекрасна. Просто иногда нужно напоминать себе об этом.»", "en": "✨ 'Life is beautiful. Sometimes you just need to remind yourself.' — Unknown"},
        {"ru": "💪 «Успех — это сумма небольших усилий, повторяемых день за днём.» — Роберт Коллиер", "en": "💪 'Success is the sum of small efforts repeated day in and day out.' — Robert Collier"},
    ],
    "rain": [
        {"ru": "🌈 «Жизнь — не в том, чтобы ждать пока пройдёт буря, а в том, чтобы учиться танцевать под дождём.» — Вивиан Грин", "en": "🌈 'Life isn't about waiting for the storm to pass — it's about learning to dance in the rain.' — V. Greene"},
        {"ru": "💧 «Дождь смывает всё лишнее и оставляет только главное.»", "en": "💧 'Rain washes away everything unnecessary, leaving only what matters.' — Unknown"},
    ],
    "snow": [
        {"ru": "❄️ «Зима — это когда земля отдыхает и набирается сил.»", "en": "❄️ 'Winter is when the earth rests and gathers strength.' — Unknown"},
        {"ru": "🧣 «Холод снаружи — тепло внутри. Всё в твоих руках.»", "en": "🧣 'Cold outside, warmth within. It's all in your hands.' — Unknown"},
    ],
    "cloud": [
        {"ru": "⛅ «Облака не могут скрыть солнце навсегда.»", "en": "⛅ 'Clouds cannot hide the sun forever.' — Unknown"},
        {"ru": "💭 «Серый день — отличный фон для ярких мыслей.»", "en": "💭 'A grey day is a perfect backdrop for bright thoughts.' — Unknown"},
    ],
    "any": [
        {"ru": "💡 «Маленький шаг каждый день — большой путь за год.»", "en": "💡 'A small step every day — a great journey in a year.' — Unknown"},
        {"ru": "🎯 «Цель без плана — просто мечта.» — Антуан де Сент-Экзюпери", "en": "🎯 'A goal without a plan is just a wish.' — Antoine de Saint-Exupery"},
    ]
}

SNOW_CODES_Q = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258, 1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252}
RAIN_CODES_Q = {1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246, 1087, 1273, 1276, 1279, 1282}

def get_quote(condition_code: int, lang: str) -> str:
    if condition_code in RAIN_CODES_Q: pool = QUOTES["rain"] + QUOTES["any"]
    elif condition_code in SNOW_CODES_Q: pool = QUOTES["snow"] + QUOTES["any"]
    elif condition_code == 1000: pool = QUOTES["sun"] + QUOTES["any"]
    elif condition_code in (1003, 1006, 1009, 1030, 1135, 1147): pool = QUOTES["cloud"] + QUOTES["any"]
    else: pool = QUOTES["any"]
    return random.choice(pool)[lang]

# ── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8914713512:AAFQQcVEzgL6M-u4yX3kANLHNakIiRWjyBU")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ade7a2b019c6498a8da62549260506")
DB_PATH = "pogoda.db"
ADMIN_ID = int(os.getenv("ADMIN_ID", "7262437300"))
DEVELOPER_USERNAME = "@BohdanViktorovich1"  # 👈 Впиши сюда свой юзернейм телеграма без пробелов

# ── AFFILIATE LINKS ──────────────────────────────────────────────────────────
AFFILIATE = {
    "bolt":       {"ru": "🚗 Заказать такси Bolt",        "en": "🚗 Order Bolt taxi",         "url": "ВСТАВЬ_ССЫЛКУ_BOLT"},
    "inDrive":    {"ru": "🚕 Заказать inDrive",            "en": "🚕 Order inDrive",           "url": "ВСТАВЬ_ССЫЛКУ_INDRIVE"},
    "wolt":       {"ru": "🍔 Доставка еды Wolt",           "en": "🍔 Food delivery Wolt",      "url": "ВСТАВЬ_ССЫЛКУ_WOLT"},
    "glovo":      {"ru": "🛵 Доставка Glovo",              "en": "🛵 Glovo delivery",          "url": "ВСТАВЬ_ССЫЛКУ_GLOVO"},
    "clothes":    {"ru": "👗 Одежда по погоде",            "en": "👗 Clothes for weather",     "url": "ВСТАВЬ_ССЫЛКУ_ОДЕЖДА"},
    "tickets":    {"ru": "✈️ Авиабилеты — Aviasales",         "en": "✈️ Cheap flights — Aviasales",           "url": "https://tp.media/r?marker=736538&trs=536752&p=4114&u=https%3A%2F%2Faviasales.ru&campaign_id=100"},
    "hotels":     {"ru": "🏨 Найти отель",                 "en": "🏨 Find a hotel",            "url": "ВСТАВЬ_ССЫЛКУ_BOOKING"},
    "bothub":     {"ru": "🤖 AI Ассистент — BotHub",        "en": "🤖 AI Assistant — BotHub",  "url": "https://bothub.chat/?invitedBy=zGQwEkF5uAu-92IxmDmZH"},
    "umbrella":   {"ru": "☂️ Зонт от дождя (Alibaba)",           "en": "☂️ Rain umbrella (Alibaba)",         "url": "https://rzekl.com/g/pm1aev55cl3fe1015811219aa26f6f/?ulp=https%3A%2F%2Fwww.alibaba.com%2Fproduct-detail%2FCustom-Wind-Resistant-Hands-Free-Inverse_1600478167223.html"},
    "warm":       {"ru": "🧥 Тёплая одежда",              "en": "🧥 Warm clothes",            "url": "ВСТАВЬ_ССЫЛКУ_ТЁПЛОЕ"},
}

# ── WEATHER MOOD & LOGIC ─────────────────────────────────────────────────────
SNOW_CODES = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258, 1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252}
RAIN_CODES = {1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246, 1087, 1273, 1276, 1279, 1282}
STORM_CODES = {1087, 1273, 1276, 1279, 1282}

def get_mood(code: int, temp: float, lang: str) -> str:
    is_snow = code in SNOW_CODES and temp <= 4
    is_rain = code in RAIN_CODES
    is_storm = code in STORM_CODES
    is_fog = code in (1030, 1135, 1147)

    if lang == "ru":
        if is_storm: return "⛈ <i>Гроза! Лучше остаться дома — безопасность прежде всего.</i>"
        elif is_snow: return "❄️ <i>Снег за окном — укутайся потеплее, и пусть этот день будет уютным!</i>"
        elif is_rain: return "🌧 <i>Дождливый день — идеально для чашки чая, любимой книги или сериала дома.</i>"
        elif is_fog: return "🌫 <i>Туман на улице — будь осторожен на дороге и не торопись.</i>"
        elif temp >= 30: return "🥵 <i>Жра! Пей больше воды, носи лёгкую одежду и береги себя.</i>"
        elif temp >= 20: return "☀️ <i>Отличный день для прогулки — солнце и тепло зовут на улицу!</i>"
        elif temp >= 10: return "🌤 <i>Приятная погода — свежий воздух. Идеально для активного дня!</i>"
        elif temp >= 0: return "🧣 <i>Прохладно — одевайся потеплее и наслаждайся днём!</i>"
        else: return "🥶 <i>Очень холодно! Одевайся по-зимнему и не забудь перчатки.</i>"
    else:
        if is_storm: return "⛈ <i>Thunderstorm! Better stay home — safety first.</i>"
        elif is_snow: return "❄️ <i>Snow outside — wrap up warm and make it a cozy day!</i>"
        elif is_rain: return "🌧 <i>Rainy day — perfect for a cup of tea or a good book at home.</i>"
        elif is_fog: return "🌫 <i>Foggy outside — be careful on the road and take it slow.</i>"
        elif temp >= 30: return "🥵 <i>Heat wave! Drink plenty of water and stay safe.</i>"
        elif temp >= 20: return "☀️ <i>Perfect day for a walk — sunshine and warmth await!</i>"
        elif temp >= 10: return "🌤 <i>Pleasant weather — fresh air. Great for an active day!</i>"
        elif temp >= 0: return "🧣 <i>Cool outside — dress warmly and enjoy the day!</i>"
        else: return "🥶 <i>Freezing cold! Dress in winter gear and don't forget gloves.</i>"

def get_wardrobe(temp: float, lang: str) -> str:
    if lang == "ru":
        if temp < 0: return "🧥 Пуховик, теплая шапка, шарф и перчатки."
        elif temp < 10: return "🧥 Пальто или теплая куртка, легкий шарф."
        elif temp < 20: return "🧥 Легкая куртка, худи или уютный свитер."
        elif temp < 25: return "👕 Футболка, джинсы или легкие брюки."
        else: return "🩳 Шорты/юбка, футболка, кепка и солнцезащитные очки 🕶."
    else:
        if temp < 0: return "🧥 Winter coat, warm beanie, scarf, and gloves."
        elif temp < 10: return "🧥 Coat or warm jacket, light scarf."
        elif temp < 20: return "🧥 Light jacket, hoodie, or cozy sweater."
        elif temp < 25: return "👕 T-shirt, jeans, or light pants."
        else: return "🩳 Shorts/skirt, t-shirt, cap, and sunglasses 🕶."

def get_eco_advice(code: int, temp: float, lang: str) -> str:
    is_rain = code in RAIN_CODES
    if lang == "ru":
        if is_rain: return "🌱 <i>Эко-совет: Соберите дождевую воду для полива домашних растений!</i>"
        elif temp > 20: return "🌱 <i>Эко-совет: Отличный день, чтобы пройтись пешком или на велосипеде вместо поездки на авто.</i>"
        else: return "🌱 <i>Эко-совет: Не забывайте выключать свет в пустых комнатах — берегите энергию.</i>"
    else:
        if is_rain: return "🌱 <i>Eco-advice: Collect rainwater to water your indoor plants!</i>"
        elif temp > 20: return "🌱 <i>Eco-advice: Great day to walk or bike instead of driving.</i>"
        else: return "🌱 <i>Eco-advice: Don't forget to turn off lights in empty rooms to save energy.</i>"

def weather_icon(code: int) -> str:
    if code == 1000: return "☀️"
    if code in (1003, 1006): return "⛅"
    if code in (1009,): return "☁️"
    if code in (1030, 1135, 1147): return "🌫"
    if code in (1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243, 1246): return "🌧"
    if code in (1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258): return "❄️"
    if code in (1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252): return "🌨"
    if code in (1087, 1273, 1276, 1279, 1282): return "⛈"
    return "🌤"

def _is_real_url(url: str) -> bool:
    return url.startswith("http")

def affiliate_block(condition_code: int, temp: float, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    sep = "\n━━━━━━━━━━━━━━━━"
    builder = InlineKeyboardBuilder()
    count = 0

    if condition_code in RAIN_CODES:
        text = sep + ("\n🚖 <b>Дождливый день — самое время остаться дома или уехать в тепло:</b>" if lang == "ru" else "\n🚖 <b>Rainy day — stay home or escape somewhere warm:</b>")
        for key in ["bolt", "inDrive", "wolt", "glovo", "umbrella", "tickets"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
    elif condition_code in SNOW_CODES:
        text = sep + ("\n🧥 <b>Холодно и снежно — одевайся теплее:</b>" if lang == "ru" else "\n🧥 <b>Cold and snowy — dress warm:</b>")
        for key in ["bolt", "inDrive", "warm", "clothes"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
    else:
        text = sep + ("\n✈️ <b>Погода и путешествия:</b>" if lang == "ru" else "\n✈️ <b>Weather & travel:</b>")
        for key in ["tickets", "hotels", "clothes"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1

    builder.button(text=AFFILIATE["bothub"][lang], url=AFFILIATE["bothub"]["url"])
    
    is_storm = condition_code in STORM_CODES
    if is_storm or temp >= 35 or temp <= -15:
        builder.button(text="🆘 " + ("Как пережить?", "How to survive?")[lang=="en"], callback_data="sos_alert")
    
    share_text = "Смотри какой крутой прогноз погоды! 🌤" if lang == "ru" else "Check out this cool weather forecast! 🌤"
    share_url = f"https://t.me/share/url?url=https://t.me/pogoda_mood_bot&text={share_text}"
    builder.button(text="↗️ " + ("Поделиться", "Share")[lang=="en"], url=share_url)

    builder.adjust(2)
    return text if count > 0 else "", builder.as_markup()

# ── DATABASE ──────────────────────────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                city TEXT,
                lang TEXT DEFAULT 'ru',
                forecast_format TEXT DEFAULT 'day',
                active INTEGER DEFAULT 1
            )
        """)
        columns_to_add = [
            "joined_at TEXT DEFAULT (datetime('now'))",
            "last_active TEXT DEFAULT (datetime('now'))",
            "tone TEXT DEFAULT 'friendly'",
            "forecast_time TEXT DEFAULT '07:00'"
        ]
        for col_def in columns_to_add:
            try: await db.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
            except Exception: pass
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, city, lang, forecast_format, active, tone, forecast_time FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return {"user_id": row[0], "city": row[1], "lang": row[2], "format": row[3], "active": row[4], "tone": row[5], "time": row[6]}
    return None

async def save_user(user_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_user(user_id)
        if existing:
            kwargs["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            vals = list(kwargs.values()) + [user_id]
            await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        else:
            await db.execute(
                "INSERT INTO users (user_id, city, lang, forecast_format, active, tone, forecast_time) VALUES (?, ?, ?, ?, 1, ?, '07:00')",
                (user_id, kwargs.get("city"), kwargs.get("lang", "ru"), kwargs.get("forecast_format", "day"), kwargs.get("tone", "friendly"))
            )
        await db.commit()

async def get_active_users_for_time(time_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, city, lang, forecast_format, tone FROM users WHERE active = 1 AND city IS NOT NULL AND forecast_time = ?", (time_str,)) as cur:
            return await cur.fetchall()

async def get_all_active_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, city, lang, forecast_format, tone FROM users WHERE active = 1 AND city IS NOT NULL") as cur:
            return await cur.fetchall()

# ── WEATHER API ───────────────────────────────────────────────────────────────
async def fetch_weather(city: str, days: int = 7):
    url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru&aqi=yes"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200: return None
                data = await resp.json()
                return data if "location" in data else None
        except Exception: return None

async def search_city(query: str):
    url = f"https://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={query}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    return results[0]["name"] if results else None
        except Exception: return None

# ── FORECAST FORMATTERS ───────────────────────────────────────────────────────
CURRENCY_MAP = {
    "United Kingdom": "GBP (£)", "USA": "USD ($)", "United States of America": "USD ($)",
    "France": "EUR (€)", "Germany": "EUR (€)", "Italy": "EUR (€)", "Spain": "EUR (€)",
    "Romania": "RON (lei)", "Moldova": "MDL (lei)", "Ukraine": "UAH (₴)",
    "Poland": "PLN (zł)", "Turkey": "TRY (₺)", "Japan": "JPY (¥)", "China": "CNY (¥)"
}

def format_day_forecast(data: dict, lang: str, tone: str) -> str:
    c = data["current"]
    loc = data["location"]
    icon = weather_icon(c["condition"]["code"])
    temp = round(c["temp_c"])
    feels = round(c["feelslike_c"])
    desc = c["condition"]["text"]
    humidity = c["humidity"]
    wind = round(c["wind_kph"])
    wind_dir = c.get("wind_dir", "")
    today = data["forecast"]["forecastday"][0]["day"]
    t_max = round(today["maxtemp_c"])
    t_min = round(today["mintemp_c"])
    rain_chance = today.get("daily_chance_of_rain", 0)
    city_name = loc["name"]
    country = loc["country"]

    if tone == 'strict':
        if lang == "ru":
            return f"{icon} <b>Погода — {city_name}, {country}</b>\n📅 {now_local().strftime('%d.%m.%Y')}\n\n🌡 <b>Температура:</b> {temp}°C (ощущается {feels}°C)\n📊 <b>Мин/Макс:</b> {t_min}°C / {t_max}°C\n🌥 <b>Состояние:</b> {desc}\n💧 <b>Влажность:</b> {humidity}%\n💨 <b>Ветер:</b> {wind} км/ч {wind_dir}\n🌂 <b>Осадки:</b> {rain_chance}%"
        else:
            return f"{icon} <b>Weather — {city_name}, {country}</b>\n📅 {now_local().strftime('%d.%m.%Y')}\n\n🌡 <b>Temperature:</b> {temp}°C (feels {feels}°C)\n📊 <b>Min/Max:</b> {t_min}°C / {t_max}°C\n🌥 <b>Condition:</b> {desc}\n💧 <b>Humidity:</b> {humidity}%\n💨 <b>Wind:</b> {wind} km/h {wind_dir}\n🌂 <b>Rain chance:</b> {rain_chance}%"

    mood = get_mood(c["condition"]["code"], temp, lang)
    wardrobe = get_wardrobe(temp, lang)
    eco = get_eco_advice(c["condition"]["code"], temp, lang)
    currency_note = f"💱 <b>Местная валюта:</b> {CURRENCY_MAP[country]}\n" if country in CURRENCY_MAP and lang == "ru" else f"💱 <b>Local currency:</b> {CURRENCY_MAP[country]}\n" if country in CURRENCY_MAP else ""

    if lang == "ru":
        return f"{icon} <b>Погода — {city_name}, {country}</b>\n📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n{mood}\n\n🌡 <b>Сейчас:</b> {temp}°C (ощущается {feels}°C)\n📊 <b>День/Ночь:</b> {t_max}°C / {t_min}°C\n🌥 <b>Состояние:</b> {desc}\n💧 <b>Влажность:</b> {humidity}%\n💨 <b>Ветер:</b> {wind} км/ч\n🌂 <b>Вероятность дождя:</b> {rain_chance}%\n\n👕 <b>Что надеть:</b> {wardrobe}\n{currency_note}\n{eco}\n\n💬 <i>{get_quote(c['condition']['code'], 'ru')}</i>"
    else:
        return f"{icon} <b>Weather — {city_name}, {country}</b>\n📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n{mood}\n\n🌡 <b>Now:</b> {temp}°C (feels {feels}°C)\n📊 <b>Day/Night:</b> {t_max}°C / {t_min}°C\n🌥 <b>Condition:</b> {desc}\n💧 <b>Humidity:</b> {humidity}%\n💨 <b>Wind:</b> {wind} km/h\n🌂 <b>Rain chance:</b> {rain_chance}%\n\n👕 <b>What to wear:</b> {wardrobe}\n{currency_note}\n{eco}\n\n💬 <i>{get_quote(c['condition']['code'], 'en')}</i>"

def format_week_forecast(data: dict, lang: str) -> str:
    days = data["forecast"]["forecastday"]
    header = f"季 <b>{'Прогноз на неделю' if lang == 'ru' else 'Weekly forecast'} — {data['location']['name']}</b>\n\n"
    lines = [header]
    for d in days:
        date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m")
        icon = weather_icon(d["day"]["condition"]["code"])
        lines.append(f"{icon} <b>{date_str}</b>: {round(d['day']['maxtemp_c'])}°/{round(d['day']['mintemp_c'])}° — {d['day']['condition']['text']}")
    return "\n".join(lines)

def format_month_forecast(data: dict, lang: str) -> str:
    days = data["forecast"]["forecastday"]
    note = "⚠️ <i>Прогноз на месяц приблизительный</i>\n\n" if lang == "ru" else "⚠️ <i>Monthly forecast is approximate</i>\n\n"
    header = f"🗓 <b>{'Прогноз на месяц' if lang == 'ru' else 'Monthly forecast'} — {data['location']['name']}</b>\n{note}"
    lines = [header]
    for d in days:
        date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m")
        lines.append(f"{weather_icon(d['day']['condition']['code'])} <b>{date_str}</b>: {round(d['day']['maxtemp_c'])}°/{round(d['day']['mintemp_c'])}°")
    return "\n".join(lines)

async def build_forecast_message(city: str, fmt: str, lang: str, tone: str = "friendly"):
    days = 14 if fmt == "month" else 7
    data = await fetch_weather(city, days)
    if not data: return None, None
    condition_code = data["current"]["condition"]["code"]
    temp = round(data["current"]["temp_c"])
    
    if fmt == "day": text = format_day_forecast(data, lang, tone)
    elif fmt == "week": text = format_week_forecast(data, lang)
    elif fmt == "month": text = format_month_forecast(data, lang)
    else: text = format_day_forecast(data, lang, tone) + "\n\n" + format_week_forecast(data, lang)

    aff_text, aff_kb = affiliate_block(condition_code, temp, lang)
    text += aff_text
    return text, aff_kb

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def main_menu_kb(lang: str):
    if lang == "ru":
        kb = [
            [KeyboardButton(text="🌤 Погода сейчас"), KeyboardButton(text="⏰ Время рассылки")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="💬 Помощь (Связаться)")]
        ]
    else:
        kb = [
            [KeyboardButton(text="🌤 Weather now"), KeyboardButton(text="⏰ Forecast time")],
            [KeyboardButton(text="⚙️ Settings"), KeyboardButton(text="💬 Help (Contact)")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def select_time_inline_kb(lang: str):
    builder = InlineKeyboardBuilder()
    times = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00"]
    for t in times:
        builder.button(text=t, callback_data=f"settime_{t}")
    builder.button(text="❌ " + ("Отключить рассылку" if lang == "ru" else "Disable alerts"), callback_data="settime_disable")
    builder.adjust(3, 3, 1)
    return builder.as_markup()

def start_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 " + ("Указать город" if lang == "ru" else "Set city"), callback_data="set_city")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский", callback_data="toggle_lang")
    builder.button(text="🎲 " + ("Чем заняться?" if lang == "ru" else "Lucky activity"), callback_data="lucky_activity")
    builder.adjust(1)
    return builder.as_markup()

def format_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 " + ("Сегодня" if lang == "ru" else "Today"),    callback_data="fmt_day")
    builder.button(text="📆 " + ("На неделю" if lang == "ru" else "Week"),   callback_data="fmt_week")
    builder.button(text="🗓 " + ("На месяц" if lang == "ru" else "Month"),   callback_data="fmt_month")
    builder.button(text="🌟 " + ("Всё сразу" if lang == "ru" else "All"),    callback_data="fmt_all")
    builder.adjust(2)
    return builder.as_markup()

def settings_kb(lang: str, tone: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 " + ("Изменить город" if lang == "ru" else "Change city"),  callback_data="set_city")
    builder.button(text="📋 " + ("Формат" if lang == "ru" else "Format"),               callback_data="choose_format")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский",               callback_data="toggle_lang")
    builder.button(text="🗣 " + ("Тон: Дружелюбный" if tone == "friendly" and lang == "ru" else "Тон: Строгий" if tone == "strict" and lang == "ru" else "Tone: Friendly" if tone == "friendly" else "Tone: Strict"), callback_data="toggle_tone")
    builder.adjust(2)
    return builder.as_markup()

# ── TRANSLATIONS ─────────────────────────────────────────────────────────────
T = {
    "welcome": {
        "ru": "👋 Привет! Я <b>PogodaMood</b> — твой личный синоптик с характером 🌤\n\nЯ буду присылать тебе утренний прогноз погоды в удобное время, с эко-советами и подсказками по гардеробу.\n\n👇 Начнем с выбора города:",
        "en": "👋 Hello! I'm <b>PogodaMood</b> — your personal weather assistant with personality 🌤\n\n👇 Start by setting your city:",
    },
    "ask_city": {
        "ru": "🏙 <b>Напиши название города:</b>\nНапример: <code>Кишинев</code> или <code>Москва</code>",
        "en": "🏙 <b>Enter your city name:</b>\nFor example: <code>Chisinau</code> or <code>London</code>",
    },
    "city_saved": {
        "ru": "✅ Город <b>{city}</b> сохранён!\n\n📋 Выбери формат отображения прогноза 👇",
        "en": "✅ City <b>{city}</b> saved!\n\n📋 Choose your forecast format 👇",
    },
}

class CityForm(StatesGroup):
    waiting_city = State()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ── TEXT MENU HANDLERS (REPLY KEYBOARD) ───────────────────────────────────────
@dp.message(F.text.in_(["🌤 Погода сейчас", "🌤 Weather now"]))
async def menu_weather_now(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    tone = user.get("tone", "friendly") if user else "friendly"
    if not user or not user.get("city"):
        await state.set_state(CityForm.waiting_city)
        await msg.answer(T["ask_city"][lang])
        return
    wait_msg = await msg.answer("⏳ " + ("Загружаю прогноз..." if lang == "ru" else "Loading forecast..."))
    text, kb = await build_forecast_message(user["city"], user.get("format", "day"), lang, tone)
    await wait_msg.delete()
    if text: await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)

@dp.message(F.text.in_(["⏰ Время рассылки", "⏰ Forecast time"]))
async def menu_time_settings(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    current_time = user.get("time", "07:00") if user else "07:00"
    is_active = user.get("active", 1) if user else 1
    
    if is_active == 0:
        status = "❌ Отключена" if lang == "ru" else "❌ Disabled"
    else:
        status = f"✅ Каждый день в {current_time}" if lang == "ru" else f"✅ Every day at {current_time}"
        
    txt = f"⏰ <b>Настройка времени рассылки</b>\n\nТекущий статус: <b>{status}</b>\n\nВыбери ниже время, когда тебе удобно получать утренний прогноз:" if lang == "ru" else f"⏰ <b>Forecast Time Settings</b>\n\nCurrent status: <b>{status}</b>\n\nSelect a convenient time below:"
    await msg.answer(txt, reply_markup=select_time_inline_kb(lang))

@dp.message(F.text.in_(["⚙️ Настройки", "⚙️ Settings"]))
async def menu_settings(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    tone = user.get("tone", "friendly") if user else "friendly"
    city = user["city"] if user and user.get("city") else ("не указан" if lang == "ru" else "not set")
    fmt_labels = {"day": "📅 Сегодня", "week": "季 Неделя", "month": "🗓 Месяц", "all": "🌟 Всё сразу"}
    fmt = fmt_labels.get(user["format"] if user else "day", "—")
    
    text = (
        f"⚙️ <b>Настройки профиля</b>\n\n🏙 Город: <b>{city}</b>\n📋 Формат: <b>{fmt}</b>\n🌐 Язык: <b>Русский 🇷🇺</b>\n🗣 Тон: <b>{'Дружелюбный 😇' if tone == 'friendly' else 'Строгий 👔'}</b>"
    ) if lang == "ru" else (
        f"⚙️ <b>Profile Settings</b>\n\n🏙 City: <b>{city}</b>\n📋 Format: <b>{user.get('format', 'day')}</b>\n🌐 Language: <b>English 🌍</b>\n🗣 Tone: <b>{tone}</b>"
    )
    await msg.answer(text, reply_markup=settings_kb(lang, tone))

@dp.message(F.text.in_(["💬 Помощь (Связаться)", "💬 Help (Contact)"]))
async def menu_help(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    if lang == "ru":
        text = f"💬 <b>Помощь и обратная связь</b>\n\nЕсли у тебя возникли проблемы с использованием бота, появились крутые идеи или ты хочешь оставить отзыв — пиши автору напрямую:\n👉 {DEVELOPER_USERNAME}\n\nМы всегда рады улучшать бота ради твоего комфорта! 😊"
    else:
        text = f"💬 <b>Help & Support</b>\n\nIf you have any issues using this bot, ideas, or recommendations, feel free to contact the author directly:\n👉 {DEVELOPER_USERNAME}"
    await msg.answer(text)

# ── COMMANDS (BACKWARD COMPATIBILITY) ─────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    if not user: await save_user(msg.from_user.id, lang=lang)
    await msg.answer(T["welcome"][lang], reply_markup=start_kb(lang))

@dp.message(Command("weather"))
async def cmd_weather_legacy(msg: Message, state: FSMContext):
    await menu_weather_now(msg, state)

@dp.message(Command("settings"))
async def cmd_settings_legacy(msg: Message):
    await menu_settings(msg)

@dp.message(Command("help"))
async def cmd_help_legacy(msg: Message):
    await menu_help(msg)

# ── FSM & CALLBACKS ───────────────────────────────────────────────────────────
@dp.message(CityForm.waiting_city)
async def process_city(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    city_input = msg.text.strip()
    wait_msg = await msg.answer("🔍 ...")

    data = await fetch_weather(city_input, 1)
    if not data:
        found_name = await search_city(city_input)
        if found_name: data = await fetch_weather(found_name, 1)

    await wait_msg.delete()
    if not data:
        await msg.answer("🤔 Не могу найти этот город. Попробуй ещё раз." if lang == "ru" else "🤔 City not found. Try again.")
        return

    city_name = data["location"]["name"]
    await save_user(msg.from_user.id, city=city_name)
    await state.clear()
    await msg.answer(T["city_saved"][lang].format(city=city_name), reply_markup=format_kb(lang))

@dp.callback_query(F.data.startswith("settime_"))
async def cb_set_time(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    chosen = call.data.replace("settime_", "")
    
    if chosen == "disable":
        await save_user(call.from_user.id, active=0)
        txt = "❌ Автоматическая рассылка прогноза отключена." if lang == "ru" else "❌ Automatic forecast disabled."
    else:
        await save_user(call.from_user.id, active=1, forecast_time=chosen)
        txt = f"✅ Успешно! Буду присылать прогноз каждый день в <b>{chosen}</b> 🌅" if lang == "ru" else f"✅ Success! Forecast will be sent daily at <b>{chosen}</b> 🌅"
        
    await call.message.answer(txt, reply_markup=main_menu_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "set_city")
async def cb_set_city(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    await state.set_state(CityForm.waiting_city)
    await call.message.answer(T["ask_city"][user["lang"] if user else "ru"])
    await call.answer()

@dp.callback_query(F.data == "toggle_lang")
async def cb_toggle_lang(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    new_lang = "en" if (user and user.get("lang") == "ru") else "ru"
    await save_user(call.from_user.id, lang=new_lang)
    await call.message.answer("Menu updated! / Меню обновлено!", reply_markup=main_menu_kb(new_lang))
    await call.answer()

@dp.callback_query(F.data == "toggle_tone")
async def cb_toggle_tone(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    if not user: return
    new_tone = "strict" if user.get("tone") == "friendly" else "friendly"
    await save_user(call.from_user.id, tone=new_tone)
    await call.answer("Тон изменен!" if user["lang"] == "ru" else "Tone changed!")
    # Перевызов настроек
    class DummyMsg:
        def __init__(self, c): self.from_user = c.from_user; self.answer = c.message.answer
    await menu_settings(DummyMsg(call))

@dp.callback_query(F.data == "choose_format")
async def cb_choose_format(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    await call.message.answer("📋 Выбери формат:" if user["lang"] == "ru" else "📋 Choose format:", reply_markup=format_kb(user["lang"]))
    await call.answer()

@dp.callback_query(F.data.startswith("fmt_"))
async def cb_format_select(call: CallbackQuery):
    fmt = call.data.replace("fmt_", "")
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(call.from_user.id, forecast_format=fmt)
    await call.message.answer("🎉 Формат сохранен! Настройки завершены.", reply_markup=main_menu_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "lucky_activity")
async def cb_lucky_activity(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    acts = [
        {"ru": "🍿 Отличный день для хорошего фильма дома или в кино!", "en": "🍿 Great day to watch a movie!"},
        {"ru": "☕️ Зайди в любимую кофейню и порадуй себя вкусным напитком.", "en": "☕️ Visit your favorite coffee shop."},
        {"ru": "🏃‍♂️ Время для прогулки на свежем воздухе или легкой тренировки.", "en": "🏃‍♂️ Great day for an outdoor walk."}
    ]
    await call.message.answer(f"🎲 {random.choice(acts)[lang]}")
    await call.answer()

@dp.callback_query(F.data == "sos_alert")
async def cb_sos_alert(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    ru = "🆘 Защита при непогоде:\n1. Оставайтесь в помещении.\n2. Закройте окна.\n3. Держите телефон заряженным."
    en = "🆘 Safety tips:\n1. Stay indoors.\n2. Keep windows closed.\n3. Keep your phone charged."
    await call.answer(ru if user["lang"] == "ru" else en, show_alert=True)

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
async def send_personalized_forecasts():
    """Срабатывает каждую минуту и рассылает прогнозы тем, чьё время совпало"""
    current_time_str = now_local().strftime("%H:%M")
    users = await get_active_users_for_time(current_time_str)
    
    for user_id, city, lang, fmt, tone in users:
        try:
            text, kb = await build_forecast_message(city, fmt, lang, tone)
            if text:
                prefix = "🌅 <b>Доброе утро! Вот твой прогноз погоды:</b>\n\n" if lang == "ru" else "🌅 <b>Good morning! Here is your weather report:</b>\n\n"
                await bot.send_message(user_id, prefix + text, reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logging.warning(f"Error sending periodic report to {user_id}: {e}")

async def send_evening_warnings():
    """Вечерняя умная проверка погоды (работает в 20:00)"""
    users = await get_all_active_users()
    for user_id, city, lang, fmt, tone in users:
        try:
            data = await fetch_weather(city, 2)
            if not data or len(data["forecast"]["forecastday"]) < 2: continue
            tomorrow = data["forecast"]["forecastday"][1]["day"]
            code = tomorrow["condition"]["code"]
            
            msg = None
            if code in SNOW_CODES:
                msg = "❄️ Напоминание: Завтра ожидается снег. Оденьтесь теплее!" if lang == "ru" else "❄️ Reminder: Snow expected tomorrow. Dress warm!"
            elif code in RAIN_CODES:
                msg = "🌧 Напоминание: Завтра обещают дождь, не забудьте взять зонт!" if lang == "ru" else "🌧 Reminder: Rain expected tomorrow, don't forget an umbrella!"
                
            if msg: await bot.send_message(user_id, msg)
        except Exception: pass

# ── MAIN RUNNER ───────────────────────────────────────────────────────────────
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    scheduler = AsyncIOScheduler(timezone="Europe/Chisinau")
    # Проверяем базу каждую минуту на соответствие кастомному времени
    scheduler.add_job(send_personalized_forecasts, CronTrigger(minute="*"))
    # Вечерние предупреждения остаются фиксированными в 20:00
    scheduler.add_job(send_evening_warnings, CronTrigger(hour=20, minute=0))
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
