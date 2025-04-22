from django.urls import path

from . import views

urlpatterns = [
    path("add_location", views.location_update, name="add_location"),

    path("route/create", views.add_route, name = "add_route"),
    path("route/update", views.update_route, name = "update route"),
    path("get_route/<str:user>", views.getRoutes, name="get_route"),
    path("route/deactivate/<str:user>", views.deactivate, name="deactivate"),
    path("route/sample", views.sampleRoute, name = "sample_route"),

    path("user/login", views.user_info, name="user_login"),
    path("user/add", views.add_user, name="user_add"),
    path("user/update_friend_state", views.update_friend_state, name="update_friend_state"),
    path("user/add_friend", views.add_friend, name="add_friend"),
    path("user/friends/<str:user>", views.get_friends, name="get_friends"),
    path("user/notifications/<str:user>", views.show_notification, name="show_notifications"),

]   