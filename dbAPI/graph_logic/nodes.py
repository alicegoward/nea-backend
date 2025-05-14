class GeoPoint:
    def __init__(self, lat: float, long: float) -> None:
        self.lat, self.long = lat, long

    def __str__(self) -> str:
        return f"lat: {self.lat}, long: {self.long}"


class NodeWithOffset:
    def __init__(self, node_id: int, dist_from_now: float):
        self.node_id, self.dist_from_now = node_id, dist_from_now


class Edge:
    def __init__(self, length: float, geometry: tuple[GeoPoint, ...], name: str):
        self.length = length
        self.geometry = geometry
        self.name = name


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

    def __str__(self) -> str:
        return f"parent {self.parent}, distance {self.dist}"