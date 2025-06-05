from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now

from services.graph_logic.nodes import GeoPoint, DijkstraNode
from services.graph_logic.utils import get_total_time
from api.models import Path, PathNode, Waypoint


def get_other_geometry(path: Path) -> dict:
    other_paths = Path.objects.filter(related_route=path.related_route).exclude(id=path.id)
    data = dict()
    for path in other_paths:
        if path.start_node is None: return data
        previous_node = path.start_node
        current_node = previous_node.child_node
        next_node = current_node.child_node
        geometry_path = [settings.G.graph[current_node.node_id].position]
        while next_node is not None and current_node is not None:
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


def route_from_nodes(not_start: int|None, start: int, end: int, path_from_start: dict[int, DijkstraNode], path_from_end: dict[int, DijkstraNode], meeting_node: int|None, waypoints: dict[int, Waypoint], path_db: Path) -> None|list[GeoPoint]:
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
    path_db.eta = now() + timedelta(seconds=get_total_time(path_db))
    path_db.save()
    return main_path_geometry