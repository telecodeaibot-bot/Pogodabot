import asyncio, logging, aiohttp, aiosqlite, os, random
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                            ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
WEATHER_API_KEY  = os.getenv("WEATHER_API_KEY", "")
DB_PATH          = "pogoda.db"
ADMIN_ID         = int(os.getenv("ADMIN_ID", "7262437300"))
TZ               = pytz.timezone("Europe/Chisinau")

def now_local():
    return datetime.now(TZ)

# ── AFFILIATE ─────────────────────────────────────────────────────────────────
AFF = {
    "bolt":     {"ru": "🚗 Такси Bolt",           "en": "🚗 Bolt taxi",          "url": "BOLT_URL"},
    "inDrive":  {"ru": "🚕 inDrive",               "en": "🚕 inDrive",            "url": "INDRIVE_URL"},
    "wolt":     {"ru": "🍔 Доставка Wolt",         "en": "🍔 Wolt delivery",      "url": "WOLT_URL"},
    "glovo":    {"ru": "🛵 Glovo",                 "en": "🛵 Glovo",              "url": "GLOVO_URL"},
    "Kino":    {"ru": "🛵 KINO",                 "en": "🛵 KINO",              "url": "https://fas.st/1fOaV?erid=MvGzQC98w3Z1gMq1pRupbPDh"},
    "Kaspersky":  {"ru": "👗 Antivirus Kaspersky",                "en": "👗 Kaspersky",            "url": "https://fas.st/JTUcVI?erid=5jtCeReLm1S3Xx3LfA8QF84"},
    "Umbrella": {"ru": "☂️ Зонт (Alibaba)",        "en": "☂️ Umbrella (Alibaba)", "url": "https://rzekl.com/g/pm1aev55cl3fe1015811219aa26f6f/?ulp=https%3A%2F%2Fwww.alibaba.com%2Fproduct-detail%2FCustom-Wind-Resistant-Hands-Free-Inverse_1600478167223.html"},
    "Aviasales":  {"ru": "✈️ Авиабилеты",            "en": "✈️ Flights",            "url": "https://tp.media/r?marker=736538&trs=536752&p=4114&u=https%3A%2F%2Faviasales.ru&campaign_id=100"},
    "BotHub":   {"ru": "🤖 AI-ассистент BotHub",   "en": "🤖 AI Assistant BotHub","url": "https://bothub.chat/?invitedBy=zGQwEkF5uAu-92IxmDmZH"},
    "OnlineMoney":    {"ru": "OnlineMoney",    "en": "OnlineMoney","url": "https://omg10.com/4/11107148"},
    "Букоед книги":    {"ru": "Букоед",    "en": "Bukoed","url": "https://heqgr.com/g/531a4560a63fe101581127ad1bb5fb/?erid=5jtCeReLm1S3Xx3LfAELCUa&ulp=https%3A%2F%2Fwww.bookvoed.ru%2F"},
}

def real(url): return url.startswith("http")

# ── WEATHER CODES ─────────────────────────────────────────────────────────────
RAIN_C  = {1063,1150,1153,1180,1183,1186,1189,1192,1195,1240,1243,1246,1087,1273,1276,1279,1282}
SNOW_C  = {1066,1114,1117,1210,1213,1216,1219,1222,1225,1255,1258,1069,1072,1168,1171,1198,1201,1204,1207,1249,1252}
STORM_C = {1087,1273,1276,1279,1282}
HSNOW_C = {1117,1225,1258}

def wicon(code):
    if code==1000: return "☀️"
    if code in(1003,1006): return "⛅"
    if code==1009: return "☁️"
    if code in(1030,1135,1147): return "🌫"
    if code in RAIN_C: return "🌧"
    if code in SNOW_C: return "❄️"
    if code in STORM_C: return "⛈"
    return "🌤"

# ── REPLY KEYBOARD ────────────────────────────────────────────────────────────
def main_kb(lang: str) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    if lang == "ru":
        b.button(text="🌤 Погода сейчас")
        b.button(text="⏰ Время прогноза")
        b.button(text="⚙️ Настройки")
        b.button(text="🎲 Активность дня")
        b.button(text="💬 Помощь")
    else:
        b.button(text="🌤 Weather now")
        b.button(text="⏰ Forecast time")
        b.button(text="⚙️ Settings")
        b.button(text="🎲 Activity of the day")
        b.button(text="💬 Help")
    b.adjust(2, 2, 1)
    return b.as_markup(resize_keyboard=True)

def time_inline_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for h in [6,7,8,9,10,11,12,14,16,18,20,22]:
        b.button(text=f"🕐 {h:02d}:00", callback_data=f"time_{h}")
    off = "🔕 Выключить" if lang=="ru" else "🔕 Turn off"
    b.button(text=off, callback_data="time_off")
    b.adjust(4, 4, 4, 1)
    return b.as_markup()

def format_inline_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 "+("Сегодня" if lang=="ru" else "Today"),   callback_data="fmt_day")
    b.button(text="📆 "+("Неделя"  if lang=="ru" else "Week"),    callback_data="fmt_week")
    b.button(text="🗓 "+("Месяц"   if lang=="ru" else "Month"),   callback_data="fmt_month")
    b.button(text="🌟 "+("Всё"     if lang=="ru" else "All"),     callback_data="fmt_all")
    b.adjust(2)
    return b.as_markup()

def settings_inline_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🏙 "+("Город"   if lang=="ru" else "City"),    callback_data="set_city")
    b.button(text="📋 "+("Формат"  if lang=="ru" else "Format"),  callback_data="choose_format")
    b.button(text="🌍 English" if lang=="ru" else "🇷🇺 Русский",  callback_data="toggle_lang")
    b.adjust(2, 1)
    return b.as_markup()

# ── RANDOM ACTIVITY ───────────────────────────────────────────────────────────
ACTIVITIES = {
    "ru": [
        "🎬 Посмотри фильм который давно откладывал — сегодня отличный день!",
        "📚 Прочитай хотя бы 10 страниц книги — маленький шаг, большой прогресс.",
        "🚶 Прогуляйся в парке хотя бы 20 минут — тело скажет спасибо.",
        "☕ Зайди в новое кафе и попробуй что-то необычное.",
        "📞 Позвони кому-то кому давно не звонил — это всегда приятно.",
        "🎵 Послушай новый альбом или плейлист который давно хотел.",
        "🍳 Приготовь блюдо которое раньше не пробовал готовить.",
        "✍️ Запиши 3 вещи за которые благодарен сегодня.",
        "🌿 Полей растения или купи один новый цветок домой.",
        "🎨 Порисуй, даже если не умеешь — это расслабляет!",
        "🏋️ Сделай 10 минут зарядки — лучше мало, чем ничего.",
        "🛍 Сделай себе маленький подарок — ты это заслуживаешь!",
        "🧹 Разбери один ящик или полку — сразу станет легче.",
        "🌅 Встреть закат сегодня — просто выгляни в окно в нужный момент.",
        "🎲 Сыграй в настольную игру с близкими или друзьями.",
    ],
    "en": [
        "🎬 Watch a movie you've been putting off — today's a great day!",
        "📚 Read at least 10 pages of a book — small step, big progress.",
        "🚶 Take a 20-minute walk in the park — your body will thank you.",
        "☕ Try a new café and order something unusual.",
        "📞 Call someone you haven't spoken to in a while — it's always nice.",
        "🎵 Listen to a new album or playlist you've been meaning to try.",
        "🍳 Cook a dish you've never made before.",
        "✍️ Write down 3 things you're grateful for today.",
        "🌿 Water your plants or buy a new flower for your home.",
        "🎨 Draw something — even if you can't draw, it's relaxing!",
        "🏋️ Do 10 minutes of exercise — a little beats nothing.",
        "🛍 Treat yourself to something small — you deserve it!",
        "🧹 Sort through one drawer or shelf — you'll feel lighter.",
        "🌅 Watch the sunset today — just look out the window at the right moment.",
        "🎲 Play a board game with family or friends.",
    ]
}

# ── QUOTES ────────────────────────────────────────────────────────────────────
QUOTES = {
    "sun":   [
        {"ru":"☀️ «Каждое утро — это шанс начать заново.»","en":"☀️ 'Every morning is a chance to begin again.'"},
        {"ru":"🔥 «Единственный способ делать великое дело — любить то что делаешь.» — Стив Джобс","en":"🔥 'The only way to do great work is to love what you do.' — Steve Jobs"},
        {"ru":"🚀 «Мечты не работают если не работаешь ты.» — Джон Максвелл","en":"🚀 'Dreams don't work unless you do.' — John C. Maxwell"},
        {"ru":"💪 «Успех — сумма небольших усилий повторяемых день за днём.» — Роберт Коллиер","en":"💪 'Success is the sum of small efforts repeated day in and day out.' — R. Collier"},
    ],
    "rain":  [
        {"ru":"🌈 «Жизнь не в том чтобы ждать пока пройдёт буря а в том чтобы танцевать под дождём.»","en":"🌈 'Life isn't about waiting for the storm to pass — it's about dancing in the rain.'"},
        {"ru":"☕ «Дождливый день — лучший повод для книги и горячего чая.»","en":"☕ 'A rainy day is a perfect excuse for a good book and hot tea.'"},
        {"ru":"💧 «Дождь смывает всё лишнее и оставляет только главное.»","en":"💧 'Rain washes away everything unnecessary, leaving only what matters.'"},
    ],
    "snow":  [
        {"ru":"❄️ «Самые тёплые воспоминания рождаются в самые холодные дни.»","en":"❄️ 'The warmest memories are born on the coldest days.'"},
        {"ru":"🧣 «Холод снаружи — тепло внутри. Всё в твоих руках.»","en":"🧣 'Cold outside, warmth within. It's all in your hands.'"},
    ],
    "any":   [
        {"ru":"🎯 «Цель без плана — просто мечта.» — Антуан де Сент-Экзюпери","en":"🎯 'A goal without a plan is just a wish.' — Antoine de Saint-Exupery"},
        {"ru":"❤️ «Будь собой — все остальные роли уже заняты.» — Оскар Уайльд","en":"❤️ 'Be yourself — everyone else is already taken.' — Oscar Wilde"},
        {"ru":"🌍 «Путешествие в тысячу миль начинается с одного шага.» — Лао-цзы","en":"🌍 'A journey of a thousand miles begins with a single step.' — Lao Tzu"},
        {"ru":"🏆 «Победитель — это мечтатель который не сдался.» — Нельсон Мандела","en":"🏆 'A winner is a dreamer who never gives up.' — Nelson Mandela"},
        {"ru":"🎨 «Творчество — это интеллект который развлекается.» — Альберт Эйнштейн","en":"🎨 'Creativity is intelligence having fun.' — Albert Einstein"},
    ]
}

def get_quote(code, lang):
    if code in RAIN_C: pool = QUOTES["rain"] + QUOTES["any"]
    elif code in SNOW_C: pool = QUOTES["snow"] + QUOTES["any"]
    elif code == 1000: pool = QUOTES["sun"] + QUOTES["any"]
    else: pool = QUOTES["any"]
    return random.choice(pool)[lang]

# ── WARDROBE ──────────────────────────────────────────────────────────────────
def get_wardrobe(temp, code, lang):
    rain = code in RAIN_C
    ru = lang == "ru"
    umbrella = (" + зонт ☂️" if ru else " + umbrella ☂️") if rain else ""
    if temp < -10:
        return ("🧥 <b>Гардероб:</b> Пуховик, термобельё, шапка, перчатки" if ru
                else "🧥 <b>Wardrobe:</b> Down coat, thermals, hat, gloves")
    elif temp < 0:
        return ("🧣 <b>Гардероб:</b> Зимнее пальто, шарф, шапка, перчатки" if ru
                else "🧣 <b>Wardrobe:</b> Winter coat, scarf, hat, gloves")
    elif temp < 5:
        return f"🧤 <b>{'Гардероб' if ru else 'Wardrobe'}:</b> {'Тёплая куртка, свитер, шарф' if ru else 'Warm jacket, sweater, scarf'}{umbrella}"
    elif temp < 10:
        return f"🧥 <b>{'Гардероб' if ru else 'Wardrobe'}:</b> {'Куртка или пальто' if ru else 'Jacket or coat'}{umbrella}"
    elif temp < 15:
        return f"👔 <b>{'Гардероб' if ru else 'Wardrobe'}:</b> {'Лёгкая куртка или толстовка' if ru else 'Light jacket or hoodie'}{umbrella}"
    elif temp < 20:
        return f"👗 <b>{'Гардероб' if ru else 'Wardrobe'}:</b> {'Кофта или лёгкий джемпер' if ru else 'Sweater or light top'}{umbrella}"
    elif temp < 28:
        return f"👕 <b>{'Гардероб' if ru else 'Wardrobe'}:</b> {'Футболка, лёгкие брюки' if ru else 'T-shirt, light pants'}{umbrella}"
    else:
        return ("🩴 <b>Гардероб:</b> Лёгкая одежда, солнечные очки 😎, головной убор" if ru
                else "🩴 <b>Wardrobe:</b> Light clothes, sunglasses 😎, hat")

# ── ECO TIP ───────────────────────────────────────────────────────────────────
def get_eco(code, temp, lang):
    ru = lang == "ru"
    if code == 1000 and temp >= 15:
        return ("🌱 <i>Эко: Сегодня отлично пройтись пешком вместо авто — поможешь природе!</i>" if ru
                else "🌱 <i>Eco: Great day to walk instead of drive — help the planet!</i>")
    elif code in RAIN_C:
        return ("🌱 <i>Эко: Собери дождевую воду для полива растений.</i>" if ru
                else "🌱 <i>Eco: Collect rainwater for your plants!</i>")
    elif temp >= 28:
        return ("🌱 <i>Эко: Используй вентилятор вместо кондиционера — экономит 70% энергии.</i>" if ru
                else "🌱 <i>Eco: Use a fan instead of AC — saves 70% energy.</i>")
    elif temp < 0:
        return ("🌱 <i>Эко: Убавь отопление на 1-2 градуса — незаметно тебе, ощутимо для планеты.</i>" if ru
                else "🌱 <i>Eco: Lower heating by 1-2 degrees — small change, big impact.</i>")
    else:
        return ("🌱 <i>Эко: Возьми многоразовую сумку вместо пластикового пакета.</i>" if ru
                else "🌱 <i>Eco: Use a reusable bag instead of plastic today.</i>")

# ── SOS ───────────────────────────────────────────────────────────────────────
def get_sos(code, temp, lang):
    ru = lang == "ru"
    if code in STORM_C:
        tips = ("⛈ <b>Советы при грозе:</b>\n⚡ Не стой под деревьями и у окон\n🚗 Не паркуй авто под деревьями\n🏠 Оставайся дома если возможно\n📱 Зарядите телефон заранее"
                if ru else
                "⛈ <b>Storm safety tips:</b>\n⚡ Stay away from trees and windows\n🚗 Don't park under trees\n🏠 Stay home if possible\n📱 Charge your phone now")
        return True, tips, ("🆘 Советы при грозе" if ru else "🆘 Storm tips")
    elif temp >= 35:
        tips = ("🥵 <b>Советы при жаре:</b>\n💧 Пей 2-3 литра воды в день\n🕶 Носи головной убор и очки\n🏠 Избегай улицы с 12 до 16\n❄️ Охлаждай запястья холодной водой"
                if ru else
                "🥵 <b>Heat safety tips:</b>\n💧 Drink 2-3 liters of water daily\n🕶 Wear a hat and sunglasses\n🏠 Avoid going out 12:00–16:00\n❄️ Cool your wrists with cold water")
        return True, tips, ("🆘 Советы при жаре" if ru else "🆘 Heat tips")
    elif code in HSNOW_C or temp < -20:
        tips = ("❄️ <b>Советы при сильном морозе:</b>\n🚗 Проверь аккумулятор и антифриз\n🧣 Закрой нос и рот шарфом\n⚠️ Осторожно на скользком тротуаре\n☕ Тёплые напитки каждые 1-2 часа"
                if ru else
                "❄️ <b>Frost safety tips:</b>\n🚗 Check battery and antifreeze\n🧣 Cover nose and mouth with scarf\n⚠️ Watch out for icy sidewalks\n☕ Drink warm drinks every 1-2 hours")
        return True, tips, ("🆘 Советы при морозе" if ru else "🆘 Frost tips")
    return False, "", ""

# ── DATABASE ──────────────────────────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                city TEXT, lang TEXT DEFAULT 'ru',
                forecast_format TEXT DEFAULT 'day',
                active INTEGER DEFAULT 1,
                notify_hour INTEGER DEFAULT 7,
                joined_at TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now'))
            )
        """)
        for col in ["notify_hour INTEGER DEFAULT 7",
                    "joined_at TEXT DEFAULT (datetime('now'))",
                    "last_active TEXT DEFAULT (datetime('now'))"]:
            try: await db.execute(f"ALTER TABLE users ADD COLUMN {col}")
            except: pass
        await db.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (uid,)) as c:
            row = await c.fetchone()
            if row:
                return {"user_id":row[0],"city":row[1],"lang":row[2],
                        "format":row[3],"active":row[4],"notify_hour":row[5]}
    return None

async def save_user(uid, **kw):
    async with aiosqlite.connect(DB_PATH) as db:
        ex = await get_user(uid)
        kw["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if ex:
            sets = ", ".join(f"{k}=?" for k in kw)
            await db.execute(f"UPDATE users SET {sets} WHERE user_id=?", [*kw.values(), uid])
        else:
            await db.execute(
                "INSERT INTO users (user_id,city,lang,forecast_format,active,notify_hour) VALUES (?,?,?,?,1,7)",
                (uid, kw.get("city"), kw.get("lang","ru"), kw.get("forecast_format","day")))
        await db.commit()

async def get_all_active():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id,city,lang,forecast_format FROM users WHERE active=1 AND city IS NOT NULL") as c:
            return await c.fetchall()

async def get_users_by_hour(hour):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id,city,lang,forecast_format FROM users WHERE active=1 AND city IS NOT NULL AND COALESCE(notify_hour,7)=?",
            (hour,)) as c:
            return await c.fetchall()

# ── WEATHER API ───────────────────────────────────────────────────────────────
async def fetch_weather(city, days=7):
    url = f"https://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={city}&days={days}&lang=ru&aqi=yes"
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200: return None
                data = await r.json()
                return data if "location" in data else None
        except: return None

async def search_city(q):
    url = f"https://api.weatherapi.com/v1/search.json?key={WEATHER_API_KEY}&q={q}"
    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    res = await r.json()
                    return res[0]["name"] if res else None
        except: return None

# ── FORMATTERS ────────────────────────────────────────────────────────────────
def fmt_day(data, lang):
    c = data["current"]; loc = data["location"]
    code = c["condition"]["code"]; temp = round(c["temp_c"])
    feels = round(c["feelslike_c"]); desc = c["condition"]["text"]
    humidity = c["humidity"]; wind = round(c["wind_kph"])
    wind_dir = c.get("wind_dir",""); vis = c.get("vis_km","—")
    pressure = round(c.get("pressure_mb",0) * 0.750062)
    uv = c.get("uv","—")
    today = data["forecast"]["forecastday"][0]["day"]
    t_max = round(today["maxtemp_c"]); t_min = round(today["mintemp_c"])
    rain_ch = today.get("daily_chance_of_rain",0)
    city = loc["name"]; country = loc["country"]
    icon = wicon(code)

    def uv_lbl(v, ru):
        try: v2=float(v)
        except: return str(v)
        if ru:
            if v2<=2: return f"{v} (Низкий)"
            elif v2<=5: return f"{v} (Умеренный)"
            elif v2<=7: return f"{v} (Высокий)"
            else: return f"{v} (Очень высокий)"
        else:
            if v2<=2: return f"{v} (Low)"
            elif v2<=5: return f"{v} (Moderate)"
            elif v2<=7: return f"{v} (High)"
            else: return f"{v} (Very High)"

    mood_ru = {
        "storm": "⛈ <i>Гроза! Лучше остаться дома — безопасность прежде всего.</i>",
        "snow":  "❄️ <i>Снег за окном — укутайся потеплее и наслаждайся уютом!</i>",
        "rain":  "🌧 <i>Дождливый день — идеально для чашки чая и любимой книги.</i>",
        "fog":   "🌫 <i>Туман на улице — будь осторожен на дороге.</i>",
        "hot":   "🥵 <i>Жара! Пей больше воды и носи лёгкую одежду.</i>",
        "warm":  "☀️ <i>Отличный день для прогулки — солнце и тепло зовут на улицу!</i>",
        "mild":  "🌤 <i>Приятная погода — свежий воздух и хорошее настроение!</i>",
        "cool":  "🧣 <i>Прохладно — одевайся потеплее и наслаждайся днём!</i>",
        "cold":  "🥶 <i>Очень холодно! Одевайся по-зимнему и не забудь перчатки.</i>",
    }
    mood_en = {
        "storm": "⛈ <i>Thunderstorm! Better stay home — safety first.</i>",
        "snow":  "❄️ <i>Snow outside — wrap up warm and enjoy the coziness!</i>",
        "rain":  "🌧 <i>Rainy day — perfect for a cup of tea and a good book.</i>",
        "fog":   "🌫 <i>Foggy outside — be careful on the road.</i>",
        "hot":   "🥵 <i>Heat wave! Drink plenty of water and wear light clothes.</i>",
        "warm":  "☀️ <i>Great day for a walk — sunshine and warmth await!</i>",
        "mild":  "🌤 <i>Pleasant weather — fresh air and good mood!</i>",
        "cool":  "🧣 <i>Cool outside — dress warmly and enjoy the day!</i>",
        "cold":  "🥶 <i>Very cold! Dress in winter gear and don't forget gloves.</i>",
    }
    is_snow_and_cold = code in SNOW_C and temp <= 4
    if code in STORM_C: mk = "storm"
    elif is_snow_and_cold: mk = "snow"
    elif code in RAIN_C: mk = "rain"
    elif code in (1030,1135,1147): mk = "fog"
    elif temp >= 30: mk = "hot"
    elif temp >= 20: mk = "warm"
    elif temp >= 10: mk = "mild"
    elif temp >= 0: mk = "cool"
    else: mk = "cold"

    mood = mood_ru[mk] if lang=="ru" else mood_en[mk]
    wardrobe = get_wardrobe(temp, code, lang)
    eco = get_eco(code, temp, lang)
    quote = get_quote(code, lang)

    if lang == "ru":
        return (f"{icon} <b>Погода — {city}, {country}</b>\n"
                f"📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n"
                f"{mood}\n\n"
                f"🌡 <b>Сейчас:</b> {temp}°C (ощущается {feels}°C)\n"
                f"📊 <b>День/Ночь:</b> {t_max}°C / {t_min}°C\n"
                f"🌥 <b>Состояние:</b> {desc}\n"
                f"💧 <b>Влажность:</b> {humidity}%\n"
                f"💨 <b>Ветер:</b> {wind} км/ч {wind_dir}\n"
                f"🌂 <b>Вероятность дождя:</b> {rain_ch}%\n"
                f"👁 <b>Видимость:</b> {vis} км\n"
                f"🔵 <b>Давление:</b> {pressure} мм рт.ст.\n"
                f"🌞 <b>УФ-индекс:</b> {uv_lbl(uv,'ru')}\n\n"
                f"{wardrobe}\n\n"
                f"{eco}\n\n"
                f"💬 <i>{quote}</i>")
    else:
        return (f"{icon} <b>Weather — {city}, {country}</b>\n"
                f"📅 {now_local().strftime('%d.%m.%Y, %A')}\n\n"
                f"{mood}\n\n"
                f"🌡 <b>Now:</b> {temp}°C (feels like {feels}°C)\n"
                f"📊 <b>Day/Night:</b> {t_max}°C / {t_min}°C\n"
                f"🌥 <b>Condition:</b> {desc}\n"
                f"💧 <b>Humidity:</b> {humidity}%\n"
                f"💨 <b>Wind:</b> {wind} km/h {wind_dir}\n"
                f"🌂 <b>Rain chance:</b> {rain_ch}%\n"
                f"👁 <b>Visibility:</b> {vis} km\n"
                f"🔵 <b>Pressure:</b> {round(c.get('pressure_mb',0))} hPa\n"
                f"🌞 <b>UV index:</b> {uv_lbl(uv,'en')}\n\n"
                f"{wardrobe}\n\n"
                f"{eco}\n\n"
                f"💬 <i>{quote}</i>")

def fmt_week(data, lang):
    loc = data["location"]
    hdr = f"📆 <b>{'Прогноз на неделю' if lang=='ru' else 'Weekly forecast'} — {loc['name']}, {loc['country']}</b>\n\n"
    lines = [hdr]
    for d in data["forecast"]["forecastday"]:
        dt = datetime.strptime(d["date"],"%Y-%m-%d").strftime("%d.%m")
        ico = wicon(d["day"]["condition"]["code"])
        tmax = round(d["day"]["maxtemp_c"]); tmin = round(d["day"]["mintemp_c"])
        desc = d["day"]["condition"]["text"]
        rain = d["day"].get("daily_chance_of_rain",0)
        lines.append(f"{ico} <b>{dt}</b>: {tmax}°/{tmin}° — {desc} 🌂{rain}%")
    return "\n".join(lines)

def fmt_month(data, lang):
    loc = data["location"]
    note = ("⚠️ <i>Прогноз на месяц приблизительный</i>\n\n" if lang=="ru"
            else "⚠️ <i>Monthly forecast is approximate</i>\n\n")
    hdr = f"🗓 <b>{'Прогноз на месяц' if lang=='ru' else 'Monthly forecast'} — {loc['name']}, {loc['country']}</b>\n{note}"
    lines = [hdr]
    for d in data["forecast"]["forecastday"]:
        dt = datetime.strptime(d["date"],"%Y-%m-%d").strftime("%d.%m")
        ico = wicon(d["day"]["condition"]["code"])
        lines.append(f"{ico} <b>{dt}</b>: {round(d['day']['maxtemp_c'])}°/{round(d['day']['mintemp_c'])}°")
    return "\n".join(lines)

def build_aff_kb(code, lang):
    b = InlineKeyboardBuilder()
    cnt = 0
    if code in RAIN_C:
        for k in ["bolt","inDrive","wolt","umbrella","tickets"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    elif code in SNOW_C:
        for k in ["bolt","inDrive","tickets"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    elif code == 1000:
        for k in ["glovo","clothes","tickets","hotels"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    else:
        for k in ["tickets","hotels","clothes"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    b.button(text=AFF["bothub"][lang], url=AFF["bothub"]["url"]); cnt+=1
    has_sos, _, sos_btn = get_sos(code, 0, lang)
    if has_sos: b.button(text=sos_btn, callback_data=f"sos_{code}_0"); cnt+=1
    b.adjust(2)
    return b.as_markup() if cnt>0 else None

async def build_msg(city, fmt, lang):
    days = 14 if fmt=="month" else 7
    data = await fetch_weather(city, days)
    if not data: return None, None
    code = data["current"]["condition"]["code"]
    temp = data["current"]["temp_c"]
    if fmt=="day": text = fmt_day(data, lang)
    elif fmt=="week": text = fmt_week(data, lang)
    elif fmt=="month": text = fmt_month(data, lang)
    else: text = fmt_day(data, lang)+"\n\n"+fmt_week(data, lang)
    # SOS button based on real temp
    b = InlineKeyboardBuilder()
    cnt = 0
    if code in RAIN_C:
        for k in ["bolt","inDrive","wolt","umbrella","tickets"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    elif code in SNOW_C:
        for k in ["bolt","inDrive","tickets"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    elif code == 1000:
        for k in ["glovo","clothes","tickets","hotels"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    else:
        for k in ["tickets","hotels","clothes"]:
            if real(AFF[k]["url"]): b.button(text=AFF[k][lang], url=AFF[k]["url"]); cnt+=1
    b.button(text=AFF["bothub"][lang], url=AFF["bothub"]["url"]); cnt+=1
    has_sos, _, sos_btn = get_sos(code, temp, lang)
    if has_sos: b.button(text=sos_btn, callback_data=f"sos_{code}_{int(temp)}"); cnt+=1
    b.adjust(2)
    kb = b.as_markup() if cnt>0 else None
    return text, kb

# ── FSM ───────────────────────────────────────────────────────────────────────
class CityForm(StatesGroup):
    waiting = State()

# ── BOT ───────────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp  = Dispatcher(storage=MemoryStorage())

# ── HANDLERS ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    if not u: await save_user(msg.from_user.id, lang=lang)
    text = ("👋 Привет! Я <b>PogodaMood</b> — твой личный синоптик с характером 🌤\n\n"
            "Каждый день буду присылать <b>настроение дня</b> — чтобы ты знал как одеться и чем заняться.\n\n"
            "👇 Начни с кнопок ниже:" if lang=="ru" else
            "👋 Hello! I'm <b>PogodaMood</b> — your personal weather assistant 🌤\n\n"
            "Every day I'll send your <b>mood of the day</b> — so you know what to wear and do.\n\n"
            "👇 Use the buttons below:")
    await msg.answer(text, reply_markup=main_kb(lang))

@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c: total=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE active=1 AND city IS NOT NULL") as c: active=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE city IS NULL") as c: no_city=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE active=0") as c: unsub=(await c.fetchone())[0]
        async with db.execute("SELECT lang,COUNT(*) FROM users GROUP BY lang") as c: langs=await c.fetchall()
        async with db.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at)=DATE('now')") as c: today=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE joined_at>=datetime('now','-7 days')") as c: week=(await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE last_active>=datetime('now','-1 day')") as c: h24=(await c.fetchone())[0]
        async with db.execute("SELECT city,COUNT(*) cnt FROM users WHERE city IS NOT NULL GROUP BY city ORDER BY cnt DESC LIMIT 5") as c: cities=await c.fetchall()
    lang_str = " | ".join(f"{l}:{n}" for l,n in langs)
    cities_str = "\n".join(f"  {i+1}. {city} — {n}" for i,(city,n) in enumerate(cities))
    await msg.answer(
        f"<b>Статистика @pogoda_mood_bot</b>\n🕐 {now_local().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Пользователи:</b>\n  Всего: <b>{total}</b>\n  Подписаны: <b>{active}</b>\n"
        f"  Без города: <b>{no_city}</b>\n  Отписались: <b>{unsub}</b>\n\n"
        f"<b>Прирост:</b>\n  Сегодня: <b>+{today}</b>\n  За 7 дней: <b>+{week}</b>\n  Активны 24ч: <b>{h24}</b>\n\n"
        f"<b>Языки:</b> {lang_str}\n\n<b>Топ городов:</b>\n{cities_str}"
    )

# ── REPLY KEYBOARD HANDLERS ───────────────────────────────────────────────────
WEATHER_BTN = {"🌤 Погода сейчас", "🌤 Weather now"}
TIME_BTN    = {"⏰ Время прогноза", "⏰ Forecast time"}
SETTINGS_BTN= {"⚙️ Настройки",     "⚙️ Settings"}
ACTIVITY_BTN= {"🎲 Активность дня","🎲 Activity of the day"}
HELP_BTN    = {"💬 Помощь",        "💬 Help"}

@dp.message(F.text.in_(WEATHER_BTN))
async def btn_weather(msg: Message, state: FSMContext):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    if not u or not u.get("city"):
        await state.set_state(CityForm.waiting)
        ask = ("🏙 Напиши название города (на русском или английском):\nПример: <code>Москва</code> или <code>Oslo</code>"
               if lang=="ru" else
               "🏙 Enter your city name:\nExample: <code>Moscow</code> or <code>Oslo</code>")
        await msg.answer(ask)
        return
    wait = await msg.answer("⏳ "+("Загружаю..." if lang=="ru" else "Loading..."))
    text, kb = await build_msg(u["city"], u.get("format","day"), lang)
    await wait.delete()
    if text: await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else: await msg.answer("😔 "+("Не удалось получить данные. Попробуй позже." if lang=="ru" else "Couldn't get data. Try again later."))

@dp.message(F.text.in_(TIME_BTN))
async def btn_time(msg: Message):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    hour = u.get("notify_hour",7) if u else 7
    text = (f"⏰ <b>Время рассылки</b>\n\nСейчас прогноз приходит в <b>{hour:02d}:00</b>\n\nВыбери удобное время:"
            if lang=="ru" else
            f"⏰ <b>Forecast time</b>\n\nCurrently sending at <b>{hour:02d}:00</b>\n\nChoose your time:")
    await msg.answer(text, reply_markup=time_inline_kb(lang))

@dp.message(F.text.in_(SETTINGS_BTN))
async def btn_settings(msg: Message):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    city = u["city"] if u and u.get("city") else ("не указан" if lang=="ru" else "not set")
    hour = u.get("notify_hour",7) if u else 7
    fmt_map = {"day":"📅","week":"📆","month":"🗓","all":"🌟"}
    fmt = fmt_map.get(u["format"] if u else "day","📅")
    text = (f"⚙️ <b>Настройки</b>\n\n🏙 Город: <b>{city}</b>\n{fmt} Формат: <b>{u['format'] if u else 'day'}</b>\n⏰ Время: <b>{hour:02d}:00</b>\n🌐 Язык: <b>Русский 🇷🇺</b>"
            if lang=="ru" else
            f"⚙️ <b>Settings</b>\n\n🏙 City: <b>{city}</b>\n{fmt} Format: <b>{u['format'] if u else 'day'}</b>\n⏰ Time: <b>{hour:02d}:00</b>\n🌐 Language: <b>English 🌍</b>")
    await msg.answer(text, reply_markup=settings_inline_kb(lang))

@dp.message(F.text.in_(ACTIVITY_BTN))
async def btn_activity(msg: Message):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    activity = random.choice(ACTIVITIES[lang])
    prefix = "🎲 <b>Активность дня:</b>\n\n" if lang=="ru" else "🎲 <b>Activity of the day:</b>\n\n"
    await msg.answer(prefix + activity)

@dp.message(F.text.in_(HELP_BTN))
async def btn_help(msg: Message):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    hour = u.get("notify_hour",7) if u else 7
    if lang == "ru":
        text = (f"ℹ️ <b>PogodaMood — помощь</b>\n\n"
                f"🌤 Присылаю прогноз с <b>настроением дня</b> каждый день в <b>{hour:02d}:00</b>\n\n"
                f"<b>Кнопки меню:</b>\n"
                f"🌤 Погода сейчас — прогноз на сейчас\n"
                f"⏰ Время прогноза — выбрать время рассылки\n"
                f"⚙️ Настройки — город, язык, формат\n"
                f"🎲 Активность дня — идея чем заняться\n\n"
                f"🌍 <b>Поддерживаю города всего мира</b>\n\n"
                f"💬 <b>Вопросы и предложения:</b>\n@BohdanViktorovich1")
    else:
        text = (f"ℹ️ <b>PogodaMood — help</b>\n\n"
                f"🌤 I send forecasts with a <b>mood of the day</b> every day at <b>{hour:02d}:00</b>\n\n"
                f"<b>Menu buttons:</b>\n"
                f"🌤 Weather now — current forecast\n"
                f"⏰ Forecast time — choose send time\n"
                f"⚙️ Settings — city, language, format\n"
                f"🎲 Activity of the day — idea for your day\n\n"
                f"🌍 <b>Supports cities worldwide</b>\n\n"
                f"💬 <b>Questions & suggestions:</b>\n@BohdanViktorovich1")
    await msg.answer(text)

@dp.message(CityForm.waiting)
async def process_city(msg: Message, state: FSMContext):
    u = await get_user(msg.from_user.id)
    lang = u["lang"] if u else "ru"
    city_input = msg.text.strip()
    wait = await msg.answer("🔍 "+("Ищу город..." if lang=="ru" else "Searching..."))
    data = await fetch_weather(city_input, 1)
    if not data:
        found = await search_city(city_input)
        if found: data = await fetch_weather(found, 1)
    await wait.delete()
    if not data:
        err = ("🤔 Не нашёл такой город. Попробуй на английском:\n<code>Oslo</code>, <code>Paris</code>, <code>New York</code>"
               if lang=="ru" else
               "🤔 City not found. Try in English:\n<code>Oslo</code>, <code>Paris</code>, <code>New York</code>")
        await msg.answer(err)
        return
    city_name = data["location"]["name"]
    country   = data["location"]["country"]
    await save_user(msg.from_user.id, city=city_name)
    await state.clear()
    saved = (f"✅ Город <b>{city_name}, {country}</b> сохранён!\n\nТеперь выбери формат прогноза 👇"
             if lang=="ru" else
             f"✅ City <b>{city_name}, {country}</b> saved!\n\nNow choose forecast format 👇")
    await msg.answer(saved, reply_markup=format_inline_kb(lang))

# ── INLINE CALLBACKS ──────────────────────────────────────────────────────────
@dp.callback_query(F.data == "set_city")
async def cb_set_city(call: CallbackQuery, state: FSMContext):
    u = await get_user(call.from_user.id)
    lang = u["lang"] if u else "ru"
    await state.set_state(CityForm.waiting)
    await call.message.answer("🏙 "+("Напиши название города:" if lang=="ru" else "Enter city name:"))
    await call.answer()

@dp.callback_query(F.data == "choose_format")
async def cb_choose_format(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    lang = u["lang"] if u else "ru"
    text = "📋 <b>" + ("Выбери формат прогноза:" if lang=="ru" else "Choose forecast format:") + "</b>"
    try:
        await call.message.edit_text(text, reply_markup=format_inline_kb(lang))
    except Exception:
        await call.message.answer(text, reply_markup=format_inline_kb(lang))
    await call.answer()

@dp.callback_query(F.data == "toggle_lang")
async def cb_lang(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    new_lang = "en" if (u and u.get("lang")=="ru") else "ru"
    await save_user(call.from_user.id, lang=new_lang)
    switched = ("✅ Язык изменён на Русский 🇷🇺" if new_lang=="ru" else "✅ Language changed to English 🌍")
    await call.message.answer(switched, reply_markup=main_kb(new_lang))
    await call.answer()

@dp.callback_query(F.data.startswith("fmt_"))
async def cb_fmt(call: CallbackQuery):
    fmt = call.data.replace("fmt_","")
    u = await get_user(call.from_user.id)
    lang = u["lang"] if u else "ru"
    await save_user(call.from_user.id, forecast_format=fmt)
    hour = u.get("notify_hour",7) if u else 7
    ok = (f"✅ Готово! Прогноз каждый день в <b>{hour:02d}:00</b> 🌅" if lang=="ru"
          else f"✅ Done! Forecast every day at <b>{hour:02d}:00</b> 🌅")
    await call.message.answer(ok, reply_markup=main_kb(lang))
    await call.answer()

@dp.callback_query(F.data.startswith("time_"))
async def cb_time(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    lang = u["lang"] if u else "ru"
    val = call.data.replace("time_","")
    if val == "off":
        await save_user(call.from_user.id, active=0)
        txt = "🔕 Рассылка отключена. Можешь включить снова через ⏰ Время прогноза." if lang=="ru" else "🔕 Notifications turned off. You can re-enable via ⏰ Forecast time."
    else:
        hour = int(val)
        await save_user(call.from_user.id, notify_hour=hour, active=1)
        txt = (f"✅ Прогноз буду присылать каждый день в <b>{hour:02d}:00</b> 🌅" if lang=="ru"
               else f"✅ I'll send your forecast every day at <b>{hour:02d}:00</b> 🌅")
    await call.message.answer(txt, reply_markup=main_kb(lang))
    await call.answer()

@dp.callback_query(F.data.startswith("sos_"))
async def cb_sos(call: CallbackQuery):
    u = await get_user(call.from_user.id)
    lang = u["lang"] if u else "ru"
    parts = call.data.split("_")
    code = int(parts[1]); temp = float(parts[2])
    _, tips, _ = get_sos(code, temp, lang)
    if tips: await call.message.answer(tips)
    await call.answer()

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
async def send_morning_forecasts():
    current_hour = now_local().hour
    users = await get_users_by_hour(current_hour)
    for uid, city, lang, fmt in users:
        try:
            text, kb = await build_msg(city, fmt, lang)
            if text:
                prefix = "🌅 <b>Доброе утро! Вот твоё настроение дня:</b>\n\n" if lang=="ru" else "🌅 <b>Good morning! Here's your mood of the day:</b>\n\n"
                await bot.send_message(uid, prefix+text, reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logging.warning(f"Send failed {uid}: {e}")

async def send_evening_alerts():
    users = await get_all_active()
    for uid, city, lang, fmt in users:
        try:
            data = await fetch_weather(city, 2)
            if not data or len(data["forecast"]["forecastday"]) < 2: continue
            tom = data["forecast"]["forecastday"][1]["day"]
            code = tom["condition"]["code"]
            tmin = round(tom["mintemp_c"]); tmax = round(tom["maxtemp_c"])
            wind = round(tom.get("maxwind_kph",0)); rain = tom.get("daily_chance_of_rain",0)
            alert = None
            ru = lang=="ru"
            if code in STORM_C:
                alert = ("⛈ <b>Завтра гроза!</b>\nЗарядите телефон заранее и возьмите зонт." if ru
                         else "⛈ <b>Thunderstorm tomorrow!</b>\nCharge your phone and bring an umbrella.")
            elif code in HSNOW_C or tmin < -10:
                alert = (f"❄️ <b>Завтра сильный мороз ({tmin}°C)!</b>\nПодготовь машину и одевайся теплее." if ru
                         else f"❄️ <b>Heavy frost tomorrow ({tmin}°C)!</b>\nPrepare your car and dress warm.")
            elif tmax >= 35:
                alert = (f"🥵 <b>Завтра аномальная жара ({tmax}°C)!</b>\nЗапаси воду, избегай улицы в полдень." if ru
                         else f"🥵 <b>Extreme heat tomorrow ({tmax}°C)!</b>\nStock up on water, avoid noon sun.")
            elif wind >= 60:
                alert = (f"💨 <b>Завтра сильный ветер ({wind} км/ч)!</b>\nЗакрепи всё на балконе." if ru
                         else f"💨 <b>Strong winds tomorrow ({wind} km/h)!</b>\nSecure items on your balcony.")
            elif rain >= 80:
                alert = ("🌧 <b>Завтра весь день дождь!</b>\nНе забудь зонт и непромокаемую обувь." if ru
                         else "🌧 <b>Heavy rain all day tomorrow!</b>\nDon't forget umbrella and waterproof shoes.")
            if alert:
                prefix = "🌙 <b>Вечернее предупреждение:</b>\n\n" if ru else "🌙 <b>Evening alert:</b>\n\n"
                await bot.send_message(uid, prefix+alert)
        except Exception as e:
            logging.warning(f"Evening alert failed {uid}: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    scheduler = AsyncIOScheduler(timezone="Europe/Chisinau")
    scheduler.add_job(send_morning_forecasts, CronTrigger(minute=0))
    scheduler.add_job(send_evening_alerts,    CronTrigger(hour=21, minute=0))
    scheduler.start()
    logging.info("✅ PogodaMood Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
