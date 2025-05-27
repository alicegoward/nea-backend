import time
from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.utils.crypto import get_random_string

from dbAPI.models import User, Notification


def add_friend(request: WSGIRequest) -> JsonResponse:
    try:
        data = loads(request.body)
        requesting = User.objects.get(username=data["userRequesting"])
        requested = User.objects.get(username=data["userRequested"])
        requested.pending_friends.add(requesting)
        Notification(
            user=requested.username,
            notification=f"{requesting} has requested to add you as a friend.",
            datetime=int(time.time())
        ).save()
        requesting.save()
        return JsonResponse({"success": True, "reason": "user successfully added"})
    except:
        return JsonResponse({"success": False, "reason": "user does not exist"})


def update_friend_state(request: WSGIRequest) -> JsonResponse:
    data = loads(request.body)
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
        data = loads(request.body)
        user = User.objects.get(username=data["username"], password=data["password"])
        token = get_random_string(16)
        print("TOKEN", token)
        user.token = token
        user.save()
        return JsonResponse({"success": True, "token": token})
    except Exception as e:
        print(e)
        return JsonResponse({"success": False, "reason": "username / password combination does not exist"})


def register(request: WSGIRequest) -> JsonResponse:
    try:
        data = loads(request.body)
        if User.objects.filter(username=data["username"]).count() > 0:
            raise Exception
        user = User(username=data["username"], password=data["password"]).save()
        return JsonResponse({"success": True, "token": user.token})
    except:
        return JsonResponse({"success": False, "reason": "user already taken"})

def get_friends(request) -> JsonResponse:
    try:
        user = User.objects.get(username=request.user)
        friend_data = {}
        for i, friend in enumerate(user.friends.all()):
            friend_data[i] = friend.username
        incoming_data = {}
        for i, friend in enumerate(user.pending_friends.all()):
            incoming_data[i] = friend.username
        outgoing_data = {}
        for i, friend in enumerate(User.objects.filter(pending_friends=user)):
            outgoing_data[i] = friend.username
        return JsonResponse(
            {"success": True, "names": friend_data, "incoming": incoming_data, "outgoing": outgoing_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason": str(e)})
