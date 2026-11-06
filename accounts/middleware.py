from django.conf import settings
from django.contrib.auth.views import redirect_to_login

# Percorsi raggiungibili senza login (l'admin ha già il suo login)
PUBLIC_PREFIXES = ('/accounts/login/', '/accounts/passkey/login/', '/admin/')


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not request.path.startswith(PUBLIC_PREFIXES):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
