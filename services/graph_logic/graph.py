import heapq
import math

from services.graph_logic.nodes import Node, GeoPoint, Edge, DijkstraNode


class Graph:
    def __init__(self) -> None:
        """
        Custom graph class, made up of nodes and edges.
        As well as weightings for calculations, this includes geographical data.
        """
        self.graph: dict[int, Node] = dict()

    def add_node(self, node_id: int, position: GeoPoint) -> None:
        """
        :param node_id: ID of the node on OSM
        :param position: Geographical position of the node
        :return:
        """
        self.graph[node_id] = Node(position)

    def add_edge(self, uid: int, vid: int, edge: Edge) -> None:
        """
        :param uid: ID of node 1
        :param vid: ID of node 2
        :param edge: Geographical and distance information about the connection
        :return:
        """
        self.graph[uid].neighbours[vid] = edge
        self.graph[vid].neighbours[uid] = edge

    def dijkstra(self, start: int, end: tuple) -> dict[int, DijkstraNode]:
        """
        Implementation of Dijkstra on the graph
        :param start: node ID of start point
        :param end: Node IDs of end points - the algorithm continues running until all end nodes have been reached.
        :return: Dictionary of nodes and their parent + distances
        """
        visited = {}
        heap = [(0, start, start)]
        while heap:
            dist, node, parent = heapq.heappop(heap)
            if node in visited: continue
            visited[node] = DijkstraNode(dist, parent)
            for neighbour, edge in self.graph[node].neighbours.items():
                if neighbour not in visited:
                    heapq.heappush(heap, (dist + edge.length, neighbour, node))
            finished = True
            for i in end:
                if i not in visited:
                    finished = False
            if finished:
                return visited
        return {}

    def closest_from_lat_long(self, point: GeoPoint, exclude: set = {}) -> int:
        """
        Finds the closest node to a lat/long coordinate.
        :param point:
        :param exclude: Any nodes that should not be considered
        :return: Node ID of the closest node.
        """
        min_dist, node_id = math.inf, 0
        for id, node in self.graph.items():
            dist = (point.long - node.position.long) ** 2 + (point.lat - node.position.lat) ** 2
            if dist < min_dist and id not in exclude:
                min_dist = dist
                node_id = id
        return node_id

    def dist_to_path_from_node(self, a_id: int, point: GeoPoint) -> dict[int, float]:
        """
        Point to line calculations for all edges adjacent to point a
        :param a_id: ID of one end of the path the point is on
        :param point: Geographical position of the point
        :return: Dictionary of the distances from the point to each edge
        """
        result = dict()
        for b_id in self.graph[a_id].neighbours:
            b_x = (self.graph[b_id].position.long - self.graph[a_id].position.long) * 111000 * math.cos(
                math.radians(self.graph[a_id].position.lat))
            if b_x == 0: b_x = 1e-10
            b_y = (self.graph[b_id].position.lat - self.graph[a_id].position.lat) * 111000
            p_x = point.long - self.graph[a_id].position.long
            p_y = point.lat - self.graph[a_id].position.lat
            m_ab = (-b_y) / (-b_x)
            if m_ab == 0: m_ab = 1e-10
            m_op = -1 / m_ab
            c_op = p_y - m_op * p_x
            o_x = (-c_op) / (m_op - m_ab)
            o_y = m_op * o_x + c_op
            abs_ob = math.sqrt((o_y - b_y) ** 2 + (o_x - b_x) ** 2)
            abs_oa = math.sqrt(o_y ** 2 + o_x ** 2)
            abs_ab = math.sqrt((-b_y) ** 2 + (-b_x) ** 2)
            if max(abs_ob, abs_oa) > abs_ab:
                if abs_oa < abs_ob:
                    o_x, o_y = 0, 0
                else:
                    o_x, o_y = b_x, b_y
            dist = ((o_x - p_x) ** 2 + (o_y - p_y) ** 2) ** 0.5
            result[b_id] = dist
        return result

    def closest_pair_from_lat_long(self, point: GeoPoint) -> tuple[int, int]:
        """
        Finds the pair of adjacent nodes that the point is between
        :param point: Geographical position of the point
        :return: ID of each node
        """
        closest_nodes = {}
        for i in range(5):
            closest_nodes[i] = math.inf
        max_node = 0
        for id, node in self.graph.items():
            dist = (point.long - node.position.long) ** 2 + (point.lat - node.position.lat) ** 2
            if dist < closest_nodes[max_node]:
                closest_nodes.pop(max_node)
                closest_nodes[id] = dist
                max_node = max(closest_nodes.items(), key=lambda k: k[1])[0]
        node_a, node_b, min_dist = 0, 0, math.inf
        for a_id in closest_nodes.keys():
            option = min(self.dist_to_path_from_node(a_id, point).items(), key=lambda k: k[1])
            if option[1] < min_dist:
                node_b, min_dist = option
                node_a = a_id
        return node_a, node_b
