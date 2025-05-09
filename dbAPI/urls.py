from django.urls import path

from .views import routing, add_route, update_route_data, user_management, notifications

urlpatterns = [
    path("add_location", routing.location_update, name="add_location"),

    path("route/create", add_route.add_route, name = "add_route"),
    path("route/update", update_route_data.update_route, name ="update route"),
    path("get_route/<str:user>", update_route_data.getRoutes, name="get_route"),
    path("route/deactivate/<str:user>", update_route_data.deactivate, name="deactivate"),
    path("route/sample", routing.sampleRoute, name = "sample_route"),
    path("route/get_individual_config", update_route_data.get_individual_config, name = "get_individual_config"),
    path("route/set_individual_config", update_route_data.set_individual_config, name="set_individual_config"),
    path("route/notify_others", notifications.notify_others, name="notify_others"),

    path("user/login", user_management.user_info, name="user_login"),
    path("user/add", user_management.add_user, name="user_add"),
    path("user/update_friend_state", user_management.update_friend_state, name="update_friend_state"),
    path("user/add_friend", user_management.add_friend, name="add_friend"),
    path("user/friends/<str:user>", user_management.get_friends, name="get_friends"),
    path("user/notifications/<str:user>", notifications.show_notification, name="show_notifications"),

]   