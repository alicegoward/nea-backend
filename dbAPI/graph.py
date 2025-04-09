import heapq

class GeoPoint:
    def __init__(self, lat: float, long: float) -> None:
        self.lat, self.long = lat, long

    def __str__(self):
        return f"lat: {self.lat}, long: {self.long}"

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
    def __init__(self, distance: float, parent: int) -> None:
        self.parent = parent
        self.dist = distance

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