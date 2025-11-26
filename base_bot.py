import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
import logging
import telebot


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv("ini.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
session_name = os.getenv("USER_SESSION_NAME")

if not all([api_id, api_hash, bot_token, session_name]):
    raise ValueError("API_ID и API_HASH должны быть установлены в .env файле")

group_id = -1003126398626
tread_id = 2452


# TARGET_CHANNELS = ['LmNewsEx', 'rabbits_run']
target_ch_ids = [-1001336280776, -1002155382308]
target_words = ["Артефакты", "СТРАЖНИК", "МАСТЕР ОГНЯ"]

bot = telebot.TeleBot(bot_token)


def send_to_thread(text: str, thread_id):
    try:        
        bot.send_message(
            chat_id=group_id,
            message_thread_id=thread_id,
            text=text,
            parse_mode='HTML'
        )
        logger.info(f" Сообщение отправлено в тред {thread_id}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")


client = TelegramClient(session_name, api_id, api_hash)


async def main():
    @client.on(events.NewMessage(incoming=True, chats=target_ch_ids))
    async def handle_channel_posts(event):
        mess = event.message
        chat = await event.get_chat()
        logger.info(f"Получен пост из канала: {mess.chat.title}")
        # logger.info(f"   Текст: {"".join(mess.text.split("\n"))}")
        if any(t in mess.text for t in target_words):
            targets_in = [t for t in target_words if t in mess.text]

            if len(targets_in) == 1 and targets_in[0] in target_words[1:]:
                targets_in = [mess.text.split(" (")[0], targets_in[0]]
            targets_text = str.join(", ", targets_in)
            value = f"Адское событие: {targets_text}!"

            logger.info(f"Подготовлено сообщение: {value}")
            send_to_thread(value, tread_id)

        await client.send_read_acknowledge(entity=chat, message=mess)
        logger.info("Обработка сообщения завершена")
    
    async with client:
        me = await client.get_me()
        logger.info(f"lmBot запущен как: {me.first_name}")
        logger.info("Ожидаю сообщения из каналов...")
        
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка: {e}")