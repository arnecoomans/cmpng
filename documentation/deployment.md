# Deployment Guide

## Environments

| Environment | Purpose | Database | Debug | Domain |
|---|---|---|---|---|
| **Development** | Local coding & tests | SQLite | `True` | `localhost:8000` |
| **Acceptance** | Staging / QA | PostgreSQL | `False` | `acc.cmpng.yourdomain.com` |
| **Production** | Live site | PostgreSQL | `False` | `cmpng.yourdomain.com` |

The Docker setup is described in [setup.md](setup.md). This document covers
everything that differs between environments, with a focus on the
SQLite → PostgreSQL transition for acceptance and production.

---

## Database

### Development — SQLite

No configuration needed. The default `DATABASE_URL` in `.env` points to a local
file:

```dotenv
DATABASE_URL=sqlite:///db.sqlite3
```

### Acceptance & Production — PostgreSQL

**1. Add the driver to `requirements.txt`:**

```
psycopg[binary] >= 3.2
```

**2. Add a `db` service to `compose.yml`:**

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: cmpng
      POSTGRES_USER: cmpng
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - /data/docker/cmpng/postgres:/var/lib/postgresql/data
    networks:
      - proxy

  cmpng:
    image: cmpng:latest
    restart: unless-stopped
    depends_on:
      - db
    env_file:
      - /data/docker/cmpng/.env
    volumes:
      - /data/docker/cmpng/staticfiles:/app/staticfiles
      - /data/docker/cmpng/mediafiles:/app/mediafiles
      - /data/docker/cmpng/logs:/var/log/cmpng
    expose:
      - "8000"
    networks:
      - proxy

networks:
  proxy:
    external: true
```

> Note: the `db.sqlite3` volume mount is removed; PostgreSQL takes its place.
> The `postgres` directory is created automatically by Docker.

**3. Update `.env`:**

```dotenv
# Database
DATABASE_URL=postgres://cmpng:${DB_PASSWORD}@db/cmpng
DB_PASSWORD=choose-a-strong-password
```

**4. Create the host directory for PostgreSQL data:**

```bash
sudo mkdir -p /data/docker/cmpng/postgres
sudo chown -R 999:999 /data/docker/cmpng/postgres   # postgres user inside container
```

---

## Environment Variables per Environment

### `.env.development`

```dotenv
SECRET_KEY=dev-secret-not-used-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=sqlite:///db.sqlite3

GOOGLE_API_KEY=your-dev-api-key
GOOGLE_MAPS_API_KEY=your-dev-maps-key

DEPARTURE_CENTER=Geldermalsen, Gelderland, Netherlands
DEFAULT_FROM_EMAIL=dev@localhost
```

### `.env.acceptance`

```dotenv
SECRET_KEY=generate-with-get_random_secret_key
DEBUG=False
ALLOWED_HOSTS=acc.cmpng.yourdomain.com

DATABASE_URL=postgres://cmpng:password@db/cmpng
DB_PASSWORD=strong-password-here

GOOGLE_API_KEY=your-api-key
GOOGLE_MAPS_API_KEY=your-maps-key

DEPARTURE_CENTER=Geldermalsen, Gelderland, Netherlands
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### `.env.production`

```dotenv
SECRET_KEY=different-secret-from-acceptance
DEBUG=False
ALLOWED_HOSTS=cmpng.yourdomain.com

DATABASE_URL=postgres://cmpng:password@db/cmpng
DB_PASSWORD=different-strong-password

GOOGLE_API_KEY=your-api-key
GOOGLE_MAPS_API_KEY=your-maps-key

DEPARTURE_CENTER=Geldermalsen, Gelderland, Netherlands
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

> Keep `.env.*` files out of version control. Add them all to `.gitignore`.

---

## CLI vs Portainer

Portainer can manage running containers and stacks but **cannot build images**
from a local Dockerfile. The table below shows what belongs where.

| Task | Where |
|---|---|
| Create host directories, set permissions | **CLI** |
| `docker build` | **CLI** — Portainer cannot build from source |
| `python manage.py migrate` | **CLI** (or Portainer exec console) |
| `python manage.py createsuperuser` | **CLI** — interactive, needs a real TTY |
| `python manage.py dumpdata / loaddata` | **CLI** |
| Deploy / start a stack | **Portainer** → Stacks → Add stack |
| Restart or redeploy a container | **Portainer** → container → Restart / Redeploy |
| Update environment variables | **Portainer** → stack editor, then redeploy |
| View live logs | **Portainer** → container → Logs |
| Open a shell in a running container | **Portainer** → container → Exec console |

### Using Portainer Stacks

Instead of referencing `compose.yml` via `-f` on the CLI, you can paste the
contents directly into Portainer's stack editor. Portainer will manage the
stack from that point on.

1. Portainer → **Stacks** → **Add stack**
2. Name it `cmpng`
3. Paste the contents of `compose.yml`
4. Under **Environment variables**, add all variables from `.env` (or upload the
   file using the **Load variables from .env file** button)
5. Click **Deploy the stack**

After deployment, Portainer's **Redeploy** button is equivalent to
`docker compose up -d --force-recreate`.

---

## First Deploy Checklist

### Step 1 — CLI: prepare the host

```bash
# Create host directories
sudo mkdir -p /data/docker/cmpng/{staticfiles,mediafiles,logs,postgres}
sudo chown -R 1000:1000 /data/docker/cmpng/{staticfiles,mediafiles,logs}
sudo chown -R 999:999 /data/docker/cmpng/postgres

# Place .env file
sudo cp .env.production /data/docker/cmpng/.env
```

### Step 2 — CLI: build the image

```bash
# Run from the project source directory
docker build -t cmpng:latest .
```

### Step 3 — Portainer: deploy the stack

1. Portainer → Stacks → Add stack → paste `compose.yml`
2. Load variables from `/data/docker/cmpng/.env`
3. Deploy the stack — this starts both `db` and `cmpng`

### Step 4 — CLI: run first-time Django setup

```bash
# Migrations
docker compose -f /data/docker/cmpng/compose.yml run --rm cmpng \
  python manage.py migrate

# Create superuser (interactive — needs CLI, not Portainer exec)
docker compose -f /data/docker/cmpng/compose.yml run --rm cmpng \
  python manage.py createsuperuser
```

---

## Update / Redeploy Checklist

### Step 1 — CLI: rebuild the image

```bash
git pull
docker build -t cmpng:latest .
```

### Step 2 — CLI: run migrations (if any)

```bash
docker compose -f /data/docker/cmpng/compose.yml run --rm cmpng \
  python manage.py migrate
```

### Step 3 — Portainer: redeploy

Portainer → Stacks → `cmpng` → **Redeploy**

This is equivalent to `docker compose up -d --no-deps --force-recreate cmpng`.
The `db` container is unaffected.

---

## Database Backups

### PostgreSQL

```bash
# Dump
docker compose -f /data/docker/cmpng/compose.yml exec db \
  pg_dump -U cmpng cmpng > /data/docker/cmpng/backup-$(date +%F).sql

# Restore
docker compose -f /data/docker/cmpng/compose.yml exec -T db \
  psql -U cmpng cmpng < /data/docker/cmpng/backup-2026-01-01.sql
```

### SQLite (development / simple production)

```bash
cp /data/docker/cmpng/db.sqlite3 /data/docker/cmpng/db.sqlite3.bak
```

---

## Migrating from SQLite to PostgreSQL

If you started with SQLite and want to switch to PostgreSQL:

```bash
# 1. Export data from SQLite
docker run --rm --env-file /data/docker/cmpng/.env.sqlite \
  -v /data/docker/cmpng/db.sqlite3:/app/db.sqlite3 \
  cmpng:latest python manage.py dumpdata \
    --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.Permission \
    > /data/docker/cmpng/data.json

# 2. Switch DATABASE_URL in .env to PostgreSQL
# 3. Start the db service, run migrate
# 4. Load the exported data
docker compose -f /data/docker/cmpng/compose.yml run --rm cmpng \
  python manage.py loaddata /app/data.json
```

> `contenttypes` and `auth.Permission` are excluded because Django recreates
> them automatically during `migrate` and importing them causes conflicts.
