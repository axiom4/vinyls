from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('passkeys/', views.passkey_list, name='passkey_list'),
    path('passkeys/<int:pk>/delete/', views.passkey_delete, name='passkey_delete'),
    path('passkey/register/options/', views.register_options, name='register_options'),
    path('passkey/register/verify/', views.register_verify, name='register_verify'),
    path('passkey/login/options/', views.login_options, name='passkey_login_options'),
    path('passkey/login/verify/', views.login_verify, name='passkey_login_verify'),
]
