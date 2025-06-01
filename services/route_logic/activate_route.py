import time
from typing import Any

from django.db.models import Exists, Subquery


from django.conf import settings

from services.graph_logic.nodes import GeoPoint, NodeWithOffset
from services.graph_logic.route_geometry import get_other_geometry, route_from_nodes
from services.graph_logic.utils import cleanup_path, get_total_dist, latlong, get_itineraries, fix_waypoints
from api.models import Route, User, Path, UserOnRoute, Waypoint, PathNode, LocationData, Notification


def activate_route(data: dict, user: User, path_db: Path|None = None) -> dict[str, Any]:
    start_coord = GeoPoint(data["position"]["lat"], data["position"]["long"])
    based_on_route = Route.objects.get(routeName=data["route"])
    other_paths = (Path.objects.filter(related_route=based_on_route).exclude(account=user)
                   .annotate(
        has_mor=Exists(UserOnRoute.objects.filter(user='account', route=based_on_route, create_mor=True)),
        mor_tolerance_s=Subquery(
            UserOnRoute.objects.filter(user='account', route=based_on_route).values('mor_tolerance_s'))
    ).filter(has_mor=True).all())

    if path_db is None:
        path_db = Path(account=user, related_route=based_on_route)
    else:
        cleanup_path(path_db)
    max_time_millis = based_on_route.end_time - data["datetime"] + UserOnRoute.objects.get(user=user,
                                                                                           route=based_on_route).mor_tolerance_s
    max_dist = max_time_millis * 4800 / (60 * 60)
    end_coord = GeoPoint(based_on_route.end_lat, based_on_route.end_long)
    joiner_mor_tolerance_m = UserOnRoute.objects.get(user=user, route=based_on_route).mor_tolerance_s * 4800 / (60 * 60)

    a, b = settings.G.closest_pair_from_lat_long(start_coord)
    end = settings.G.closest_from_lat_long(end_coord)
    if ((settings.G.graph[a].position.long - end_coord.long) ** 2 + (
            settings.G.graph[a].position.lat - end_coord.lat) ** 2 <
            (settings.G.graph[b].position.long - end_coord.long) ** 2 + (
                    settings.G.graph[b].position.lat - end_coord.lat) ** 2):
        start = a
        not_start = b
        route_start_offset = (settings.G.graph[b].position.long - end_coord.long) ** 2 + (
                settings.G.graph[b].position.lat - end_coord.lat) ** 2
    else:
        start = b
        not_start = a
        route_start_offset = (settings.G.graph[a].position.long - end_coord.long) ** 2 + (
                settings.G.graph[a].position.lat - end_coord.lat) ** 2
    path_db.offset_from_start = route_start_offset
    meeting_node = None
    meeting_path = None
    path_from_end = dict()
    paths_could_meet = dict()
    set_paths: dict[Path, list[NodeWithOffset]] = dict()  # THESE ARE ALL NODES !!!!
    movable_paths: dict[Path, NodeWithOffset] = dict()  # THESE ARE START NODES !!!!
    move_other_path = True

    route = settings.G.dijkstra(start, (end,))
    if route[end].dist < max_dist:
        for path in other_paths:
            total_path_dist = path.start_node.dist_to_end - path.offset_from_start
            nodes_to_add = [path.start_node]
            waiting_offset = 0
            while nodes_to_add[-1].child_node is not None:
                next_node = nodes_to_add[-1].child_node
                if next_node.waypoint is not None:
                    set_paths[path] = [NodeWithOffset(i.node_id, total_path_dist - i.dist_to_end + waiting_offset) for i
                                       in nodes_to_add]
                    waiting_offset += next_node.dist_waiting_at_node
                    nodes_to_add = []
                nodes_to_add.append(next_node)
            movable_paths[path] = NodeWithOffset(nodes_to_add[0].node_id,
                                                 total_path_dist - nodes_to_add[0].dist_to_end + waiting_offset)

        path_from_end = settings.G.dijkstra(end, tuple([start] + [i.node_id for i in movable_paths.values()]))
        min_dist_until_meet = float('inf')

        # CHECK MOVABLE PATHS
        for path, path_start in movable_paths.items():
            paths_could_meet[path] = settings.G.dijkstra(path_start.node_id, (end,))

        for node in route:
            for path, nodes in paths_could_meet.items():
                if node in nodes and node in path_from_end:
                    dist_new_a = path_from_end[node].dist + route[node].dist - route_start_offset
                    dist_old_a = route[end].dist - route_start_offset
                    dist_new_b = path_from_end[node].dist + nodes[node].dist + movable_paths[path].dist_from_now
                    dist_old_b = nodes[end].dist + movable_paths[path].dist_from_now
                    distance_difference_to_node = nodes[node].dist + movable_paths[path].dist_from_now - (
                            route[node].dist - route_start_offset)
                    if distance_difference_to_node > 0:
                        dist_new_b += distance_difference_to_node
                    else:
                        dist_new_a -= distance_difference_to_node
                    mor_tolerance_m = min(joiner_mor_tolerance_m, UserOnRoute.objects.get(user=path.account,
                                                                                          route=based_on_route).mor_tolerance_s * 4800 / (
                                                      60 * 60))
                    if (abs(distance_difference_to_node) < mor_tolerance_m and route[
                        node].dist - route_start_offset < min_dist_until_meet
                            and dist_new_a - dist_old_a < mor_tolerance_m and dist_new_b - dist_old_b < mor_tolerance_m
                            and dist_new_a < max_dist and dist_new_b < max_dist):
                        meeting_node = node
                        meeting_path = path
                        min_dist_until_meet = route[node].dist - route_start_offset

        # CHECK SET PATHS
        for path, node_list in set_paths.items():
            for node in node_list:
                if node.node_id in route and node.node_id in path_from_end:
                    mor_tolerance_m = min(joiner_mor_tolerance_m, UserOnRoute.objects.get(user=path.account,
                                                                                          route=based_on_route).mor_tolerance_s * 4800 / (
                                                      60 * 60))
                    total_path_dist = route[node.node_id].dist + path_from_end[node.node_id].dist - route_start_offset
                    dist_old = route[end].dist - route_start_offset
                    distance_difference_to_node = node.dist_from_now - route[node.node_id].dist
                    if distance_difference_to_node < mor_tolerance_m and total_path_dist - dist_old < mor_tolerance_m:
                        if route[node.node_id].dist - route_start_offset < min_dist_until_meet:
                            meeting_node = node.node_id
                            meeting_path = path
                            move_other_path = False
                            min_dist_until_meet = route[node.node_id].dist - route_start_offset

    waypoint_list = Waypoint.objects.all()
    waypoints = dict()

    for i in waypoint_list:
        node = PathNode.objects.filter(waypoint=i).all().first()
        if node is not None: waypoints[node.node_id] = i
    new_waypoint = None
    if meeting_node is not None:
        if meeting_node not in waypoints.keys():
            new_waypoint = Waypoint()
            new_waypoint.save()
            waypoints[meeting_node] = new_waypoint
        else:
            new_waypoint = waypoints[meeting_node]
            new_waypoint.save()

    path_db.current_location = LocationData(datetime=data["datetime"], lat=data["position"]["lat"],
                                            long=data["position"]["long"])
    path_db.current_location.save()

    if meeting_node is not None:
        main_path_geometry = route_from_nodes(not_start, start, end, route, path_from_end, meeting_node, waypoints,
                                              path_db)
        if move_other_path:
            moving_paths = [i[0] for i in movable_paths.items() if i[1].node_id == movable_paths[meeting_path].node_id]
            for path_to_move in moving_paths:
                route_from_nodes(None, movable_paths[path_to_move].node_id, end, paths_could_meet[path_to_move], path_from_end,
                             meeting_node, waypoints, path_to_move)
        paths_to_move_nodes = PathNode.objects.filter(node_id=meeting_node)
        for i in paths_to_move_nodes:
            i.waypoint = new_waypoint
            i.save()
        fix_waypoints(waypoints)
        new_waypoint.save()
        for i in PathNode.objects.all():
            if i.waypoint == new_waypoint:
                Notification(
                    user=i.path_on.account.username,
                    notification="new meeting place",
                    datetime=int(time.time())
                ).save()
    else:
        main_path_geometry = route_from_nodes(not_start, start, end, route, path_from_end, None, waypoints, path_db)

    print(main_path_geometry)

    if path_db.eta.timestamp() - 5 > based_on_route.end_time:
        for i in UserOnRoute.objects.filter(route=based_on_route).exclude(user=user):
            Notification(user=i.user.username,
                         notification=f"{user.username} is running {int((path_db.eta.timestamp() - based_on_route.end_time) / 60)} minutes late",
                         datetime=int(time.time())).save()

    data = {}
    for idx, point in enumerate(main_path_geometry):
        data[idx] = {"lat": point.lat, "long": point.long}
    return {"geometry": data,
            "dist": get_total_dist(path_db),
            "other_paths": get_other_geometry(path_db),
            "waypoints": latlong([settings.G.graph[i].position for i in waypoints.keys()]),
            "itineraries": get_itineraries(based_on_route)}
