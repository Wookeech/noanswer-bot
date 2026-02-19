import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials


async def handle_reaction_added_events(body, client, logger):
    """
    Обрабатывает реакцию no_mobile_phones и записывает данные в Google Таблицу.
    Работает и на обычных сообщениях, и на сообщениях в тредах.
    """
    try:
        event = body["event"]
        reaction = event.get("reaction")

        # Проверяем, наша ли реакция
        if reaction != "no_mobile_phones":
            return

        logger.info("🎯 Сработала нужная реакция: no_mobile_phones")

        item = event["item"]
        channel_id = item["channel"]
        message_ts = item["ts"]

        # === Получаем текст сообщения (работает и для топ-левел, и для тредов) ===
        # Сначала пробуем через history
        result = await client.conversations_history(
            channel=channel_id,
            latest=message_ts,
            limit=1,
            inclusive=True
        )
        messages = result.get("messages", [])

        if not messages:
            # Если не нашли — это сообщение внутри треда
            result = await client.conversations_replies(
                channel=channel_id,
                ts=message_ts,
                limit=1
            )
            messages = result.get("messages", [])

        if not messages:
            logger.warning("⚠️ Сообщение не найдено")
            return

        message = messages[0]
        text = message.get("text", "")

        # === Находим первого тегнутого (@...) ===
        mentions = re.findall(r"<@([A-Z0-9]+)>", text)
        user_id = mentions[0] if mentions else event.get("item_user")

        # === Получаем ФИО ===
        user_info = await client.users_info(user=user_id)
        profile = user_info["user"].get("profile", {})
        fio = (
            profile.get("real_name_normalized") or
            profile.get("real_name") or
            user_info["user"].get("real_name") or
            user_info["user"]["name"]
        )

        # === Ссылка на сообщение (РУЧНАЯ — без chat:read) ===
        # Работает идеально и для обычных сообщений, и для треда
        permalink = f"https://1win.slack.com/archives/{channel_id}/p{message_ts.replace('.', '')}"

        # === Время реакции ===
        reaction_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        logger.info(f"📝 Записываем → {fio} | {permalink}")

        # === Запись в Google Таблицу ===
        creds_path = "slack-noanswer-bot-46b2c0893952.json"   # ← файл должен быть В КОРНЕ проекта
        spreadsheet_id = "1EobzI5LgCTgxflqr5R3mkME5_CvGeBL--qFjq4gAvi0"

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("Лист1")   # ← точное название листа

        worksheet.append_row([reaction_time, fio, permalink])

        logger.info("✅ УСПЕШНО записано в Google Таблицу!")

    except Exception as e:
        logger.error(f"❌ ОШИБКА при обработке реакции: {e}")
        logger.exception(e)
