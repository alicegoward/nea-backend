import time
from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.utils.crypto import get_random_string

from dbAPI.models import User, Notification


def add_friend(request: WSGIRequest) -> JsonResponse:
    try:
        add_friend_data(loads(request.body))
        return JsonResponse({"success": True, "reason": "user successfully added"})
    except:
        return JsonResponse({"success": False, "reason": "user does not exist"})


def add_friend_data(data):
    requesting = User.objects.get(username=data["userRequesting"])
    requested = User.objects.get(username=data["userRequested"])
    requested.pending_friends.add(requesting)
    Notification(
        user=requested.username,
        notification=f"{requesting} has requested to add you as a friend.",
        datetime=int(time.time())
    ).save()
    requesting.save()


def update_friend_state(request: WSGIRequest) -> JsonResponse:
    update_friend_state_data(loads(request.body))
    return JsonResponse({"success": True})


def update_friend_state_data(data):
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


def login(request: WSGIRequest) -> JsonResponse:
    try:
        token = login_data(request.body)
        return JsonResponse({"success": True, "token": token})
    except Exception as e:
        return JsonResponse({"success": False, "reason": "username / password combination does not exist"})


def login_data(data):
    user = User.objects.get(username=data["username"], password=data["password"])
    token = get_random_string(16)
    print("TOKEN", token)
    user.token = token
    user.save()
    return token


def register(request: WSGIRequest) -> JsonResponse:
    try:
        user = register_data(loads(request.body))
        return JsonResponse({"success": True, "token": user.token})
    except:
        return JsonResponse({"success": False, "reason": "user already taken"})


def register_data(data):
    if User.objects.filter(username=data["username"]).count() > 0:
        raise Exception
    user = User(username=data["username"], password=data["password"]).save()
    return user


def get_friends(request) -> JsonResponse:
    try:
        return JsonResponse(get_friends_data(request.user))
    except Exception as e:
        return JsonResponse({"success": False, "reason": str(e)})


def get_friends_data(username):
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
    return {"success": True, "names": friend_data, "incoming": incoming_data, "outgoing": outgoing_data}
