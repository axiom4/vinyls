from django.conf import settings
from django.db import models


class Passkey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='passkeys')
    # shortcut: nessun vincolo unique, MySQL non indicizza i BLOB senza lunghezza; gli id WebAuthn sono già univoci, aggiungi un hash indicizzato se serve il vincolo a livello DB
    credential_id = models.BinaryField()
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.name}'
