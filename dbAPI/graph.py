import heapq
import math

class GeoPoint:
    def __init__(self, lat: float, long: float) -> None:
        self.lat, self.long = lat, long

    def __str__(self):
        return f"lat: {self.lat}, long: {self.long}"

class NodeWithOffset:
    def __init__(self, node_id, dist_from_now):
        self.node_id, self.dist_from_now = node_id, dist_from_now


class Edge:
    def __init__(self, length: float, geometry: tuple[GeoPoint, ...]):
        self.length = length
        self.geometry = geometry

class Node:
    def __init__(self, position: GeoPoint) -> None:
        self.position = position
        self.neighbours: dict[int, Edge] = {}

    def __str__(self) -> str:
        return f"lat: {self.position.lat}, long: {self.position.long}\nneighbours: {self.neighbours}"

class DijkstraNode:
    def __init__(self, distance: float, parent) -> None:
        self.parent = parent
        self.dist = distance
    
    def __str__(self) -> str:
        return (f"parent {self.parent}, distance {self.dist}")

class Graph:
    def __init__(self) -> None:
       self.graph: dict[int, Node] = dict()

    def add_node(self, node_id: int, position: GeoPoint) -> None:
        self.graph[node_id] = Node(position)

    def add_edge(self, uid: int, vid: int, edge: Edge) -> None:
        self.graph[uid].neighbours[vid] = edge
        self.graph[vid].neighbours[uid] = edge

    def dijkstra(self, start: int, end: tuple) -> dict[int, DijkstraNode]:
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
    
    def closest_from_lat_long(self, point: GeoPoint) -> int:
        min_dist, node_id = math.inf, 0
        for id, node in self.graph.items():
            dist = (point.long-node.position.long)**2 + (point.lat-node.position.lat)**2
            if dist < min_dist:
                min_dist = dist
                node_id = id
        return node_id
    
    def dist_to_path_from_node(self, a_id: int, point: GeoPoint) -> dict[int, float]:
        result = dict()
        for b_id in self.graph[a_id].neighbours:
            b_x = (self.graph[b_id].position.long - self.graph[a_id].position.long) * 111000 * math.cos(math.radians(self.graph[a_id].position.lat))
            b_y = (self.graph[b_id].position.lat - self.graph[a_id].position.lat) * 111000
            p_x = point.long - self.graph[a_id].position.long
            p_y = point.lat - self.graph[a_id].position.lat
            m_ab = (-b_y)/(-b_x)
            if m_ab == 0: m_ab = 1e-10
            m_op = -1/m_ab
            c_op = p_y-m_op*p_x
            o_x = (-c_op)/(m_op-m_ab)
            o_y = m_op*o_x+c_op
            abs_ob = math.sqrt((o_y-b_y)**2+(o_x-b_x)**2)
            abs_oa = math.sqrt(o_y ** 2 + o_x ** 2)
            abs_ab = math.sqrt((-b_y)**2+(-b_x)**2)
            if max(abs_ob, abs_oa) > abs_ab:
                if abs_oa < abs_ob:
                    o_x, o_y = 0, 0
                else:
                    o_x, o_y = b_x, b_y
            dist = ((o_x-p_x)**2 + (o_y-p_y)**2)**0.5
            print(dist)
            result[b_id] = dist
        return result
    
    def closest_pair_from_lat_long(self, point: GeoPoint) -> tuple[int, int]:
        closest_nodes = {}
        for i in range(5):
            closest_nodes[i] = math.inf
        max_node = 0
        for id, node in self.graph.items():
            dist = (point.long-node.position.long)**2 + (point.lat-node.position.lat)**2
            if dist < closest_nodes[max_node]:
                closest_nodes.pop(max_node)
                closest_nodes[id] = dist
                max_node = max(closest_nodes.items(), key=lambda k: k[1])[0]
        node_a, node_b, min_dist = 0, 0, math.inf
        for a_id in closest_nodes.keys():
            option = min(self.dist_to_path_from_node(a_id, point).items(), key = lambda k: k[1])
            if option[1] < min_dist:
                node_b, min_dist = option
                node_a = a_id
        return node_a, node_b
