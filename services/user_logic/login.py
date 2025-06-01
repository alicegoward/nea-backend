from django.utils.crypto import get_random_string

from api.models import User


def login_data(data):
    user = User.objects.get(username=data["username"], password=data["password"])
    token = get_random_string(16)
    print("TOKEN", token)
    user.token = token
    user.save()
    return token


def register_data(data):
    if User.objects.filter(username=data["username"]).count() > 0:
        raise Exception
    user = User(username=data["username"], password=data["password"]).save()
    return user