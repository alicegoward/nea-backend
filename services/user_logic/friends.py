import time
from typing import Any

from api.models import Notification, User


def add_friend_data(data: dict[str, str]) -> None:
    """
    :param data: information about the requesting and requested user to add to pending friends
    """
    requesting = User.objects.get(username=data["userRequesting"])
    requested = User.objects.get(username=data["userRequested"])
    requested.pending_friends.add(requesting)
    Notification(
        user=requested.username,
        notification=f"{requesting} has requested to add you as a friend.",
        datetime=int(time.time())
    ).save()
    requesting.save()


def update_friend_state_data(data: dict[str, str]) -> None:
    """
    :param data: accepted and accepting friends to update their relationship in the database.
    """
    accepting = User.objects.get(username=data["userAccepting"])
    accepted = User.objects.get(username=data["userAccepted"])
    accepting.pending_friends.remove(accepted)
    if data["result"] == "accepted":
        accepting.friends.add(accepted)
        Notification(
            user=accepted.username,
            notification=f"{accepting} has accepted your friend request.",
            datetime=int(time.time())
        ).save()
    accepting.save()


def get_friends_data(username: str) -> dict[str, dict[Any, Any]]:
    """
    :param username: User
    :return: Enumerated dictionaries of usernames for full, incoming and outgoing friends.
    """
    user = User.objects.get(username=username)
    friend_data = {}
    for i, friend in enumerate(user.friends.all()):
        friend_data[i] = friend.username
    incoming_data = {}
    for i, friend in enumerate(user.pending_friends.all()):
        incoming_data[i] = friend.username
    outgoing_data = {}
    for i, friend in enumerate(User.objects.filter(pending_friends=user)):
        outgoing_data[i] = friend.username
    return {"names": friend_data, "incoming": incoming_data, "outgoing": outgoing_data}
