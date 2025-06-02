from typing import Any

from django.utils.crypto import get_random_string

from api.models import User


def login_data(data: dict[str, str]) -> str:
    user = User.objects.get(username=data["username"], password=data["password"])
    print("here", user)
    token = get_random_string(16)
    print("TOKEN", token)
    user.token = token
    user.save()
    return token


def register_data(data: dict[str, str]) -> str:
    if User.objects.filter(username=data["username"]).count() > 0:
        raise Exception
    user = User(username=data["username"], password=data["password"])
    user.save()
    return user.token