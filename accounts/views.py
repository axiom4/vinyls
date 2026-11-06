import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from webauthn import (
    generate_authentication_options, generate_registration_options, options_to_json,
    verify_authentication_response, verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor,
    ResidentKeyRequirement, UserVerificationRequirement,
)

from .models import Passkey

BACKEND = 'django.contrib.auth.backends.ModelBackend'
UV = UserVerificationRequirement.REQUIRED  # impronta / PIN obbligatori


def _safe_next(request):
    nxt = request.POST.get('next') or request.GET.get('next') or ''
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    return nxt if ok else '/'


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next(request))
    return render(request, 'accounts/login.html', {'form': form, 'next': _safe_next(request)})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


def passkey_list(request):
    return render(request, 'accounts/passkeys.html', {'passkeys': request.user.passkeys.order_by('created_at')})


@require_POST
def passkey_delete(request, pk):
    get_object_or_404(Passkey, pk=pk, user=request.user).delete()
    messages.success(request, 'Passkey rimossa.')
    return redirect('accounts:passkey_list')


@require_POST
def register_options(request):
    user = request.user
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(user.pk).encode(),
        user_name=user.get_username(),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UV),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=bytes(p.credential_id)) for p in user.passkeys.all()],
    )
    request.session['webauthn_reg_challenge'] = bytes_to_base64url(options.challenge)
    return HttpResponse(options_to_json(options), content_type='application/json')


@require_POST
def register_verify(request):
    challenge = request.session.pop('webauthn_reg_challenge', None)
    if not challenge:
        return JsonResponse({'error': 'challenge mancante'}, status=400)
    try:
        body = json.loads(request.body)
        verified = verify_registration_response(
            credential=body['credential'],
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=True,
        )
    except Exception:
        return JsonResponse({'error': 'registrazione non valida'}, status=400)
    Passkey.objects.create(
        user=request.user,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        name=(body.get('name') or 'Passkey')[:100],
    )
    return JsonResponse({'ok': True})


@require_POST
def login_options(request):
    options = generate_authentication_options(rp_id=settings.WEBAUTHN_RP_ID, user_verification=UV)
    request.session['webauthn_auth_challenge'] = bytes_to_base64url(options.challenge)
    return HttpResponse(options_to_json(options), content_type='application/json')


@require_POST
def login_verify(request):
    challenge = request.session.pop('webauthn_auth_challenge', None)
    if not challenge:
        return JsonResponse({'error': 'challenge mancante'}, status=400)
    try:
        body = json.loads(request.body)
        passkey = Passkey.objects.select_related('user').get(
            credential_id=base64url_to_bytes(body['credential']['rawId']))
        verified = verify_authentication_response(
            credential=body['credential'],
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=bytes(passkey.public_key),
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,
        )
    except Exception:
        return JsonResponse({'error': 'autenticazione non valida'}, status=400)
    if not passkey.user.is_active:
        return JsonResponse({'error': 'utente disattivato'}, status=403)
    passkey.sign_count = verified.new_sign_count
    passkey.save(update_fields=['sign_count'])
    login(request, passkey.user, backend=BACKEND)
    return JsonResponse({'ok': True, 'next': _safe_next(request)})
