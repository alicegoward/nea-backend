import time

from api.models import Notification, UserOnRoute


def show_notifications_data(user: object) -> dict[int, str]:
    """
    :param user: User
    :return: Dictionary of notifications data, which are then deleted from the database.
    """
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=user).all().delete()
    return data


def notify_others_data(data: dict[str, str], user: str) -> None:
    """
    :param data: Route which the notification is pertaining to, and what the notification
    :param user: User sending the notification.
    """
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=user):
        Notification(user=i.user.username, notification=data["data"], datetime=int(time.time())).save()
