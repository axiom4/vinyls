from django.contrib import admin

from .models import Passkey


@admin.register(Passkey)
class PasskeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at', 'sign_count')
    list_filter = ('user',)
    readonly_fields = ('credential_id', 'public_key', 'sign_count', 'created_at')
