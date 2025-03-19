from django.shortcuts import render
from django.core.serializers import serialize
from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from .models import Question, Location_data, User
from datetime import datetime

def index(request):
    data = User.objects.all()
    out = {}
    for i in data:
        out[i.pk] = model_to_dict(i)
    return JsonResponse(out)

def location_update(request):
    try:
        data = loads(request.body)
        print("aaaa", data)
        Location_data(datetime=data["datetime"], user=data["user"], lat=data["lat"], long=data["long"]).save()
        return JsonResponse({"success":True})
    except:
        return JsonResponse({"success": False, "reason":"unknown error"})

def user_info(request, user, password):
    try:
        print(user,password)
        user = model_to_dict(User.objects.get(username=user, password=password))
        print(user)
        user["success"] = True
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