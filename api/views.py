from json import loads
from typing import Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from services.route_logic.config import *
from services.route_logic.routing import *
from services.user_logic.friends import *
from services.user_logic.login import *
from services.user_logic.notifications import *


def add_route(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Route information
    :return: Empty JsonResponse
    """
    return send_request(lambda: add_route_data(loads(request.body), request.user))

def delete_route(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Route name
    :return: Empty JsonResponse
    """
    return send_request(lambda: delete_route_data(loads(request.body), request.user))


def show_notification(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Request for user's pending notifications
    :return: List of notifications
    """
    return send_request(lambda: {"notifications": show_notifications_data(request.user)})


def notify_others(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Information about what to notify
    :return: Empty JsonResponse
    """
    return send_request(lambda: notify_others_data(loads(request.body), request.user))


def location_update(request: WSGIRequest) -> JsonResponse:
    """
    :param request: New location information
    :return: New route geometry
    """
    return send_request(lambda: location_update_data(loads(request.body), request.user))


def update_route(request: WSGIRequest) -> JsonResponse:
    """
    :param request: New data about the route
    :return: Empty JsonResponse
    """
    return send_request(lambda: update_route_data(loads(request.body)))


def get_individual_config(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Who and what route to get data for
    :return: User's current configuration of the route
    """
    return send_request(lambda: get_individual_config_data(loads(request.body), request.user))


def set_individual_config(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Data to set, who and what to set it for
    :return: Empty JsonResponse
    """
    return send_request(lambda: set_individual_config_data(loads(request.body), request.user))


def get_routes(request) -> JsonResponse:
    """
    :param request: User to get routes for
    :return: Routes the user is a participant of
    """
    return send_request(lambda: get_routes_data(request.user))


def activate_route(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Which route to activate, user's current state
    :return: Route geometry + waypoints
    """
    return send_request(lambda: ActivateRoute(loads(request.body), request.user).get_result())


def deactivate(request) -> JsonResponse:
    """
    :param request: User to deactivate path
    :return: Empty JsonResponse:
    """
    return send_request(lambda: deactivate_data(request.user))


def add_friend(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Requesting + requested users
    :return: Either error reason or empty JsonResponse
    """
    return send_request(lambda: add_friend_data(loads(request.body)),
                        "user does not exist",
                        206)


def update_friend_state(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Accepting + accepted users
    :return: Empty JsonResponse
    """
    return send_request(lambda: update_friend_state_data(loads(request.body)))


def get_friends(request) -> JsonResponse:
    """
    :param request: User to get friends for
    :return: User's pending and full friends lists
    """
    return send_request(lambda: get_friends_data(request.user))


def login(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Username and password to log in with
    :return: Authentication token or error message
    """
    return send_request(lambda: {"token": login_data(loads(request.body))},
                        "username / password combination does not exist",
                        206)


def register(request: WSGIRequest) -> JsonResponse:
    """
    :param request: Username and password to register
    :return: Authentication token or error message
    """
    return send_request(lambda: {"token": register_data(loads(request.body))},
                        "user already registered",
                        206)


def send_request(do_on_thing: Callable[[], dict | None], failure_reason: str | None = None,
                 failure_status: int = 500) -> JsonResponse:
    """
    Wrapper function for calling any logical functions - extracts the JsonResponse call and handles errors
    :param do_on_thing: lambda of the function that will perform the operation, called in a try/except block for error handling
    :param failure_reason: If relevant (failure for reasons other than server error), the cause of the failure
    :param failure_status: HTTP status code of the cause of the failure (default is 500 server error)
    :return: JsonResponse containing the return value of the lambda (empty if lambda returns none)
    """
    try:
        result = do_on_thing()
        if result is not None:
            return JsonResponse(result, status=200)
        else:
            return JsonResponse({}, status=200)
    except Exception as e:
        print(e)
        if failure_reason is not None:
            return JsonResponse({"reason": failure_reason}, status=failure_status)
        return JsonResponse({}, status=failure_status)
