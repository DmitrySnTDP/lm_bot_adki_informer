import asyncio
import logging
from pyrogram import Client


API_ID = 36470021
API_HASH = 'aaeaf27aa86d03212c47b90bb01783c7'
SESSION_NAME = 'usertest_session'

TARGET_CHANNELS = ['@LmNewsEx']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def diagnose_session_issue():
    """Диагностика проблем с сессиями"""
    app = Client("diagnose", api_id=API_ID, api_hash=API_HASH)
    
    async with app:
        # Проверяем базовую функциональность
        me = await app.get_me()
        logger.info(f"✅ Авторизация: {me.first_name}")
        
        # Проверяем доступ к каналу
        try:
            chat = await app.get_chat(TARGET_CHANNELS[0])
            logger.info(f"✅ Доступ к каналу: {chat.title}")
            
            # Пытаемся получить последние сообщения
            async for message in app.get_chat_history(chat.id, limit=1):
                [print(chat.id, chat.username, chat.title)]
                logger.info(f"✅ Чтение сообщений: доступно")
                
        except Exception as e:
            logger.error(f"❌ Ошибка доступа: {e}")
            return False
        
        # logger.info("🔍 Диагностика завершена. Если сообщения не приходят:")
        # logger.info("   1. Закройте Telegram на других устройствах")
        # logger.info("   2. Убедитесь, что канал публичный или вы участник")
        # logger.info("   3. Попробуйте использовать ID канала вместо @username")
        
        return True

asyncio.run(diagnose_session_issue())