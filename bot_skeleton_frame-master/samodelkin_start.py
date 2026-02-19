import logging
import os
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from slack_bolt.async_app import AsyncApp

from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from configs import config as cfg
from listeners import register_listeners

from slack_utils.utils import get_all_users, get_user_id_by_mail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




# Инициализация Slack Bolt
app = AsyncApp(token=cfg.SLACK_BOT_TOKEN)

# функция регистрации
register_listeners(app)

# Флаги для проб кубера
startup_complete = False
ready = False


# Запуск внутри FastAPI/ Немного избыточно, так как нужен только для веб ответов куберу
@asynccontextmanager
async def lifespan(api:FastAPI):
    """Контролирует жизненный цикл FastAPI (startup + shutdown)"""
    global startup_complete, ready, jira_conn, samodelkin_bot, gmeet, app
    logger.info("⏳ Запуск приложения...")
    startup_complete = True


    # Запуск Slack Socket Mode в фоне
    # почитать по Slack Socket Mode
    # И про асинхронность в Python/

    try:
        handler = AsyncSocketModeHandler(app, cfg.SLACK_APP_TOKEN)
        # Запускаем Slack SocketMode в отдельной задаче
        task = asyncio.create_task(handler.start_async())  # Запуск асинхронной задачи через create_task
    except Exception as e:
        logger.error(f"Бот не стартовал {e}")
    try:
        auth_info = await app.client.auth_test()
        # на версии для developers поймал баг, бот ходит под другой team_id,  {user["last_name"]}где ему не хватает прав
        if auth_info.get("ok"):
            cfg.SLACK_TEAM_ID = auth_info.get("team_id")
            cfg.SLACK_BOT_USER_ID = auth_info.get("user_id")
        # сохраним данные всех пользователей, чтобы не дергать каждый раз
        # в полной версии идет обновление этих данных по шедулеру
        cfg.USER_LIST = await get_all_users(app.client, team_id=cfg.SLACK_TEAM_ID, token=cfg.SLACK_BOT_TOKEN)
    except Exception as e:
        logger.error("Проверьте токены бота")
        logger.error(f"{e}")
    ready = True
    logger.info("Приложение запущено!")
    yield  # FastAPI продолжает работать здесь
    # Завершение работы
    logger.info("Завершение работы приложения...")
    ready = False

    # Ждем завершения задачи Slack-бота перед выходом
    await task
    logger.info("Slack-бот завершил свою работу")


# FastAPI приложение с использованием lifespan
api = FastAPI(lifespan=lifespan)


@api.get("/healthz")
async def liveness_probe():
    """ Liveness Probe: Проверяет, жив ли сервер """
    return {"status": "alive"}

@api.get("/ready")
async def readiness_probe():
    """ Readiness Probe: Готов ли сервер к приёму трафика? """
    if ready:
        return {"status": "ready"}
    return {"status": "not ready"}, 503

@api.get("/startup")
async def startup_probe():
    """ Startup Probe: Завершился ли запуск сервера? """
    if startup_complete:
        return {"status": "started"}
    return {"status": "starting"}, 503