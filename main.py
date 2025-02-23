import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from collections import defaultdict

# Bot tokenini kiriting
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Guruh IDlari
SOURCE_CHAT_IDS = [
    -1002295479087, -1001839437480, -1002387184511, -1001669239085, -1002348953296,
    -1002403641031, -1002323086782, -1002421350983, -1002473575781, -1001562060904,
    -1001405504917
]  # Foydalanuvchilar xabar yozadigan guruhlar
DESTINATION_CHAT_ID = -1002290968836  # Xabarlar yo‘naltiriladigan guruh

# Spamni nazorat qilish
user_message_count = defaultdict(list)

# Bot chiqarib yuborilgan guruhlar ro‘yxati
removed_chats = set()

# Bot va dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Logger sozlash
logging.basicConfig(level=logging.INFO)

async def is_admin(chat_id: int, user_id: int) -> bool:
    """Foydalanuvchi admin yoki yo‘qligini tekshirish"""
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]
    except Exception:
        return False

async def is_bot_removed(chat_id: int) -> bool:
    """Bot guruhdan chiqarib yuborilganligini tekshirish"""
    if chat_id in removed_chats:
        return True
    try:
        await bot.get_chat(chat_id)
        return False
    except Exception as e:
        logging.warning(f"Bot guruhdan chiqarilgan: {chat_id}, sabab: {e}")
        removed_chats.add(chat_id)
        return True

@dp.message()
async def handle_messages(message: Message):
    """Admin bo‘lmagan foydalanuvchilarning xabarlarini boshqa guruhga yo‘naltirish"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    current_time = time.time()

    if chat_id in removed_chats:
        return  

    if chat_id in SOURCE_CHAT_IDS:
        if not message.text and not message.contact:  
            return

        if await is_admin(chat_id, user_id):  
            return

        if await is_bot_removed(chat_id):
            return  

        # Foydalanuvchi xabar tarixini tekshiramiz
        user_message_count[user_id].append(current_time)
        user_message_count[user_id] = [t for t in user_message_count[user_id] if current_time - t < 1800]  # 30 daqiqa

        if len(user_message_count[user_id]) > 2:  # Agar 2 tadan ko‘p xabar yozgan bo‘lsa
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {message.from_user.full_name}, iltimos, ortiqcha xabar yubormang!"
                )
            except Exception as e:
                logging.error(f"Xatolik (xabar o‘chirishda): {e}")
            return  

        try:
            sent_message = await bot.forward_message(
                chat_id=DESTINATION_CHAT_ID,
                from_chat_id=chat_id,
                message_id=message.message_id
            )

            user_info = f"👤 *Ism:* {message.from_user.full_name}\n"
            if message.from_user.username:
                user_info += f"📌 *Username:* @{message.from_user.username}\n"

            if message.contact and message.contact.phone_number:
                user_info += f"📞 *Telefon:* {message.contact.phone_number}\n"
            else:
                user_info += "📞 *Telefon:* ❌ Mavjud emas\n"

            user_info += "\n📢 *Sizga xabar berishadi!*"

            await bot.send_message(
                chat_id=DESTINATION_CHAT_ID,
                text=user_info,
                parse_mode="Markdown",
                reply_to_message_id=sent_message.message_id
            )

            await bot.delete_message(chat_id=chat_id, message_id=message.message_id)

            await bot.send_message(
                chat_id=chat_id,
                text=f"✅ *{message.from_user.full_name}, xabaringiz qabul qilindi!* \n\n"
                     f"🚖 Ishonchli va tajribali taxchilar siz bilan tez orada bog‘lanishadi! 📞",
                parse_mode="Markdown"
            )

        except Exception as e:
            logging.error(f"Xatolik: {e}")

async def main():
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
