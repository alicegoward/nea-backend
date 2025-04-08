from django.urls import path

from . import views

urlpatterns = [
    path("location/add", views.location_update, name="add_location"),

    path("route/create", views.add_route, name = "add_route"),

    path("user/login", views.user_info, name="user"),
    path("user/add", views.add_user, name="user"),
    path("user/update_friend_state", views.update_friend_state, name="update_friend_state"),
    path("user/add_friend", views.add_friend, name="add_friend"),
    path("user/friends/<str:user>", views.get_friends, name="get_friends"),
    path("user/notifications/<str:user>", views.show_notification, name="show_notifications"),

]   