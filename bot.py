import asyncio
import logging
import aiohttp
import aiosqlite
from datetime import datetime, time
from aiogram import Bot, Dispatcher, F
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

# ── AFFILIATE LINKS ──────────────────────────────────────────────────────────
AFFILIATE = {
    "bolt":    {"ru": "🚗 Заказать такси Bolt",    "en": "🚗 Order Bolt taxi",    "url": "https://invite.bolt.eu/POGODA"},
    "inDrive": {"ru": "🚕 Заказать inDrive",        "en": "🚕 Order inDrive",       "url": "https://indrive.com/promo/pogoda"},
    "wolt":    {"ru": "🍔 Доставка еды Wolt",       "en": "🍔 Food delivery Wolt",  "url": "https://wolt.com"},
    "glovo":   {"ru": "🛵 Доставка Glovo",          "en": "🛵 Glovo delivery",      "url": "https://glovoapp.com"},
    "clothes": {"ru": "👗 Одежда по погоде",        "en": "👗 Clothes for weather",  "url": "https://www.lamoda.ru"},
}

# ── TRANSLATIONS ─────────────────────────────────────────────────────────────
T = {
    "welcome": {
        "ru": (
            "👋 Привет! Я <b>PogodaMood</b> — твой личный синоптик в Telegram.\n\n"
            "🌤 Каждое утро буду присылать прогноз погоды прямо тебе.\n\n"
            "Для начала — <b>укажи свой город</b> командой /city\n"
            "или нажми кнопку ниже 👇"
        ),
        "en": (
            "👋 Hello! I'm <b>PogodaMood</b> — your personal weather assistant.\n\n"
            "🌤 Every morning I'll send you the weather forecast.\n\n"
            "Let's start — <b>set your city</b> with /city\n"
            "or tap the button below 👇"
        ),
    },
    "ask_city": {
        "ru": "🏙 Напиши название своего города на английском или русском языке:\n\nПример: <code>Chisinau</code> или <code>Moscow</code>",
        "en": "🏙 Enter your city name:\n\nExample: <code>Chisinau</code> or <code>London</code>",
    },
    "city_saved": {
        "ru": "✅ Город <b>{city}</b> сохранён!\n\nТеперь выбери, что присылать каждое утро 👇",
        "en": "✅ City <b>{city}</b> saved!\n\nNow choose what to send every morning 👇",
    },
    "city_error": {
        "ru": "❌ Город не найден. Попробуй написать на английском, например: <code>Chisinau</code>",
        "en": "❌ City not found. Try writing in English, e.g.: <code>Chisinau</code>",
    },
    "no_city": {
        "ru": "⚠️ Сначала укажи город командой /city",
        "en": "⚠️ Please set your city first with /city",
    },
    "choose_format": {
        "ru": "📋 Выбери формат прогноза:",
        "en": "📋 Choose forecast format:",
    },
    "format_saved": {
        "ru": "✅ Готово! Буду присылать прогноз каждое утро в <b>7:00</b> 🌅\n\nКоманды:\n/weather — погода прямо сейчас\n/settings — изменить настройки\n/help — помощь",
        "en": "✅ Done! I'll send forecast every morning at <b>7:00</b> 🌅\n\nCommands:\n/weather — weather right now\n/settings — change settings\n/help — help",
    },
    "btn_day":   {"ru": "📅 На сегодня",    "en": "📅 Today"},
    "btn_week":  {"ru": "📆 На неделю",     "en": "📆 Week"},
    "btn_month": {"ru": "🗓 На месяц",      "en": "🗓 Month"},
    "btn_all":   {"ru": "🌟 Всё сразу",     "en": "🌟 All"},
    "btn_city":  {"ru": "🏙 Изменить город","en": "🏙 Change city"},
    "btn_fmt":   {"ru": "📋 Формат",        "en": "📋 Format"},
    "help": {
        "ru": (
            "ℹ️ <b>Помощь</b>\n\n"
            "/start — главное меню\n"
            "/city — изменить город\n"
            "/weather — погода сейчас\n"
            "/settings — настройки\n"
            "/help — эта справка\n\n"
            "🕖 Рассылка приходит каждый день в <b>7:00</b> по Кишинёву (UTC+3)"
        ),
        "en": (
            "ℹ️ <b>Help</b>\n\n"
            "/start — main menu\n"
            "/city — change city\n"
            "/weather — current weather\n"
            "/settings — settings\n"
            "/help — this help\n\n"
            "🕖 Daily forecast sent at <b>7:00</b> Chisinau time (UTC+3)"
        ),
    },
}

# ── WEATHER ICONS ─────────────────────────────────────────────────────────────
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
    """Контекстный блок с партнёрскими ссылками по погоде"""
    lines = ["\n─────────────────"]
    # Дождь/снег → такси
    if condition_code in range(1063, 1282):
        lines.append(f"<a href='{AFFILIATE['bolt']['url']}'>{AFFILIATE['bolt'][lang]}</a>")
        lines.append(f"<a href='{AFFILIATE['inDrive']['url']}'>{AFFILIATE['inDrive'][lang]}</a>")
        if lang == "ru":
            lines.append(f"<a href='{AFFILIATE['wolt']['url']}'>{AFFILIATE['wolt'][lang]}</a> — не выходи под дождь 🏠")
        else:
            lines.append(f"<a href='{AFFILIATE['wolt']['url']}'>{AFFILIATE['wolt'][lang]}</a> — stay dry at home 🏠")
    # Жара → еда/одежда
    elif condition_code == 1000:
        lines.append(f"<a href='{AFFILIATE['glovo']['url']}'>{AFFILIATE['glovo'][lang]}</a>")
        lines.append(f"<a href='{AFFILIATE['clothes']['url']}'>{AFFILIATE['clothes'][lang]}</a>")
    # Холод → одежда
    else:
        lines.append(f"<a href='{AFFILIATE['clothes']['url']}'>{AFFILIATE['clothes'][lang]}</a>")
    lines.append("─────────────────")
    return "\n".join(lines)

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

# ── WEATHER API ───────────────────────────────────────────────────────────────
async def fetch_weather(city: str, days: int = 7):
    url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None

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

def format_week_forecast(data: dict, lang: str) -> str:
    loc = data["location"]
    city_name = loc["name"]
    days = data["forecast"]["forecastday"]
    header = f"📆 <b>{'Прогноз на неделю' if lang == 'ru' else 'Weekly forecast'} — {city_name}</b>\n\n"
    lines = [header]
    for d in days:
        date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m %a") if lang == "en" else datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m")
        icon = weather_icon(d["day"]["condition"]["code"])
        t_max = round(d["day"]["maxtemp_c"])
        t_min = round(d["day"]["mintemp_c"])
        desc = d["day"]["condition"]["text"]
        lines.append(f"{icon} <b>{date_str}</b>: {t_max}°/{t_min}° — {desc}")
    return "\n".join(lines)

def format_month_forecast(data: dict, lang: str) -> str:
    """WeatherAPI free дает до 14 дней, показываем с предупреждением"""
    loc = data["location"]
    city_name = loc["name"]
    days = data["forecast"]["forecastday"]
    note = "⚠️ <i>Прогноз на месяц менее точен — используйте как ориентир</i>\n\n" if lang == "ru" else "⚠️ <i>Monthly forecast is approximate — use as guidance</i>\n\n"
    header = f"🗓 <b>{'Прогноз на месяц' if lang == 'ru' else 'Monthly forecast'} — {city_name}</b>\n{note}"
    lines = [header]
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        date_str = dt.strftime("%d.%m")
        icon = weather_icon(d["day"]["condition"]["code"])
        t_max = round(d["day"]["maxtemp_c"])
        t_min = round(d["day"]["mintemp_c"])
        lines.append(f"{icon} <b>{date_str}</b>: {t_max}°/{t_min}°")
    return "\n".join(lines)

async def build_forecast_message(city: str, fmt: str, lang: str) -> str | None:
    days = 14 if fmt == "month" else 7
    data = await fetch_weather(city, days)
    if not data:
        return None
    condition_code = data["current"]["condition"]["code"]
    if fmt == "day":
        text = format_day_forecast(data, lang)
    elif fmt == "week":
        text = format_week_forecast(data, lang)
    elif fmt == "month":
        text = format_month_forecast(data, lang)
    else:  # all
        text = format_day_forecast(data, lang) + "\n\n" + format_week_forecast(data, lang)
    text += affiliate_block(condition_code, lang)
    return text

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def start_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=T["btn_city"][lang], callback_data="set_city")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский", callback_data="toggle_lang")
    builder.adjust(1)
    return builder.as_markup()

def format_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=T["btn_day"][lang],   callback_data="fmt_day")
    builder.button(text=T["btn_week"][lang],  callback_data="fmt_week")
    builder.button(text=T["btn_month"][lang], callback_data="fmt_month")
    builder.button(text=T["btn_all"][lang],   callback_data="fmt_all")
    builder.adjust(2)
    return builder.as_markup()

def settings_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=T["btn_city"][lang], callback_data="set_city")
    builder.button(text=T["btn_fmt"][lang],  callback_data="choose_format")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский", callback_data="toggle_lang")
    builder.adjust(2)
    return builder.as_markup()

# ── FSM ───────────────────────────────────────────────────────────────────────
class CityForm(StatesGroup):
    waiting_city = State()

# ── BOT + DISPATCHER ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

# ── HANDLERS ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(msg.from_user.id, lang=lang)
    await msg.answer(T["welcome"][lang], reply_markup=start_kb(lang))

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    await msg.answer(T["help"][lang])

@dp.message(Command("city"))
async def cmd_city(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    await state.set_state(CityForm.waiting_city)
    await msg.answer(T["ask_city"][lang])

@dp.message(Command("settings"))
async def cmd_settings(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    city = user["city"] if user and user["city"] else ("не указан" if lang == "ru" else "not set")
    fmt_map = {"day": T["btn_day"][lang], "week": T["btn_week"][lang], "month": T["btn_month"][lang], "all": T["btn_all"][lang]}
    fmt = fmt_map.get(user["format"] if user else "day", "—")
    text = (
        f"⚙️ <b>{'Настройки' if lang == 'ru' else 'Settings'}</b>\n\n"
        f"🏙 {'Город' if lang == 'ru' else 'City'}: <b>{city}</b>\n"
        f"📋 {'Формат' if lang == 'ru' else 'Format'}: <b>{fmt}</b>\n"
        f"🌐 {'Язык' if lang == 'ru' else 'Language'}: <b>{'Русский' if lang == 'ru' else 'English'}</b>"
    )
    await msg.answer(text, reply_markup=settings_kb(lang))

@dp.message(Command("weather"))
async def cmd_weather(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    if not user or not user["city"]:
        await msg.answer(T["no_city"][lang])
        return
    wait_text = "⏳ Загружаю прогноз..." if lang == "ru" else "⏳ Loading forecast..."
    wait_msg = await msg.answer(wait_text)
    text = await build_forecast_message(user["city"], user["format"], lang)
    await wait_msg.delete()
    if text:
        await msg.answer(text, disable_web_page_preview=True)
    else:
        err = "❌ Не удалось получить данные. Попробуй позже." if lang == "ru" else "❌ Failed to get data. Try again later."
        await msg.answer(err)

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

# ── CALLBACKS ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "set_city")
async def cb_set_city(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await state.set_state(CityForm.waiting_city)
    await call.message.answer(T["ask_city"][lang])
    await call.answer()

@dp.callback_query(F.data == "choose_format")
async def cb_choose_format(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await call.message.answer(T["choose_format"][lang], reply_markup=format_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "toggle_lang")
async def cb_toggle_lang(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    new_lang = "en" if (user and user["lang"] == "ru") else "ru"
    await save_user(call.from_user.id, lang=new_lang)
    await call.message.answer(T["welcome"][new_lang], reply_markup=start_kb(new_lang))
    await call.answer()

@dp.callback_query(F.data.startswith("fmt_"))
async def cb_format(call: CallbackQuery):
    fmt = call.data.replace("fmt_", "")
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(call.from_user.id, forecast_format=fmt)
    await call.message.answer(T["format_saved"][lang])
    await call.answer()

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
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

# ── MAIN ──────────────────────────────────────────────────────────────────────
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
