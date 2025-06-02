from django.test import TestCase
from api.models import User
from services.user_logic.login import login_data, register_data


class LoginTestCase(TestCase):
    def setUp(self) -> None:
        User.objects.create(username="a", password="b")

    def test_login_fail(self) -> None:
        """attempting to login with incorrect password"""
        try:
            login_data({"username": "a", "password": "c"})
            raise Exception("test failed")
        except: pass

    def test_login_success(self) -> None:
        """attempting to login with correct password"""
        login_data({"username": "a", "password": "b"})

    def test_register_fail(self) -> None:
        """attempting to register with non-unique username"""
        try:
            register_data({"username": "a", "password": "c"})
            raise Exception("test failed")
        except: pass

    def test_register_success(self) -> None:
        """attempting to register with the unique username"""
        register_data({"username": "b", "password": "c"})
