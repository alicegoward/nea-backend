from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from .models import Location_data, User, Notification
from random import randint
import time

def index(_):
    data = User.objects.all()
    out = {}
    for i in data:
        data = model_to_dict(i)
    return JsonResponse(out)

def location_update(request):
    try:
        data = loads(request.body)
        print("aaaa", data)
        Location_data(datetime=data["datetime"], user=data["user"], lat=data["lat"], long=data["long"]).save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"unknown error"})

def user_info(_, user, password):
    try:
        print(user,password)
        user = model_to_dict(User.objects.get(username=user, password=password))
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
        friends = User.objects.get(username=user).friends
        friend_data = {}
        for i, friend in enumerate(friends.all()):
            friend_data[i] = friend.username
        return JsonResponse({"success": True, "names":friend_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason":str(e)})
    
def add_friend(request):
    try:
        data = loads(request.body)
        requesting = User.objects.get(username=data["user_requesting"])
        requested = User.objects.get(username=data["user_requested"])
        requested.pending_friends.add(requesting)
        Notification(
            user = requested, 
            notification = f"{requesting} has requested to add you as a friend.", 
            datetime = int(time.time())
            ).save()
        requesting.save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"user does not exist"})
    
def get_pending_requests(_, user):
    try:
        friends = User.objects.get(username=user).pending_friends
        friend_data = {}
        for i, friend in enumerate(friends.all()):
            friend_data[i] = friend.username
        return JsonResponse({"success": True, "names":friend_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason":str(e)})
    
def update_friend_state(request):
    data = loads(request.body)
    accepting = User.objects.get(username=data["user_accepting"])
    accepted = User.objects.get(username=data["user_accepted"])
    accepting.pending_friends.remove(accepted)
    if data["result"] == "accepted":
        accepting.friends.add(accepted)
    accepting.save()
