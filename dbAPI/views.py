from json import loads
from django.forms.models import model_to_dict
from django.http import JsonResponse

from .models import Location_data, User, Notification, Route, Path, PathNode, Waypoint
from random import randint
import time
from django.db.models import Q
from django.conf import settings
from dbAPI.graph import GeoPoint, NodeWithOffset


def add_route(request):
    try:
        data = loads(request.body)
        print("some route data", data)
        route = Route(
            user=data["username"],
            end_lat=data["lat"],
            end_long=data["long"],
            end_time=data["endTime"],
            routeName=data["name"]
        )
        route.save()
        print(route)
        for i in data["friends"].values():
            route.participants.add(User.objects.get(username=i))
        return JsonResponse({"success": True})
    except Exception as e:
        print(e)
        return JsonResponse({"success": False, "reason": "unknown error"})
    
def get_other_geometry(path: Path):
    other_paths = Path.objects.filter(related_route=path.related_route).exclude(id=path.id)
    data = dict()
    for path in other_paths:
        previous_node = path.start_node
        current_node = previous_node.child_node
        next_node = current_node.child_node
        geometry_path = [settings.G.graph[current_node.node_id].position]
        while next_node != None:
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

    

def route_from_nodes(not_start, start, end, path_from_start, path_from_end, meeting_node, waypoints, path_db):
    print(not_start, start, end, path_from_start, path_from_end, meeting_node, waypoints, path_db)
    print(start, meeting_node, end)
    print("path from end:")
    [print(f"{i[0]}: f{i[1]}") for i in path_from_end.items()]
    print("path from start")
    [print(f"{i[0]}: f{i[1]}") for i in path_from_start.items()]
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
            print("before node")
        node_list += before_node
    else:
        node = end
        node_list.append(node)
        while node != start:
            node = path_from_start[node].parent
            node_list.append(node)
    route_start = []
    if not_start is None:
        node = path_db.start_node
        while node.node_id != start:
            print(node)
            route_start.append(node.node_id)
            node = node.child_node
    else:
        route_start.append(not_start)
    node_list+=route_start[::-1]

    nodes_db = [PathNode(node_id=node_list[0], path_on=path_db, dist_to_end=0)]
    main_path_geometry = [settings.G.graph[node_list[0]].position]
    for node in node_list[1:]:
        prev_node = nodes_db[-1]
        nodes_db.append(PathNode(node_id=node,
                                 path_on=path_db,
                                 dist_to_end=prev_node.dist_to_end + settings.G.graph[prev_node.node_id].neighbours[node].length))
        if node in waypoints: nodes_db[-1].waypoint = waypoints[node]
        path_section = list(settings.G.graph[prev_node.node_id].neighbours[node].geometry)
        if path_section[0] == main_path_geometry[-1]:
            main_path_geometry += path_section
        else:
            main_path_geometry += path_section[::-1]
    path_db.save()
    for i in nodes_db: i.save()
    for i in range(len(nodes_db) - 1):
        nodes_db[i].parent_node = nodes_db[i + 1]
        nodes_db[i + 1].child_node = nodes_db[i]
    for i in nodes_db: i.save()
    path_db.start_node = nodes_db[-1]
    path_db.end_node = nodes_db[0]
    path_db.save()
    return main_path_geometry


def sampleRoute(request):
    tolerance_s = 2 * 60 * 1000
    tolerance_m = tolerance_s * 4800 / (1000 * 60 * 60)
    data = loads(request.body)
    start_coord = GeoPoint(data["start"]["lat"], data["start"]["long"])
    based_on_route = Route.objects.get(routeName=data["route"])
    other_paths = Path.objects.filter(related_route=based_on_route).all()
    path_db = Path(account=User.objects.get(username=data["user"]), related_route=based_on_route)
    print("end time: " + str(based_on_route.end_time) + " start time " + str(data["datetime"]))
    max_time_millis = based_on_route.end_time - data["datetime"] + tolerance_s
    max_dist = max_time_millis * 4800 / (1000 * 60 * 60)
    end_coord = GeoPoint(based_on_route.end_lat, based_on_route.end_long)
    print(other_paths, max_dist)

    print(f"coords {start_coord}, {end_coord}")
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

    meeting_node = None
    meeting_path = None
    path_from_end = dict()
    paths_could_meet = dict()
    movable_paths: dict[Path, NodeWithOffset] = dict()  # THESE ARE START NODES !!!!

    print(f"nodes: {start}, {end}")
    print("starting to make route")
    route = settings.G.dijkstra(start, (end,))
    print("found dijkstra")
    if route[end].dist < max_dist:
        print("in if statement")
        print(other_paths)
        set_paths: list[NodeWithOffset] = []
        for path in other_paths:
            total_path_dist = path.start_node.dist_to_end - path.offset_from_start
            nodes_to_add = [path.start_node]
            while nodes_to_add[-1].child_node is not None:
                next_node = nodes_to_add[-1].child_node
                if next_node.waypoint is not None:
                    set_paths += [NodeWithOffset(i.node_id, total_path_dist - i.dist_to_end) for i in nodes_to_add]
                    nodes_to_add = []
                nodes_to_add.append(next_node)
            movable_paths[path] = NodeWithOffset(nodes_to_add[0].node_id, total_path_dist - nodes_to_add[0].dist_to_end)

        path_from_end = settings.G.dijkstra(end, tuple([start] + [i.node_id for i in movable_paths.values()]))
        min_dist_until_meet = float('inf')
        print("found movable / set paths")
        # TODO currently this just presumes that you speedwalk and don't wait in terms of future time calculations

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
                    if (abs(distance_difference_to_node) < tolerance_m and route[
                        node].dist - route_start_offset < min_dist_until_meet
                            and dist_new_a - dist_old_a < tolerance_m and dist_new_b - dist_old_b < tolerance_m
                            and dist_new_a < max_dist and dist_new_b < max_dist):
                        meeting_node = node
                        meeting_path = path
                        min_dist_until_meet = route[node].dist - route_start_offset
        print("checked movable paths")

        # CHECK SET PATHS
        for node in set_paths:
            total_path_dist = route[node.node_id].dist + path_from_end[node.node_id].dist - route_start_offset
            dist_old = route[end].dist - route_start_offset
            distance_difference_to_node = node.dist_from_now - route[node.node_id].dist
            if distance_difference_to_node < tolerance_m and total_path_dist - dist_old < tolerance_m:
                if route[node.node_id].dist - route_start_offset < min_dist_until_meet:
                    meeting_node = node
                    meeting_path = None
                    min_dist_until_meet = route[node.node_id].dist - route_start_offset
        print("checked set paths")
    
    print("found applicable meeting points")

    waypoint_list = Waypoint.objects.all()
    waypoints = dict()
    for i in waypoint_list:
        waypoints[PathNode.objects.filter(waypoint=i).all()[0].node_id] = i
    if meeting_node is not None:
        new_waypoint = Waypoint()
        new_waypoint.save()
        waypoints[meeting_node] = new_waypoint

    print("getting route from nodes")

    main_path_geometry = route_from_nodes(not_start, start, end, route, path_from_end, meeting_node, waypoints, path_db)
    print("made geometry")

    # modify other route for connecting with set path (if applicable)
    if meeting_path is not None:
        route_from_nodes(None,
                         movable_paths[meeting_path].node_id,
                         end,
                         paths_could_meet[meeting_path],
                         path_from_end,
                         meeting_node,
                         waypoints,
                         meeting_path)


    data = {}
    for idx, point in enumerate(main_path_geometry):
        data[idx] = {"lat": point.lat, "long": point.long}
    other_geometry = get_other_geometry(path_db)
    return JsonResponse({"geometry": data, "dist": 0, "other_paths":other_geometry})


def getRoutes(_, user):
    routes = Route.objects.filter(Q(user=user) | Q(participants=user))
    print(routes)
    data = {"success": True, "data": {}}
    for i, route in enumerate(routes):
        route_data = {
            "username": route.user,
            "lat": route.end_lat,
            "long": route.end_long,
            "endTime": route.end_time,
            "name": route.routeName,
            "friends": {}
        }
        for j, friend in enumerate(route.participants.all()):
            route_data["friends"][j] = friend.username
        data["data"][i] = route_data
    return JsonResponse(data)


def location_update(request):
    data = loads(request.body)
    path = Path.objects.select_related('current_location').filter(account__username=data["user"]).first()
    if path is None:
        return JsonResponse({"geometry": {}, "dist": 0, "other_paths": {}})
    if path.current_location is not None:
        path.current_location.datetime = data["datetime"]
        path.current_location.lat = data["lat"]
        path.current_location.long = data["long"]
        path.current_location.save()
    else:
        path.current_location = Location_data(datetime=data["datetime"], lat=data["lat"], long=data["long"])
        path.current_location.save()

    if path.start_node is None: return JsonResponse({"geometry": {}, "dist": 0, "other_paths": {}})
    previous_node = path.start_node
    current_node = previous_node.child_node
    geometry_path = [settings.G.graph[current_node.node_id].position]
    if current_node.child_node is not None:
        next_node = current_node.child_node
        closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id,
                                                                  GeoPoint(path.current_location.lat,
                                                                           path.current_location.long))
        while closest_lines_to_node[next_node.node_id] < closest_lines_to_node[previous_node.node_id]:
            print("next section")
            path.start_node = current_node
            print(path.start_node)
            previous_node.delete()
            previous_node = current_node
            current_node = next_node
            next_node = current_node.child_node
            closest_lines_to_node = settings.G.dist_to_path_from_node(current_node.node_id,
                                                                      GeoPoint(path.current_location.lat,
                                                                               path.current_location.long))
            if next_node is None: break
        if closest_lines_to_node[previous_node.node_id] > 0.001:
            print("gone off course" + str(closest_lines_to_node[previous_node.node_id]))
            if path.on_path:
                Notification(notification="gone off course " + str(randint(0, 1000)), user=data["user"],
                             datetime=int(time.time())).save()
                path.on_path = False

        while next_node != None:
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
    path.save()
    data = {}
    for idx, point in enumerate(geometry_path):
        data[idx] = {"lat": point.lat, "long": point.long}
    return JsonResponse({"geometry": data, "dist": path.start_node.dist_to_end - path.offset_from_start, "other_paths": get_other_geometry(path)})


def user_info(request):
    try:
        data = loads(request.body)
        user = model_to_dict(User.objects.get(username=data["username"], password=data["password"]))
        print(user)
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


def create_notification(_, user):
    try:
        Notification(notification="some sample text " + str(randint(0, 1000)), user=user,
                     datetime=int(time.time())).save()
        return JsonResponse({"success": True})
    except Exception as e:
        print(e)
        return JsonResponse({"success": False})


def deactivate(_, user):
    Path.objects.filter(account=User.objects.get(username=user)).delete()
    return JsonResponse({'success': True})


def show_notification(_, user):
    notifications = Notification.objects.filter(user=user).order_by("datetime")
    data = {}
    for i in notifications:
        data[i.datetime] = i.notification
    Notification.objects.all().delete()
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
        print(f"{friend_data}\n{incoming_data}\n{outgoing_data}")
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
            user=requested,
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
    accepting.save()
