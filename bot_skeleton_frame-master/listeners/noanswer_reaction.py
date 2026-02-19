import logging
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from slack_bolt import Ack

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)   # ← важно!

# ================= НАСТРОЙКИ =================
REACTION_NAME = "no_mobile_phones"

SHEET_ID = "1EobzI5LgCTgxflqr5R3mkME5_CvGeBL--qFjq4gAvi0"   # ← айди таблицы
SHEET_NAME = "Лист1"                 # ← точно как называется лист

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

logger.info("✅ Обработчик noanswer_reaction.py загружен успешно")

async def handle_reaction_added(event, client, ack: Ack):
    logger.info(f"🔥 Получено событие reaction_added: {event}")
    await ack()

    reaction = event.get("reaction")
    logger.info(f"   Реакция: {reaction} (ожидаем: {REACTION_NAME})")

    if reaction != REACTION_NAME:
        logger.info("   Реакция не совпадает — выходим")
        return

    item = event.get("item", {})
    logger.info(f"   Item: {item}")

    if item.get("type") != "message":
        logger.info("   Это не реакция на сообщение — выходим")
        return

    channel_id = item["channel"]
    message_ts = item["ts"]

    try:
        logger.info(f"   Получаем сообщение из канала {channel_id}, ts={message_ts}")
        history = await client.conversations_history(
            channel=channel_id,
            latest=message_ts,
            limit=1,
            inclusive=True
        )
        message = history["messages"][0]
        text = message.get("text", "")
        logger.info(f"   Текст сообщения: {text}")

        # Ищем @упоминания
        mentions = re.findall(r'<@([A-Z0-9]+)>', text)
        logger.info(f"   Найдено упоминаний: {mentions}")

        if not mentions:
            logger.warning("   Нет @упоминаний — выходим")
            return

        tagged_user_id = mentions[0]
        logger.info(f"   Тегнутый пользователь: {tagged_user_id}")

        user_info = await client.users_info(user=tagged_user_id)
        full_name = user_info["user"]["profile"]["real_name_normalized"]
        logger.info(f"   ФИО: {full_name}")

        permalink_resp = await client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
        permalink = permalink_resp["permalink"]
        logger.info(f"   Ссылка: {permalink}")

        reaction_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = [reaction_time, full_name, permalink]
        sheet.append_row(row, value_input_option="RAW")
        logger.info(f"✅ УСПЕШНО записано в таблицу: {row}")

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)