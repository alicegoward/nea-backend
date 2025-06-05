from django.urls import path

import api.views as views

urlpatterns = [
    path("add_location", views.location_update, name="add_location"),

    path("route/create", views.add_route, name="add_route"),
    path("route/update", views.update_route, name="update route"),
    path("get_route", views.get_routes, name="get_route"),
    path("route/activate", views.activate_route, name="activate_route"),
    path("route/deactivate", views.deactivate, name="deactivate"),
    path("route/get_individual_config", views.get_individual_config, name="get_individual_config"),
    path("route/set_individual_config", views.set_individual_config, name="set_individual_config"),
    path("route/notify_others", views.notify_others, name="notify_others"),

    path("user/login", views.login, name="user_login"),
    path("user/register", views.register, name="user_register"),
    path("user/update_friend_state", views.update_friend_state, name="update_friend_state"),
    path("user/add_friend", views.add_friend, name="add_friend"),
    path("user/friends", views.get_friends, name="get_friends"),
    path("user/notifications", views.show_notification, name="show_notifications"),

]
