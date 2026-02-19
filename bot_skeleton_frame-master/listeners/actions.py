import asyncio
import logging
from json.encoder import encode_basestring
from slack_sdk.web.async_client import AsyncWebClient as WebClient
from slack_bolt.async_app import AsyncAck, AsyncBoltContext
from configs import config as cfg
from slack_utils.utils import (get_blocks_form_value_by_action_id, get_dict_key,
                               update_slack_message, create_slack_incident_message,
                               get_user_display_name_by_id)
from slack_utils.message_formatters import  parse_rich_text_values_users



logger = logging.getLogger(__name__)

async def handle_add_incident_submission_events(ack: AsyncAck, body: dict, context: AsyncBoltContext,
    client: WebClient, logger: logging.Logger):
    global jira_conn, samodelkin_bot, gmeet
    await ack()
    logger.debug("add_incident_submit")
    logger.debug(body)
    workflow_step_conf_data = body["function_data"]["inputs"]
    values_dict = body["view"]["state"]["values"]
    # logger.debug(values_dict)
    # logger.debug(context.values())
    # logger.debug(context.inputs)

    slack_channel_id = get_dict_key(workflow_step_conf_data, "slack_channel_id")
    cfg.SlACK_CHANNEL_ID = slack_channel_id
    create_slack_channel = get_dict_key(workflow_step_conf_data, "create_slack_channel")
    cfg.SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL = create_slack_channel
    tg_channel_id = get_dict_key(workflow_step_conf_data, "tg_channel_id")
    cfg.TG_CHANNEL_ID = tg_channel_id
    users_notify_default_raw = get_dict_key(workflow_step_conf_data, "users_notify")
    users_notify_P1_raw = get_dict_key(workflow_step_conf_data, "users_notify_P1")
    users_notify_P2_raw = get_dict_key(workflow_step_conf_data, "users_notify_P2")
    user_started_flow_id = get_dict_key(workflow_step_conf_data, "user_started_flow")
    is_google_meet_link = get_dict_key(workflow_step_conf_data, "google_meet_link")
    cfg.CREATE_GOOGLE_MEET_LINK = is_google_meet_link

    # user_started_flow_from_context_id = context.actor_user_id
    # user_started_flow_from_context_id2 = context.user_id
    user_started_flow = None
    try:
        user_started_flow = await client.users_info(user=user_started_flow_id)
        user_started_flow = user_started_flow["user"]
    except Exception as e:
        logger.exception(e)
    logger.info("\n\n\n\t\t\t\thandle_add_incident_submission_events\n\n\n")
    # Ниже не получает профиль с ошибкой нет прав доступа, какой-то баг Bolt Api
    # так как клиент обращается не с тем токеном, который указан в конфигах
    # user_started_flow2 = client.users_profile_get(user=user_started_flow_id,)

    summary = get_blocks_form_value_by_action_id(values_dict, "action_id_summary")
    priority = get_blocks_form_value_by_action_id(values_dict, "action_id_priority")
    team = get_blocks_form_value_by_action_id(values_dict, "action_id_team")
    users_notify_default_ids = parse_rich_text_values_users(users_notify_default_raw)
    cfg.SLACK_USERS_NOTIFY = users_notify_default_ids
    users_notify_P1_ids = parse_rich_text_values_users(users_notify_P1_raw)
    cfg.SLACK_USERS_NOTIFY_P1 = users_notify_P1_ids
    users_notify_P2_ids = parse_rich_text_values_users(users_notify_P2_raw)
    cfg.SLACK_USERS_NOTIFY_P2 = users_notify_P2_ids

    metadata_init = {
        "event_type": "task_creating",
        "event_payload":
            {
            "users_notify": users_notify_default_ids,
            "users_notify_P1": users_notify_P1_ids,
            "users_notify_P2": users_notify_P2_ids,
            "priority": priority,
            "team": team,
            "creator": user_started_flow_id,
            "creator_info": user_started_flow,
            "summary": summary
            }
    }

    metadata_new = await create_slack_incident_message(metadata_init, client, gmeet)
    issue = None
    google_meet_link = None
    slack_post_url = None
    if metadata_new.get("event_payload"):
        google_meet_link = metadata_new["event_payload"].get("google_meet_link")
        slack_post_url = metadata_new["event_payload"].get("slack_post_url")
        metadata_new["event_payload"]["creator_info"] = user_started_flow
        key = metadata_new["event_payload"].get("key")
        status = metadata_new["event_payload"].get("status")

        display_name = get_user_display_name_by_id(user_started_flow_id)
        if display_name:
            metadata_new["event_payload"]["creator_display_name"] = display_name

        # tg_msg_id, tg_channel_id = await create_tg_incident_message(metadata_new, samodelkin_bot)
        tg_msg_id = None
        tg_channel_id = None
        metadata_tg = {
            "event_type": "task_created-ok-tg-msg-id-channel-id",
            "event_payload":
                {
                    "users_notify": users_notify_default_ids,
                    "users_notify_P1": users_notify_P1_ids,
                    "users_notify_P2": users_notify_P2_ids,
                    "priority": priority,
                    "team": team,
                    "creator": user_started_flow_id,
                    "creator_info": user_started_flow,
                    "summary": summary,
                    "key": key,
                    "slack_post_url": slack_post_url,
                    "google_meet_link": google_meet_link,
                    "status": status,
                    "tg_msg_id": tg_msg_id,
                    "tg_channel_id": tg_channel_id
                }
        }
        logger.info(f"\n\n\n\t\tmetadata_tg: {metadata_tg}\n\n")
        await update_slack_message(client, slack_post_url, metadata_tg)


