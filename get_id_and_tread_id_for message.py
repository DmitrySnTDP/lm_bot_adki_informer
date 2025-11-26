import telebot

def get_group_info(bot_token):
    """Получает информацию о группах (требует другой подход)"""
    bot = telebot.TeleBot(bot_token)
    
    # Для получения списка групп в telebot нужно использовать getUpdates
    # или заранее знать ID группы
    
    @bot.message_handler(content_types=['text'])
    def echo_all(message):
        print(f"Чат ID: {message.chat.id}")
        print(f"Название: {message.chat.title}")
        print(f"Тип: {message.chat.type}")
        print(f'tread id: {message.message_thread_id}')
    
    print("Отправьте сообщение боту чтобы получить ID чата...")
    bot.polling()


def test_bot_connection(bot_token, group_id, thread_id=None):
    """Тестирует подключение бота и отправку сообщений"""
    bot = telebot.TeleBot(bot_token)
    
    try:
        kwargs = {
            'chat_id': group_id,
            'text': '🤖 Тестовое сообщение от бота!'
        }
        
        if thread_id:
            kwargs['message_thread_id'] = thread_id
        
        bot.send_message(**kwargs)
        print("✅ Тест пройден - бот может отправлять сообщения")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
# test_bot_connection("your_token", -1001234567890, 123)
get_group_info("8361667826:AAEvpjEDAvk3_tf6VHNmZeGt-HGyeZJ5jLc")