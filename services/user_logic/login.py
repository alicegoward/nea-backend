from django.utils.crypto import get_random_string

from api.models import User


def login_data(data: dict[str, str]) -> str:
    """
    :param data: username and password to log in with.
    :return: token to authenticate themselves when sending future requests.
    """
    user = User.objects.get(username=data["username"],
                            password=data["password"])
    token = get_random_string(16)
    user.token = token
    user.save()
    return token


def register_data(data: dict[str, str]) -> str:
    """
    :param data: Username and password to attempt registration, which requires a
    unique username.
    :return: token to authenticate themselves when sending future requests.
    """
    if User.objects.filter(username=data["username"]).count() > 0:
        raise Exception
    user = User(username=data["username"], password=data["password"])
    user.save()
    return user.token
