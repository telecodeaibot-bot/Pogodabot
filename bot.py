import asyncio
import logging
import aiohttp
import aiosqlite
from datetime import datetime
import pytz

def now_local():
    return datetime.now(pytz.timezone("Europe/Chisinau"))
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

# ── QUOTES ───────────────────────────────────────────────────────────────────
import random

QUOTES = {
    "sun": [
        {"ru": "☀️ «Каждое утро — это шанс начать заново.» — Неизвестный автор", "en": "☀️ 'Every morning is a chance to begin again.' — Unknown"},
        {"ru": "🌅 «Не жди подходящего момента — создавай его.» — Джордж Бернард Шоу", "en": "🌅 'Don't wait for the right moment. Create it.' — G.B. Shaw"},
        {"ru": "✨ «Жизнь прекрасна. Просто иногда нужно напоминать себе об этом.»", "en": "✨ 'Life is beautiful. Sometimes you just need to remind yourself.' — Unknown"},
        {"ru": "💪 «Успех — это сумма небольших усилий, повторяемых день за днём.» — Роберт Коллиер", "en": "💪 'Success is the sum of small efforts repeated day in and day out.' — R. Collier"},
        {"ru": "🔥 «Единственный способ делать великое дело — любить то, что делаешь.» — Стив Джобс", "en": "🔥 'The only way to do great work is to love what you do.' — Steve Jobs"},
        {"ru": "🚀 «Мечты не работают, если не работаешь ты.» — Джон Максвелл", "en": "🚀 'Dreams don't work unless you do.' — John C. Maxwell"},
        {"ru": "🌻 «Делай сегодня то, что другие не хотят — завтра будешь жить так, как другие не могут.»", "en": "🌻 'Do today what others won't, so tomorrow you can do what others can't.' — Unknown"},
        {"ru": "🌟 «Верь в себя — и всё станет возможным.»", "en": "🌟 'Believe in yourself and anything becomes possible.' — Unknown"},
    ],
    "rain": [
        {"ru": "🌧 «После дождя всегда выходит солнце.»", "en": "🌧 'After every storm, the sun will smile.' — Unknown"},
        {"ru": "☕ «Дождливый день — лучший повод для хорошей книги и горячего чая.»", "en": "☕ 'A rainy day is a perfect excuse for a good book and hot tea.' — Unknown"},
        {"ru": "🌈 «Жизнь — не в том, чтобы ждать пока пройдёт буря, а в том, чтобы учиться танцевать под дождём.» — Вивиан Грин", "en": "🌈 'Life isn't about waiting for the storm to pass — it's about learning to dance in the rain.' — V. Greene"},
        {"ru": "💧 «Дождь смывает всё лишнее и оставляет только главное.»", "en": "💧 'Rain washes away everything unnecessary, leaving only what matters.' — Unknown"},
        {"ru": "🏠 «Уют начинается там, где ты чувствуешь себя дома.»", "en": "🏠 'Coziness begins where you feel at home.' — Unknown"},
        {"ru": "🌿 «Трудности — это дождь. Без него не вырастет ничего прекрасного.»", "en": "🌿 'Difficulties are like rain. Without it, nothing beautiful grows.' — Unknown"},
        {"ru": "📚 «Хорошая книга в дождливый день — это маленькое счастье.»", "en": "📚 'A good book on a rainy day is a small happiness.' — Unknown"},
        {"ru": "🎵 «Пусть дождь снаружи — внутри тебя пусть будет солнце.»", "en": "🎵 'Let it rain outside — let there be sunshine within you.' — Unknown"},
    ],
    "snow": [
        {"ru": "❄️ «Зима — это когда земля отдыхает и набирается сил.»", "en": "❄️ 'Winter is when the earth rests and gathers strength.' — Unknown"},
        {"ru": "🧣 «Холод снаружи — тепло внутри. Всё в твоих руках.»", "en": "🧣 'Cold outside, warmth within. It's all in your hands.' — Unknown"},
        {"ru": "🔥 «Трудности закаляют — как мороз закаляет деревья.»", "en": "🔥 'Hardships forge us, just as frost hardens the trees.' — Unknown"},
        {"ru": "🕯 «Самые тёплые воспоминания рождаются в самые холодные дни.»", "en": "🕯 'The warmest memories are born on the coldest days.' — Unknown"},
        {"ru": "⛄ «Снег — это природа, которая говорит: притормози и насладись моментом.»", "en": "⛄ 'Snow is nature saying: slow down and enjoy the moment.' — Unknown"},
    ],
    "cloud": [
        {"ru": "⛅ «Облака не могут скрыть солнце навсегда.»", "en": "⛅ 'Clouds cannot hide the sun forever.' — Unknown"},
        {"ru": "🌫 «Даже в туман можно найти свой путь, если знаешь куда идти.»", "en": "🌫 'Even in fog, you can find your way if you know where you're going.' — Unknown"},
        {"ru": "💭 «Серый день — отличный фон для ярких мыслей.»", "en": "💭 'A grey day is a perfect backdrop for bright thoughts.' — Unknown"},
        {"ru": "🌙 «Не каждый день будет солнечным — и это тоже нормально.»", "en": "🌙 'Not every day will be sunny — and that's okay too.' — Unknown"},
        {"ru": "🧩 «Пасмурный день напоминает: красота не всегда очевидна.»", "en": "🧩 'A cloudy day reminds us: beauty is not always obvious.' — Unknown"},
    ],
    "any": [
        {"ru": "💡 «Маленький шаг каждый день — большой путь за год.»", "en": "💡 'A small step every day — a great journey in a year.' — Unknown"},
        {"ru": "🎯 «Цель без плана — просто мечта.» — Антуан де Сент-Экзюпери", "en": "🎯 'A goal without a plan is just a wish.' — Antoine de Saint-Exupery"},
        {"ru": "❤️ «Будь собой — все остальные роли уже заняты.» — Оскар Уайльд", "en": "❤️ 'Be yourself — everyone else is already taken.' — Oscar Wilde"},
        {"ru": "🌱 «Расти там, где тебя посадили.»", "en": "🌱 'Bloom where you are planted.' — Unknown"},
        {"ru": "🧠 «Единственный человек, которым ты должен быть лучше — это ты вчерашний.»", "en": "🧠 'The only person you should be better than is who you were yesterday.' — Unknown"},
        {"ru": "🌍 «Путешествие в тысячу миль начинается с одного шага.» — Лао-цзы", "en": "🌍 'A journey of a thousand miles begins with a single step.' — Lao Tzu"},
        {"ru": "💬 «Говори меньше, делай больше.» — Бенджамин Франклин", "en": "💬 'Well done is better than well said.' — Benjamin Franklin"},
        {"ru": "🎨 «Творчество — это интеллект, который развлекается.» — Альберт Эйнштейн", "en": "🎨 'Creativity is intelligence having fun.' — Albert Einstein"},
        {"ru": "🏆 «Победитель — это просто мечтатель, который не сдался.» — Нельсон Мандела", "en": "🏆 'A winner is a dreamer who never gives up.' — Nelson Mandela"},
        {"ru": "⏳ «Не трать время на то, чтобы быть кем-то другим.»", "en": "⏳ 'Don't waste time being someone else.' — Unknown"},
    ]
}

SNOW_CODES_Q = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258,
                1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252}
RAIN_CODES_Q = {1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243,
                1246, 1087, 1273, 1276, 1279, 1282}

def get_quote(condition_code: int, lang: str) -> str:
    if condition_code in RAIN_CODES_Q:
        pool = QUOTES["rain"] + QUOTES["any"]
    elif condition_code in SNOW_CODES_Q:
        pool = QUOTES["snow"] + QUOTES["any"]
    elif condition_code == 1000:
        pool = QUOTES["sun"] + QUOTES["any"]
    elif condition_code in (1003, 1006, 1009, 1030, 1135, 1147):
        pool = QUOTES["cloud"] + QUOTES["any"]
    else:
        pool = QUOTES["any"]
    return random.choice(pool)[lang]


# ── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8914713512:AAFQQcVEzgL6M-u4yX3kANLHNakIiRWjyBU")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ade7a2b019c6498a8da62549260506")
DB_PATH = "pogoda.db"

# ── AFFILIATE LINKS ──────────────────────────────────────────────────────────
# 👇 ЗАМЕНИ URL на свои партнёрские ссылки когда получишь их в Admitad или другой CPA сети
AFFILIATE = {
    "bolt":       {"ru": "🚗 Заказать такси Bolt",        "en": "🚗 Order Bolt taxi",         "url": "ВСТАВЬ_ССЫЛКУ_BOLT"},
    "inDrive":    {"ru": "🚕 Заказать inDrive",            "en": "🚕 Order inDrive",           "url": "ВСТАВЬ_ССЫЛКУ_INDRIVE"},
    "wolt":       {"ru": "🍔 Доставка еды Wolt",           "en": "🍔 Food delivery Wolt",      "url": "ВСТАВЬ_ССЫЛКУ_WOLT"},
    "glovo":      {"ru": "🛵 Доставка Glovo",              "en": "🛵 Glovo delivery",          "url": "ВСТАВЬ_ССЫЛКУ_GLOVO"},
    "clothes":    {"ru": "👗 Одежда по погоде",            "en": "👗 Clothes for weather",     "url": "ВСТАВЬ_ССЫЛКУ_ОДЕЖДА"},
    "rainy_ideas":{"ru": "🛍 Идеи для дождливого дня",    "en": "🛍 Rainy day ideas",         "url": "ВСТАВЬ_ССЫЛКУ_ALIEXPRESS"},
    "tickets":    {"ru": "✈️ Дешёвые авиабилеты",         "en": "✈️ Cheap flights",           "url": "ВСТАВЬ_ССЫЛКУ_AVIASALES"},
    "hotels":     {"ru": "🏨 Найти отель",                 "en": "🏨 Find a hotel",            "url": "ВСТАВЬ_ССЫЛКУ_BOOKING"},
    "umbrella":   {"ru": "☂️ Товары для дождя",           "en": "☂️ Rain essentials",         "url": "ВСТАВЬ_ССЫЛКУ_ЗОНТЫ"},
    "warm":       {"ru": "🧥 Тёплая одежда",              "en": "🧥 Warm clothes",            "url": "ВСТАВЬ_ССЫЛКУ_ТЁПЛОЕ"},
}

# ── WEATHER MOOD ─────────────────────────────────────────────────────────────
# Коды снега/льда WeatherAPI
SNOW_CODES = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258,
              1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252}
# Коды дождя WeatherAPI
RAIN_CODES = {1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243,
              1246, 1087, 1273, 1276, 1279, 1282}
# Коды грозы
STORM_CODES = {1087, 1273, 1276, 1279, 1282}

def get_mood(code: int, temp: float, lang: str) -> str:
    """Эмоциональная подача — определяем по коду И температуре"""
    is_snow = code in SNOW_CODES and temp <= 4
    is_rain = code in RAIN_CODES
    is_storm = code in STORM_CODES
    is_fog = code in (1030, 1135, 1147)

    if lang == "ru":
        if is_storm:
            return "⛈ <i>Гроза! Лучше остаться дома — безопасность прежде всего.</i>"
        elif is_snow:
            return "❄️ <i>Снег за окном — укутайся потеплее, и пусть этот день будет уютным!</i>"
        elif is_rain:
            return "🌧 <i>Дождливый день — идеально для чашки чая, любимой книги или сериала дома.</i>"
        elif is_fog:
            return "🌫 <i>Туман на улице — будь осторожен на дороге и не торопись.</i>"
        elif temp >= 30:
            return "🥵 <i>Жара! Пей больше воды, носи лёгкую одежду и береги себя.</i>"
        elif temp >= 20:
            return "☀️ <i>Отличный день для прогулки или пикника — солнце и тепло зовут на улицу!</i>"
        elif temp >= 10:
            return "🌤 <i>Приятная погода — свежий воздух. Идеально для активного дня!</i>"
        elif temp >= 0:
            return "🧣 <i>Прохладно — одевайся потеплее и наслаждайся осенним/весенним днём!</i>"
        else:
            return "🥶 <i>Очень холодно! Одевайся по-зимнему и не забудь перчатки.</i>"
    else:
        if is_storm:
            return "⛈ <i>Thunderstorm! Better stay home — safety first.</i>"
        elif is_snow:
            return "❄️ <i>Snow outside — wrap up warm and make it a cozy day!</i>"
        elif is_rain:
            return "🌧 <i>Rainy day — perfect for a cup of tea, a good book or binge-watching at home.</i>"
        elif is_fog:
            return "🌫 <i>Foggy outside — be careful on the road and take it slow.</i>"
        elif temp >= 30:
            return "🥵 <i>Heat wave! Drink plenty of water, wear light clothes and stay safe.</i>"
        elif temp >= 20:
            return "☀️ <i>Perfect day for a walk or picnic — sunshine and warmth await!</i>"
        elif temp >= 10:
            return "🌤 <i>Pleasant weather — fresh air. Great for an active day!</i>"
        elif temp >= 0:
            return "🧣 <i>Cool outside — dress warmly and enjoy the day!</i>"
        else:
            return "🥶 <i>Freezing cold! Dress in winter gear and don't forget gloves.</i>"

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

# Коды для фильтрации placeholder-ссылок (не показываем если не заменены)
def _is_real_url(url: str) -> bool:
    return url.startswith("http")

def affiliate_block(condition_code: int, lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """Возвращает текст + кнопки партнёрок по контексту погоды"""
    sep = "\n━━━━━━━━━━━━━━━━"
    builder = InlineKeyboardBuilder()
    count = 0

    SNOW_CODES = {1066, 1114, 1117, 1210, 1213, 1216, 1219, 1222, 1225, 1255, 1258,
                  1069, 1072, 1168, 1171, 1198, 1201, 1204, 1207, 1249, 1252}
    RAIN_CODES = {1063, 1150, 1153, 1180, 1183, 1186, 1189, 1192, 1195, 1240, 1243,
                  1246, 1087, 1273, 1276, 1279, 1282}

    if condition_code in RAIN_CODES:
        # 🌧 Дождь → такси, доставка, зонты, билеты (раз дома сидишь — помечтай о поездке)
        text = sep + ("\n🚖 <b>Дождливый день — самое время остаться дома или уехать в тепло:</b>"
                      if lang == "ru" else
                      "\n🚖 <b>Rainy day — stay home or escape somewhere warm:</b>")
        for key in ["bolt", "inDrive", "wolt", "glovo", "umbrella", "tickets"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
        builder.adjust(2)

    elif condition_code in SNOW_CODES:
        # ❄️ Снег → такси, тёплая одежда
        text = sep + ("\n🧥 <b>Холодно и снежно — одевайся теплее:</b>"
                      if lang == "ru" else
                      "\n🧥 <b>Cold and snowy — dress warm:</b>")
        for key in ["bolt", "inDrive", "warm", "clothes"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
        builder.adjust(2)

    elif condition_code == 1000:
        # ☀️ Солнце → одежда, еда, билеты (хорошая погода — время путешествовать)
        text = sep + ("\n🌞 <b>Солнечный день — идеальное время для активности или поездки:</b>"
                      if lang == "ru" else
                      "\n🌞 <b>Sunny day — perfect for going out or planning a trip:</b>")
        for key in ["clothes", "glovo", "tickets", "hotels"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
        builder.adjust(2)

    elif condition_code in (1003, 1006, 1009):
        # ⛅ Облачно → нейтральный блок
        text = sep + ("\n🌥 <b>Обычный день — планируй с умом:</b>"
                      if lang == "ru" else
                      "\n🌥 <b>Cloudy day — plan ahead:</b>")
        for key in ["clothes", "tickets", "hotels"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
        builder.adjust(2)

    else:
        text = sep + ("\n✈️ <b>Погода и путешествия:</b>"
                      if lang == "ru" else
                      "\n✈️ <b>Weather & travel:</b>")
        for key in ["tickets", "hotels", "clothes"]:
            if _is_real_url(AFFILIATE[key]["url"]):
                builder.button(text=AFFILIATE[key][lang], url=AFFILIATE[key]["url"])
                count += 1
        builder.adjust(2)

    # 🎁 Бонус дня — показываем всегда, последней кнопкой
    BONUS_URL = "https://omg10.com/4/11107148"
    bonus_text = "🎁 Бонус дня" if lang == "ru" else "🎁 Bonus of the day"
    builder.button(text=bonus_text, url=BONUS_URL)
    builder.adjust(2)

    kb = builder.as_markup()
    return text if count > 0 else "", kb

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
    url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru&aqi=yes"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data if "location" in data else None
        except Exception as e:
            logging.error(f"Weather fetch error for {city}: {e}")
            return None

async def search_city(query: str):
    """Поиск города через WeatherAPI search endpoint — поддерживает кириллицу"""
    url = f"https://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={query}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    return results[0]["name"] if results else None
        except Exception:
            return None
    return None

# ── FORECAST FORMATTERS ───────────────────────────────────────────────────────
def format_day_forecast(data: dict, lang: str) -> str:
    c = data["current"]
    loc = data["location"]
    icon = weather_icon(c["condition"]["code"])
    temp = round(c["temp_c"])
    feels = round(c["feelslike_c"])
    desc = c["condition"]["text"]
    humidity = c["humidity"]
    wind = round(c["wind_kph"])
    wind_dir = c.get("wind_dir", "")
    visibility = c.get("vis_km", "—")
    pressure = round(c.get("pressure_mb", 0))
    uv = c.get("uv", "—")
    air_quality = c.get("air_quality", {})
    aqi = round(air_quality.get("us-epa-index", 0)) if air_quality else "—"
    today = data["forecast"]["forecastday"][0]["day"]
    t_max = round(today["maxtemp_c"])
    t_min = round(today["mintemp_c"])
    rain_chance = today.get("daily_chance_of_rain", 0)
    city_name = loc["name"]
    country = loc["country"]
    mood = get_mood(c["condition"]["code"], temp, lang)

    # УФ уровень
    def uv_label(val, lang):
        try:
            v = float(val)
        except:
            return str(val)
        if lang == "ru":
            if v <= 2: return f"{val} (Низкий)"
            elif v <= 5: return f"{val} (Умеренный)"
            elif v <= 7: return f"{val} (Высокий)"
            else: return f"{val} (Очень высокий)"
        else:
            if v <= 2: return f"{val} (Low)"
            elif v <= 5: return f"{val} (Moderate)"
            elif v <= 7: return f"{val} (High)"
            else: return f"{val} (Very High)"

    if lang == "ru":
        return (
            f"{icon} <b>Погода — {city_name}, {country}</b>\n"
            f"📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n"
            f"{mood}\n\n"
            f"🌡 <b>Сейчас:</b> {temp}°C (ощущается {feels}°C)\n"
            f"📊 <b>День/Ночь:</b> {t_max}°C / {t_min}°C\n"
            f"🌥 <b>Состояние:</b> {desc}\n"
            f"💧 <b>Влажность:</b> {humidity}%\n"
            f"💨 <b>Ветер:</b> {wind} км/ч {wind_dir}\n"
            f"🌂 <b>Вероятность дождя:</b> {rain_chance}%\n"
            f"👁 <b>Видимость:</b> {visibility} км\n"
            f"🔵 <b>Давление:</b> {round(pressure * 0.750062)} мм рт.ст.\n"
            f"🌞 <b>УФ-индекс:</b> {uv_label(uv, 'ru')}\n\n"
            f"💬 <i>{get_quote(c['condition']['code'], 'ru')}</i>"
        )
    else:
        return (
            f"{icon} <b>Weather — {city_name}, {country}</b>\n"
            f"📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n"
            f"{mood}\n\n"
            f"🌡 <b>Now:</b> {temp}°C (feels like {feels}°C)\n"
            f"📊 <b>Day/Night:</b> {t_max}°C / {t_min}°C\n"
            f"🌥 <b>Condition:</b> {desc}\n"
            f"💧 <b>Humidity:</b> {humidity}%\n"
            f"💨 <b>Wind:</b> {wind} km/h {wind_dir}\n"
            f"🌂 <b>Rain chance:</b> {rain_chance}%\n"
            f"👁 <b>Visibility:</b> {visibility} km\n"
            f"🔵 <b>Pressure:</b> {pressure} hPa\n"
            f"🌞 <b>UV index:</b> {uv_label(uv, 'en')}\n\n"
            f"💬 <i>{get_quote(c['condition']['code'], 'en')}</i>"
        )

def format_week_forecast(data: dict, lang: str) -> str:
    loc = data["location"]
    city_name = loc["name"]
    country = loc["country"]
    days = data["forecast"]["forecastday"]
    header = (
        f"📆 <b>{'Прогноз на неделю' if lang == 'ru' else 'Weekly forecast'}"
        f" — {city_name}, {country}</b>\n\n"
    )
    lines = [header]
    for d in days:
        date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m")
        icon = weather_icon(d["day"]["condition"]["code"])
        t_max = round(d["day"]["maxtemp_c"])
        t_min = round(d["day"]["mintemp_c"])
        desc = d["day"]["condition"]["text"]
        rain = d["day"].get("daily_chance_of_rain", 0)
        lines.append(f"{icon} <b>{date_str}</b>: {t_max}°/{t_min}° — {desc} 🌂{rain}%")
    return "\n".join(lines)

def format_month_forecast(data: dict, lang: str) -> str:
    loc = data["location"]
    city_name = loc["name"]
    country = loc["country"]
    days = data["forecast"]["forecastday"]
    note = ("⚠️ <i>Прогноз на месяц приблизительный — используй как ориентир</i>\n\n"
            if lang == "ru" else
            "⚠️ <i>Monthly forecast is approximate — use as guidance</i>\n\n")
    header = (
        f"🗓 <b>{'Прогноз на месяц' if lang == 'ru' else 'Monthly forecast'}"
        f" — {city_name}, {country}</b>\n{note}"
    )
    lines = [header]
    for d in days:
        date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%d.%m")
        icon = weather_icon(d["day"]["condition"]["code"])
        t_max = round(d["day"]["maxtemp_c"])
        t_min = round(d["day"]["mintemp_c"])
        lines.append(f"{icon} <b>{date_str}</b>: {t_max}°/{t_min}°")
    return "\n".join(lines)

async def build_forecast_message(city: str, fmt: str, lang: str):
    """Возвращает (text, keyboard) или (None, None)"""
    days = 14 if fmt == "month" else 7
    data = await fetch_weather(city, days)
    if not data:
        return None, None
    condition_code = data["current"]["condition"]["code"]
    if fmt == "day":
        text = format_day_forecast(data, lang)
    elif fmt == "week":
        text = format_week_forecast(data, lang)
    elif fmt == "month":
        text = format_month_forecast(data, lang)
    else:
        text = format_day_forecast(data, lang) + "\n\n" + format_week_forecast(data, lang)

    aff_text, aff_kb = affiliate_block(condition_code, lang)
    text += aff_text
    return text, aff_kb

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def start_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 " + ("Указать город" if lang == "ru" else "Set city"), callback_data="set_city")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский", callback_data="toggle_lang")
    builder.button(text="☀️ " + ("Прогноз сейчас" if lang == "ru" else "Weather now"), callback_data="weather_now")
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

def settings_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏙 " + ("Изменить город" if lang == "ru" else "Change city"),  callback_data="set_city")
    builder.button(text="📋 " + ("Формат" if lang == "ru" else "Format"),               callback_data="choose_format")
    builder.button(text="🌍 English" if lang == "ru" else "🇷🇺 Русский",               callback_data="toggle_lang")
    builder.adjust(2)
    return builder.as_markup()

def subscribe_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ " + ("Да, присылай!" if lang == "ru" else "Yes, subscribe!"), callback_data="subscribe_yes")
    builder.button(text="❌ " + ("Нет, спасибо" if lang == "ru" else "No, thanks"),       callback_data="subscribe_no")
    builder.adjust(2)
    return builder.as_markup()

# ── TRANSLATIONS ─────────────────────────────────────────────────────────────
T = {
    "welcome": {
        "ru": (
            "👋 Привет! Я <b>PogodaMood</b> — твой личный синоптик с характером 🌤\n\n"
            "Каждое утро буду присылать не просто цифры, а <b>настроение дня</b> — "
            "чтобы ты знал, как одеться и чем заняться.\n\n"
            "👇 Начни с выбора города:"
        ),
        "en": (
            "👋 Hello! I'm <b>PogodaMood</b> — your personal weather assistant with personality 🌤\n\n"
            "Every morning I'll send not just numbers, but a <b>mood of the day</b> — "
            "so you know what to wear and what to do.\n\n"
            "👇 Start by setting your city:"
        ),
    },
    "ask_city": {
        "ru": (
            "🏙 <b>Напиши название города</b>\n\n"
            "Можно на русском или английском:\n"
            "• <code>Москва</code> или <code>Moscow</code>\n"
            "• <code>Кишинёв</code> или <code>Chisinau</code>\n"
            "• <code>Осло</code> или <code>Oslo</code>"
        ),
        "en": (
            "🏙 <b>Enter your city name</b>\n\n"
            "Works in English or Russian:\n"
            "• <code>London</code>\n"
            "• <code>New York</code>\n"
            "• <code>Oslo</code>"
        ),
    },
    "city_saved": {
        "ru": "✅ Город <b>{city}</b> сохранён!\n\n📋 Теперь выбери формат рассылки 👇",
        "en": "✅ City <b>{city}</b> saved!\n\n📋 Now choose your forecast format 👇",
    },
    "no_city": {
        "ru": "⚠️ Сначала укажи свой город — нажми /city",
        "en": "⚠️ Please set your city first — tap /city",
    },
    "format_saved": {
        "ru": (
            "🎉 Всё готово! Буду присылать прогноз каждое утро в <b>7:00</b> 🌅\n\n"
            "<b>Команды:</b>\n"
            "/weather — прогноз прямо сейчас\n"
            "/settings — настройки\n"
            "/help — помощь"
        ),
        "en": (
            "🎉 All set! I'll send your forecast every morning at <b>7:00</b> 🌅\n\n"
            "<b>Commands:</b>\n"
            "/weather — weather right now\n"
            "/settings — settings\n"
            "/help — help"
        ),
    },
    "help": {
        "ru": (
            "ℹ️ <b>PogodaMood — помощь</b>\n\n"
            "🌤 Я присылаю прогноз погоды с <b>настроением дня</b> каждое утро в 7:00.\n\n"
            "<b>Команды:</b>\n"
            "/start — главное меню\n"
            "/city — изменить город\n"
            "/weather — прогноз прямо сейчас\n"
            "/settings — язык, город, формат\n"
            "/help — эта справка\n\n"
            "🌍 <b>Поддерживаю города всего мира</b>\n"
            "Можно вводить на русском и английском языке."
        ),
        "en": (
            "ℹ️ <b>PogodaMood — help</b>\n\n"
            "🌤 I send weather forecasts with a <b>mood of the day</b> every morning at 7:00.\n\n"
            "<b>Commands:</b>\n"
            "/start — main menu\n"
            "/city — change city\n"
            "/weather — weather right now\n"
            "/settings — language, city, format\n"
            "/help — this help\n\n"
            "🌍 <b>Supports cities worldwide</b>\n"
            "You can type in English or Russian."
        ),
    },
}

# ── FSM ───────────────────────────────────────────────────────────────────────
class CityForm(StatesGroup):
    waiting_city = State()

# ── BOT ───────────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# ── HANDLERS ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    if not user:
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
    city = user["city"] if user and user.get("city") else ("не указан" if lang == "ru" else "not set")
    fmt_labels = {
        "day":   "📅 " + ("Сегодня" if lang == "ru" else "Today"),
        "week":  "📆 " + ("Неделя" if lang == "ru" else "Week"),
        "month": "🗓 " + ("Месяц" if lang == "ru" else "Month"),
        "all":   "🌟 " + ("Всё сразу" if lang == "ru" else "All"),
    }
    fmt = fmt_labels.get(user["format"] if user else "day", "—")
    text = (
        f"⚙️ <b>{'Настройки' if lang == 'ru' else 'Settings'}</b>\n\n"
        f"🏙 {'Город' if lang == 'ru' else 'City'}: <b>{city}</b>\n"
        f"📋 {'Формат' if lang == 'ru' else 'Format'}: <b>{fmt}</b>\n"
        f"🌐 {'Язык' if lang == 'ru' else 'Language'}: <b>{'Русский 🇷🇺' if lang == 'ru' else 'English 🌍'}</b>"
    )
    await msg.answer(text, reply_markup=settings_kb(lang))

@dp.message(Command("weather"))
async def cmd_weather(msg: Message):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    if not user or not user.get("city"):
        await msg.answer(T["no_city"][lang])
        return
    wait_msg = await msg.answer("⏳ " + ("Загружаю прогноз..." if lang == "ru" else "Loading forecast..."))
    text, kb = await build_forecast_message(user["city"], user.get("format", "day"), lang)
    await wait_msg.delete()
    if text:
        await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        err = ("😔 Ой, не могу получить прогноз прямо сейчас.\nПопробуй чуть позже — я уже разбираюсь в чём дело!" 
               if lang == "ru" else 
               "😔 Oops, I can't get the forecast right now.\nTry again in a moment!")
        await msg.answer(err)

@dp.message(CityForm.waiting_city)
async def process_city(msg: Message, state: FSMContext):
    user = await get_user(msg.from_user.id)
    lang = user["lang"] if user else "ru"
    city_input = msg.text.strip()

    wait_msg = await msg.answer("🔍 " + ("Ищу город..." if lang == "ru" else "Searching city..."))

    # Прямой запрос
    data = await fetch_weather(city_input, 1)

    # Если не нашло — пробуем через search endpoint (поддержка кириллицы)
    if not data:
        found_name = await search_city(city_input)
        if found_name:
            data = await fetch_weather(found_name, 1)

    await wait_msg.delete()

    if not data:
        if lang == "ru":
            err = (
                "🤔 Ой, кажется, этот город спрятался от меня!\n\n"
                "Проверь, пожалуйста, правильность написания и попробуй ещё раз.\n\n"
                "Примеры:\n"
                "• <code>Oslo</code> вместо Осло\n"
                "• <code>Paris</code> вместо Париж\n"
                "• <code>New York</code> вместо Нью-Йорк"
            )
        else:
            err = (
                "🤔 Hmm, I couldn't find that city!\n\n"
                "Please check the spelling and try again.\n\n"
                "Examples:\n"
                "• <code>Oslo</code>\n"
                "• <code>Paris</code>\n"
                "• <code>New York</code>"
            )
        await msg.answer(err)
        return

    city_name = data["location"]["name"]
    country = data["location"]["country"]
    await save_user(msg.from_user.id, city=city_name)
    await state.clear()

    confirmed = T["city_saved"][lang].format(city=f"{city_name}, {country}")
    await msg.answer(confirmed, reply_markup=format_kb(lang))

# ── CALLBACKS ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "set_city")
async def cb_set_city(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await state.set_state(CityForm.waiting_city)
    await call.message.answer(T["ask_city"][lang])
    await call.answer()

@dp.callback_query(F.data == "weather_now")
async def cb_weather_now(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    if not user or not user.get("city"):
        await call.message.answer(T["no_city"][lang])
        await call.answer()
        return
    wait_msg = await call.message.answer("⏳ " + ("Загружаю..." if lang == "ru" else "Loading..."))
    text, kb = await build_forecast_message(user["city"], user.get("format", "day"), lang)
    await wait_msg.delete()
    if text:
        await call.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await call.answer()

@dp.callback_query(F.data == "choose_format")
async def cb_choose_format(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    txt = "📋 <b>" + ("Выбери формат прогноза:" if lang == "ru" else "Choose forecast format:") + "</b>"
    await call.message.answer(txt, reply_markup=format_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "toggle_lang")
async def cb_toggle_lang(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    new_lang = "en" if (user and user.get("lang") == "ru") else "ru"
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
    # Предложить подписку
    sub_text = ("🔔 <b>Хочешь получать прогноз автоматически каждое утро в 7:00?</b>"
                if lang == "ru" else
                "🔔 <b>Want to receive the forecast automatically every morning at 7:00?</b>")
    await call.message.answer(sub_text, reply_markup=subscribe_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "subscribe_yes")
async def cb_subscribe_yes(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(call.from_user.id, active=1)
    txt = ("✅ Отлично! Буду будить тебя прогнозом каждое утро в 7:00 🌅\n\nДо завтра!"
           if lang == "ru" else
           "✅ Great! I'll wake you up with a forecast every morning at 7:00 🌅\n\nSee you tomorrow!")
    await call.message.answer(txt)
    await call.answer()

@dp.callback_query(F.data == "subscribe_no")
async def cb_subscribe_no(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    lang = user["lang"] if user else "ru"
    await save_user(call.from_user.id, active=0)
    txt = ("Окей, не буду беспокоить 🙂\nЕсли передумаешь — просто напиши /start"
           if lang == "ru" else
           "Okay, I won't bother you 🙂\nIf you change your mind — just type /start")
    await call.message.answer(txt)
    await call.answer()

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
async def send_morning_forecasts():
    users = await get_all_active_users()
    for user_id, city, lang, fmt in users:
        try:
            text, kb = await build_forecast_message(city, fmt, lang)
            if text:
                prefix = "🌅 <b>Доброе утро! Вот твоё настроение дня:</b>\n\n" if lang == "ru" else "🌅 <b>Good morning! Here's your mood of the day:</b>\n\n"
                await bot.send_message(user_id, prefix + text, reply_markup=kb, disable_web_page_preview=True)
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
