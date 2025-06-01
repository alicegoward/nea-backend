import time
from typing import Any

from api.models import Notification, User


def add_friend_data(data: dict[str, str]) -> None:
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
