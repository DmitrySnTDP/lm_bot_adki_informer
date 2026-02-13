import asyncio
from datetime import datetime, timedelta, timezone
import os
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
import logging
import telebot


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log',
    filemode='a',
    encoding='utf-8'
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
target_words = ["Артефакты", "СТРАЖНИК", "МАСТЕР ОГНЯ", "test"]
base_wait_time = 15
wait_time = 15


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


client = TelegramClient(session_name, api_id, api_hash, connection_retries = 0, auto_reconnect = False, timeout=30, request_retries=3)


async def main():
    global restart_count, client

    client = TelegramClient(session_name, api_id, api_hash, connection_retries = 0, auto_reconnect = False, timeout=30, request_retries=3)
    
    @client.on(events.NewMessage(incoming=True, chats=target_ch_ids))
    async def handle_channel_posts(event):

        mess = event.message
        chat = await event.get_chat()
        await process_message(mess, chat)
        

    async def process_message(mess, chat):
        global restart_count

        restart_count = 0
        time_now = datetime.now(timezone.utc).replace(microsecond=0)

        if 55 <= time_now.minute < 60:
            min_time = time_now.replace(minute=55, second=0)
            max_time = time_now.replace(minute=54, second=59) + timedelta(hours=1)
        else:
            min_time = time_now.replace(minute=55, second=0) - timedelta(hours=1)
            max_time = time_now.replace(minute=54, second=59)

        if min_time < mess.date < max_time:
            logger.info(f"Получен пост из канала: {mess.chat.title}, message_time: {mess.date}")
            if any(t in mess.text for t in target_words):
                targets_in = [t for t in target_words if t in mess.text]

                if len(targets_in) == 1 and targets_in[0] in target_words[1:]:
                    targets_in = [mess.text.split(" (")[0], targets_in[0]]
                targets_text = str.join(", ", targets_in)
                value = f"Адское событие: {targets_text}!"

                logger.info(f"Подготовлено сообщение: {value}")
                send_to_thread(value, tread_id)
        else:
            logger.info("message is very old")

        await client.send_read_acknowledge(entity=chat, message=mess)
        logger.info("Обработка сообщения завершена")


    async def check_unread_messagges():
        dialogs = await client.get_dialogs()
        target_dialogs = [d for d in dialogs if d.id in target_ch_ids]

        for t_d in target_dialogs:
            if t_d.is_channel and t_d.unread_count > 0:
                messages = await client.get_messages(
                    t_d.entity,
                    limit=t_d.unread_count,
                )
                if messages:
                    for message in messages:
                        await process_message(message, t_d.id)
        logger.info("all unread_message was processed")
    

    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"lmBot запущен как: {me.first_name}")
        await check_unread_messagges()
        logger.info("Ожидаю сообщения из каналов...")
        await client.run_until_disconnected()
            
    except (ConnectionError, ConnectionAbortedError, ConnectionResetError, TimeoutError) as e:
        logger.error(f"disconnect with err: {e}")
        raise e
    finally:
        if client.is_connected():
            await client.disconnect()


if __name__ == "__main__":
    max_restart_count = 120
    restart_count = 0
    while restart_count < max_restart_count:
        if restart_count == 0:
            logger.info("start")
        else:
            logger.info("restart")

        try:
            asyncio.run(main())
            asyncio.Future()
            
        except KeyboardInterrupt:
            logger.info("Остановлено пользователем")
            break
        except (ConnectionError, ConnectionAbortedError, ConnectionResetError, TimeoutError) as e:
            logger.info(f"connection error: {e}")
            restart_count += 1
            wait_time = min(base_wait_time*restart_count, 600)
            logger.info(f"wait {wait_time} seconds and restart")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"unknown err: {e}")
            restart_count += 1
            wait_time = min(base_wait_time*restart_count, 600)
            logger.info(f"wait {wait_time} seconds and restart")
            time.sleep(wait_time)
            