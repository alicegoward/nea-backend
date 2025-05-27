import time
from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from dbAPI.models import Notification, UserOnRoute, User


def show_notification(request: WSGIRequest) -> JsonResponse:
    notifications = Notification.objects.filter(user=request.user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=request.user).all().delete()
    return JsonResponse({"success": True, "notifications": data})

def notify_others(request: WSGIRequest) -> JsonResponse:
    data = loads(request.body)
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=request.user):
        Notification(user=request.user.username, notification=data["data"], datetime=int(time.time())).save()
    return JsonResponse({"success": True})