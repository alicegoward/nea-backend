from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("", views.index, name="index"),
    path("add_location", views.location_update, name="add_location"),
    path("user/view/<str:user>/<str:password>", views.user_info, name="user"),
    path("user/add", views.add_user, name="user"),
    path("notifications/<str:user>", views.show_notification, name="show_notifications"),
    path("notifications/add/<str:user>", views.create_notification, name="create_notifications"),
    path("friends/<str:user>", views.get_friends, name="get_friends"),
    path("add_friend", views.add_friend, name="add_friend"),
    path("friend_requests/<str:user>", views.get_pending_requests, name="get_pending_requests"),
    path("update_friend_state", views.update_friend_state, name="update_friend_state")

]   