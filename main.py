import os
import re

import structlog
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.context.say import Say

from chai import Chai
from memory import Memory

load_dotenv()

logger = structlog.get_logger()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

memory = Memory()
chai = Chai()


def init_user_profile(user_id: str) -> dict:
    """
    Initialize user profile

    :param user_id: User ID
    """
    user_profile = memory.get_profile(user_id)
    logger.debug(
        "Initializing user profile", user_id=user_id, user_profile=user_profile
    )
    if not user_profile:
        user_profile = app.client.users_profile_get(user=user_id).get("profile", {})
        team_info = app.client.team_info().get("team", None)
        user_profile["team"] = team_info

        memory.set_profile(user_id, user_profile)
        logger.debug("User profile initialized", user_profile=user_profile)

    return user_profile


def get_chat_id(event) -> tuple[str, str]:
    """
    Get chat ID from event

    :param event: Slack event
    :return: Chat ID and thread ID
    """
    uid = event["channel"]
    thread = event.get("thread_ts", event.get("ts"))
    chat_id = f"{uid}_{thread}"
    return chat_id, thread


def append_system_message(messages_history: list, user_profile: dict) -> list:
    """
    Append system message to the beginning of the history

    :param messages_history: Messages history
    :param user_profile: User profile
    :return: Messages history
    """
    messages_history.insert(
        0,
        {
            "role": "system",
            "content": f"User profile:\nName: {user_profile['real_name']} | Title: {user_profile['title']} | Company: {user_profile['team']['name']}",
        },
    )

    return messages_history


@app.event("message")
def process_message(event, say: Say):
    """
    Process message

    This process is triggered when a user sends a message to the bot
    through a direct message or a thread.

    Bot replies inside the thread. If the user sends a message to the bot
    outside a thread, the bot will create a new thread and reply there.

    :param event: Slack event
    :param say: Say
    """
    chat_id, thread = get_chat_id(event)

    user_profile = init_user_profile(event["user"])

    message = event.get("text", "")
    message = re.sub("<@.*?> ", "", message, flags=re.IGNORECASE)

    memory.add_message(chat_id, {"role": "user", "content": message})
    messages_history = memory.get_messages(chat_id)

    logger.debug(
        "Processing message",
        chat_id=chat_id,
        user_profile=user_profile,
        message=message,
        messages_history=messages_history,
    )

    messages_history = append_system_message(messages_history, user_profile)

    response = chai.completion(
        messages=[
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in messages_history
        ],
    )

    if len(response["choices"]) > 0:
        response = response["choices"][0]["message"]["content"]
    else:
        logger.error("No response from model", chat_id=chat_id, response=response)
        response = ""

    memory.add_message(chat_id, {"role": "assistant", "content": response})

    say(response, thread_ts=thread)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
