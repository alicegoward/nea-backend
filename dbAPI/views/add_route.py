from json import loads

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from dbAPI.graph_logic.nodes import GeoPoint
from dbAPI.graph_logic.utils import get_junction_name
from dbAPI.models import Route, UserOnRoute, User


def add_route(request: WSGIRequest) -> JsonResponse:
    data = loads(request.body)
    route = Route(
        user=data["username"],
        end_lat=data["lat"],
        end_long=data["long"],
        end_time=data["endTime"],
        routeName=data["name"],
        junction_name=get_junction_name(GeoPoint(data["lat"], data["long"]))
    )
    route.save()
    UserOnRoute(user=User.objects.get(username=route.user), route=route).save()
    for i in data["friends"].values():
        UserOnRoute(user=User.objects.get(username=i), route=route).save()
    return JsonResponse({"success": True})