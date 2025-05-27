from django.http import JsonResponse

from dbAPI.models import User


class TokenAuth:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = ['/db/user/login', '/db/user/register', '/admin']
    def __call__(self, request):
        try:
            if any(request.path.lower().startswith(i) for i in self.exempt_paths):
                return self.get_response(request)
            token = request.META.get("HTTP_AUTH")
            request.user = User.objects.get(token=token)
            return self.get_response(request)
        except:
            print("UNAUTHORIZED", request.META.get("HTTP_AUTH"))
            return JsonResponse({}, status=401)