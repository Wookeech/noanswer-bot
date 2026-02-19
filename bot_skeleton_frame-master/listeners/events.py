import asyncio
import logging
import os
from slack_sdk.web.async_client import AsyncWebClient as WebClient
from configs import config as cfg
from slack_utils.utils import (create_slack_incident_message, delete_slack_message,
                                update_slack_message,
                               get_slack_message, get_slack_channel_from_url,
                               archieve_incident_channel, unarchieve_incident_channel,
                               conversation_invite_users, get_user_id_by_mail, get_user_display_name_by_id)

logger = logging.getLogger(__name__)


async def handle_rc_message(message, say, client:WebClient):
    global jira_conn, samodelkin_bot, gmeet
    logger.info(f"\nrc_message\n\t\t:  {message}")
    channel_id = message.get("channel")
    logs_channel_id = await asyncio.to_thread(os.environ.get,"LOGS_SLACK_CHANNEL")
    if channel_id == logs_channel_id:
        metadata = message.get("metadata")
        logger.info(f"metadata: {metadata}")
        if metadata:
            if "event_payload" in metadata and "event_type" in metadata:
                slack_post_url = metadata["event_payload"].get("slack_post_url")

                if metadata["event_type"] == "task_created":
                    if not slack_post_url:  # Если создали в Jira не через Slack Workflow

                        metadata_new = await create_slack_incident_message(metadata, client, gmeet)
                        key = metadata["event_payload"].get("key")
                        if metadata_new:
                            if "event_payload" in metadata_new:
                                slack_post_url = metadata_new["event_payload"].get("slack_post_url")
                                if not key:
                                    key = metadata_new["event_payload"].get("key")
                                if slack_post_url and key:
                                    fields = {}
                                    fields[jira_conn.customfieldIDRhLink] = f'{slack_post_url}'
                                    try:
                                        pass
                                        # обновление инциента в Jira
                                        #res = await jira_conn.update_issue_async(issue_key=key, fields=fields)
                                    except Exception as e:
                                        logger.exception(e)

                        # update_slack_message(client, slack_post_url, metadata_new)
                        user_mail = metadata["event_payload"].get("creator_mail")
                        user_id = await get_user_id_by_mail(client, user_mail)
                        display_name = None
                        if user_id:
                            display_name = get_user_display_name_by_id(user_id)
                        metadata_new["event_payload"]["creator_mail"] = user_mail
                        metadata_new["event_payload"]["creator_display_name"] = display_name

                        channel_id = get_slack_channel_from_url(slack_post_url)
                        if channel_id:
                            await conversation_invite_users(client, channel_id, [cfg.SLACK_BOT_USER_ID])
                        await update_slack_message(client, slack_post_url, metadata_new)

                if metadata["event_type"] == "task_deleted":
                    logger.info(f"\n\n\t\tevent task_deleted:\n")
                    logger.info(f"\n\nslack_post_url:\n\t\t\t {slack_post_url}\n\t\t\t metadata: {metadata}")
                    if slack_post_url:
                        message, metadata_del = await get_slack_message(client, slack_post_url)
                        await unarchieve_incident_channel(client, channel_id, cfg.SLACK_BOT_TOKEN_USER)
                        if metadata_del:
                            if "event_payload" in metadata_del:
                                tg_msg_id = metadata_del["event_payload"].get("tg_msg_id")
                                tg_channel_id = metadata_del["event_payload"].get("tg_channel_id")
                                metadata_del["event_payload"]["status"] = "УДАЛЕН в JIRA"
                                logger.info(f"Delete task metadata_del: {metadata_del}")
                                logger.info(f"tg_msg_id: {tg_msg_id} tg_channel_id: {tg_channel_id}")
                                await update_slack_message(client, slack_post_url, metadata_del)
                                if tg_msg_id and tg_channel_id:
                                    # samodelkin_bot.delete_message(tg_channel_id, tg_msg_id)
                                    # await update_tg_message(samodelkin_bot, tg_msg_id, tg_channel_id, metadata_del)
                                    logger.info(f"\n\n\t\tUpdated: tg_msg_id: {tg_msg_id} tg_channel_id: {tg_channel_id}\n\n")

                        channel_id = get_slack_channel_from_url(slack_post_url)
                        logger.info(f"channel_id: {channel_id} will be archived.")
                        await archieve_incident_channel(client, channel_id, cfg.SLACK_BOT_TOKEN_USER)
                        # delete_slack_message(client, slack_post_url)

                if metadata["event_type"] == "task_updated":
                    logger.info(f"\nevent task_updated:\n\t\t\tslack_post_url: {slack_post_url}\n\n")
                    if slack_post_url:
                        key = metadata["event_payload"].get("key")
                        status = metadata["event_payload"].get("status")
                        priority = metadata["event_payload"].get("priority")
                        summary = metadata["event_payload"].get("summary")
                        team = metadata["event_payload"].get("team")
                        user_mail = metadata["event_payload"].get("creator_mail")
                        channel_id = get_slack_channel_from_url(slack_post_url)
                        logger.info(f"\nchannel_id:\n {channel_id} will be updated.\n")
                        if channel_id:
                            await conversation_invite_users(client, channel_id, [cfg.SLACK_BOT_USER_ID])

                        _, metadata_upd = await get_slack_message(client, slack_post_url)
                        if metadata_upd:
                            if "event_payload" in metadata_upd:
                                tg_msg_id = metadata_upd["event_payload"].get("tg_msg_id")
                                tg_channel_id = metadata_upd["event_payload"].get("tg_channel_id")

                                metadata_upd["event_payload"]["summary"] = summary
                                metadata_upd["event_payload"]["priority"] = priority
                                metadata_upd["event_payload"]["team"] = team
                                metadata_upd["event_payload"]["updater"] = metadata["event_payload"].get("updater")
                                metadata_upd["event_payload"]["status"] = status
                                metadata_upd["event_payload"]["key"] = key
                                metadata_upd["event_payload"]["slack_post_url"] = slack_post_url
                                if user_mail:
                                    logger.info(f"\n\n\n\t\tcreator_mail: {user_mail}\n\n\n")
                                    metadata_upd["event_payload"]["creator_mail"] = user_mail
                                    user_id = await get_user_id_by_mail(client, user_mail)
                                    if user_id:
                                        display_name = get_user_display_name_by_id(user_id)
                                        metadata_upd["event_payload"]["display_name"] = display_name

                                    logger.info(f"\n\n\n\t\tcreator_display_name: {display_name}\n\n\n")
                                statuses = ["done", "decline", "удалено в jira"]
                                if status.lower() in statuses:
                                    metadata_upd["event_payload"]["google_meet_link"] = None
                                await update_slack_message(client, slack_post_url, metadata_upd)
                                if tg_msg_id and tg_channel_id:
                                    # status = await update_tg_message(samodelkin_bot, tg_msg_id, tg_channel_id, metadata_upd)
                                    logger.info(f"Update_tg_message. status: {status}")
                                else:
                                    logger.warning(f"tg_msg_id: {tg_msg_id} or tg_channel_id: {tg_channel_id} is None")

                if metadata["event_type"] == "task_archive":
                    slack_post_url = metadata["event_payload"].get("slack_post_url")
                    channel_id = get_slack_channel_from_url(slack_post_url)
                    logger.info(f"channel_id: {channel_id} will be archived.")
                    await archieve_incident_channel(client, channel_id, cfg.SLACK_BOT_TOKEN_USER)

                if metadata["event_type"] == "task_unarchive":
                    slack_post_url = metadata["event_payload"].get("slack_post_url")
                    channel_id = get_slack_channel_from_url(slack_post_url)
                    logger.info(f"channel_id: {channel_id} will be unarchived.")
                    await unarchieve_incident_channel(client, channel_id, cfg.SLACK_BOT_TOKEN_USER)
                    await conversation_invite_users(client, channel_id, [cfg.SLACK_BOT_USER_ID])

async def handle_message_events(body, client: WebClient, logger):
    pass
    # if "event" in body:
    #     chan = body["event"].get("channel")
    #     if chan == cfg.LOGS_SLACK_CHANNEL:
    #         metadata = body["event"].get("metadata")
    #         if metadata:
                # if "event_payload" in metadata and "event_type" in metadata:
                #     slack_post_url = metadata["event_payload"].get("slack_post_url")
                #     if metadata["event_type"] == "task_created":
                #         if not slack_post_url: # Если создали в Jira не через Slack Workflow
                #             metadata_new = create_slack_incident_message(metadata, client, gmeet)
                #             key = metadata["event_payload"].get("key")
                #             if metadata_new:
                #                 if "event_payload" in metadata_new:
                #                     slack_post_url = metadata_new["event_payload"].get("slack_post_url")
                #                     if not key:
                #                         key = metadata_new["event_payload"].get("key")
                #                     if slack_post_url and key:
                #                         fields = {}
                #                         fields[jira_conn.customfieldIDRhLink] = f'{slack_post_url}'
                #                         try:
                #                             res = jira_conn.update_issue(issue_key=key,fields=fields)
                #                         except Exception as e:
                #                             logger.exception(e)
                #
                #             # update_slack_message(client, slack_post_url, metadata_new)
                #             tg_msg_id, tg_channel_id = create_tg_incident_message(metadata_new, samodelkin_bot)
                #             metadata_new["event_payload"]["tg_channel_id"] = tg_channel_id
                #             metadata_new["event_payload"]["tg_msg_id"] = tg_msg_id
                #             update_slack_message(client, slack_post_url, metadata_new)
                #
                #     if metadata["event_type"] == "task_deleted":
                #         if slack_post_url:
                #             message, metadata_del = get_slack_message(client, slack_post_url)
                #             if metadata_del:
                #                 if "event_payload" in metadata_del:
                #                     tg_msg_id = metadata_del["event_payload"].get("tg_msg_id")
                #                     tg_channel_id = metadata_del["event_payload"].get("tg_channel_id")
                #                     if tg_msg_id and tg_channel_id:
                #                         samodelkin_bot.delete_message(tg_channel_id, tg_msg_id)
                #             delete_slack_message(client,slack_post_url)
                #
                #     if metadata["event_type"] == "task_updated":
                #         status = None
                #         if slack_post_url:
                #
                #             key = metadata["event_payload"].get("key")
                #             status = metadata["event_payload"].get("status")
                #             priority = metadata["event_payload"].get("priority")
                #             summary = metadata["event_payload"].get("summary")
                #             team = metadata["event_payload"].get("team")
                #             _, metadata_upd = get_slack_message(client, slack_post_url)
                #             if metadata_upd:
                #                 if "event_payload" in metadata_upd:
                #                     tg_msg_id = metadata_upd["event_payload"].get("tg_msg_id")
                #                     tg_channel_id = metadata_upd["event_payload"].get("tg_channel_id")
                #
                #                     metadata_upd["event_payload"]["summary"] = summary
                #                     metadata_upd["event_payload"]["priority"] = priority
                #                     metadata_upd["event_payload"]["team"] = team
                #                     metadata_upd["event_payload"]["updater"] = metadata["event_payload"].get("updater")
                #                     metadata_upd["event_payload"]["status"] = status
                #                     metadata_upd["event_payload"]["key"] = key
                #                     metadata_upd["event_payload"]["slack_post_url"] = slack_post_url
                #
                #                     if status.lower() == "done":
                #                         metadata_upd["event_payload"]["google_meet_link"] = None
                #                     update_slack_message(client, slack_post_url, metadata_upd)
                #                     if tg_msg_id and tg_channel_id:
                #                         update_tg_message(samodelkin_bot, tg_msg_id, tg_channel_id, metadata_upd)

async def handle_reaction_added_events(body, logger):
    print(body)

async def handle_reaction_removed_events(body, logger):
    print(body)

