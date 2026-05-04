import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8642619178:AAHnJxQgW0DsUOZvt13Zlf-fP95-fCG-1wY"

# Reklama matni
REKLAMA_MATNI = """🚚 LABO XIZMATI – NAMANGAN
📦 Har qanday yukni tez va ishonchli yetkazamiz!
🏠 Uy ko‘chirish | 🪑 Mebel | 🧱 Qurilish yuklari
⚡️ Tezkor xizmat – 24/7
💰 Arzon narxlar
👨🔧 Ishonchli haydovchilar
🔥 1 qo‘ng‘iroq – muammo hal!
👉 Buyurtma berish uchun yozing:
📲 Telegram: Namangan_labo24
📞 +998950703345
📞 +998912933345"""

# Rasm fayli nomi
RASM_NOMI = "Screenshot 2026-05-04 125452.png"

# --- DATABASE SOZLAMALARI ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def add_chat(chat_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO chats (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Chat allaqachon mavjud bo'lsa
    conn.close()

def get_all_chats():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM chats")
    chats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return chats

# --- BOT LOGIKASI ---
logging.basicConfig(level=logging.INFO)
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
    chats = get_all_chats()
    count = 0
    
    from aiogram.types import FSInputFile
    import os
    
    if not os.path.exists(RASM_NOMI):
        photo = None
    else:
        photo = FSInputFile(RASM_NOMI)

    for chat_id in chats:
        try:
            if photo:
                await bot.send_photo(chat_id=chat_id, photo=photo, caption=REKLAMA_MATNI)
            else:
                await bot.send_message(chat_id=chat_id, text=REKLAMA_MATNI)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Xatolik {chat_id} ga yuborishda: {e}")
    
    logging.info(f"Reklama {count} ta chatga muvaffaqiyatli yuborildi.")

# --- ASOSIY FUNKSIYA ---
async def main():
    init_db()
    
    scheduler = AsyncIOScheduler()
    # Siz bergan yangi vaqtlar: 07:00, 12:00, 13:50, 17:00, 22:00
    scheduler.add_job(send_advertisement, "cron", hour="7,12,17,22", minute=0)
    scheduler.add_job(send_advertisement, "cron", hour=13, minute=50)
    scheduler.start()

    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
