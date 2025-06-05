import osmnx
from django.apps import AppConfig
from django.conf import settings

from services.graph_logic.graph import Graph
from services.graph_logic.nodes import GeoPoint, Edge


class APIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self) -> None:
        """
        code that runs on server startup
        Gets the OSM data for the local area and converts it into a custom graph.
        Adds other attributes to each edge used for display but not relevant to calculations (name and geometry).
        """
        raw_map = osmnx.graph.graph_from_bbox((-0.24689, 51.50247, -0.18595, 51.48607), network_type="walk",
                                              simplify=True)
        settings.G = Graph()
        for node_id, data in raw_map.nodes(data=True):
            settings.G.add_node(node_id, GeoPoint(data["y"], data["x"]))
        for u, v, data in raw_map.edges(data=True):
            line = [settings.G.graph[u].position]
            if "geometry" in data:
                for point in data["geometry"].coords:
                    line.append(GeoPoint(point[1], point[0]))
            if "name" in data:
                name = data["name"]
            else:
                name = "unnamed road"
            line.append(settings.G.graph[v].position)
            edge = Edge(data["length"], tuple(line), name)
            if v in settings.G.graph[u].neighbours:
                if settings.G.graph[u].neighbours[v].length > data["length"]:
                    settings.G.graph[u].neighbours[v] = edge
                    settings.G.graph[v].neighbours[u] = edge
            else:
                settings.G.add_edge(u, v, edge)
