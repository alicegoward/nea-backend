from django.shortcuts import render
from django.core.serializers import serialize
from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.utils import timezone
from .models import Question, Location_data
from datetime import datetime

def index(request):
    data = Location_data.objects.all()
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
        return JsonResponse({"success": False})

