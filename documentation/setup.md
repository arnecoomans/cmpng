# Setup Guide

## Database Strategy

| Environment | Database | Why |
|---|---|---|
| **Development** | SQLite | Zero config, file-based, sufficient for one developer |
| **Acceptance** | PostgreSQL | Matches production; catches SQL compatibility issues early |
| **Production** | PostgreSQL | Concurrent writes, reliability, proper locking |

SQLite works fine for local development but should never be used in acceptance or
production. Django's `DATABASE_URL` setting (via `django-environ`) makes switching
databases a one-line change in `.env`.

To use PostgreSQL, add `psycopg[binary]` to `requirements.txt`:

```
psycopg[binary] >= 3.2
```

See [Deployment Guide](deployment.md) for the full PostgreSQL setup.

---

## Local Development

### Requirements

- Python 3.12+
- SQLite (default, no install needed)

### Steps

```bash
# Clone and enter the project
git clone <repo> cmpng
cd cmpng

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (see Environment Variables below)
cp .env.example .env

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Run Tests

```bash
pytest                                        # all tests
pytest locations/tests/ -v                   # locations app only
pytest --cov=locations --cov-report=html     # with coverage report
```

---

## Docker Deployment (Production)

The recommended production setup runs CMPNG in a Docker container behind
[Nginx Proxy Manager](https://nginxproxymanager.com/). Gunicorn serves the
Django application; static and media files are served directly by the proxy.

### Directory Layout on the Host

```
/data/docker/cmpng/
├── .env                  # Environment variables (secrets, API keys)
├── db.sqlite3            # SQLite database (persisted via volume)
├── staticfiles/          # Collected static files (populated on first run)
├── mediafiles/           # User-uploaded media
└── logs/                 # Gunicorn + geocoding logs
```

Create these directories before starting the container:

```bash
sudo mkdir -p /data/docker/cmpng/{staticfiles,mediafiles,logs}
sudo chown -R 1000:1000 /data/docker/cmpng   # match the UID inside the container
```

### compose.yml

```yaml
services:
  cmpng:
    image: cmpng:latest        # build locally — see Dockerfile section below
    restart: unless-stopped
    env_file:
      - /data/docker/cmpng/.env
    volumes:
      - /data/docker/cmpng/db.sqlite3:/app/db.sqlite3
      - /data/docker/cmpng/staticfiles:/app/staticfiles
      - /data/docker/cmpng/mediafiles:/app/mediafiles
      - /data/docker/cmpng/logs:/var/log/cmpng
    expose:
      - "8000"
    networks:
      - proxy

networks:
  proxy:
    external: true             # shared network used by Nginx Proxy Manager
```

> The `proxy` network must already exist. Create it once on the host:
> ```bash
> docker network create proxy
> ```
> Nginx Proxy Manager must be on the same network.

### Dockerfile

Place this file in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# System dependencies (Pillow, pillow-heif need libheif)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libheif-dev \
    libffi-dev \
  && rm -rf /var/lib/apt/lists/*

# Create log directory
RUN mkdir -p /var/log/cmpng

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files (needs a dummy SECRET_KEY)
RUN SECRET_KEY=build GOOGLE_API_KEY=none python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "cmpng.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "/var/log/cmpng/access.log", \
     "--error-logfile", "/var/log/cmpng/error.log"]
```

### Environment Variables (`.env`)

```dotenv
# Django
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=cmpng.yourdomain.com

# Database
# SQLite (simple, acceptable for low-traffic production):
DATABASE_URL=sqlite:////app/db.sqlite3
# PostgreSQL (recommended for acc/prod — see deployment.md):
# DATABASE_URL=postgres://cmpng:password@db/cmpng

# Google APIs
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Location settings
DEPARTURE_CENTER=Geldermalsen, Gelderland, Netherlands

# Email
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### fixture_users.json

User credentials (password hashes and emails) are kept out of version control in
`locations/fixtures/fixture_users.json` — alongside the other fixture files but
excluded via `.gitignore`. Create it on the server before running `load_fixtures`.

```json
{
  "arnecoomans":  { "email": "arne@example.com",   "password_hash": "pbkdf2_sha256$..." },
  "ingecoomans":  { "email": "inge@example.com",   "password_hash": "pbkdf2_sha256$..." },
  "sandracoomans":{ "email": "sandra@example.com", "password_hash": "pbkdf2_sha256$..." },
  "morice":       { "email": "morice@example.com", "password_hash": "pbkdf2_sha256$..." }
}
```

Keys must match the `username` values hard-coded in `create_fixture_users.py`.
Any user without a matching entry is created with an unusable password.

**Generating a password hash:**

```bash
python manage.py shell -c "
from django.contrib.auth.hashers import make_password
print(make_password('your-password-here'))
"
```

Paste the printed `pbkdf2_sha256$...` string as the `password_hash` value.

### First Deploy

```bash
# Build the image
docker build -t cmpng:latest .

# Run migrations
docker run --rm --env-file /data/docker/cmpng/.env \
  -v /data/docker/cmpng/db.sqlite3:/app/db.sqlite3 \
  cmpng:latest python manage.py migrate

# Place fixture_users.json on the host (see above), then load all fixtures
# (creates users, loads data, applies summaries, calculates distances)
docker run --rm --env-file /data/docker/cmpng/.env \
  -v /data/docker/cmpng/db.sqlite3:/app/db.sqlite3 \
  -v /data/docker/cmpng/fixture_users.json:/app/locations/fixtures/fixture_users.json:ro \
  cmpng:latest python manage.py load_fixtures

# Start the container
docker compose -f /data/docker/cmpng/compose.yml up -d
```

### Subsequent Deploys

```bash
# Rebuild the image after a code change
docker build -t cmpng:latest /path/to/source

# Run migrations (if any)
docker compose -f /data/docker/cmpng/compose.yml run --rm cmpng \
  python manage.py migrate

# Restart the container
docker compose -f /data/docker/cmpng/compose.yml up -d --force-recreate
```

### Nginx Proxy Manager Configuration

1. Add a **Proxy Host** in the NPM UI.
2. Set the forward hostname to `cmpng` (the compose service name) and port `8000`.
3. Enable SSL via Let's Encrypt.
4. Under **Advanced**, add the following custom Nginx config to serve static and
   media files directly from the mounted host directories:

```nginx
location /static/ {
    alias /data/docker/cmpng/staticfiles/;
    expires 30d;
    access_log off;
}

location /media/ {
    alias /data/docker/cmpng/mediafiles/;
    expires 7d;
    access_log off;
}
```

> Static files are served by Nginx rather than Django/Gunicorn, which is faster
> and avoids unnecessary Python overhead for every asset request.

### Logs

| File | Contents |
|---|---|
| `/data/docker/cmpng/logs/access.log` | Gunicorn HTTP access log |
| `/data/docker/cmpng/logs/error.log` | Gunicorn error log |
| `/data/docker/cmpng/logs/geocoding.log` | Google API calls (see `LOGGING` in `settings.py`) |

Tail logs live:

```bash
tail -f /data/docker/cmpng/logs/geocoding.log
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | Yes | `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `DATABASE_URL` | Yes | `sqlite:////app/db.sqlite3` or `postgres://user:pass@host/db` |
| `GOOGLE_API_KEY` | Yes | Used for geocoding and Places API |
| `GOOGLE_MAPS_API_KEY` | Yes | Used for embedded maps |
| `DEPARTURE_CENTER` | No | Home location for distance calculations |
| `DEFAULT_FROM_EMAIL` | No | Sender address for outgoing email |
