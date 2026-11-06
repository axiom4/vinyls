import secrets

from django.conf import settings
from django.contrib.auth.views import redirect_to_login

# Percorsi raggiungibili senza login (l'admin ha già il suo login)
PUBLIC_PREFIXES = ('/accounts/login/', '/accounts/passkey/login/', '/admin/', '/i18n/')


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not request.path.startswith(PUBLIC_PREFIXES):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)


class CspMiddleware:
    """CSP con nonce per richiesta: gli <script> inline usano nonce="{{ request.csp_nonce }}"."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        response['Content-Security-Policy'] = (
            f"default-src 'none'; script-src 'nonce-{request.csp_nonce}' 'strict-dynamic'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; base-uri 'self'; "
            "object-src 'none'; frame-ancestors 'none'; manifest-src 'self'; worker-src 'none'"
        )
        return response
