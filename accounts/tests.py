from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Passkey


class SecondFactorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('u', password='pw')

    def _login(self):
        return self.client.post('/accounts/login/', {'username': 'u', 'password': 'pw'})

    def test_no_passkey_logs_in_with_password(self):
        self.assertRedirects(self._login(), '/', fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

    def test_with_passkey_password_alone_is_not_enough(self):
        Passkey.objects.create(user=self.user, credential_id=b'x', public_key=b'y', name='k')
        self.assertRedirects(self._login(), '/accounts/2fa/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get('/vinyl/').status_code, 302)
        self.assertEqual(self.client.post('/accounts/passkey/login/options/').status_code, 200)

    def test_passkey_endpoints_need_pending_password_step(self):
        for url in ('options', 'verify'):
            self.assertEqual(self.client.post(f'/accounts/passkey/login/{url}/').status_code, 403)

    def test_admin_requires_login(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
