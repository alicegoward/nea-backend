from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse

from .models import Location_data, User, Notification, Route, Path, PathNode, Waypoint, UserOnRoute
import time
from django.db.models import Q, Subquery, OuterRef, Exists
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
from dbAPI.graph import GeoPoint, NodeWithOffset


def getJunctionName(point):
    checked = set()
    junction_name = ""
    while junction_name == "":
        end_node = settings.G.closest_from_lat_long(point, checked)
        junction_name += ", ".join(
            set([i.name for i in settings.G.graph[end_node].neighbours.values() if i.name != "unnamed road"]))
        checked.add(end_node)
    return junction_name


def add_route(request):
    data = loads(request.body)
    route = Route(
        user=data["username"],
        end_lat=data["lat"],
        end_long=data["long"],
        end_time=data["endTime"],
        routeName=data["name"],
        junction_name=getJunctionName(GeoPoint(data["lat"], data["long"]))
    )
    route.save()
    UserOnRoute(user=User.objects.get(username=route.user), route=route).save()
    for i in data["friends"].values():
        UserOnRoute(user=User.objects.get(username=i), route=route).save()
    return JsonResponse({"success": True})


def update_route(request):
    data = loads(request.body)
    route = Route.objects.get(routeName=data["route"])
    if "time" in data:
        route.end_time = int(data["time"])
    elif "lat" in data:
        route.end_lat = float(data["lat"])
        route.end_long = float(data["long"])
        route.junction_name = getJunctionName(GeoPoint(route.end_lat, route.end_long))
    else:
        UserOnRoute.objects.filter(route=route).delete()
        for i in data.items():
            if i[0] != "route":
                UserOnRoute(route=route, user=User.objects.get(username=i[1])).save()

    return JsonResponse({"success": True})


def get_other_geometry(path: Path):
    other_paths = Path.objects.filter(related_route=path.related_route).exclude(id=path.id)
    data = dict()
    for path in other_paths:
        if path.start_node is None: return data
        previous_node = path.start_node
        current_node = previous_node.child_node
        next_node = current_node.child_node
        geometry_path = [settings.G.graph[current_node.node_id].position]
        while next_node is not None:
            geometry = list(settings.G.graph[current_node.node_id].neighbours[next_node.node_id].geometry)
            if geometry[0] == geometry_path[-1]:
                geometry_path += geometry
            else:
                geometry_path += geometry[::-1]
            current_node = next_node
            next_node = current_node.child_node
        geometry_path.insert(0, GeoPoint(path.current_location.lat, path.current_location.long))
        path_data = {}
        for idx, point in enumerate(geometry_path):
            path_data[idx] = {"lat": point.lat, "long": point.long}
        data[path.account.username] = path_data
    return data


def fix_waypoints(waypoints):
    for waypoint in waypoints.values():
        nodes_at_waypoint = PathNode.objects.filter(waypoint=waypoint).all()
        if len(nodes_at_waypoint) < 2:
            for node in nodes_at_waypoint:
                node.waypoint = None
                node.save()
                Notification(
                    user=node.path_on.account,
                    notification=f"The meeting at {settings.G.graph[node.node_id].position} has been cancelled.",
                    datetime=int(time.time())
                ).save()
            waypoint.delete()
        else:
            max_dist_to_end = max(nodes_at_waypoint, key=lambda k: k.dist_to_end).dist_to_end
            for node in nodes_at_waypoint:
                node.dist_waiting_at_node = max_dist_to_end - node.dist_to_end
                node.save()


def get_total_dist(path: Path):
    return path.start_node.dist_to_end - path.offset_from_start + sum(
        i.dist_waiting_at_node for i in PathNode.objects.filter(path_on=path).all())


def latlong(nodes):
    data = {}
    for idx, point in enumerate(nodes):
        data[idx] = {"lat": point.lat, "long": point.long}
    return data


def route_from_nodes(not_start, start, end, path_from_start, path_from_end, meeting_node, waypoints, path_db):
    node_list = []
    if meeting_node is not None:
        node = meeting_node
        after_node = []
        while node != end:
            node = path_from_end[node].parent
            after_node.append(node)
        node_list += after_node[::-1]
        node = meeting_node
        before_node = [meeting_node]
        while node != start:
            node = path_from_start[node].parent
            before_node.append(node)
        node_list += before_node
    else:
        node = end
        node_list.append(node)
        while node != start and node in path_from_start:
            node = path_from_start[node].parent
            node_list.append(node)
    route_start = []
    if not_start is None:
        node = path_db.start_node
        while node.node_id != start:
            route_start.append(node.node_id)
            node = node.child_node
    else:
        route_start.append(not_start)
    node_list += route_start[::-1]

    nodes_db = [PathNode(node_id=node_list[0], path_on=path_db, dist_to_end=0)]
    main_path_geometry = [settings.G.graph[node_list[0]].position]
    for node in node_list[1:]:
        prev_node = nodes_db[-1]
        nodes_db.append(PathNode(node_id=node,
                                 path_on=path_db,
                                 dist_to_end=prev_node.dist_to_end + settings.G.graph[prev_node.node_id].neighbours[
                                     node].length))
        if node in waypoints: nodes_db[-1].waypoint = waypoints[node]
        path_section = list(settings.G.graph[prev_node.node_id].neighbours[node].geometry)
        if path_section[0] == main_path_geometry[-1]:
            main_path_geometry += path_section
        else:
            main_path_geometry += path_section[::-1]
    try:
        path_db.save()
    except:
        pass
    for i in nodes_db: i.save()
    path_db.save()
    for i in range(len(nodes_db) - 1):
        nodes_db[i].parent_node = nodes_db[i + 1]
        nodes_db[i + 1].child_node = nodes_db[i]
    for i in nodes_db: i.save()
    path_db.start_node = nodes_db[-1]
    path_db.end_node = nodes_db[0]
    old_nodes = PathNode.objects.filter(path_on=path_db).exclude(id__in=[i.id for i in nodes_db])
    for i in old_nodes: i.delete()
    path_db.save()
    path_db.eta = now() + timedelta(seconds=get_total_dist(path_db) / 1.34)
    path_db.save()
    return main_path_geometry


def cleanup_path(path_db: Path):
    all_waypoints = Waypoint.objects.all()
    waypoints = dict()
    for i in all_waypoints:
        node = PathNode.objects.filter(waypoint=i).all().first()
        if node is not None: waypoints[node] = i
    node = path_db.start_node
    while node != path_db.end_node:
        next_node = node.child_node
        node.delete()
        node = next_node
    path_db.start_node.delete()
    path_db.start_node = None
    path_db.end_node.delete()
    path_db.end_node = None
    path_db.save()
    fix_waypoints(waypoints)


def activate_route(data, path_db=None):
    start_coord = GeoPoint(data["position"]["lat"], data["position"]["long"])
    based_on_route = Route.objects.get(routeName=data["route"])
    user = User.objects.get(username=data["user"])

    other_paths = (Path.objects.filter(related_route=based_on_route).exclude(account=user)
                   .annotate(
        has_mor=Exists(UserOnRoute.objects.filter(user=OuterRef('account'), route=based_on_route, create_mor=True)),
        mor_tolerance_s=Subquery(
            UserOnRoute.objects.filter(user=OuterRef('account'), route=based_on_route).values('mor_tolerance_s'))
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
    print("MEETING NODE!!!", meeting_node)

    for i in waypoint_list:
        node = PathNode.objects.filter(waypoint=i).all().first()
        if node is not None: waypoints[node.node_id] = i
    new_waypoint = None
    if meeting_node is not None:
        print("these are the waypoints",waypoints, meeting_node)
        if meeting_node not in waypoints.keys():
            new_waypoint = Waypoint()
            new_waypoint.save()
            waypoints[meeting_node] = new_waypoint
        else:
            new_waypoint = waypoints[meeting_node]
            new_waypoint.save()

    path_db.current_location = Location_data(datetime=data["datetime"], lat=data["position"]["lat"],
                                             long=data["position"]["long"])
    path_db.current_location.save()

    # modify other route for connecting with set path (if applicable)
    if meeting_node is not None:
        main_path_geometry = route_from_nodes(not_start, start, end, route, path_from_end, meeting_node, waypoints,
                                              path_db)
        if move_other_path:
            route_from_nodes(None, movable_paths[meeting_path].node_id, end, paths_could_meet[meeting_path], path_from_end,
                             meeting_node, waypoints, meeting_path)
        print(meeting_node)
        paths_to_move_nodes = PathNode.objects.filter(node_id=meeting_node)
        print(paths_to_move_nodes, paths_to_move_nodes.count())
        for i in paths_to_move_nodes:
            i.waypoint = new_waypoint
            i.save()
        fix_waypoints(waypoints)
        new_waypoint.save()
        print(new_waypoint)
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
    return JsonResponse({"geometry": data,
                         "dist": get_total_dist(path_db),
                         "other_paths": get_other_geometry(path_db),
                         "waypoints": latlong([settings.G.graph[i].position for i in waypoints.keys()]),
                         "itineraries": get_itineraries(based_on_route)})


def sampleRoute(request):
    return activate_route(loads(request.body))


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
        for j, friend in enumerate(User.objects.filter(useronroute__route=route)):
            route_data["friends"][j] = friend.username
        data["data"][i] = route_data
    return JsonResponse(data)


def get_itineraries(route: Route):
    paths = Path.objects.filter(related_route=route)
    out = dict()
    for path_idx, path in enumerate(paths):
        data = dict()
        data["username"] = path.account.username
        data["eta"] = path.eta.timestamp()
        data["waypoints"] = dict()
        for waypoint_idx, waypoint in enumerate(
                i.waypoint for i in PathNode.objects.filter(path_on=path).exclude(waypoint=None)):
            waypoint_data = {"participants": dict()}
            waypoint_participants = PathNode.objects.filter(waypoint=waypoint)
            for node_idx, participating_node in enumerate(waypoint_participants):
                waypoint_data["participants"][node_idx] = participating_node.path_on.account.username
            node = waypoint_participants[0]
            dist_to_end = node.dist_to_end
            while node is not None:
                dist_to_end += node.dist_waiting_at_node
                node = node.child_node
            waypoint_data["eta"] = (path.eta - timedelta(seconds=(dist_to_end * 60 * 60 / 4800))).timestamp()
            data["waypoints"][waypoint_idx] = waypoint_data
        out[path_idx] = data
    return out


def location_update(request):
    data = loads(request.body)
    path = Path.objects.select_related('current_location').filter(account__username=data["user"]).first()
    if path is None:
        return JsonResponse({"geometry": {}, "dist": 0, "other_paths": {}, "waypoints": {}, "itineraries": {}})
    path.current_location.datetime = data["datetime"]
    path.current_location.lat = data["position"]["lat"]
    path.current_location.long = data["position"]["long"]
    path.current_location.save()

    data["route"] = path.related_route.routeName

    if path.start_node is None: return JsonResponse(
        {"geometry": {}, "dist": 0, "other_paths": {}, "waypoints": {}, "itineraries": {}})
    previous_node = path.start_node
    current_node = previous_node.child_node
    geometry_path = [settings.G.graph[current_node.node_id].position]
    if current_node.child_node is not None:
        next_node = current_node.child_node
        closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id,
                                                                  GeoPoint(path.current_location.lat,
                                                                           path.current_location.long))
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
            Notification(notification="gone off course (distance)", user=data["user"], datetime=int(time.time())).save()
            return activate_route(data, path)

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
            seconds=get_total_dist(path) / 1.34)).total_seconds()) > UserOnRoute.objects.get(user=path.account,
                                                                                             route=path.related_route).auto_notify_late:
        Notification(notification="gone off course (time)", user=data["user"], datetime=int(time.time())).save()
        return activate_route(data, path)

    path.save()

    waypoint_nodes = [PathNode.objects.filter(waypoint=i).all().first() for i in Waypoint.objects.all()]
    return JsonResponse({"geometry": latlong(geometry_path),
                         "dist": get_total_dist(path),
                         "other_paths": get_other_geometry(path),
                         "waypoints": latlong(
                             [settings.G.graph[i.node_id].position for i in waypoint_nodes if i is not None]),
                         "itineraries": get_itineraries(path.related_route)})


def user_info(request):
    try:
        data = loads(request.body)
        user = model_to_dict(User.objects.get(username=data["username"], password=data["password"]))
        user["success"] = True
        user.pop("friends")
        return JsonResponse(user)
    except:
        return JsonResponse({"success": False, "reason": "username / password combination does not exist"})


def add_user(request):
    try:
        data = loads(request.body)
        if User.objects.filter(username=data["username"]).count() > 0:
            raise Exception
        User(username=data["username"], password=data["password"]).save()
        return JsonResponse({"success": True})
    except:
        return JsonResponse({"success": False, "reason": "user already taken"})


def deactivate(_, user):
    Path.objects.filter(account=User.objects.get(username=user)).delete()
    waypoints = dict()
    for i in Waypoint.objects.all():
        node = PathNode.objects.filter(waypoint=i).all().first()
        if node is not None: waypoints[node.node_id] = i
    fix_waypoints(waypoints)
    return JsonResponse({'success': True})


def show_notification(_, user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.filter(user=user).all().delete()
    return JsonResponse({"success": True, "notifications": data})


def get_friends(_, user):
    try:
        user = User.objects.get(username=user)
        friend_data = {}
        for i, friend in enumerate(user.friends.all()):
            friend_data[i] = friend.username
        incoming_data = {}
        for i, friend in enumerate(user.pending_friends.all()):
            incoming_data[i] = friend.username
        outgoing_data = {}
        for i, friend in enumerate(User.objects.filter(pending_friends=user)):
            outgoing_data[i] = friend.username
        return JsonResponse(
            {"success": True, "names": friend_data, "incoming": incoming_data, "outgoing": outgoing_data})
    except Exception as e:
        return JsonResponse({"success": False, "reason": str(e)})


def add_friend(request):
    try:
        data = loads(request.body)
        requesting = User.objects.get(username=data["userRequesting"])
        requested = User.objects.get(username=data["userRequested"])
        requested.pending_friends.add(requesting)
        Notification(
            user=requested.username,
            notification=f"{requesting} has requested to add you as a friend.",
            datetime=int(time.time())
        ).save()
        requesting.save()
        return JsonResponse({"success": True, "reason": "user successfully added"})
    except:
        return JsonResponse({"success": False, "reason": "user does not exist"})


def update_friend_state(request):
    data = loads(request.body)
    accepting = User.objects.get(username=data["userAccepting"])
    accepted = User.objects.get(username=data["userAccepted"])
    accepting.pending_friends.remove(accepted)
    if data["result"] == "accepted":
        accepting.friends.add(accepted)
        Notification(
            user=accepted.username,
            notification=f"{accepting} has accepted your friend request.",
            datetime=int(time.time())
        ).save()
    accepting.save()


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


def notify_others(request):
    data = loads(request.body)
    for i in UserOnRoute.objects.filter(route__routeName=data["route"]).exclude(user__username=data["user"]):
        Notification(user=i.user.username, notification=data["data"], datetime=int(time.time())).save()
    return JsonResponse({"success": True})
