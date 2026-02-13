import asyncio
from datetime import datetime, timezone, timedelta
import sys
import time
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
import logging
import telebot
import threading
import json


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
bot_hear_thread = None

load_dotenv("ini.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
session_name = os.getenv("USER_SESSION_NAME")

if not all([api_id, api_hash, bot_token, session_name]):
    raise ValueError("API_ID и API_HASH должны быть установлены в .env файле")


target_ch_ids = [-1001336280776, -1002155382308]
target_words = ["Артефакты", "СТРАЖНИК", "МАСТЕР ОГНЯ"]
events_list = ["Артефакты", "Стройка", "Исследование", "Охота", "Лабиринт", "Сокровищница", "Пакты"]
medal_list = ["Мастер огня", "Стражник"]

new_settings = {
    "medals" : [],
    "events" : []
}

bot = telebot.TeleBot(bot_token)

target_chat_id = -1003126398626
target_thread_id = 2452


@bot.message_handler(commands=["settings"])
def handle_panel_settings(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Задать события с медалями", callback_data="set_with_medals"),
        telebot.types.InlineKeyboardButton("Задать события без медалей", callback_data="set_without_medals"),
        telebot.types.InlineKeyboardButton("По умолчанию", callback_data="set_default"),
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close"),
    )


    if chat_id == target_chat_id and thread_id == target_thread_id:
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
            telebot.types.InlineKeyboardButton("Задать события с медалями", callback_data="set_with_medals"),
            telebot.types.InlineKeyboardButton("Задать события без медалей", callback_data="set_without_medals"),
            telebot.types.InlineKeyboardButton("По умолчанию", callback_data="set_default"),
            telebot.types.InlineKeyboardButton("Закрыть", callback_data="close"),
        )
        send_text = "Меню настроек:"

    elif call.data == "set_with_medals":
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(m, callback_data=m) for m in medal_list if m.lower() not in new_settings.get('medals')]
        buttons.append(telebot.types.InlineKeyboardButton("Сохранить", callback_data="set_events"))
        for b in buttons:
            markup.add(b)
        send_text = "Выберите нужные варианты, а затем нажмите \"Сохранить\"."

    elif call.data == "set_without_medals" or call.data == "set_events":
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(e, callback_data=e) for e in events_list if e.lower() not in new_settings.get('events')]
        buttons.append(telebot.types.InlineKeyboardButton("Сохранить", callback_data="go_to_settings"))
        for b in buttons:
            markup.add(b)
        send_text = "Выбери нужные события в категории, а после нажмите \"Сохранить\"."

    elif call.data == "set_default":
        bot.answer_callback_query(call.id, text="Установлены настройки по умолчанию!")
        settings = def_settings
        print(def_settings)
        write_settings(settings)
        return

    elif call.data in medal_list:
        new_settings["medals"].append(call.data.lower())
        bot.answer_callback_query(call.id, text=f"Добавлено {call.data}")

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = [telebot.types.InlineKeyboardButton(m, callback_data=m) for m in medal_list if m.lower() not in new_settings.get('medals')]
        buttons.append(telebot.types.InlineKeyboardButton("Сохранить", callback_data="set_events"))
        for b in buttons:
            markup.add(b)
    
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


def send_to_thread(text: str, thread_id):
    try:        
        bot.send_message(
            chat_id=target_chat_id,
            message_thread_id=thread_id,
            text=text,
            parse_mode='HTML'
        )
        logger.info(f"Message sent to thread {thread_id}")
        
    except Exception as e:
        logger.error(f"Sending error: {e}")


client = TelegramClient(session_name, api_id, api_hash)


async def main():
    global bot_helper_thread


    @client.on(events.NewMessage(incoming=True, chats=target_ch_ids))
    async def handle_channel_posts(event):
        mess = event.message
        chat = await event.get_chat()
        logger.info(f"Received post from the channel: {mess.chat.title}")
        text = mess.text.lower()
        output = ""

        time_now = datetime.now(timezone.utc).replace(microsecond=0)

        if 55 <= time_now.minute < 60:
            min_time = time_now.replace(minute=55, second=0)
            max_time = time_now.replace(minute=54, second=59) + timedelta(hours=1)
        else:
            min_time = time_now.replace(minute=55, second=0) - timedelta(hours=1)
            max_time = time_now.replace(minute=54, second=59)

        if min_time < mess.date < max_time:
            logger.info(f"my time: {time_now}")
            for preset in settings:
                if len(preset.get("events")) < 1:
                    continue
                evs = []
                for ev in preset.get("events"):
                    if ev in text:
                        evs.append(ev)
                if len(evs) > 0:
                    if len(preset.get("medals")) > 0:
                        for m in preset.get("medals"):
                            if m in text:
                                output = f", {m}"
                    vals = ", ".join(evs)
                    if "24-часовое испытание" in text:
                        output = f"24-часовое испытание: {vals}{output}!"
                    else:
                        output = f"Адское событие: {vals}{output}!"
                    break
            send_to_thread(output, target_thread_id)       
            logger.info(f"Message prepared: {output}")
                
            # if any(t in mess.text for t in target_words):
            #     targets_in = [t for t in target_words if t in mess.text]

            #     if len(targets_in) == 1 and targets_in[0] in target_words[1:]:
            #         targets_in = [mess.text.split(" (")[0], targets_in[0]]
            #     targets_text = str.join(", ", targets_in)
            #     value = f"Адское событие: {targets_text}!"

            #     logger.info(f"Подготовлено сообщение: {value}")
            #     send_to_thread(value, target_thread_id)
        else:
            logger.error(f"The message is not in the timings: {mess.date}")

        await client.send_read_acknowledge(entity=chat, message=mess)
        logger.info("message processing completed")

    bot_helper_thread = threading.Thread(target=bot.polling, daemon=True)
    bot_helper_thread.start()

    async with client:
        me = await client.get_me()
        logger.info(f"lmBot running with name: {me.first_name}")
        logger.info("Wait message from channels...")
        
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"{e}")
        if "Connection to Telegram failed 5 time(s)" in e:
            time.sleep(5)
            logger.info("wait 5 seconds and restart")
            
