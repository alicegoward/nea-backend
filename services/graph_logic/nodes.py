class GeoPoint:
    def __init__(self, lat: float, long: float) -> None:
        """Geographical point"""
        self.lat, self.long = lat, long

    def __str__(self) -> str:
        """Debugging purposes only"""
        return f"lat: {self.lat}, long: {self.long}"


class NodeWithOffset:
    def __init__(self, node_id: int, dist_from_now: float):
        """
        :param node_id: ID on the graph
        :param dist_from_now: How far away the node is
        """
        self.node_id, self.dist_from_now = node_id, dist_from_now


class Edge:
    def __init__(self, length: float, geometry: tuple[GeoPoint, ...], name: str):
        """
        :param length: Distance
        :param geometry: Lat/Long geometry of the edge
        :param name: Road name on OSM (if applicable)
        """
        self.length = length
        self.geometry = geometry
        self.name = name


class Node:
    def __init__(self, position: GeoPoint) -> None:
        """
        :param position: GeoPoint
        """
        self.position = position
        self.neighbours: dict[int, Edge] = {}

    def __str__(self) -> str:
        """Debugging purposes only"""
        return f"lat: {self.position.lat}, long: {self.position.long}\nneighbours: {self.neighbours}"


class DijkstraNode:
    def __init__(self, distance: float, parent: int) -> None:
        """
        :param distance: Distance to start
        :param parent: Parent node (closer to the start, used to trace the route)
        """
        self.parent = parent
        self.dist = distance

    def __str__(self) -> str:
        """Debugging purposes only"""
        return f"parent {self.parent}, distance {self.dist}"
