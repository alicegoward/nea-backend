from typing import Any, Callable

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from api.models import User


class TokenAuth:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        self.exempt_paths = ['/api/user/login', '/api/user/register', '/admin']
    def __call__(self, request: WSGIRequest) -> JsonResponse | Any:
        try:
            if any(request.path.lower().startswith(i) for i in self.exempt_paths):
                return self.get_response(request)
            token = request.META.get("HTTP_AUTH")
            request.user = User.objects.get(token=token)
            return self.get_response(request)
        except:
            print("UNAUTHORIZED", request.META.get("HTTP_AUTH"))
            return JsonResponse({}, status=401)