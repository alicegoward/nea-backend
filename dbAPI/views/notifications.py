import time
from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from dbAPI.models import Notification, UserOnRoute, User


def show_notification(request: WSGIRequest) -> JsonResponse:
    data = show_notifications_data(request.user)
    return JsonResponse({"success": True, "notifications": data})


def show_notifications_data(user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=user).all().delete()
    return data


def notify_others(request: WSGIRequest) -> JsonResponse:
    notify_others_data(loads(request.body), request.user)
    return JsonResponse({"success": True})


def notify_others_data(data, user):
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=user):
        Notification(user=i.username, notification=data["data"], datetime=int(time.time())).save()