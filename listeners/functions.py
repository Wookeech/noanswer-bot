import logging

from slack_bolt.context.say.async_say import AsyncSay
from slack_bolt.context.ack.async_ack import AsyncAck
from slack_sdk.web.async_client import AsyncWebClient as WebClient
from slack_bolt.async_app import AsyncBoltContext
from configs import config as cfg
from slack_utils.utils import archieve_old_incidents_channels
logger = logging.getLogger(__name__)



async def handle_archieve_rc_channels(inputs: dict, say: AsyncSay,client:WebClient, logger: logging.Logger):
    logger.debug("archieve_rc_channels")
    time = inputs["time_days"]
    logger.debug(inputs["time_days"])
    # archieve_old_incidents_channels(client, time_sec=time*60*60*24)

async def handle_add_jira_incident_modal_function(inputs: dict, say: AsyncSay, client:WebClient, logger: logging.Logger):
    global jira_conn, samodelkin_bot, gmeet
    logger.info("\nopen_jira_add_incident_modal_function\n")
    logger.info(inputs)
    # ack()
    # trigger_id = body["event"]["inputs"]['inp_trig_id.interactivity_pointer']
    trigger_id = inputs['inp_trig_id.interactivity_pointer']
    allowed_teams = await jira_conn.get_allowed_vals_for_Teams_async()
    allowed_priorities = await jira_conn.get_allowed_vals_for_Priority_async()

    #Open the modal for incident create
    view = {
        "type": "modal",
        "callback_id": "form_add_incident_to_jira",
        "title": {
            "type": "plain_text",
            "text": "Создать инцидент в Jira",
            "emoji": True
        },
        "submit": {
            "type": "plain_text",
            "text": "Submit",
            "emoji": True
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
            "emoji": True
        },
        "blocks": [
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "action_id_summary"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Summary",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "optional": True,
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Выберите команду",
                        "emoji": True
                    },
                    "options": allowed_teams
                    ,
                    "action_id": "action_id_team"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Команда",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "optional": True,
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Выберите приоритет",
                        "emoji": True
                    },
                    "options": allowed_priorities,
                    "action_id": "action_id_priority"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Приоритет",
                    "emoji": True
                }
            }
        ]
    }
    await client.views_open(trigger_id=trigger_id, view=view)
