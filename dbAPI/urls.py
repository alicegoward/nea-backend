from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("", views.index, name="index"),
    path("add_location", views.location_update, name="add_location"),
    path("user/view/<str:user>/<str:password>", views.user_info, name="user"),
    path("user/add", views.add_user, name="user"),
    path("notifications/<str:user>", views.show_notification, name="show_notifications"),
    path("notifications/add/<str:user>", views.create_notification, name="create_notifications")
]   