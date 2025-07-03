import time

from django.conf import settings
from django.db.models import Q

from api.models import Route, Path, PathNode, Notification, Waypoint
from services.graph_logic.nodes import GeoPoint

TIME_FROM_DIST = 60 * 60 / 4800

def get_itineraries(route: Route) -> dict[int, dict]:
    """
    :param route: Database object of the relevant route
    :return: Enumerated dictionary of itineraries, each with ETAs and waypoints
    with participants
    """
    paths = Path.objects.filter(
        Q(related_route=route) & Q(start_node__isnull=False))
    out = dict()
    for path_idx, path in enumerate(paths):
        data = dict()
        data["username"] = path.account.username
        data["eta"] = time.time() + get_total_time(path)
        data["waypoints"] = dict()
        for waypoint_idx, waypoint in enumerate(
                i.waypoint for i in
                PathNode.objects.filter(path_on=path).exclude(
                    waypoint=None)):
            for i in out.values():
                for j in i["waypoints"].values():
                    if j["id"] == waypoint.id:
                        data["eta"] = i["eta"]
            waypoint_data = {"participants": dict()}
            waypoint_participants = PathNode.objects.filter(
                waypoint=waypoint)
            participants_lst = list(
                {i.path_on.account.username for i in waypoint_participants})
            for node_idx, participant in enumerate(
                    participants_lst):
                waypoint_data["participants"][
                    node_idx] = participant
            node = waypoint_participants[0]
            dist_to_end = node.dist_to_end
            while node is not None:
                dist_to_end += node.dist_waiting_at_node
                node = node.child_node
            waypoint_data["eta"] = time.time() + get_total_time(
                waypoint_participants[0].path_on) - (
                                           dist_to_end * TIME_FROM_DIST)
            waypoint_data["id"] = waypoint.id
            data["waypoints"][waypoint_idx] = waypoint_data
        out[path_idx] = data
    return out


def get_junction_name(point: GeoPoint) -> str:
    """
    :param point: GeoPoint
    :return: Name of adjacent streets (or nearest street if adjacent ones are
    unnamed)
    """
    checked = set()
    junction_name = ""
    while junction_name == "":
        end_node = settings.G.closest_from_lat_long(point, checked)
        junction_name += ", ".join(
            set([i.name for i in
                 settings.G.graph[end_node].neighbours.values()
                 if i.name != "unnamed road"]))
        checked.add(end_node)
    return junction_name


def get_total_dist(path: Path) -> float:
    """
    :param path: Database object of the relevant path
    :return: Total distance of path, including distance waiting at each node.
    """
    return path.start_node.dist_to_end - path.offset_from_start + sum(
        i.dist_waiting_at_node for i in
        PathNode.objects.filter(path_on=path).all())


def get_total_time(path: Path) -> float:
    """
    :param path: Database object of the relevant path
    :return: Total time of the path, including time waiting at each node.
    """
    return get_total_dist(path) * TIME_FROM_DIST


def latlong(nodes) -> dict[int, dict[str, float]]:
    """
    :param nodes: List of graph nodes
    :return: Enumerated dictionary of all nodes lat / long
    """
    data = {}
    for idx, point in enumerate(nodes):
        data[idx] = {"lat": point.lat, "long": point.long}
    return data


def cleanup_path(path_db: Path) -> None:
    """
    Deletion of all waypoints and nodes for a path.
    :param path_db: Database object of the relevant path
    :return:
    """
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


def fix_waypoints(waypoints: dict[int, Waypoint]) -> None:
    """
    Checks that there are multiple people still at each waypoint, deleting
    and notifying if not, possibly updating the time waiting if there are.
    :param waypoints: Waypoints to fix
    :return:
    """
    for waypoint in waypoints.values():
        nodes_at_waypoint = PathNode.objects.filter(
            waypoint=waypoint).all()
        if len(nodes_at_waypoint) < 2:
            for node in nodes_at_waypoint:
                node.waypoint = None
                node.save()
                Notification(
                    user=node.path_on.account,
                    notification=f"The meeting at {
                    settings.G.graph[node.node_id].position
                    } has been cancelled.",
                    datetime=int(time.time())
                ).save()
            waypoint.delete()
        else:
            all_nodes_at_point = PathNode.objects.filter(node_id=nodes_at_waypoint[0].node_id)
            for i in all_nodes_at_point:
                i.waypoint = waypoint
                i.save()
            max_dist_to_end = (max(
                nodes_at_waypoint,
                key=lambda k: k.path_on.start_node.dist_to_end).
                               path_on.start_node.dist_to_end)
            for node in nodes_at_waypoint:
                node.dist_waiting_at_node = (
                        max_dist_to_end -
                        node.path_on.start_node.dist_to_end)
                node.save()
