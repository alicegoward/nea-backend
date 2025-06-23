from typing import Any, Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from api.models import User


class TokenAuth:
    def __init__(self, get_response: Callable) -> None:
        """
        :param get_response: function of the next step in the processing of
        the request
        """
        self.get_response = get_response
        self.exempt_paths = ['/api/user/login', '/api/user/register', '/admin',
                             '/static/admin']

    def __call__(self, request: WSGIRequest) -> JsonResponse | Any:
        """
        Checks if the token is valid or the request is to one of the exempt
        paths (admin for debugging, login / register
        as these provide tokens)
        :param request: HTTP request
        :return: Response to the request
        """
        try:
            if any(request.path.lower().startswith(i) for i in
                   self.exempt_paths):
                return self.get_response(request)
            token = request.META.get("HTTP_AUTH")
            request.user = User.objects.get(token=token)
            return self.get_response(request)
        except:
            print("UNAUTHORIZED", request.META.get("HTTP_AUTH"))
            return JsonResponse({}, status=401)
