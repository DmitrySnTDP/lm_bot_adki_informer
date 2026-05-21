import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import threading
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
import logging
import telebot


with open('settings.json', "r", encoding="utf-8") as file:
    settings = json.load(file)

with open("default_settings.json", "r", encoding="utf-8") as file:
    def_settings = json.load(file)


def write_settings(set):
    with open("settings.json", "w", encoding="utf-8") as file:
        json.dump(set, file, ensure_ascii=False, indent=4)


def update_settings(new_preset):
    for i in range (len(settings)):
        check = True
        for m in new_preset.get("medals"):
            if m not in settings[i].get("medals"):
                check = False
                break
        if check and len(new_preset.get("medals")) == len(settings[i].get("medals")):
            settings[i]["events"] = new_preset.get("events")
            break


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log',
    filemode='a',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)
bot_helper_thread = None

load_dotenv("ini.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
session_name = os.getenv("USER_SESSION_NAME")

if not all([api_id, api_hash, bot_token, session_name]):
    raise ValueError("API_ID and API_HASH must be set in the .env file.")

target_ch_ids = [-1001336280776, -1002155382308]
target_words = ["Артефакты", "СТРАЖНИК", "МАСТЕР ОГНЯ"]
events_list = ["Артефакты", "Стройка", "Исследование", "Охота", "Лабиринт", "Сокровищница", "Пакты"]
medal_list = ["Мастер огня", "Стражник"]

new_settings = {
    "medals" : [],
    "events" : []
}

base_wait_time = 15
wait_time = 15


bot = telebot.TeleBot(bot_token)

target_chat_id = -1003126398626
# target_chat_id = 5314192316 # for tests
target_thread_id = 2452

text="""Мои команды:\n1️⃣ /help - открывает описание функционала\n2️⃣ /start - запустить бота (актуально для лс)*\n3️⃣ /stop - остановить бота*\n4️⃣ /settings - настроить фильтры для создания уведомлений\n\n*️⃣ - находится на стадии разработки\n\n⚙️ Принцип работы настроек:\n1️⃣ Вызвать команду /settings в нужной теме группы.\n2️⃣ В появившемся меню выбираем "Настроить события" для детального выбора событий или "По умолчанию", чтобы вернуть стандартные настройки.\n➡️ Далее описание принципа работы детальных настроек.\n3️⃣ После выбора детальных настроек, появляется меню выбора медали (стражник, мастер огня или без медалей).\n4️⃣ После выбора, откроется меню со списком видов событий (пакты, охота, исследования и т.д.), нажимаем все необходимые варианты, после чего нажимаем сохранить.\n❕❕❕Пример работы: выбрали Настроить события ➡️ Стражник ➡️ Артефакты, Пакты, Стройка ➡️ Сохранить. Эта комбинация включит уведомления для событий на артефакты или пакты или стройки, содержащие медали стражника.\n5️⃣ Повторить для всех видов медалей при необходимости.\n6️⃣ Нажать "Закрыть" в меню настроек, оно исчезнет после этого через 3 секунды.\n\n❗️ выбор параметра по умолчанию настраивает уведомления так: все события с медалями и любые адки на артефакты""",

@bot.message_handler(commands=["help"])
def send_start_message(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    # if (chat_id == target_chat_id and thread_id == target_thread_id) or chat_id != target_chat_id:
    bot.send_message(
        chat_id=chat_id,
        message_thread_id=thread_id,
        text=
"""Мои команды:
1️⃣ /help - открывает описание функционала
2️⃣ /start - запустить бота (актуально для лс)*
3️⃣ /stop - остановить бота*
4️⃣ /settings - настроить фильтры для создания уведомлений

*️⃣ - находится на стадии разработки

⚙️ Принцип работы настроек:
1️⃣ Вызвать команду /settings в нужной теме группы.
2️⃣ В появившемся меню выбираем "Настроить события" для детального выбора событий или "По умолчанию", чтобы вернуть стандартные настройки.
➡️ Далее описание принципа работы детальных настроек.
3️⃣ После выбора детальных настроек, появляется меню выбора медали (стражник, мастер огня или без медалей).
4️⃣ После выбора, откроется меню со списком видов событий (пакты, охота, исследования и т.д.), нажимаем все необходимые варианты, после чего нажимаем сохранить.
❕❕❕Пример работы: выбрали Настроить события ➡️ Стражник ➡️ Артефакты, Пакты, Стройка ➡️ Сохранить. Эта комбинация включит уведомления для событий на артефакты или пакты или стройки, содержащие медали стражника.
5️⃣ Повторить для всех видов медалей при необходимости.
6️⃣ Нажать "Закрыть" в меню настроек, оно исчезнет после этого через 3 секунды.

❗️ выбор параметра по умолчанию настраивает уведомления так: все события с медалями и любые адки на артефакты""",
    )
    logger.info(f"command {message.text} processed!")


@bot.message_handler(commands=["start"])
def send_start_message(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    if (chat_id == target_chat_id and thread_id == target_thread_id) or chat_id != target_chat_id:
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Привет!",
        )
    logger.info(f"command {message.text} processed!")


@bot.message_handler(commands=["settings"])
def handle_panel_settings(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Настроить события", callback_data="set_evs_medal"),
        telebot.types.InlineKeyboardButton("По умолчанию", callback_data="set_default"),
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close"),
    )


    if chat_id == target_chat_id and thread_id == target_thread_id:
    # if chat_id == target_chat_id: # for tests
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Меню настроек:",
            reply_markup=markup
        )
        logger.info(f"command {message.text} processed!")
    else:
        logger.error("A command from another channel.")


@bot.callback_query_handler(func=lambda call: True)
def handle_text_input(call):
    global settings, new_settings

    chat_id = call.message.chat.id
    message_id = call.message.message_id
    markup = None
    send_text = ""

    if call.data == "go_to_settings":
        update_settings(new_settings)
        write_settings(settings)
        new_settings["medals"] = []
        new_settings["events"] = []

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("Настроить события", callback_data="set_evs_medal"),
            telebot.types.InlineKeyboardButton("По умолчанию", callback_data="set_default"),
            telebot.types.InlineKeyboardButton("Закрыть", callback_data="close"),
        )
        send_text = "Меню настроек:"

    elif call.data == "set_evs_medal":
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(m, callback_data=m) for m in medal_list if m.lower() not in new_settings.get('medals')]
        buttons.append(telebot.types.InlineKeyboardButton("Без медалей", callback_data="без медалей"))
        for b in buttons:
            markup.add(b)
        send_text = "Выберите нужную медаль:"

    elif call.data == "без медалей" or call.data in medal_list:
        if call.data in medal_list:
            new_settings["medals"].append(call.data.lower())
        bot.answer_callback_query(call.id, text=f"Выбрано {call.data}")

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(e, callback_data=e) for e in events_list if e.lower() not in new_settings.get('events')]
        buttons.append(telebot.types.InlineKeyboardButton("Сохранить", callback_data="go_to_settings"))
        for b in buttons:
            markup.add(b)
        if len(new_settings["medals"]) == 0:
            medal_str = "без медалей"
        else:
            medal_str = ", ".join(new_settings["medals"])
        send_text = f"Выбери нужные события для {medal_str}, а после нажмите \"Сохранить\"."

    elif call.data == "set_default":
        bot.answer_callback_query(call.id, text="Установлены настройки по умолчанию!")
        settings = def_settings
        print(def_settings)
        write_settings(settings)
        return
    
    elif call.data in events_list:
        new_settings["events"].append(call.data.lower())
        bot.answer_callback_query(call.id, text=f"Добавлено {call.data}")

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(e, callback_data=e) for e in events_list if e.lower() not in new_settings.get('events')]
        buttons.append(telebot.types.InlineKeyboardButton("Сохранить", callback_data="go_to_settings"))
        for b in buttons:
            markup.add(b)

    elif call.data == "close":
        bot.answer_callback_query(call.id, text="Настройка завершена!")
        time.sleep(3)
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id, timeout=5)
        except:
            logger.error(f"can't delete message: {message_id}, from chat: {chat_id}")
        return
    
    else:
        print(call.data)
        return

    bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup
        )
    if send_text != "":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=send_text,
            reply_markup=markup
        )


def send_to_thread(text: str, chat_id, thread_id=None):
    try:        
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=text,
            parse_mode='HTML'
        )
        logger.info(f"Message was send to thread {thread_id}")
        
    except Exception as e:
        logger.error(f"Sending error: {e}")


client = TelegramClient(session_name, api_id, api_hash, connection_retries = 0, auto_reconnect = False, timeout=30, request_retries=3)


async def main():
    global restart_count, client, bot_helper_thread

    client = TelegramClient(session_name, api_id, api_hash, connection_retries = 0, auto_reconnect = False, timeout=30, request_retries=3)
    
    @client.on(events.NewMessage(incoming=True, chats=target_ch_ids))
    async def handle_channel_posts(event):

        mess = event.message
        chat = await event.get_chat()
        await process_message(mess, chat)
        

    async def process_message(mess, chat):
        global restart_count

        restart_count = 0
        text = mess.text.lower()

        time_now = datetime.now(timezone.utc).replace(microsecond=0)

        if 55 <= time_now.minute < 60:
            min_time = time_now.replace(minute=55, second=0)
            max_time = time_now.replace(minute=54, second=59) + timedelta(hours=1)
        else:
            min_time = time_now.replace(minute=55, second=0) - timedelta(hours=1)
            max_time = time_now.replace(minute=54, second=59)

        if min_time < mess.date < max_time:
            logger.info(f"my time: {time_now}")
            output = ""
            for preset in settings:
                if len(preset.get("events")) < 1 or (len(preset.get("medals")) > 0 and preset.get("medals")[0] not in text):
                    continue
                evs = [ev for ev in preset.get("events") if ev in text]
                print(evs, preset.get("medals"))
                if len(evs) > 0:
                    if "24-часовое испытание" in text:
                        output = f"24-часовое испытание: "
                    else:
                        output = f"Адское событие: "
                    vals = ", ".join(evs + list(map(lambda m: m.upper(), preset.get("medals"))))
                    output += f"{vals}"

                    print(output)
                    send_to_thread(output, target_chat_id, target_thread_id)
                    # send_to_thread(output, target_chat_id) # for tests
                    logger.info(f"Message prepared: {output}")
                    break
        else:
            logger.error(f"The message is not in the timings: {mess.date}")

        await client.send_read_acknowledge(entity=chat, message=mess)
        logger.info("message processing completed")


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
        logger.info(f"lmBot started witn name: {me.first_name}")
        await check_unread_messagges()
        logger.info("Wait messages from chats...")
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
    bot_helper_thread = threading.Thread(target=bot.polling, daemon=True)
    bot_helper_thread.start()
    while restart_count < max_restart_count:
        if restart_count == 0:
            logger.info("start")
        else:
            logger.info("restart")

        try:
            asyncio.run(main())
            asyncio.Future()
            
        except KeyboardInterrupt:
            logger.info("Stopped by user")
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
            