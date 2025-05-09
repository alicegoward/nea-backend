import time
from json import loads

from django.http import JsonResponse

from dbAPI.models import Notification, UserOnRoute


def show_notification(_, user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=user).all().delete()
    return JsonResponse({"success": True, "notifications": data})

def notify_others(request):
    data = loads(request.body)
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=data["user"]):
        Notification(user=i.user.username, notification=data["data"], datetime=int(time.time())).save()
    return JsonResponse({"success": True})