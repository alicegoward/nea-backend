from json import loads

from django.db.models import Q
from django.http import JsonResponse

from dbAPI.graph_logic.nodes import GeoPoint
from dbAPI.graph_logic.utils import get_junction_name, fix_waypoints
from dbAPI.models import Route, UserOnRoute, User, Waypoint, PathNode, Path


def update_route(request):
    data = loads(request.body)
    route = Route.objects.get(routeName=data["route"])
    if "time" in data:
        route.end_time = int(data["time"])
    elif "lat" in data:
        route.end_lat = float(data["lat"])
        route.end_long = float(data["long"])
        route.junction_name = get_junction_name(GeoPoint(route.end_lat, route.end_long))
    else:
        UserOnRoute.objects.filter(route=route).delete()
        for i in data.items():
            if i[0] != "route":
                UserOnRoute(route=route, user=User.objects.get(username=i[1])).save()
    return JsonResponse({"success": True})

def get_individual_config(request):
    data = loads(request.body)
    user_on_route = UserOnRoute.objects.get(
        Q(user=User.objects.get(username=data["user"])) &
        Q(route=Route.objects.get(routeName=data["route"])))
    data["create_mor"] = user_on_route.create_mor
    data["mor_tolerance_s"] = user_on_route.mor_tolerance_s
    data["reroute_tolerance_m"] = user_on_route.reroute_tolerance_m
    data["auto_notify_late"] = user_on_route.auto_notify_late
    return JsonResponse(data)


def set_individual_config(request):
    data = loads(request.body)
    user_on_route = UserOnRoute.objects.get(
        Q(user=User.objects.get(username=data["user"])) &
        Q(route=Route.objects.get(routeName=data["route"])))
    user_on_route.create_mor = data["create_mor"]
    user_on_route.mor_tolerance_s = data["mor_tolerance_s"]
    user_on_route.reroute_tolerance_m = data["reroute_tolerance_m"]
    user_on_route.auto_notify_late = data["auto_notify_late"]
    user_on_route.save()
    return JsonResponse({"success": True})

def getRoutes(_, user):
    routes = Route.objects.filter(Q(useronroute__user=user))
    data = {"success": True, "data": {}}
    for i, route in enumerate(routes):
        route_data = {
            "username": route.user,
            "lat": route.end_lat,
            "long": route.end_long,
            "endTime": route.end_time,
            "name": route.routeName,
            "junction_name": route.junction_name,
            "friends": {}
        }
        for j, friend in enumerate(User.objects.filter(useronroute__route=route).exclude(user = route.user)):
            route_data["friends"][j] = friend.username
        data["data"][i] = route_data
    return JsonResponse(data)


def deactivate(_, user):
    Path.objects.filter(account=User.objects.get(username=user)).delete()
    waypoints = dict()
    for i in Waypoint.objects.all():
        node = PathNode.objects.filter(waypoint=i).all().first()
        if node is not None: waypoints[node.node_id] = i
    fix_waypoints(waypoints)
    return JsonResponse({'success': True})