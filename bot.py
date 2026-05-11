import asyncio
import logging
import psycopg2
import os
import pytz
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8642619178:AAHZxlUfGLDd-uwcBXJ4DYa_ijc48CUFFK8"

# Reklama matni
REKLAMA_MATNI = """🚚 LABO XIZMATI – NAMANGAN
📦 Har qanday yukni tez va ishonchli yetkazamiz!
🏠 Uy ko‘chirish | 🪑 Mebel | 🧱 Qurilish yuklari
⚡️ Tezkor xizmat – 24/7
💰 Arzon narxlar
👨🔧 Ishonchli haydovchilar
🔥 1 qo‘ng‘iroq – muammo hal!
👉 Buyurtma berish uchun yozing:
📲 Telegram: Labo_93
📞 +998950703345
📞 +998912933345"""

# Rasm fayli nomi
RASM_NOMI = "ChatGPT Image May 7, 2026, 12_14_07 PM.png"

# Neon.tech PostgreSQL ulanish manzili
DATABASE_URL = "postgresql://neondb_owner:npg_ehtQ4OvUiP0F@ep-winter-shadow-aqvf5uub-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT UNIQUE
            )
        """)
        conn.commit()
        conn.close()
        logging.info("PostgreSQL bazasi tayyor.")
    except Exception as e:
        logging.error(f"Bazani ishga tushirishda xatolik: {e}")

def add_chat(chat_id):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        # ON CONFLICT orqali dublikat ID larni oldini olamiz
        cursor.execute("INSERT INTO chats (chat_id) VALUES (%s) ON CONFLICT (chat_id) DO NOTHING", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Chatni qo'shishda xatolik: {e}")

def get_all_chats():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM chats")
        chats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return chats
    except Exception as e:
        logging.error(f"Chatlarni olishda xatolik: {e}")
        return []

# --- BOT LOGIKASI ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Bot guruh yoki kanalga qo'shilganda ID ni saqlash
@dp.message(Command("test"))
@dp.channel_post(Command("test"))
async def test_command(message: types.Message):
    await message.answer("Reklama yuborish boshlandi...")
    await send_advertisement()

@dp.message()
@dp.channel_post()
async def check_new_chat(message: types.Message):
    # Faqat guruh, superguruh va kanallarni saqlaymiz (shaxsiy chatlarni emas)
    if message.chat.type in ["group", "supergroup", "channel"]:
        add_chat(message.chat.id)

@dp.my_chat_member()
async def on_my_chat_member(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["administrator", "member"]:
        if event.chat.type in ["group", "supergroup", "channel"]:
            add_chat(event.chat.id)
            logging.info(f"Bot yangi chatga qo'shildi: {event.chat.id}")

# Reklama yuborish funksiyasi
async def send_advertisement():
    logging.info("REKLAMA VAKTI KELDI! Jarayon boshlandi...")
    chats = get_all_chats()
    logging.info(f"Bazada {len(chats)} ta chat topildi.")
    
    if not chats:
        logging.warning("Reklama yuborish uchun hech qanday chat topilmadi!")
        return

    count = 0
    from aiogram.types import FSInputFile
    import os
    
    if not os.path.exists(RASM_NOMI):
        photo = None
        logging.error(f"Rasm fayli topilmadi: {RASM_NOMI}")
    else:
        photo = FSInputFile(RASM_NOMI)

    for chat_id in chats:
        try:
            if photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=REKLAMA_MATNI)
            else:
                await bot.send_message(chat_id=chat_id, text=REKLAMA_MATNI)
            count += 1
            await asyncio.sleep(0.1) # Biroz sekinroq yuboramiz (Telegram limiti uchun)
        except Exception as e:
            logging.error(f"Xatolik {chat_id} ga yuborishda: {e}")
    
    logging.info(f"Reklama {count} ta chatga muvaffaqiyatli yuborildi.")

# --- RENDER UCHUN WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render beradigan portni olamiz, bo'lmasa 10000
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server {port}-portda ishga tushdi.")

async def heartbeat_task():
    while True:
        logging.info("HEARTBEAT: Bot tirik va ishlayapti.")
        await asyncio.sleep(1800) # Har 30 daqiqada log yozadi

# --- ASOSIY FUNKSIYA ---
async def main():
    init_db()
    
    asyncio.create_task(start_web_server())
    asyncio.create_task(heartbeat_task())

    # Pytz orqali O'zbekiston vaqtini sozlash
    uzb_tz = pytz.timezone('Asia/Tashkent')
    scheduler = AsyncIOScheduler(timezone=uzb_tz)
    
    # Vaqtlar: 05:00, 07:00, 10:00, 12:00, 15:00, 18:00, 21:00, 23:00
    scheduler.add_job(
        send_advertisement, 
        "cron", 
        hour="5,7,10,12,15,18,21,23", 
        minute=0,
        misfire_grace_time=3600
    )
    scheduler.start()
    
    logging.info(f"Scheduler ishga tushdi. Vaqt zonasi: {uzb_tz}")

    logging.info("Bot ishga tushdi...")
    
    # Chat ID larni loglarda ko'rsatish uchun (Sizga yordam berishim uchun)
    @dp.message()
    @dp.channel_post()
    async def log_chat_id(message: types.Message):
        if message.chat.type in ["group", "supergroup", "channel"]:
            add_chat(message.chat.id)
            logging.info(f"YANGI CHAT ANIQLANDI! Nomi: {message.chat.title}, ID: {message.chat.id}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
