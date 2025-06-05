import time
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils.timezone import now

from api.models import Path, UserOnRoute, Notification, Waypoint, PathNode, Route, User
from services.graph_logic.nodes import GeoPoint
from services.graph_logic.route_geometry import get_other_geometry
from services.graph_logic.utils import get_total_time, latlong, get_total_dist, get_itineraries, get_junction_name
from services.route_logic.activate_route import ActivateRoute


def location_update_data(data: dict[str, Any], user: str) -> dict[str, Any]:
    """
    Updates the route by moving the user onto the next edge (possibly skipping some).
    If they have gone off course in terms of time or distance, deletes the path and reactivates the route, notifying them.
    :param data: New location data
    :param user: User
    :return: New information about the route
    """
    path = Path.objects.select_related('current_location').filter(account__username=user).first()
    if path is None:
        return {"geometry": {}, "dist": 0, "other_paths": {}, "waypoints": {}, "itineraries": {}}
    path.current_location.datetime = data["datetime"]
    path.current_location.lat = data["position"]["lat"]
    path.current_location.long = data["position"]["long"]
    path.current_location.save()
    data["route"] = path.related_route.routeName
    if path.start_node is None:
        return {"geometry": {}, "dist": 0, "other_paths": {}, "waypoints": {}, "itineraries": {}}
    previous_node = path.start_node
    current_node = previous_node.child_node
    geometry_path = [settings.G.graph[current_node.node_id].position]
    if current_node.child_node is not None:
        next_node = current_node.child_node
        closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id,
                                                                  GeoPoint(path.current_location.lat,
                                                                           path.current_location.long))
        # updates position along route by moving onto a later edge
        while closest_lines_to_node[next_node.node_id] < closest_lines_to_node[previous_node.node_id]:
            path.start_node = current_node
            previous_node.delete()
            previous_node = current_node
            current_node = next_node
            if next_node is None or current_node is None: break
            next_node = current_node.child_node
            closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id,
                                                                      GeoPoint(path.current_location.lat,
                                                                               path.current_location.long))
        if closest_lines_to_node[previous_node.node_id] > UserOnRoute.objects.get(user=path.account,
                                                                                  route=path.related_route).reroute_tolerance_m:
            Notification(notification="gone off course (distance)", user=user, datetime=int(time.time())).save()
            return ActivateRoute(data, user, path).get_result()
        # forms new geometry
        while next_node is not None:
            geometry = list(settings.G.graph[current_node.node_id].neighbours[next_node.node_id].geometry)
            if geometry[0] == geometry_path[-1]:
                geometry_path += geometry
            else:
                geometry_path += geometry[::-1]
            current_node = next_node
            next_node = current_node.child_node
    geometry_path.insert(0, GeoPoint(path.current_location.lat, path.current_location.long))
    path.offset_from_start = ((path.current_location.lat - settings.G.graph[
        path.start_node.node_id].position.lat) ** 2 +
                              (path.current_location.long - settings.G.graph[
                                  path.start_node.node_id].position.long) ** 2) ** (1 / 2)
    if abs((now() - path.eta + timedelta(
            seconds=get_total_time(path))).total_seconds()) > UserOnRoute.objects.get(user=path.account,
                                                                                      route=path.related_route).auto_notify_late:
        Notification(notification="gone off course (time)", user=user, datetime=int(time.time())).save()
        return ActivateRoute(data, user, path).get_result()
    path.save()
    waypoint_nodes = [PathNode.objects.filter(waypoint=i).all().first() for i in Waypoint.objects.all()]
    return {"geometry": latlong(geometry_path),
            "dist": get_total_dist(path),
            "other_paths": get_other_geometry(path),
            "waypoints": latlong([settings.G.graph[i.node_id].position for i in waypoint_nodes if i is not None]),
            "itineraries": get_itineraries(path.related_route)}


def add_route_data(data: dict[str, int | str], user: str) -> None:
    """
    :param data: information about the route to create
    :param user: user creating the route (who will be the route admin)
    """
    route = Route(
        user=data["username"],
        end_lat=data["lat"],
        end_long=data["long"],
        end_time=data["endTime"],
        routeName=data["name"],
        junction_name=get_junction_name(GeoPoint(data["lat"], data["long"]))
    )
    route.save()
    UserOnRoute(user=user, route=route).save()
    for i in data["friends"].values():
        UserOnRoute(user=User.objects.get(username=i), route=route).save()
