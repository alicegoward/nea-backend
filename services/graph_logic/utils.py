import time

from django.conf import settings

from services.graph_logic.nodes import GeoPoint
from api.models import Route, Path, PathNode, Notification, Waypoint


def get_itineraries(route: Route) -> dict[int, dict]:
    paths = Path.objects.filter(related_route=route)
    out = dict()
    for path_idx, path in enumerate(paths):
        data = dict()
        data["username"] = path.account.username
        data["eta"] = time.time()+ get_total_time(path)
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
            waypoint_data["eta"] = time.time() + get_total_time(waypoint_participants[0].path_on) - (dist_to_end * 60 * 60 / 4800)
            data["waypoints"][waypoint_idx] = waypoint_data
        out[path_idx] = data
    return out


def get_junction_name(point: GeoPoint) -> str :
    checked = set()
    junction_name = ""
    while junction_name == "":
        end_node = settings.G.closest_from_lat_long(point, checked)
        junction_name += ", ".join(
            set([i.name for i in settings.G.graph[end_node].neighbours.values() if i.name != "unnamed road"]))
        checked.add(end_node)
    return junction_name

def get_total_dist(path: Path) -> float:
    return path.start_node.dist_to_end - path.offset_from_start + sum(
        i.dist_waiting_at_node for i in PathNode.objects.filter(path_on=path).all())

def get_total_time(path: Path) -> float:
    return get_total_dist(path) * 60 * 60 / 4800


def latlong(nodes) -> dict[int, dict[str, float]]:
    data = {}
    for idx, point in enumerate(nodes):
        data[idx] = {"lat": point.lat, "long": point.long}
    return data


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
            max_dist_to_end = max(nodes_at_waypoint,
                                  key=lambda k: k.path_on.start_node.dist_to_end).path_on.start_node.dist_to_end
            for node in nodes_at_waypoint:
                node.dist_waiting_at_node = max_dist_to_end - node.path_on.start_node.dist_to_end
                node.save()