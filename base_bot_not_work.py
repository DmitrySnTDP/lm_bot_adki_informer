        # logger.info(f"ПОЛУЧЕН ПОСТ ИЗ КАНАЛА: {message.chat.title}")
        # logger.info(f"   Текст: {message.text or message.caption}")
        # if any(t in message.text for t in target_words):
        #     targets_in = [t for t in target_words if t in message.text]
        #     if len(targets_in) == 1 and targets_in[0] == target_words[-1]:
        #         targets_in = [message.text.split(" (")[0], targets_in[0]]
        #     value = f"Адское событие: {str.join(", ", targets_in)}!"
        #     send_to_thread(value, tread_id)
        #     logger.info(f"{value}")
        # # else:
        #     # logger.info(f"ПОЛУЧЕН ПОСТ ИЗ НЕОТСЛЕЖИВАЕМОГО КАНАЛА {message.chat.title}")
        # await app.read_chat_history(message.chat.id)



# with client:
#     client.loop.run_forever(main())

# async def main():
#     app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
    
#     @app.on_message(filters.channel and (filters.chat(target_ch_ids) or filters.chat(TARGET_CHANNELS)))
#     async def handle_channel_posts(client, message):
#         try:
#         # if message.chat.username in TARGET_CHANNELS:
#             logger.info(f"ПОЛУЧЕН ПОСТ ИЗ КАНАЛА: {message.chat.title}")
#             logger.info(f"   Текст: {message.text or message.caption}")
#             if any(t in message.text for t in target_words):
#                 targets_in = [t for t in target_words if t in message.text]
#                 if len(targets_in) == 1 and targets_in[0] == target_words[-1]:
#                     targets_in = [message.text.split(" (")[0], targets_in[0]]
#                 value = f"Адское событие: {str.join(", ", targets_in)}!"
#                 send_to_thread(value, tread_id)
#                 logger.info(f"{value}")
#             # else:
#                 # logger.info(f"ПОЛУЧЕН ПОСТ ИЗ НЕОТСЛЕЖИВАЕМОГО КАНАЛА {message.chat.title}")
#             await app.read_chat_history(message.chat.id)
#         except Exception as e:
#             print(f"Ошибка при обработке сообщения: {e}")
    
#     async with app:
#         me = await app.get_me()
#         logger.info(f"lmBot запущен как: {me.first_name}")
#         logger.info("Ожидаю сообщения из каналов...")
        
#         await asyncio.Future()