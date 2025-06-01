from json import loads
from typing import Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

import services.route_logic as route_logic
import services.user_logic as user_logic


def add_route(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: route_logic.routing.add_route_data(loads(request.body), request.user))

def show_notification(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: user_logic.notifications.show_notifications_data(request.user))

def notify_others(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: user_logic.notifications.notify_others_data(loads(request.body), request.user))

def location_update(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: route_logic.routing.location_update_data(loads(request.body), request.user))

def update_route(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: route_logic.config.update_route_data(loads(request.body)))

def get_individual_config(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: route_logic.config.get_individual_config_data(loads(request.body), request.user))

def set_individual_config(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: route_logic.config.set_individual_config_data(loads(request.body),request.user))

def get_routes(request) -> JsonResponse:
    return send_request(lambda: route_logic.config.get_routes_data(request.user))

def deactivate(request) -> JsonResponse:
    return send_request(lambda: route_logic.config.deactivate_data(request.user))

def add_friend(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: user_logic.friends.add_friend_data(loads(request.body)))

def update_friend_state(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: user_logic.friends.update_friend_state_data(loads(request.body)))

def get_friends(request) -> JsonResponse:
    return send_request(lambda: user_logic.friends.get_friends_data(request.user))

def login(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: {"token": user_logic.login.login_data(loads(request.body))},
                        "username / password combination does not exist",
                        409)

def register(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: {"token": user_logic.login.login_data(loads(request.body))},
                        "user already registered",
                        409)

def send_request(do_on_thing: Callable[[], dict | None], failure_reason: str | None=None, failure_status: int=500) -> JsonResponse:
    try:
        result = do_on_thing()
        if result is not None: return JsonResponse(result, status=200)
        else: return JsonResponse({}, status=200)
    except Exception as e:
        print(e)
        if failure_reason: return JsonResponse({"reason": failure_reason}, status=failure_status)
        return JsonResponse({}, status=failure_status)
