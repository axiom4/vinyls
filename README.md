# Vinyl

Django application for cataloguing your vinyl (and book) collection. Access is protected by login: password or passkey (WebAuthn).

## Requirements

- Python 3.12 or later
- pip and `venv`
- Optional: PostgreSQL or MySQL (SQLite is used by default), Redis for caching

## Local installation

```bash
git clone <repository-url> vinyl
cd vinyl

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Open `.env` and set at least `SECRET_KEY`. To generate one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Then create the database and the admin user, and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://localhost:8000> and sign in with the credentials you just created.

> Always use `localhost`, not `127.0.0.1`: passkeys are bound to the host (`WEBAUTHN_RP_ID`).

### Passkeys

After your first password login, open the user menu at the top right → **Passkey** and register your fingerprint, Face ID or security key. Passkeys require HTTPS or `http://localhost`.

## Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key. Required in production. | insecure development value |
| `DEBUG` | `True` or `False`. | `True` |
| `ALLOWED_HOSTS` | Allowed hosts, comma-separated. | empty |
| `WEBAUTHN_RP_ID` | Domain for passkeys (no scheme or port). | `localhost` |
| `WEBAUTHN_ORIGIN` | Full origin used in the browser. | `http://localhost:8000` |
| `DATABASE_URL` | External database, e.g. `postgres://user:password@host:5432/db_name`. | SQLite (`db.sqlite3`) |
| `REDIS_URL` | Redis cache, e.g. `redis://localhost:6379/1`. | in-memory cache |
| `EXTERNAL_API_CACHE_SECONDS` | Cache duration for external APIs (covers and metadata). | `86400` |
| `BEHIND_PROXY` | `True` if the app runs behind a proxy that terminates TLS. | off |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for forms, e.g. `https://vinyl.example.com`. | empty |
| `SECURE_HSTS_SECONDS` | HSTS duration in production. Keep `0` until HTTPS is stable. | `0` |

With an external database, also install the driver: `pip install "psycopg[binary]"` for PostgreSQL or `pip install mysqlclient` for MySQL.

## Production installation

With `DEBUG=False` the app enforces HTTPS and secure cookies. The example below uses nginx and gunicorn.

1. Follow the local installation steps, then install the WSGI server:

   ```bash
   pip install gunicorn
   ```

2. Set `.env` for production, adjusting the domain:

   ```ini
   SECRET_KEY=<generated-key>
   DEBUG=False
   ALLOWED_HOSTS=vinyl.example.com
   BEHIND_PROXY=True
   CSRF_TRUSTED_ORIGINS=https://vinyl.example.com
   WEBAUTHN_RP_ID=vinyl.example.com
   WEBAUTHN_ORIGIN=https://vinyl.example.com
   ```

   With `DEBUG=False` and no `BEHIND_PROXY=True` behind nginx, the app enters a redirect loop.

3. Prepare the database and static files:

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

4. Start the application, for example with systemd or supervisor:

   ```bash
   gunicorn mysite.wsgi:application --bind 127.0.0.1:8002
   ```

5. Configure nginx. A complete example is in `deploy/nginx/` (proxy to `127.0.0.1:8002`, TLS, security headers). nginx must serve these directly:
   - `/static/` from the `staticfiles/` folder
   - `/media/` from the `media/` folder (uploaded covers)

   The example file contains the domain and paths of the original installation (`vinyl.axiom4.net`, `/home/axiom/www/...`): replace them with your own.

## Updating

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then restart gunicorn.

## Maintenance

Removes artists, labels and genres with no records, and unused covers. Without `--apply` it only simulates:

```bash
python manage.py cleanup_vinyl           # dry run
python manage.py cleanup_vinyl --apply   # performs the cleanup
```

## Backup

You need two things: the database (`db.sqlite3`, or a dump of the external database) and the `media/` folder. The `.env` file contains the secret key: keep it safe and do not commit it to the repository.

## License

Released under the BSD 3-Clause license. See [LICENSE](LICENSE).
