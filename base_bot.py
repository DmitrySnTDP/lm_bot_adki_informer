import asyncio
from datetime import datetime, timedelta, timezone
import os
import threading
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
# import logging
import telebot
from random import randint
from database import Database, logger


bot_helper_thread = None

load_dotenv("ini.env")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
session_name = os.getenv("USER_SESSION_NAME")

if not all([api_id, api_hash, bot_token, session_name]):
    raise ValueError("API_ID and API_HASH must be set in the .env file.")

target_ch_ids = [-1001336280776, -1002155382308]


base_wait_time = 15
wait_time = 15


bot = telebot.TeleBot(bot_token)

verify_group_codes = dict()
user_evs_cache = dict()
group_name_cahce = dict()


def create_stop_markup(message, user_id=None):
    if user_id == None:
        user_id = message.from_user.id
    targets = bot_db.execute_query("select GroupName from GroupTarget where ? = UserID", (user_id,))
    is_active_local_target = bot_db.execute_query("select IsActive from LocalTarget where UserID = ?", (user_id,))

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    if len(is_active_local_target) != 0:
        is_active = False if len(is_active_local_target) == 0 else is_active_local_target[0][0]
        markup.add(
        telebot.types.InlineKeyboardButton(f"Личные сообщения {"✅" if is_active else "❌"}", callback_data="stop_target_pm"),
    )
    for target in targets:
        group_name = target[0]
        db_res_is_active = bot_db.execute_query("select IsActive from GroupTarget where GroupName = ?", (group_name,))
        is_active = False if len(db_res_is_active) == 0 else db_res_is_active[0][0]
        group_id = bot_db.execute_query("select GroupID from GroupTarget where GroupName = ?", (group_name,))[0][0]
        markup.add(
            telebot.types.InlineKeyboardButton(f"{group_name if len(group_name) < 33 else group_name[:33]+"..."} {"✅" if is_active else "❌"}", callback_data=f"stop_target_group__{group_id}")
        )
    markup.add(
        telebot.types.InlineKeyboardButton("В меню", callback_data="close_menu")
    )
    return markup


def create_remove_markup(message, user_id=None):
    if user_id == None:
        user_id = message.from_user.id
    targets = bot_db.execute_query("select GroupName from GroupTarget where ? = UserID", (user_id,))
    local_target = bot_db.execute_query("select LTargetID from LocalTarget where UserID = ?", (user_id,))

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    if len(local_target) != 0:
        markup.add(
        telebot.types.InlineKeyboardButton(f"Личные сообщения", callback_data="remove_target_pm"),
    )
    for target in targets:
        group_name = target[0]
        group_id = bot_db.execute_query("select GroupID from GroupTarget where GroupName = ?", (group_name,))[0][0]
        markup.add(
            telebot.types.InlineKeyboardButton(f"{group_name if len(group_name) < 33 else group_name[:33]+"..."}", callback_data=f"remove_target_group__{group_id}")
        )
    markup.add(
        telebot.types.InlineKeyboardButton("В меню", callback_data="close_menu")
    )
    return markup


def create_evs_markup(message, target_id, user_id=None):
    if user_id == None:
        user_id = message.from_user.id
    evs = [ev[0] for ev in bot_db.execute_query("select EventName from EventType")]
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    for ev in evs:        
        markup.add(
            telebot.types.InlineKeyboardButton(f"{ev}{"✅" if user_evs_cache.get(user_id) != None and ev in user_evs_cache.get(user_id)[1] else ""}", callback_data=f"add_us__{ev}__{target_id}")
        )
    markup.add(
        telebot.types.InlineKeyboardButton("Сохранить", callback_data=f"save_evs_med_preset__{target_id}")
    )

    return markup


def process_connection_code(message, user_id):
    chat_id = message.chat.id
    input_text = message.text.strip()
    
    if not input_text.isdigit():
        msg = bot.send_message(
            chat_id,
            "Некорректный ввод, попробуйте ещё раз:",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_connection_code, user_id)
        return
    
    check_verify_code(int(input_text), message)


def check_verify_code(code, local_message):
    if code in verify_group_codes.keys():
        group_message = verify_group_codes[code]
        verify_group_codes.pop(code)
        group_name_cahce[group_message.chat.id] = group_message.chat.title

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("Да", callback_data=f"complete_add_bot__{group_message.chat.id}__{group_message.message_thread_id}"),
            telebot.types.InlineKeyboardButton("Нет", callback_data=f"bot_is_add_in_group__{group_message.chat.id}")
        )
        theme_info = ""
        if group_message.chat.is_forum:
            if group_message.reply_to_message != None:
                theme_info = f"вкл\nИмя темы: {group_message.reply_to_message.forum_topic_created.name}"
            else:
                theme_info = f"вкл\nИмя темы: #General"
        else:
            theme_info = "выкл"

        bot.send_message(
            chat_id=local_message.chat.id,
            message_thread_id=local_message.message_thread_id,
            text=f"Группа найдена! Информация о ней:\nНазвание: {group_message.chat.title}\nТемы: {theme_info}\nВерно?",
            reply_markup=markup
        )
    else:
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("Повторить", callback_data="bot_is_add_in_group__"),
            telebot.types.InlineKeyboardButton("В меню", callback_data="close_menu")
        )
        bot.send_message(
            chat_id=local_message.chat.id,
            message_thread_id=local_message.message_thread_id,
            text="Неверный или неактуальный код, попробуйте отправить команду в группе заново.",
            reply_markup=markup
        )


@bot.message_handler(commands=["start"])
def send_start_message(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Привет! Я могу отправлять уведомления об адских и 24-часовых событиях тебе лично в этом чате или в группу на основе твоих предпочтений. Чтобы узнать о всех возможностях отправь команду /help.",
        )


@bot.message_handler(commands=["stop_continue_target"])
def stop_continue_target(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Выберите цель уведомлений, которую хотите остановить или запустить:",
            reply_markup=create_stop_markup(message)
        )

@bot.message_handler(commands=["add_target"])
def clear_user_data(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("В личный чат (здесь)", callback_data="add_target_local"),
            telebot.types.InlineKeyboardButton("В группу", callback_data="add_target_group")
        )
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Куда вы хотите подключить уведомления?",
            reply_markup=markup
        )


@bot.message_handler(commands=["remove_target"])
def remove_target(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id
        
        bot.send_message(
            text="Нажмите на цели, которые хотите <b>безвозвратно</b> удалить:",
            chat_id=chat_id,
            message_thread_id=thread_id,
            reply_markup=create_remove_markup(message),
            parse_mode="HTML",
        )


@bot.message_handler(commands=["clear_data"])
def clear_user_data(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            telebot.types.InlineKeyboardButton("Удалить", callback_data="delete_user_data"),
            telebot.types.InlineKeyboardButton("Отмена", callback_data="close_menu")
        )

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Вы действительно хотите удалить все данные об уведомлених для вас? Это необратимое действие!",
            reply_markup=markup
        )


@bot.message_handler(commands=["link_group"])
def connect_group(message):
    if message.chat.type == "supergroup" or "group":
        text = ""
        if len(bot_db.execute_query("select IsActive from GroupTarget where GroupID = ?", (message.chat.id,))) < 1:
            new_code = randint(1000,9999)
            while new_code in verify_group_codes.keys():
                new_code = randint(1000, 9999)
            verify_group_codes[new_code] = message
            text=f"Код привязки группы: <code>{new_code}</code>"
        else:
            text = "Уведомления для этой группы уже были подключены одним из участников."
        
        bot.send_message(
            text=text,
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            parse_mode="HTML"
        )


@bot.message_handler(commands=["help"])
def send_start_message(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=
"""Мои команды:
1️⃣ /help - открывает описание функционала
2️⃣ /stop_continue_target -  Остановить или возобновить уведомления для любой из целей
3️⃣ /add_target - Добавить новую цель уведомлений
4️⃣ /settings - настроить фильтры для уведомлений определённой цели 
5️⃣  /remove_target - удалить цель из профиля 
6️⃣ /clear_data - удалить все данные пользователя из бота
⚙️ Принцип работы настроек:
1️⃣ Вызвать команду /settings и выбираем нужную цель.
2️⃣ В появившемся меню выбираем "Настроить события" для детального выбора событий или "По умолчанию", чтобы вернуть стандартные настройки.
➡️ Далее описание принципа работы детальных настроек.
3️⃣ После выбора детальных настроек, появляется меню выбора медали (стражник, мастер огня или без медалей).
4️⃣ После выбора, откроется меню со списком видов событий (пакты, охота, исследования и т.д.), нажимаем все необходимые варианты, после чего нажимаем сохранить.
❕❕❕Пример работы:
вызвали /settings ➡️
выбрали Личные сообщения ➡️
нажали Настроить события ➡️
Стражник ➡️
Артефакты, Пакты, Стройка ➡️
Сохранить.
Эта комбинация включит уведомления в Личные сообщения для событий на артефакты или пакты или стройки, содержащие медали стражника.
5️⃣ Повторить для всех видов медалей при необходимости.
6️⃣ Теперь можно закрыть настройки.
❗️ выбор параметра по умолчанию настраивает уведомления так: все события с медалями + артефакты без медалей""",
    )


@bot.message_handler(commands=["settings"])
def handle_panel_settings(message):
    if message.chat.type == "private":
        chat_id = message.chat.id
        thread_id = message.message_thread_id
        user_id = message.from_user.id

        targets = bot_db.execute_query("select GroupName from GroupTarget where ? = UserID", (user_id,))
        group_ids = bot_db.execute_query("select GroupID from GroupTarget where ? = UserID", (user_id,))
        local_target = bot_db.execute_query("select LTargetID from LocalTarget where UserID = ?", (user_id,))

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        if len(local_target) != 0:
            markup.add(
            telebot.types.InlineKeyboardButton(f"Личные сообщения", callback_data=f"setting_target__"),
        )
        for i in range(len(targets)):
            group_name = targets[i][0]
            markup.add(
                telebot.types.InlineKeyboardButton(f"{group_name if len(group_name) < 32 else group_name[:33]+"..."}", callback_data=f"setting_target__{group_ids[i][0]}")
            )
        markup.add(
            telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu")
        )

        bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text="Выберите цель, которую хотите настроить:",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("setting_target__"))
def set_target_group(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    values = call.data.split("__")
    if values[-1] =="":
        target_id = user_id
        target = "Личные сообщения"
    else:
        target_id = values[-1]
        target = bot_db.execute_query("select GroupName from GroupTarget where GroupID = ?", (target_id,))[0][0]

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Настроить события", callback_data=f"notification_setting__{target_id}{"__u" if values[-1] == "" else ""}"), #set_evs_medal
        telebot.types.InlineKeyboardButton("По умолчанию", callback_data=f"set_default__{target_id}{"__u" if values[-1] == "" else ""}"), #"set_default"
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu"),
    )

    bot.edit_message_text(
        text=f"Выберите, как нужно настроить цель {target}:",
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("set_default__"))
def set_default(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    values = call.data.split("__")
    is_user = len(values) == 3
    target_id = values[1]
    target = "Личные сообщения" if is_user else bot_db.execute_query("select GroupName from GroupTarget where GroupID = ?", (target_id,))[0][0]
    if is_user:
        user_id = call.from_user.id
        bot_db.execute_procedure("ResetLocalTargetToDefault", user_id)
    else:
        bot_db.execute_procedure("ResetGroupTargetToDefault", target_id)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu"),
    )
    bot.edit_message_text(
        text=f"Для {target} установлены настроки по умолчанию!",
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("notification_setting__"))
def set_medal(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    values = call.data.split("__")
    is_user = len(values) == 3
    target_id = values[1]

    medal_list = [med[0] for med in bot_db.execute_query("select MedName from Medal")]
    medal_ids = [med_id[0] for med_id in bot_db.execute_query("select MedID from Medal")]

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    buttons = [telebot.types.InlineKeyboardButton(medal_list[i] if medal_list[i]!="" else "Без медалей", callback_data=f"set_evs_medal__{medal_ids[i]}__{target_id}{"__u" if is_user else ""}") for i in range(len(medal_list))]
    for b in buttons:
        markup.add(b)
    bot.edit_message_text(
        text="Выберите нужную медаль:",
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )
    

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_evs_medal__"))
def set_evs_for_medal(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    values = call.data.split("__")
    if len(values) >= 3:
        user_evs_cache[user_id] = [values[1], []]
        target_id = values[2]
    medal_name = bot_db.execute_query("select MedName from Medal where MedID = ?", (values[1]))[0][0]
    select_medal = medal_name if medal_name !="" else "Без медалей"

    new_markup = create_evs_markup(call.message, target_id, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_text(
                    text=f"Выберите нужные события для {select_medal}, а затем нажмите \"Сохранить\"",
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_us__"))
def add_evs_to_user(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    ev, target_id = call.data.split("__")[1:]
    if user_evs_cache.get(user_id) != None:
        if ev not in user_evs_cache.get(user_id)[1]:
            user_evs_cache[user_id][1].append(ev)
        else:
            user_evs_cache[user_id][1].remove(ev)
    else:
        user_evs_cache[user_id] = ["",[ev]]

    new_markup = create_evs_markup(call.message, target_id, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise


@bot.callback_query_handler(func=lambda call: call.data.startswith("save_evs_med_preset__"))
def save_evs_preset(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    target_id = call.data.split("__")[1]
    medal_id = user_evs_cache.get(user_id)[0]
    evs = user_evs_cache.get(user_id)[1]
    user_evs_cache.pop(user_id)
    tvp_data = [bot_db.execute_query("select EventID from EventType where EventName = ?", (ev,))[0] for ev in evs]
    select_medal = bot_db.execute_query("select MedName from Medal where MedID = ?", (medal_id,))[0][0]
    if select_medal == "":
        select_medal = "Без медалей"
    if target_id == str(user_id):
        bot_db.execute_procedure("SetLocalTargetSettings", user_id, medal_id, tvp_data)
        target_name = "Личные сообщения"
    else:
        bot_db.execute_procedure("SetGroupTargetSettings", target_id, medal_id, tvp_data)
        target_name = bot_db.execute_query("select GroupName from GroupTarget where GroupID = ?", (target_id,))[0][0]
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Вернуться к настройке цели", callback_data=f"notification_setting__{target_id}"),
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu")
    )
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=f"Настройки {select_medal} для {target_name} сохранены!",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "add_target_local")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu")
    )
    if len(bot_db.execute_query("select 1 from LocalTarget where UserID = ?", (user_id,))) == 0:
        if len(bot_db.execute_query("select 1 from Users where UserID = ?", (user_id,))) == 0:
            bot_db.execute_edit_query("insert into Users (UserID) values (?)", (user_id,))
        bot_db.execute_edit_query("insert into LocalTarget (UserID) values (?)", (user_id,))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text = "Уведомления успешно подключены! Чтобы изменить их перейдите в настройки. Чтобы приостановить или посмотреть их статус уведомлений откройте .",
            reply_markup=markup,
        )
    else:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text = "Уведомления для этой цели уже были добавлены ранее.",
            reply_markup=markup,
        )


@bot.callback_query_handler(func=lambda call: call.data == "add_target_group")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Продолжить", callback_data="continue_add_target_group")
    )
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text = "Примечание! Чтобы подключить уведомления в группу, вы должны иметь роль администратора и право добавлять участников! После подключения уведомлений, их настройка выполняется только вами в этом личном чате с ботом!",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("complete_add_bot__"))
def adding_bot_in_profile(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    group_chat_id, group_thread_id = call.data.split("__")[1:]
    group_name = group_name_cahce[int(group_chat_id)]
    group_name_cahce.pop(int(group_chat_id))

    user_id = call.from_user.id
    is_forum = group_thread_id != "None"
    text = ""

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu")
    )
    if len(bot_db.execute_query("select 1 from Users where UserID = ?", (user_id,))) == 0:
        bot_db.execute_edit_query("insert into Users (UserID) values (?)", (user_id,))
    if len(bot_db.execute_query("select 1 from GroupTarget where GroupID = ?", (group_chat_id,))) == 0:
        if is_forum:
            bot_db.execute_edit_query(
                "insert into GroupTarget (GroupID, UserID, IsSuperGroup, ThemeID, GroupName) values (?,?,?,?,?)",
                (group_chat_id, user_id, is_forum, group_thread_id, group_name,)
            )
        else:
            bot_db.execute_edit_query(
                "insert into GroupTarget (GroupID, UserID, IsSuperGroup, GroupName) values (?,?,?,?)",
                (group_chat_id, user_id, is_forum, group_name,)
            )
        text = "Уведомления успешно подключены! Чтобы изменить их перейдите в настройки. Чтобы приостановить или посмотреть их статус уведомлений откройте."
    else:
        text = "Уведомления для этой группы уже были добавлены ранее."
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text = text,
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "continue_add_target_group")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Готово", callback_data="bot_is_add_in_group__")
    )
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text = "Добавьте меня в нужную группу.",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("bot_is_add_in_group__"))
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    if len(call.data.split("__")) > 1:
        group_id = call.data.split("__")[1]
        if group_name_cahce.get(group_id) != None:
            group_name_cahce.pop(group_id)

    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id, timeout=5)
    except:
        logger.error(f"can't delete message: {message_id}, from chat: {chat_id}")
        
    msg = bot.send_message(
        chat_id,
        text = "Отправьте в группе (или нужной теме группы, если они включены) команду /link_group. В нужное место бот отправит код подключения, который укажите здесь:"
    )
    bot.register_next_step_handler(msg, process_connection_code, user_id)


@bot.callback_query_handler(func=lambda call: call.data == "delete_user_data")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    bot_db.execute_edit_query("delete from LocalTarget where UserID = ?", (user_id,))
    bot_db.execute_edit_query("delete from GroupTarget where UserID = ?", (user_id,))
    bot_db.execute_edit_query("delete from Users where UserID = ?", (user_id,))
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("Закрыть", callback_data="close_menu")
    )
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text = "Готово! Информация о ваших источниках полностью удалена.",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_target_group__"))
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    bot_db.execute_edit_query("update GroupTarget set IsActive = ~IsActive where GroupID = ?", (call.data.split("__")[-1],))

    new_markup = create_stop_markup(call.message, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise


@bot.callback_query_handler(func=lambda call: call.data == "stop_target_pm")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    bot_db.execute_edit_query("update LocalTarget set IsActive = ~IsActive where UserID = ?", (user_id,))

    new_markup = create_stop_markup(call.message, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_target_group__"))
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    group_name = bot_db.execute_query("select GroupName from GroupTarget where GroupID = ?", (call.data.split("__")[-1],))[0][0]
    bot_db.execute_edit_query("delete from GroupTarget where GroupID = ?", (call.data.split("__")[-1],))

    new_markup = create_remove_markup(call.message, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise
    
        bot.answer_callback_query(call.id, text=f"Удалена цель: {group_name}")


@bot.callback_query_handler(func=lambda call: call.data == "remove_target_pm")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    bot_db.execute_edit_query("delete from LocalTarget where UserID = ?", (user_id,))

    new_markup = create_remove_markup(call.message, user_id)

    if new_markup and call.message.reply_markup:
        if call.message.reply_markup.to_dict() != new_markup.to_dict():
            try:
                bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=new_markup
                )
                bot.answer_callback_query(call.id, text=f"Удалена цель: Личные сообщения")
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise


@bot.callback_query_handler(func=lambda call: call.data == "close_menu")
def handle_text_input(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id, timeout=5)
    except:
        logger.error(f"can't delete message: {message_id}, from chat: {chat_id}")


async def send_messages(medal: str, evs: list, text: str):
    medal_id = bot_db.execute_query("select MedID from Medal where MedName = ?", (medal,))[0][0]
    for ev in evs:
        ev_id = bot_db.execute_query("select EventID from EventType where EventName = ?", (ev,))[0][0]
        targets = bot_db.query_procedure("GetTargetsByMedalAndEvent", medal_id, ev_id)
        if len(targets) < 1:
            return
        for target in targets:
            target_type = target[0]
            target_id = target[1]
            if target_type == "Local":
                thread_id = None
            else:
                thread_id = bot_db.execute_query("select ThemeID from GroupTarget where GroupID = ?", (target_id,))[0][0]
            bot.send_message(
                text=text,
                chat_id=target_id,
                message_thread_id=thread_id
            )



def run_bot_with_retry(timewait = 1):
    while True:
        try:
            logger.info("Telebot is running")
            bot.polling(
                non_stop=False,
                interval=3,
                timeout=60,
                long_polling_timeout=50
            )
            
        except Exception as e:
            logger.error(f"Error in telebot: {e}")
            logger.warning(f"Restart telebot after {timewait} sec timeout")
            time.sleep(timewait)


# client = TelegramClient(session_name, api_id, api_hash, connection_retries = 0, auto_reconnect = False, timeout=30, request_retries=3)

async def main():
    global restart_count, client, bot_helper_thread


    if client == None:
        client = TelegramClient(
            session_name,
            api_id,
            api_hash,
            connection_retries = 0,
            auto_reconnect = False,
            timeout=30,
            request_retries=3,
            device_model='iPhone 13 Pro Max',
            system_version='15.0',
            app_version='12.7.0',
            lang_code='en',
            system_lang_code='en'
        )
    
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
            medals_list = [m[0].lower() for m in  bot_db.execute_query("select MedName from Medal") if m[0] != ""]
            evs = bot_db.execute_query("select EventName from EventType")
            searched_medal = ""
            searched_evs = []

            for medal in medals_list:
                if medal in text:
                    searched_medal = medal
            for ev in evs:
                ev = ev[0]
                if ev in text:
                    searched_evs.append(ev)

            output = ""
            if "24-часовое испытание" in text:
                    output = f"24-часовое испытание: "
            else:
                output = f"Адское событие: "
            vals = ", ".join(searched_evs + [searched_medal.upper()])
            output += f"{vals}"

            await send_messages(searched_medal, searched_evs, output)
        
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
            client = None


if __name__ == "__main__":
    client = None
    max_restart_count = 120
    restart_count = 0
    bot_db = Database()
    bot_helper_thread = threading.Thread(target=run_bot_with_retry, daemon=True,)
    bot_helper_thread.start()
    while restart_count < max_restart_count:
        try:
            if restart_count == 0:
                logger.info("start")
            else:
                logger.info("restart")
            
            asyncio.run(main())
            asyncio.Future()
            
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break
        except (ConnectionError, ConnectionAbortedError, ConnectionResetError, TimeoutError) as e:
            logger.error(f"connection error: {e}")
            restart_count += 1
            wait_time = min(base_wait_time*restart_count, 600)
            logger.warning(f"wait {wait_time} seconds and restart")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"unknown err: {e}")
            restart_count += 1
            wait_time = min(base_wait_time*restart_count, 600)
            logger.warning(f"wait {wait_time} seconds and restart")
            time.sleep(wait_time)
        finally:
            client = None
bot_db.close()