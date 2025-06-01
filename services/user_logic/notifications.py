import time

from api.models import Notification, UserOnRoute


def show_notifications_data(user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=user).all().delete()
    return data


def notify_others_data(data, user):
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=user):
        Notification(user=i.username, notification=data["data"], datetime=int(time.time())).save()