import re
from configs import config as cfg
from urllib.parse import quote_plus

def get_jira_link_from_issue_key(issue_key):
    return cfg.JIRA_SERVER + f'/browse/{issue_key}'

def make_slack_link_from_url(url, link_text):
    return f'<{url}|{link_text}>'

def make_link_to_jira_issue(issue_key):
    return make_slack_link_from_url(get_jira_link_from_issue_key(issue_key),issue_key)

def format_incident_message(creator, issue_key, summary, priority, team, status, google_meet_link, tg=False, users_notify=None, users_notify_P1=None, users_notify_P2=None, ):
    circle = "⚪️ "

    if priority:
        if "p3" in str(priority).lower():
            circle = "🟡 "
        if "p1" in str(priority).lower():
            circle = "🔴 "
        if "p2" in str(priority).lower():
            circle = "🟠 "

    metadata = {
        "event_type": "task",
        "event_payload":
        {
            "priority": priority,
            "team": team,
            "creator": creator,
            "summary": summary,
            "google_meet_link": google_meet_link,
            "status": status,
            "key": issue_key,
            "users_notify_P1": users_notify_P1,
            "users_notify_P2": users_notify_P2,
            "users_notify": users_notify
        }
    }

    users_notify_string = "\n"
    users_notify_extra_string = "\n"
    users_notify_no_doubles = []

    status_res = f":loading2: Статус:"
    if tg:
        status_res = f"🕙 Статус:"
    if status:
        if status.lower() == "done" or status.lower() == "готово":
            status_res = f"✅ Статус:"
        if status.lower() == "declined" or status.lower() == "удален в jira":
            status_res = f"🚫 Статус:"
    if tg:
        issue_link = f'[{escape_markdown_v2(issue_key)}]({escape_markdown_v2(get_jira_link_from_issue_key(issue_key))})'
        status_res = f"{status_res} {escape_markdown_v2(str(status))}"
        team = escape_markdown_v2(str(team))
        creator = escape_markdown_v2(str(creator))
        summary = escape_markdown_v2(str(summary))
    else:
        creator = f'<@{creator}>'
        issue_link = make_link_to_jira_issue(issue_key)
        status_res = f"{status_res} {str(status)}"
        team = str(team)
        creator = str(creator)


    message_text = (f'{circle} *{str(priority)}* инцидент *{issue_link}*\n '
                    f'Summary: *{summary}*\n'
                    f' 👥Команда: *{str(team)}*\n'
                    f'{status_res}\n'
                    f'Создал сотрудник: {str(creator)}\n\n'
                    )

    if priority == "P1":
        if users_notify:
            for usr in users_notify:
                if users_notify_P1:
                    if usr not in users_notify_P1 and usr != creator:
                        users_notify_no_doubles.append(usr)
        if users_notify_P1:
            i = 1
            for user in users_notify_P1:
                if user == creator:
                    continue
                if i % 2:
                    users_notify_extra_string = users_notify_extra_string + "\n\t"
                users_notify_extra_string = users_notify_extra_string + f"\t{user}"
                i += 1

    if priority == "P2":
        if users_notify:
            for usr in users_notify:
                if users_notify_P2:
                    if usr not in users_notify_P2 and usr != creator:
                        users_notify_no_doubles.append(usr)
        i = 1
        if users_notify_P2:
            i = 1
            for user in users_notify_P2:
                if user == creator:
                    continue
                if i % 2:
                    users_notify_extra_string = users_notify_extra_string + "\n\t"
                users_notify_extra_string = users_notify_extra_string + f"\t{user}"
                i += 1


    if not users_notify_no_doubles:
        if priority != "P1" and priority != "P2":
            i = 1
            if users_notify:
                for user in users_notify:
                    if user == creator:
                        continue
                    if i % 2:
                        users_notify_string = users_notify_string + "\n\t"
                    users_notify_string = users_notify_string + f"\t{user}"
                    i += 1
    else:
        i = 1
        for user in users_notify_no_doubles:
            if user == creator:
                continue
            if i % 2:
                users_notify_string = users_notify_string + "\n\t"
            users_notify_string = users_notify_string + f"\t{user}"
            i += 1

    if len(users_notify_string) > 4:
        message_text = message_text + f'Сотрудники для уведомления: {users_notify_string}\n\n'

    if (users_notify_P1 and priority == "P1") or (users_notify_P2 and priority == "P2"):
        message_text = message_text + f'Сотрудники для *уведомления в связи с {priority}*: {users_notify_extra_string}\n\n'

    st = status.lower()
    statuses = ["done","declined","удален в jira", "готово"]
    if google_meet_link and st not in statuses:
        if tg:
            google_meet_link = escape_markdown_v2(google_meet_link)
            google_meet_text = escape_markdown_v2("Google meet")
            message_text = f"{message_text}\n[{google_meet_text}]({google_meet_link})\n"
        else:
            message_text = f"{message_text}\n Google meet: {google_meet_link}\n"


    return message_text, metadata

def parse_rich_text_values_users(rich_text_raw_dict):
    parsed_users = []
    if rich_text_raw_dict:
        for element in rich_text_raw_dict:
            if "type" in element:
                if element["type"] == "rich_text":
                    if "elements" in element:
                        for sub_element in element["elements"]:
                            if "type" in sub_element:
                                if sub_element["type"] == "rich_text_section":
                                    if "elements" in sub_element:
                                        for user_dict in sub_element["elements"]:
                                            if "user_id" in user_dict:
                                                parsed_users.append(user_dict["user_id"])

    return parsed_users


def remove_special_chars_keep_dash(text):
    return re.sub(r'[^a-zA-Z0-9а-яА-ЯёЁ\- ]', '', text)  # Оставляем буквы, цифры, тире и пробелы


def convert_to_user_tag(users_notify_ids):
    users_notify_tags = []
    if not users_notify_ids:
        return users_notify_tags
    for user_id in users_notify_ids:
        users_notify_tags.append(f'<@{user_id}>')
        # код yиже не работает
        # users_notify_tags.append( "<@" + str(re.sub(r'[^0-9]', '', user_id)) + ">" )
    return users_notify_tags


def quote_msg(msg):
    return quote_plus(msg)


def escape_markdown_v2(text: str):
    """
    Экранирует специальные символы для Telegram MarkdownV2.
    """
    if not text:
        return None
    special_chars = r"_*[]()~`>#+-=|{}.!"
    res = re.sub(r"([" + re.escape(special_chars) + r"])", r"\\\1", text)
    if res:
        return res
    return text