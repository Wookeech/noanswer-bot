import os
from typing import List

# PROD

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_BOT_TOKEN_USER = os.environ.get("SLACK_BOT_TOKEN_USER")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_BOT_USER_ID = None

SLACK_TEAM_ID = ""
SLACK_WORKSPACE = os.environ.get("SLACK_WORKSPACE")
LOGS_SLACK_CHANNEL = os.environ.get("LOGS_SLACK_CHANNEL")
SlACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")
if os.environ.get("SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL").lower() == "true":
    SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL = True
else:
    SLACK_CREATE_MSG_IN_SEPARATE_CHANNEL = False
if os.environ.get("CREATE_GOOGLE_MEET_LINK").lower() == "true":
    CREATE_GOOGLE_MEET_LINK = True
else:
    CREATE_GOOGLE_MEET_LINK = False

# Andrei Semenov, Ilya Kiryakov, Vadim Gundarev, Aleksandr Goncharov
SLACK_USERS_NOTIFY = ['U08BH3U2VFH', 'U06AAMH2RS5', 'U04TV9LPZNE', 'U07LQRHFNQN']  # type: List[str]
SLACK_USERS_NOTIFY_P1 = ['U06AAMH2RS5']  # type: List[str]
# SLACK_USERS_NOTIFY = ['U08BH3U2VFH']  # type: List[str]
SLACK_USERS_NOTIFY_P1 = []  # type: List[str]
SLACK_USERS_NOTIFY_P2 = []  # type: List[str]
USER_LIST = None



