import time
from typing import Any

from django.conf import settings
from django.db.models import Exists, Subquery, OuterRef

from api.models import Route, User, Path, UserOnRoute, Waypoint, PathNode, LocationData, Notification
from services.graph_logic.nodes import GeoPoint, NodeWithOffset
from services.graph_logic.route_geometry import get_other_geometry, route_from_nodes
from services.graph_logic.utils import cleanup_path, get_total_dist, latlong, get_itineraries, fix_waypoints


class ActivateRoute:
    def __init__(self, data: dict, user: User, path_db: Path | None = None) -> None:
        """
        Creates the path for a user on the route, possibly adding a waypoint where they join with another route.
        Also updates other paths where relevant.
        This is a context object as many variables are required throughout the algorithm, but it is too long for one function.
        :param data: Data about the route from the HTTP request
        :param user: User activating the route
        :param path_db: Current path (if called due to going off course)
        """
        # initialisation + loading data dictionary and database
        self.route_start_offset = None
        self.not_start = None
        self.start = None
        self.main_path_geometry = dict()
        self.data = data
        self.user = user
        self.path_db = path_db
        self.start_coord = GeoPoint(data["position"]["lat"], self.data["position"]["long"])
        self.based_on_route = Route.objects.get(routeName=self.data["route"])
        self.other_paths = (Path.objects.filter(related_route=self.based_on_route).exclude(account=self.user)
                            .annotate(
            has_mor=Exists(
                UserOnRoute.objects.filter(user=OuterRef('account'), route=self.based_on_route, create_mor=True)),
            mor_tolerance_s=Subquery(
                UserOnRoute.objects.filter(user=OuterRef('account'), route=self.based_on_route).values(
                    'mor_tolerance_s'))
        ).filter(has_mor=True).all())
        if self.path_db is None:
            Path.objects.filter(account=self.user).delete()
            self.path_db = Path(account=self.user, related_route=self.based_on_route)
        else:
            cleanup_path(self.path_db)
        max_time_millis = self.based_on_route.end_time - self.data["datetime"] + UserOnRoute.objects.get(user=self.user,
                                                                                                         route=self.based_on_route).mor_tolerance_s
        self.max_dist = max_time_millis * 4800 / (60 * 60)
        self.end_coord = GeoPoint(self.based_on_route.end_lat, self.based_on_route.end_long)
        self.joiner_mor_tolerance_m = UserOnRoute.objects.get(user=user,
                                                              route=self.based_on_route).mor_tolerance_s * 4800 / (
                                              60 * 60)
        self.end = settings.G.closest_from_lat_long(self.end_coord)
        self.get_start()
        self.path_db.offset_from_start = self.route_start_offset
        self.meeting_node = None
        self.meeting_path = None
        self.path_from_end = dict()
        self.paths_could_meet = dict()
        self.set_paths: dict[Path, list[NodeWithOffset]] = dict()  # all nodes in the set paths
        self.movable_paths: dict[Path, NodeWithOffset] = dict()  # start nodes of the movable paths
        self.move_other_path = True
        self.route = settings.G.dijkstra(self.start, (self.end,))

        # If already running late then meeting on route is not an option
        if self.route[self.end].dist < self.max_dist:
            self.get_other_paths()
            # to find waypoints Dijkstra's from both the beginning and end is required
            self.path_from_end = settings.G.dijkstra(self.end, tuple(
                [self.start] + [i.node_id for i in self.movable_paths.values()]))
            self.min_dist_until_meet = float('inf')
            self.check_movable_paths()
            self.check_set_paths()

        # adds / fixes waypoints
        self.waypoints = dict()
        self.new_waypoint = None
        self.get_new_waypoint()

        # sets the current location
        self.path_db.current_location = LocationData(datetime=self.data["datetime"], lat=self.data["position"]["lat"],
                                                     long=self.data["position"]["long"])
        self.path_db.current_location.save()
        self.make_main_path_geometry()

        # notifies others of the waypoint
        if self.path_db.eta.timestamp() - 5 > self.based_on_route.end_time:
            for i in UserOnRoute.objects.filter(route=self.based_on_route).exclude(user=user):
                Notification(user=i.user.username,
                             notification=f"{user.username} is running {int((self.path_db.eta.timestamp() - self.based_on_route.end_time) / 60)} minutes late",
                             datetime=int(time.time())).save()

        self.output_data = {}
        for idx, point in enumerate(self.main_path_geometry):
            self.output_data[idx] = {"lat": point.lat, "long": point.long}

    def get_result(self) -> dict[str, dict | dict[Any, Any] | float | dict[int, dict[str, float]] | dict[int, dict]]:
        """
        Separate function from __init__ as this must return None
        :return: Data to send to client with route geometry and itineraries etc.
        """
        return {"geometry": self.output_data,
                "dist": get_total_dist(self.path_db),
                "other_paths": get_other_geometry(self.path_db),
                "waypoints": latlong([settings.G.graph[i].position for i in self.waypoints.keys()]),
                "itineraries": get_itineraries(self.based_on_route)}

    def get_start(self) -> None:
        """
        Finds the edge the person is currently on, and where on the edge they currently are.
        Assumes that the end geographically closer to the end node is the one they will be going towards, and sets the other
        as "not start" (node they are coming from).
        Also calculates the offset from "not start".
        :return:
        """
        a, b = settings.G.closest_pair_from_lat_long(self.start_coord)
        if ((settings.G.graph[a].position.long - self.end_coord.long) ** 2 + (
                settings.G.graph[a].position.lat - self.end_coord.lat) ** 2 <
                (settings.G.graph[b].position.long - self.end_coord.long) ** 2 + (
                        settings.G.graph[b].position.lat - self.end_coord.lat) ** 2):
            self.start = a
            self.not_start = b
            self.route_start_offset = (settings.G.graph[b].position.long - self.end_coord.long) ** 2 + (
                    settings.G.graph[b].position.lat - self.end_coord.lat) ** 2
        else:
            self.start = b
            self.not_start = a
            self.route_start_offset = (settings.G.graph[a].position.long - self.end_coord.long) ** 2 + (
                    settings.G.graph[a].position.lat - self.end_coord.lat) ** 2

    def make_main_path_geometry(self) -> None:
        """
        Gets the geometry of the newly created path as well as any moved paths.
        Updates the waypoints, sends resulting notifications and saves everything to the database.
        :return:
        """
        if self.meeting_node is not None:
            self.main_path_geometry = route_from_nodes(self.not_start, self.start, self.end, self.route,
                                                       self.path_from_end, self.meeting_node, self.waypoints,
                                                       self.path_db)
            if self.move_other_path:
                moving_paths = [i[0] for i in self.movable_paths.items() if
                                i[1].node_id == self.movable_paths[self.meeting_path].node_id]
                for path_to_move in moving_paths:
                    route_from_nodes(None, self.movable_paths[path_to_move].node_id, self.end,
                                     self.paths_could_meet[path_to_move], self.path_from_end,
                                     self.meeting_node, self.waypoints, path_to_move)
            paths_to_move_nodes = PathNode.objects.filter(node_id=self.meeting_node)
            for i in paths_to_move_nodes:
                i.waypoint = self.new_waypoint
                i.save()
            fix_waypoints(self.waypoints)
            self.new_waypoint.save()
            for i in PathNode.objects.all():
                if i.waypoint == self.new_waypoint:
                    Notification(
                        user=i.path_on.account.username,
                        notification="new meeting place",
                        datetime=int(time.time())
                    ).save()
        else:
            self.main_path_geometry = route_from_nodes(self.not_start, self.start, self.end, self.route,
                                                       self.path_from_end, None, self.waypoints, self.path_db)

    def check_movable_paths(self) -> None:
        """
        Iterates through the paths that can be moved to check for suitable waypoint positions.
        :return:
        """
        for path, path_start in self.movable_paths.items():
            self.paths_could_meet[path] = settings.G.dijkstra(path_start.node_id, (self.end,))

        for node in self.route:
            for path, nodes in self.paths_could_meet.items():
                if node in nodes and node in self.path_from_end:
                    self.check_movable(path, nodes, node)

    def check_movable(self, path: Path, nodes: dict, node: int) -> None:
        """
        Calculates if this node falls within meet on route constraints and is the most optimal
        :param path: Path object that will be moved
        :param nodes: Result of Dijkstra's algorithm
        :param node: Node in question
        :return:
        """
        dist_new_a = self.path_from_end[node].dist + self.route[node].dist - self.route_start_offset
        dist_old_a = self.route[self.end].dist - self.route_start_offset
        dist_new_b = self.path_from_end[node].dist + nodes[node].dist + self.movable_paths[
            path].dist_from_now
        dist_old_b = nodes[self.end].dist + self.movable_paths[path].dist_from_now
        distance_difference_to_node = nodes[node].dist + self.movable_paths[path].dist_from_now - (
                self.route[node].dist - self.route_start_offset)
        if distance_difference_to_node > 0:
            dist_new_b += distance_difference_to_node
        else:
            dist_new_a -= distance_difference_to_node
        mor_tolerance_m = min(self.joiner_mor_tolerance_m, UserOnRoute.objects.get(user=path.account,
                                                                                   route=self.based_on_route).mor_tolerance_s * 4800 / (
                                      60 * 60))
        if (abs(distance_difference_to_node) < mor_tolerance_m and self.route[
            node].dist - self.route_start_offset < self.min_dist_until_meet
                and dist_new_a - dist_old_a < mor_tolerance_m and dist_new_b - dist_old_b < mor_tolerance_m
                and dist_new_a < self.max_dist and dist_new_b < self.max_dist):
            self.meeting_node = node
            self.meeting_path = path
            self.min_dist_until_meet = self.route[node].dist - self.route_start_offset

    def check_set_paths(self) -> None:
        """
        Iterates through set paths to check for suitable waypoint positions.
        :return:
        """
        for path, node_list in self.set_paths.items():
            for node in node_list:
                if node.node_id in self.route and node.node_id in self.path_from_end:
                    self.check_set(path, node)

    def check_set(self, path, node) -> None:
        """
        Calculates if this node falls within meet on route constraints and is the most optimal
        :param path: Path that would be joined
        :param node: Joining node
        :return:
        """
        mor_tolerance_m = min(self.joiner_mor_tolerance_m, UserOnRoute.objects.get(user=path.account,
                                                                                   route=self.based_on_route).mor_tolerance_s * 4800 / (
                                      60 * 60))
        total_path_dist = self.route[node.node_id].dist + self.path_from_end[
            node.node_id].dist - self.route_start_offset
        dist_old = self.route[self.end].dist - self.route_start_offset
        distance_difference_to_node = node.dist_from_now - self.route[node.node_id].dist
        if distance_difference_to_node < mor_tolerance_m and total_path_dist - dist_old < mor_tolerance_m:
            if self.route[node.node_id].dist - self.route_start_offset < self.min_dist_until_meet:
                self.meeting_node = node.node_id
                self.meeting_path = path
                self.move_other_path = False
                self.min_dist_until_meet = self.route[node.node_id].dist - self.route_start_offset

    def get_other_paths(self) -> None:
        """
        Gets the other paths on the route, and classifies them (or parts of them) into set and movable.
        Movable paths are direct to the destination (possibly from a waypoint), so a detour to a meeting point is possible.
        Set paths are on their way to another intermediary waypoint, so can be joined but cannot be moved as this would
        create inconsistencies in the waypoint timing.
        :return:
        """
        for path in self.other_paths:
            total_path_dist = path.start_node.dist_to_end - path.offset_from_start
            nodes_to_add = [path.start_node]
            waiting_offset = 0
            while nodes_to_add[-1].child_node is not None:
                next_node = nodes_to_add[-1].child_node
                if next_node.waypoint is not None:
                    self.set_paths[path] = [NodeWithOffset(i.node_id, total_path_dist - i.dist_to_end + waiting_offset)
                                            for i
                                            in nodes_to_add]
                    waiting_offset += next_node.dist_waiting_at_node
                    nodes_to_add = []
                nodes_to_add.append(next_node)
            self.movable_paths[path] = NodeWithOffset(nodes_to_add[0].node_id,
                                                      total_path_dist - nodes_to_add[0].dist_to_end + waiting_offset)

    def get_new_waypoint(self) -> None:
        """
        Adds waypoints that are passed to the path, including the meeting node.
        :return:
        """
        waypoint_list = Waypoint.objects.all()
        for i in waypoint_list:
            node = PathNode.objects.filter(waypoint=i).all().first()
            if node is not None: self.waypoints[node.node_id] = i
        if self.meeting_node is not None:
            if self.meeting_node not in self.waypoints.keys():
                self.new_waypoint = Waypoint()
                self.new_waypoint.save()
                self.waypoints[self.meeting_node] = self.new_waypoint
            else:
                self.new_waypoint = self.waypoints[self.meeting_node]
                self.new_waypoint.save()
