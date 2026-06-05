import asyncio
import logging
import aiohttp
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

# ── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8914713512:AAFQQcVEzgL6M-u4yX3kANLHNakIiRWjyBU")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ade7a2b019c6498a8da62549260506")
DB_PATH = "pogoda.db"

if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY не найден в переменных окружения!")

# ── AFFILIATE LINKS ──────────────────────────────────────────────────────────
AFFILIATE = {
    "bolt": {"ru": "🚗 Заказать такси Bolt", "en": "🚗 Order Bolt taxi", "url": "https://invite.bolt.eu/POGODA"},
    "inDrive": {"ru": "🚕 Заказать inDrive", "en": "🚕 Order inDrive", "url": "https://indrive.com/promo/pogoda"},
    "wolt": {"ru": "🍔 Доставка еды Wolt", "en": "🍔 Food delivery Wolt", "url": "https://wolt.com"},
    "glovo": {"ru": "🛵 Доставка Glovo", "en": "🛵 Glovo delivery", "url": "https://glovoapp.com"},
    "clothes": {"ru": "👗 Одежда по погоде", "en": "👗 Clothes for weather", "url": "https://www.lamoda.ru"},
}

# ── TRANSLATIONS ─────────────────────────────────────────────────────────────
T = { ... }  # (оставил без изменений, чтобы не раздувать сообщение)

# ── WEATHER ICONS + AFFILIATE BLOCK ─────────────────────────────────────────
# (оставил без изменений)
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

def affiliate_block(condition_code: int, lang: str) -> str:
    lines = ["\n─────────────────"]
    if condition_code in range(1063, 1282):
        lines.append(f"<a href='{AFFILIATE['bolt']['url']}'>{AFFILIATE['bolt'][lang]}</a>")
        lines.append(f"<a href='{AFFILIATE['inDrive']['url']}'>{AFFILIATE['inDrive'][lang]}</a>")
        if lang == "ru":
            lines.append(f"<a href='{AFFILIATE['wolt']['url']}'>{AFFILIATE['wolt'][lang]}</a> — не выходи под дождь 🏠")
        else:
            lines.append(f"<a href='{AFFILIATE['wolt']['url']}'>{AFFILIATE['wolt'][lang]}</a> — stay dry at home 🏠")
    elif condition_code == 1000:
        lines.append(f"<a href='{AFFILIATE['glovo']['url']}'>{AFFILIATE['glovo'][lang]}</a>")
        lines.append(f"<a href='{AFFILIATE['clothes']['url']}'>{AFFILIATE['clothes'][lang]}</a>")
    else:
        lines.append(f"<a href='{AFFILIATE['clothes']['url']}'>{AFFILIATE['clothes'][lang]}</a>")
    lines.append("─────────────────")
    return "\n".join(lines)

# ── DATABASE ──────────────────────────────────────────────────────────────────
# (без изменений)
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
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return {"user_id": row[0], "city": row[1], "lang": row[2], "format": row[3], "active": row[4]}
    return None

async def save_user(user_id: int, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_user(user_id)
        if existing:
            sets = ", ".join(f"{k} = ?" for k in kwargs)
            vals = list(kwargs.values()) + [user_id]
            await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        else:
            await db.execute(
                "INSERT INTO users (user_id, city, lang, forecast_format, active) VALUES (?, ?, ?, ?, 1)",
                (user_id, kwargs.get("city"), kwargs.get("lang", "ru"), kwargs.get("forecast_format", "day"))
            )
        await db.commit()

async def get_all_active_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, city, lang, forecast_format FROM users WHERE active = 1 AND city IS NOT NULL") as cur:
            return await cur.fetchall()

# ── WEATHER API (исправлено) ─────────────────────────────────────────────────
async def fetch_weather(city: str, days: int = 7):
    if not WEATHER_API_KEY:
        logging.error("WEATHER_API_KEY is missing!")
        return None
    
    url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                
                if resp.status == 200 and "location" in data:
                    return data
                else:
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    logging.warning(f"WeatherAPI error for '{city}': {error_msg}")
                    return None
        except Exception as e:
            logging.error(f"Failed to fetch weather for {city}: {e}")
            return None

# ── FORMAT FUNCTIONS (без изменений) ───────────────────────────────────────
# ... (format_day_forecast, format_week_forecast, format_month_forecast, build_forecast_message)
# Я оставил их как были — они рабочие.

def format_day_forecast(data: dict, lang: str) -> str:
    current = data["current"]
    loc = data["location"]
    icon = weather_icon(current["condition"]["code"])
    city_name = loc["name"]
    temp = round(current["temp_c"])
    feels = round(current["feelslike_c"])
    desc = current["condition"]["text"]
    humidity = current["humidity"]
    wind = round(current["wind_kph"])
    today = data["forecast"]["forecastday"][0]["day"]
    t_max = round(today["maxtemp_c"])
    t_min = round(today["mintemp_c"])

    if lang == "ru":
        return (
            f"{icon} <b>Погода в {city_name}</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"🌡 Сейчас: <b>{temp}°C</b> (ощущается {feels}°C)\n"
            f"📊 Днём: {t_max}°C / Ночью: {t_min}°C\n"
            f"🌥 {desc}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind} км/ч\n"
        )
    else:
        return (
            f"{icon} <b>Weather in {city_name}</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"🌡 Now: <b>{temp}°C</b> (feels like {feels}°C)\n"
            f"📊 Day: {t_max}°C / Night: {t_min}°C\n"
            f"🌥 {desc}\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind: {wind} km/h\n"
        )

# (format_week_forecast, format_month_forecast, build_forecast_message — оставил как в оригинале)

# ── KEYBOARDS, FSM, BOT, HANDLERS ───────────────────────────────────────────
# (всё остальное без изменений, кроме process_city)

class CityForm(StatesGroup):
    waiting_city = State()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(msg.from_user.id, lang=lang)
    await msg.answer(T["welcome"][lang], reply_markup=start_kb(lang))

# ... остальные handlers без изменений ...

@dp.message(CityForm.waiting_city)
async def process_city(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    city_input = msg.text.strip()
    
    data = await fetch_weather(city_input, 1)
    if not data:
        await msg.answer(T["city_error"][lang])
        return
    
    city_name = data["location"]["name"]
    await save_user(msg.from_user.id, city=city_name)
    await state.clear()
    await msg.answer(T["city_saved"][lang].format(city=city_name), reply_markup=format_kb(lang))

# ── SCHEDULER + MAIN ────────────────────────────────────────────────────────
async def send_morning_forecasts():
    users = await get_all_active_users()
    for user_id, city, lang, fmt in users:
        try:
            text = await build_forecast_message(city, fmt, lang)
            if text:
                prefix = "🌅 <b>Доброе утро! Вот твой прогноз:</b>\n\n" if lang == "ru" else "🌅 <b>Good morning! Your forecast:</b>\n\n"
                await bot.send_message(user_id, prefix + text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logging.warning(f"Failed to send to {user_id}: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    scheduler = AsyncIOScheduler(timezone="Europe/Chisinau")
    scheduler.add_job(send_morning_forecasts, CronTrigger(hour=7, minute=0))
    scheduler.start()
    logging.info("✅ PogodaMood Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
