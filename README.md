# CMPNG

[![codecov](https://codecov.io/github/arnecoomans/cmpng/graph/badge.svg?token=R7AA982PE5)](https://codecov.io/github/arnecoomans/cmpng)

Personal vacation planning app for managing camping locations and hotel stays across Europe. Browse locations by region, category, tag, and distance from home. Built with Django, self-hosted via Docker.

## Features

- Location database with geographic hierarchy (Country → Region → Department)
- Filter by category, tag, region, distance, and visit status
- Mark locations as visited or add to personal lists
- Map view with nearby suggestions
- Media gallery per location
- Multi-user with visibility controls (public / community / family / private)
- Tag and category taxonomy with parent/child grouping
- Docker-ready with Gunicorn + Nginx Proxy Manager

## Stack

- Python 3.12+, Django 6
- SQLite (development) / PostgreSQL (production)
- pytest + factory_boy (702 tests, 97% coverage)

## Getting Started

See [documentation/setup.md](documentation/setup.md) for local development and Docker deployment instructions.

## Documentation

| Document | Description |
|---|---|
| [Setup & Deployment](documentation/setup.md) | Local dev, Docker, Nginx Proxy Manager |
| [Deployment Guide](documentation/deployment.md) | Dev / acc / prod environments, PostgreSQL |
| [Architecture](documentation/locations/structure.md) | Service layer, managers, FilterMixin |
| [Models](documentation/locations/models.md) | Field reference for all models |
| [Services](documentation/locations/services.md) | Business logic layer |
| [Testing](documentation/locations/testing.md) | Test patterns and factory usage |

## License

MIT — see [LICENSE](LICENSE).
