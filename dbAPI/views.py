from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from .models import Location_data, User, Notification
from random import randint
import time

def location_update(request):
    try:
        data = loads(request.body)
        print("aaaa", data)
        Location_data(datetime=data["datetime"], user=data["user"], lat=data["lat"], long=data["long"]).save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"unknown error"})

def user_info(request):
    try:
        data = loads(request.body)
        user = model_to_dict(User.objects.get(username=data["username"], password=data["password"]))
        print(user)
        user["success"] = True
        user.pop("friends")
        return JsonResponse(user)
    except:
        return JsonResponse({"success":False, "reason":"username / password combination does not exist"})

def add_user(request):
    try:
        data = loads(request.body)
        if User.objects.filter(username = data["username"]).count() > 0:
            raise Exception
        print("aaaa", data)
        User(username=data["username"], password=data["password"]).save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"user already taken"})
    
def create_notification(_, user):
    try:
        Notification(notification="some sample text "+str(randint(0,1000)), user=user, datetime=int(time.time())).save()
        return JsonResponse({"success":True})
    except Exception as e:
        print(e)
        return JsonResponse({"success":False})


def show_notification(_, user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime]=i.notification
    Notification.objects.all().delete()
    return JsonResponse({"success": True, "notifications": data})

def get_friends(_, user):
    try:
        user = User.objects.get(username=user)
        friend_data = {}
        for i, friend in enumerate(user.friends.all()):
            friend_data[i] = friend.username
        incoming_data = {}
        for i, friend in enumerate(user.pending_friends.all()):
            incoming_data[i] = friend.username
        outgoing_data = {}
        for i, friend in enumerate(User.objects.filter(pending_friends=user)):
            outgoing_data[i] = friend.username
        print(f"{friend_data}\n{incoming_data}\n{outgoing_data}")
        return JsonResponse({"success": True, "names":friend_data, "incoming":incoming_data, "outgoing":outgoing_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason":str(e)})
    
def add_friend(request):
    try:
        data = loads(request.body)
        requesting = User.objects.get(username=data["userRequesting"])
        requested = User.objects.get(username=data["userRequested"])
        requested.pending_friends.add(requesting)
        Notification(
            user = requested, 
            notification = f"{requesting} has requested to add you as a friend.", 
            datetime = int(time.time())
            ).save()
        requesting.save()
        return JsonResponse({"success":True, "reason":"user successfully added"})
    except:
        return JsonResponse({"success": False, "reason":"user does not exist"})
    
def update_friend_state(request):
    data = loads(request.body)
    accepting = User.objects.get(username=data["userAccepting"])
    accepted = User.objects.get(username=data["userAccepted"])
    accepting.pending_friends.remove(accepted)
    if data["result"] == "accepted":
        accepting.friends.add(accepted)
    accepting.save()
