import slack_bolt
from slack_bolt.async_app import AsyncApp
from .events import handle_message_events,handle_rc_message, handle_reaction_added_events, handle_reaction_removed_events
from .actions import handle_add_incident_submission_events
from .functions import (handle_archieve_rc_channels,
                        handle_add_jira_incident_modal_function,
                        )




# В этом коде мы просто: подписываемся на события указываем, какие функции их обрабатывают

# register_listeners — регистрирует обработчики событий Slack.
# «Если в Slack происходит X — запусти функцию Y».
def register_listeners(ap:AsyncApp):

    # Если в Slack приходит сообщение и  в тексте есть INC-
    # Тогда вызываем функцию handle_rc_message
    ap.message("INC-")(handle_rc_message)

    # Это перехватывает любое событие типа message обработка в функции handle_message_events.
    ap.event("message")(handle_message_events)

    # Если кто-то поставил emoji на сообщение — вызовется функция handle_reaction_added_events
    ap.event("reaction_added")(handle_reaction_added_events)

    # Если кто-то убрал emoji на сообщение — вызовется функция handle_reaction_removed_events
    ap.event("reaction_removed")(handle_reaction_removed_events)

    # Это не обычное событие.
    # Это Slack Workflow Function.
    # То есть:
    # В Workflow Builder есть кастомная функция
    # Она называется "add_jira_incident_modal_function"
    # При её запуске вызывается handle_add_jira_incident_modal_function
    # Это уже продвинутый уровень Slack-интеграции.
    ap.function("add_jira_incident_modal_function")(handle_add_jira_incident_modal_function)

    # Это обработчик отправки формы.
    # Когда пользователь: открывает modal и  нажимает Submit
    ap.view("form_add_incident_to_jira")(handle_add_incident_submission_events)



