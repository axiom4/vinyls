# Vinyl

Django application for cataloguing your vinyl (and book) collection. Access is protected by login: password or passkey (WebAuthn).

## Requirements

- Python 3.12 or later
- pip and `venv`
- Optional: PostgreSQL or MySQL (SQLite is used by default), Redis for caching

## Local installation

```bash
git clone https://github.com/axiom4/vinyls.git
cd vinyls

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
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` to apply HSTS to all subdomains. Only if every subdomain is HTTPS-only. | `False` |
| `SECURE_HSTS_PRELOAD` | `True` to allow browser preload-list submission. Hard to undo. | `False` |

For PostgreSQL or MySQL, see [Using PostgreSQL or MySQL](#using-postgresql-or-mysql).

## Using PostgreSQL or MySQL

By default the app uses SQLite. To use PostgreSQL or MySQL instead, create an empty database, install the driver in the virtual environment and set `DATABASE_URL` in `.env`.

### PostgreSQL

1. Install the driver:

   ```bash
   pip install "psycopg[binary]"
   ```

2. Create the user and the database (as the `postgres` superuser):

   ```sql
   CREATE USER vinyl WITH PASSWORD 'choose-a-password';
   CREATE DATABASE vinyl OWNER vinyl ENCODING 'UTF8';
   ```

3. Set the connection string in `.env`:

   ```ini
   DATABASE_URL=postgres://vinyl:choose-a-password@localhost:5432/vinyl
   ```

### MySQL / MariaDB

1. Install the driver. `mysqlclient` is compiled against the MySQL client library, so install that first (macOS: `brew install mysql pkg-config`; Debian/Ubuntu: `sudo apt install libmysqlclient-dev pkg-config build-essential python3-dev`). Then:

   ```bash
   pip install mysqlclient
   ```

2. Create the user and the database with the `utf8mb4` character set:

   ```sql
   CREATE DATABASE vinyl CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'vinyl'@'localhost' IDENTIFIED BY 'choose-a-password';
   GRANT ALL PRIVILEGES ON vinyl.* TO 'vinyl'@'localhost';
   ```

3. Set the connection string in `.env`:

   ```ini
   DATABASE_URL=mysql://vinyl:choose-a-password@localhost:3306/vinyl
   ```

If the password contains special characters (`@`, `:`, `/`, `#`, `%`), URL-encode them in `DATABASE_URL`.

### Create the tables

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Moving existing data from SQLite

To keep the data you already have, export it **before** changing `DATABASE_URL`, then load it into the new database:

```bash
# 1. with the current SQLite configuration
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.permission -e admin.logentry -e sessions \
    --indent 2 -o db.json

# 2. set DATABASE_URL in .env, then create the tables
python manage.py migrate

# 3. load the data
python manage.py loaddata db.json
```

Passkeys are stored in the database and are copied too, so they keep working as long as `WEBAUTHN_RP_ID` stays the same. `db.json` contains your users and password hashes: delete it when you are done and never commit it (`db.json` is already in `.gitignore`). The `media/` folder is not part of the database and does not need to move.

## Production installation

With `DEBUG=False` the app enforces HTTPS and secure cookies. The example below uses nginx and uvicorn (ASGI server, already in `requirements.txt`).

1. Follow the local installation steps. No extra server needs to be installed.

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
   uvicorn vinyls.asgi:application --host 127.0.0.1 --port 8002 --workers 2 --proxy-headers
   ```

   Uvicorn does not serve static or media files: nginx must do it (next step). `runserver` remains the way to develop locally.

   With supervisor, share one socket among several uvicorn processes (`fcgi-program`; adjust paths and user):

   ```ini
   [fcgi-program:vinyl]
   socket=tcp://127.0.0.1:8002
   directory=/path/to/vinyls
   command=/path/to/vinyls/venv/bin/uvicorn vinyls.asgi:application --fd 0 --access-log --proxy-headers
   numprocs=4
   process_name=asgi%(process_num)d
   autostart=true
   autorestart=true
   stdout_logfile=/path/to/logs/vinyl_supervisor.log
   redirect_stderr=true
   user=www-data
   ```

   The module is `vinyls.asgi` (the Django project package), not the repository name.

   Prefer a WSGI server? `pip install gunicorn` and run `gunicorn vinyls.wsgi:application --bind 127.0.0.1:8002`.

5. Configure nginx. A complete example is in `deploy/nginx/` (proxy to `127.0.0.1:8002`, TLS, security headers). nginx must serve these directly:
   - `/static/` from the `staticfiles/` folder
   - `/media/` from the `media/` folder (uploaded covers)

   The example file contains the domain and paths of the original installation (`vinyl.axiom4.net`, `/home/axiom/www/...`): replace them with your own.

## Languages

The interface is available in English, Italian, French, German, Russian, Simplified Chinese, Spanish and Japanese. The language is picked from the browser (`Accept-Language`) and can be changed with the selector in the navigation bar; the choice is stored in a cookie. Italian is the fallback.

Source strings are in Italian and wrapped with Django's gettext. Translations live in `locale/<language>/LC_MESSAGES/django.po`, and the compiled `django.mo` files are committed.

After changing any text, update and recompile the catalogs (requires GNU gettext):

```bash
python manage.py makemessages -a --ignore=venv --ignore=staticfiles
# translate the new empty msgstr entries in locale/*/LC_MESSAGES/django.po
python manage.py compilemessages -l en -l fr -l de -l ru -l zh_Hans -l es -l ja
```

To add a language, add it to `LANGUAGES` in `vinyls/settings.py` and run `makemessages -l <code>`. The `cleanup_vinyl` command output is not translated.

## Updating

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then restart uvicorn.

## Maintenance

Removes artists, labels and genres with no records, and unused covers. Without `--apply` it only simulates:

```bash
python manage.py cleanup_vinyl           # dry run
python manage.py cleanup_vinyl --apply   # performs the cleanup
```

## Backup

You need two things: the database (`db.sqlite3`, or a dump of the external database made with `pg_dump` or `mysqldump`) and the `media/` folder. The `.env` file contains the secret key: keep it safe and do not commit it to the repository.

## License

Released under the BSD 3-Clause license. See [LICENSE](LICENSE).
