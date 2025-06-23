import math

from django.test import TestCase

from api.models import User
from services.graph_logic.graph import Graph
from services.graph_logic.nodes import GeoPoint, Edge
from services.user_logic.login import login_data, register_data


class LoginTestCase(TestCase):
    def setUp(self) -> None:
        User.objects.create(username="a", password="b")

    def test_login_fail(self) -> None:
        """attempting to login with incorrect password"""
        try:
            login_data({"username": "a", "password": "c"})
            raise Exception("test failed")
        except:
            pass

    def test_login_success(self) -> None:
        """attempting to login with correct password"""
        login_data({"username": "a", "password": "b"})

    def test_register_fail(self) -> None:
        """attempting to register with non-unique username"""
        try:
            register_data({"username": "a", "password": "c"})
            raise Exception("test failed")
        except:
            pass

    def test_register_success(self) -> None:
        """attempting to register with the unique username"""
        register_data({"username": "b", "password": "c"})


class PointToLineTestCase(TestCase):
    def setUp(self) -> None:
        self.graph = Graph()
        self.graph.add_node(0, GeoPoint(-2, 2))
        self.graph.add_node(1, GeoPoint(0, 0))
        self.graph.add_node(2, GeoPoint(2, 0))
        self.graph.add_node(3, GeoPoint(2, 2))
        self.graph.add_edge(0, 1, Edge(math.sqrt(8), (), "01"))
        self.graph.add_edge(0, 3, Edge(4, (), "03"))
        self.graph.add_edge(1, 2, Edge(2, (), "12"))
        self.graph.add_edge(2, 3, Edge(2, (), "23"))
        self.graph.add_edge(1, 3, Edge(math.sqrt(8), (), "13"))

    def test_1(self) -> None:
        """exactly on an edge"""
        ans = self.graph.dist_to_path_from_node(1, GeoPoint(1, 1))
        for key, value in ans.items():
            ans[key] = round(value, 4)
        assert (ans == {0: round(math.sqrt(2), 4), 2: 1, 3: 0})

    def test_2(self) -> None:
        """away from an edge"""
        ans = self.graph.dist_to_path_from_node(0, GeoPoint(-2, 0))
        for key, value in ans.items():
            ans[key] = round(value, 4)
        assert (ans == {1: round(math.sqrt(2), 4), 3: 2})

    def test_3(self) -> None:
        """on a node"""
        ans = self.graph.dist_to_path_from_node(1, GeoPoint(0, 0))
        for key, value in ans.items():
            ans[key] = round(value, 4)
        assert (ans == {0: 0, 2: 1, 3: 0})
