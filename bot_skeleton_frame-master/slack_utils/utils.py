import datetime
import time
from json.encoder import encode_basestring
from configs import config as cfg
import uuid
import logging
logger = logging.getLogger(__name__)
from slack_utils.message_formatters import (format_incident_message, remove_special_chars_keep_dash,
                                            convert_to_user_tag, escape_markdown_v2)


def get_blocks_form_value_by_action_id(values_dict, action_id):
    for element in values_dict:
        if action_id in values_dict[element]:
            # logger.debug(values_dict[element][action_id])
            if "selected_option" in values_dict[element][action_id]:
                if not values_dict[element][action_id].get("selected_option"):
                    return None
                if "value" in values_dict[element][action_id].get("selected_option"):
                    return values_dict[element][action_id]["selected_option"]["value"]
            else:
                if "value" in values_dict[element][action_id]:
                    return values_dict[element][action_id]["value"]
    return None

def get_dict_key(dict, key):
    if key in dict:
        return dict[key]
    else:
        return None

def get_slack_user_real_name(user_id, user):
    creator = None
    if not user:
        return user_id
    if "user" in user:
        user = user["user"]
    if "id" in user:
        creator = user["id"]
        return creator
    return user_id

def get_tg_user_real_name(user_id, user):
    creator = None
    if not user:
        return user_id
    if "user" in user:
        user = user["user"]
    if "profile" in user:
        if "real_name_normalized" in user["profile"]:
            if user["profile"]["real_name_normalized"]:
                if user["profile"]["real_name_normalized"] != "":
                    creator = user["profile"]["real_name_normalized"]
                    return creator

    if "real_name" in user:
        creator = user["real_name"]
        return creator

    return user_id

def get_slack_post_url(channel_id, ts, workspace = cfg.SLACK_WORKSPACE):
        # Convert ts (e.g., 1700299172.92959 → 170029917292959)
        if not ts or not channel_id or not workspace:
            return None
        ts_formatted = ts.replace(".", "")
        return f"https://{workspace}.slack.com/archives/{channel_id}/p{ts_formatted}"

def get_slack_timestamp_from_url(slack_post_url):
    if not slack_post_url:
        return None
    slack_ts = slack_post_url.split("/")[-1]
    return f"{slack_ts[1:11]}.{slack_ts[11:]}"  # Convert "p1740029917292959" → "1740029917.292959"

def get_slack_channel_from_url(slack_post_url):
    if not slack_post_url:
        return None
    slack_channel = slack_post_url.split("/")[-2]
    return slack_channel

async def get_slack_message(client, slack_post_url):
    channel_id = get_slack_channel_from_url(slack_post_url)
    message_ts = get_slack_timestamp_from_url(slack_post_url)
    try:
        response = await client.conversations_replies(
            channel=channel_id,
            ts=message_ts,
            include_all_metadata=True
        )
        metadata = {}
        if response["ok"]:
            messasge_raw = response["messages"][0]["text"]
            if "metadata" in response["messages"][0]:
                metadata = response["messages"][0]["metadata"]
            return messasge_raw, metadata

        else:
            return None, None
    except Exception as e:
        logger.error(f"Error getting Slack message: {e}")

    return None, None

async def delete_slack_message(client, slack_post_url):
    channel_id = get_slack_channel_from_url(slack_post_url)
    message_ts = get_slack_timestamp_from_url(slack_post_url)
    try:
        response = await client.chat_delete(
            channel=channel_id,
            ts=message_ts  # Timestamp сообщения
        )
        if response["ok"]:
            return True, "ok"
        else:
            return False, f"Ошибка: {response['error']}"
    except Exception as e:
        return False, f"Ошибка удаления: {e}"

async def update_tg_message(tg_bot, tg_msg_id, tg_channel_id, metadata):
    issue_key = metadata["event_payload"].get("key", None)
    summary = metadata["event_payload"].get("summary", None)
    priority = metadata["event_payload"].get("priority", None)
    team = metadata["event_payload"].get("team", None)
    inc_status = metadata["event_payload"].get("status", None)
    google_meet_link = metadata["event_payload"].get("google_meet_link", None)
    display_name = metadata["event_payload"].get("display_name", None)
    if display_name:
        creator = display_name
    else:
        creator = get_tg_user_real_name(metadata["event_payload"].get("creator", None),
                                        metadata["event_payload"].get("creator_info", None))

    message, metadata_new = format_incident_message(creator, issue_key, summary, priority, team, inc_status, google_meet_link, True)

    status, msg = await tg_bot.edit_message_async(message, tg_channel_id, tg_msg_id)
    logger.info(f"TG message edited:\n Status{status}:\n Message: {message}\nMetadata: {metadata} ")
    return status

async def update_slack_message(client, slack_post_url, metadata):
    channel_id = get_slack_channel_from_url(slack_post_url)
    message_ts = get_slack_timestamp_from_url(slack_post_url)
    creator_info = metadata["event_payload"].get("creator_info")
    creator = get_slack_user_real_name(metadata["event_payload"].get("creator"),
                                       creator_info)
    user_mail = metadata["event_payload"].get("creator_mail")
    issue_key = metadata["event_payload"].get("key",None)
    summary = metadata["event_payload"].get("summary",None)
    priority = metadata["event_payload"].get("priority",None)
    team = metadata["event_payload"].get("team",None)
    inc_status = metadata["event_payload"].get("status", None)
    users_notify_default_ids = metadata["event_payload"].get("users_notify",cfg.SLACK_USERS_NOTIFY)
    users_notify_P1_ids =  metadata["event_payload"].get("users_notify_P1",cfg.SLACK_USERS_NOTIFY_P1)
    users_notify_P2_ids = metadata["event_payload"].get("users_notify_P2",cfg.SLACK_USERS_NOTIFY_P2)
    google_meet_link = metadata["event_payload"].get("google_meet_link",None)
    tg_msg_id = metadata["event_payload"].get("tg_msg_id",None)
    tg_channel_id = metadata["event_payload"].get("tg_channel_id",None)
    logger.info(f"\n\n\t\tUpdating Slack message: {tg_msg_id}\n\t\t{tg_channel_id}\n\n")

    if user_mail:
        user_id = await get_user_id_by_mail(client, user_mail)
    else:
        user_id = get_user_id_by_display_name(creator)
    if user_id:
        creator = user_id
    message, metadata_new = format_incident_message(creator,issue_key,summary,priority,team,
                                                    inc_status,google_meet_link,False,
                                                    convert_to_user_tag(users_notify_default_ids),
                                                    convert_to_user_tag(users_notify_P1_ids),
                                                    convert_to_user_tag(users_notify_P2_ids))

    if cfg.SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL:
        incident = remove_special_chars_keep_dash(
            str(( f'{issue_key}-{str(priority)}-{summary.replace(" ", "-")[:54]}-'
                f'{(str(inc_status)).replace(" ", "-").replace("_", "-")}')).lower()
        )[:80]
        try:
            response = await client.conversations_info(channel=channel_id)
            channel_name = response["channel"]["name"]
            if channel_name != incident:
                # Изменение названия канала канала в Слак с именем инцидента
                response = await client.conversations_rename(
                    channel=channel_id,
                    name=incident,  # нельзя пробелы и знаки пунктуации, кроие тире
                    team_id=cfg.SLACK_TEAM_ID,
                    token = cfg.SLACK_BOT_TOKEN_USER
                )
                logger.debug(f"\n\n\t\tChannel renamed: {response['channel']['name']} (ID: {response['channel']['id']})\n\n")
        except Exception as e:
            logger.error(f"Error renaming channel: {e}")

        result_users_notify = []
        if users_notify_default_ids:
            result_users_notify.extend(users_notify_default_ids)
        if priority == "P1":
            if users_notify_P1_ids:
                result_users_notify.extend(users_notify_P1_ids)
        if priority == "P2":
            if users_notify_P2_ids:
                result_users_notify.extend(users_notify_P2_ids)
        if user_id:
            result_users_notify.append(user_id)
        await conversation_invite_users(client, channel_id, result_users_notify)
    try:
        logger.info(f"\n\n\t\tUpdating Slack message: {message}\n\t\t{metadata}\n\n")
        response = await client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=message,
            metadata=metadata
        )
        if response["ok"]:
            return True, "ok"
        else:
            return False, f"Ошибка: {response['error']}"
    except Exception as e:
        return False, f"Ошибка обновления: {e}"

async def create_slack_incident_message(metadata, client, gmeet):
    key = metadata["event_payload"].get("key",None)
    if not key:
        key = f"RC-{str(uuid.uuid4())[:8]}"
    summary = metadata["event_payload"].get("summary","Creating incident")
    priority = metadata["event_payload"].get("priority",None)
    team = metadata["event_payload"].get("team",None)
    user = metadata["event_payload"].get("creator","")
    user_mail = metadata["event_payload"].get("creator_mail",None)
    inc_status = metadata["event_payload"].get("status", "В ПРОЦЕССЕ СОЗДАНИЯ")
    users_notify_default_ids = metadata["event_payload"].get("users_notify", cfg.SLACK_USERS_NOTIFY)
    users_notify_P1_ids = metadata["event_payload"].get("users_notify_P1", cfg.SLACK_USERS_NOTIFY_P1)
    users_notify_P2_ids = metadata["event_payload"].get("users_notify_P2", cfg.SLACK_USERS_NOTIFY_P2)
    message_slack = None
    metadata_new = {}
    tg = cfg.TG_CHANNEL_ID
    try:
        incident = remove_special_chars_keep_dash(
            str(( f'{key}-{str(priority)}-{summary.replace(" ", "-")[:54]}-'
                f'{(str(inc_status)).replace(" ", "-").replace("_", "-")}')).lower()
        )[:80]

        google_meet_link = None
        if cfg.CREATE_GOOGLE_MEET_LINK:
            google_meet_link = await gmeet.create_meet_async(f"{priority}  {incident}")
            if not google_meet_link:
                google_meet_link = await gmeet.create_meet_async(f"{priority}  {incident}")
        user_id = None
        if user_mail:
            user_id = await get_user_id_by_mail(client, user_mail)
        else:
            user_id = get_user_id_by_display_name(user)
        if user_id:
            user = user_id
        message_slack, metadata_new = format_incident_message(user, key, summary, priority, team, inc_status, google_meet_link, False,
                                          convert_to_user_tag(users_notify_default_ids),
                                          convert_to_user_tag(users_notify_P1_ids),
                                          convert_to_user_tag(users_notify_P2_ids)
                                          )

        slack_channel_id = cfg.SlACK_CHANNEL_ID
        metadata_new["event_type"] = "task_creating"
        metadata_new["event_payload"]["google_meet_link"] = google_meet_link
        metadata_new["event_payload"]["key"] = key
        metadata_new["event_payload"]["summary"] = encode_basestring(summary)
        metadata_new["event_payload"]["priority"] = priority
        metadata_new["event_payload"]["team"] = team
        metadata_new["event_payload"]["creator"] = user
        metadata_new["event_payload"]["creator_info"] = None
        metadata_new["event_payload"]["status"] = inc_status
        metadata_new["event_payload"]["users_notify"] = users_notify_default_ids
        metadata_new["event_payload"]["users_notify_P1"] = users_notify_P1_ids
        metadata_new["event_payload"]["users_notify_P2"] = users_notify_P2_ids

        if cfg.SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL:
            try:
                # Создание нового канала в Слак с именем инцидента
                response = await client.conversations_create(
                    name=incident,  # нельзя пробелы и знаки пунктуации, кроие тире
                    team_id=cfg.SLACK_TEAM_ID,
                    token = cfg.SLACK_BOT_TOKEN_USER
                )
                slack_channel_id = response['channel']['id']
                logger.debug(f" Channel created: {response['channel']['name']} (ID: {response['channel']['id']})")
            except Exception as e:
                logger.error(f"Error creating channel: {e}")

            result_users_notify = []
            if users_notify_default_ids:
                result_users_notify.extend(users_notify_default_ids)
            if priority == "P1":
                if users_notify_P1_ids:
                    result_users_notify.extend(users_notify_P1_ids)
            if priority == "P2":
                if users_notify_P2_ids:
                    result_users_notify.extend(users_notify_P2_ids)
            if user:
                user_id = get_user_id_by_display_name(user)
                if user_id and not user_id == "None" :
                    result_users_notify.append(user_id)
            await conversation_invite_users(client, slack_channel_id, [cfg.SLACK_BOT_USER_ID])
            await conversation_invite_users(client, slack_channel_id, result_users_notify)
        response = await client.chat_postMessage(channel=slack_channel_id,
                                           text=message_slack,
                                           metadata=metadata_new)
        if response['ok']:
            ts = response['ts']
            slack_post_url = get_slack_post_url(slack_channel_id, ts, cfg.SLACK_WORKSPACE)
            metadata_new["event_payload"]["slack_post_url"] = slack_post_url
            message, metadata_in = await get_slack_message(client,slack_post_url)
            logger.debug(f"Message: {message}\nMetadata: {metadata_in}")
            print(f"Message: {message}\nMetadata_res: {metadata_in}")
            return metadata_new
        return None

    except Exception as e:
        logger.exception(e)
        return None

async def unarchieve_incident_channel(client, channel_id, token):
    logger.info(f"Unarchiving channel: {channel_id}")
    try:
        response = await client.conversations_unarchive(channel=channel_id, token=token)
    except Exception as e:
        logger.error(f"Error UNarchiving channel:{channel_id}\n {e}")
        return False
    finally:
        logger.info(f"Channel: {channel_id} successfully UNarchived.")
        return True

async def archieve_incident_channel(client, channel_id, token):
    logger.info(f"Archiving channel: {channel_id}")
    try:
        response = await client.conversations_archive(channel=channel_id, token=token)
    except Exception as e:
        logger.error(f"Error archiving channel:{channel_id}\n {e}")
        return False
    finally:
        logger.info(f"Channel: {channel_id} successfully archived.")
        return True

async def conversation_invite_users(client, channel_id, users_to_invite):
    try:
        unique_users_notify = list(dict.fromkeys(users_to_invite))
        logger.info(f"\ncfg.SLACK_BOT_USER_ID\n: {cfg.SLACK_BOT_USER_ID}\n")
        if 'U08BH3U2VFH' in unique_users_notify:
            unique_users_notify.remove('U08BH3U2VFH')
        if cfg.SLACK_BOT_USER_ID:
            if cfg.SLACK_BOT_USER_ID not in unique_users_notify:
                unique_users_notify.append(cfg.SLACK_BOT_USER_ID)
        logger.info(f"\nUsers to notify\n: {unique_users_notify}\n")
        if unique_users_notify and channel_id:
            res = await client.conversations_invite(channel=channel_id,
                                              token=cfg.SLACK_BOT_TOKEN_USER,
                                              users=unique_users_notify)
    except Exception as e:
        logger.error(f"Error inviting users to channel: {e} Users: {users_to_invite}")
        return False
    finally:
        return True


def archieve_old_incidents_channels(client, time_sec):
    now = int(time.time())  # Текущее время в секундах
    time_ago = now - int(time_sec)
    try:
        response = client.conversations_list(
            exclude_archived=True,
            limit=10000
        )
        if response["ok"]:
            channels = response["channels"]
            for channel in channels:
                if (channel["is_channel"] and
                    channel["name"].startswith("rc-") and
                    len(channel["name"]) > 10 and
                    channel["created"] < time_ago
                ):
                    logger.info(f"Archiving channel: {channel['name']} (ID: {channel['id']})")
                    try:
                        response = client.conversations_archive(channel=channel["id"])
                    except Exception as e:
                        logger.error(f"Error archiving channel:{channel["name"]}\n {e}")

    except Exception as e:
        logger.error(f"Error archiving old incidents channels: {e}")
    finally:
        return True

async def get_user_id_by_mail(client, email):
    if not email or not cfg.USER_LIST:
        return None
    try:
        user = await client.users_lookupByEmail(token=cfg.SLACK_BOT_TOKEN, email=email)
        if user.get("ok"):
            logger.info(f"\n\n\t\tUser found by email: {email} (ID: {user['user'].get('id')})")
            user = user["user"]
            return user.get("id")
    except Exception as e:
        logger.error(f"Error getting user id by email:{email}\nException: {e}")
        return None

def get_user_display_name_by_id(user_id):
    if not user_id or not cfg.USER_LIST:
        return None
    for user in cfg.USER_LIST:
        if user.get("deleted"):
            continue
        if user.get("id") == user_id:
            usr = user.get("profile")
            name = user.get("name").split(".")
            first_name = str(usr.get("first_name"))
            last_name = str(usr.get("last_name"))
            display_name = usr.get("display_name")
            if display_name:
                return display_name
            return f"{first_name} {last_name}"

def get_user_id_by_display_name(display_name):
    if not display_name or not cfg.USER_LIST:
        return None
    # hardcode
    if display_name == "Shaulykbay Zhumanazarov":
        display_name = "Adik Zhumanazarov"
    for user in cfg.USER_LIST:
        if  user.get("deleted"):
            continue
        if user.get("id") == display_name:
            return display_name
        usr = user.get("profile")
        name =user.get("name").split(".")
        first_name = ""
        last_name = ""
        if name:
            first_name = name[0].lower()
            if len(name) > 1:
                last_name = name[1].lower()
        if (f"{first_name} {last_name}" in display_name.lower() or
            f"{last_name} {first_name}" in display_name.lower()):
            return user.get("id")
        first_name = str(usr.get("first_name")).lower()
        last_name = str(usr.get("last_name")).lower()
        if (f"{first_name} {last_name}" in display_name.lower() or
                f"{last_name} {first_name}" in display_name.lower()):
            return user.get("id")
    return None

async def get_all_users(client, token, team_id):
    users = []
    cursor = None  # Для пагинации

    while True:
        try:
            response = await client.users_list(cursor=cursor, team_id=team_id, token = token)
            if response["ok"]:
                users.extend(response["members"])
                cursor = response.get("response_metadata", {}).get("next_cursor", None)
                if not cursor:  # Если нет следующей страницы, выходим из цикла
                    break
            else:
                print("Ошибка:", response["error"])
                break
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            break
    return users