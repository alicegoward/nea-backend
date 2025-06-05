from json import loads
from typing import Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from services.route_logic.routing import *
from services.route_logic.config import *
from services.user_logic.notifications import *
from services.user_logic.friends import *
from services.user_logic.login import *


def add_route(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: add_route_data(loads(request.body), request.user))

def show_notification(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: show_notifications_data(request.user))

def notify_others(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: notify_others_data(loads(request.body), request.user))

def location_update(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: location_update_data(loads(request.body), request.user))

def update_route(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: update_route_data(loads(request.body)))

def get_individual_config(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: get_individual_config_data(loads(request.body), request.user))

def set_individual_config(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: set_individual_config_data(loads(request.body),request.user))

def get_routes(request) -> JsonResponse:
    return send_request(lambda: get_routes_data(request.user))

def activate_route(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: ActivateRoute(loads(request.body), request.user).get_result())

def deactivate(request) -> JsonResponse:
    return send_request(lambda: deactivate_data(request.user))

def add_friend(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: add_friend_data(loads(request.body)),
                        "user does not exist",
                        206)

def update_friend_state(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: update_friend_state_data(loads(request.body)))

def get_friends(request) -> JsonResponse:
    return send_request(lambda: get_friends_data(request.user))

def login(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: {"token": login_data(loads(request.body))},
                        "username / password combination does not exist",
                        206)

def register(request: WSGIRequest) -> JsonResponse:
    return send_request(lambda: {"token": register_data(loads(request.body))},
                        "user already registered",
                        206)

def send_request(do_on_thing: Callable[[], dict | None], failure_reason: str | None=None, failure_status: int=500) -> JsonResponse:
    try:
        result = do_on_thing()
        if result is not None: return JsonResponse(result, status=200)
        else: return JsonResponse({}, status=200)
    except Exception as e:
        print(e)
        if failure_reason is not None:
            return JsonResponse({"reason": failure_reason}, status=failure_status)
        return JsonResponse({}, status=failure_status)
