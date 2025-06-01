from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

import services.route_logic as route_logic
import services.user_logic as user_logic


def add_route(request: WSGIRequest) -> JsonResponse:
    route_logic.routing.add_route_data(loads(request.body), request.user)
    return JsonResponse({"success": True})

def show_notification(request: WSGIRequest) -> JsonResponse:
    data = user_logic.notifications.show_notifications_data(request.user)
    return JsonResponse({"success": True, "notifications": data})

def notify_others(request: WSGIRequest) -> JsonResponse:
    user_logic.notifications.notify_others_data(loads(request.body), request.user)
    return JsonResponse({"success": True})

def location_update(request: WSGIRequest) -> JsonResponse:
    return JsonResponse(route_logic.routing.location_update_data(loads(request.body), request.user))

def update_route(request: WSGIRequest) -> JsonResponse:
    data = loads(request.body)
    route_logic.config.update_route_data(data)
    return JsonResponse({"success": True})

def get_individual_config(request: WSGIRequest) -> JsonResponse:
    data = route_logic.config.get_individual_config_data(loads(request.body), request.user)
    return JsonResponse(data)

def set_individual_config(request: WSGIRequest) -> JsonResponse:
    route_logic.config.set_individual_config_data(loads(request.body), request.user)
    return JsonResponse({"success": True})

def get_routes(request) -> JsonResponse:
    data = route_logic.config.get_routes_data(request.user)
    return JsonResponse(data)

def deactivate(request) -> JsonResponse:
    route_logic.config.deactivate_data(request.user)
    return JsonResponse({'success': True})


def add_friend(request: WSGIRequest) -> JsonResponse:
    try:
        user_logic.friends.add_friend_data(loads(request.body))
        return JsonResponse({"success": True, "reason": "user successfully added"})
    except:
        return JsonResponse({"success": False, "reason": "user does not exist"})


def update_friend_state(request: WSGIRequest) -> JsonResponse:
    user_logic.friends.update_friend_state_data(loads(request.body))
    return JsonResponse({"success": True})

def get_friends(request) -> JsonResponse:
    try:
        return JsonResponse(user_logic.friends.get_friends_data(request.user))
    except Exception as e:
        return JsonResponse({"success": False, "reason": str(e)})


def login(request: WSGIRequest) -> JsonResponse:
    try:
        token = user_logic.login.login_data(request.body)
        return JsonResponse({"success": True, "token": token})
    except Exception as e:
        return JsonResponse({"success": False, "reason": "username / password combination does not exist"})


def register(request: WSGIRequest) -> JsonResponse:
    try:
        user = user_logic.login.register_data(loads(request.body))
        return JsonResponse({"success": True, "token": user.token})
    except:
        return JsonResponse({"success": False, "reason": "user already taken"})