# Infrastructure — Mastery Engine

> Docker, Nginx, PostgreSQL, Redis, and monitoring configuration.

## Structure

```
infrastructure/
├── docker/
│   ├── backend.Dockerfile     # Multi-stage Python 3.13 build
│   └── frontend.Dockerfile    # Multi-stage Node 20 build
├── nginx/
│   └── nginx.conf             # Reverse proxy: /api → backend, / → frontend
├── postgres/
│   └── init/
│       └── 01-create-schemas.sql  # Creates 10 bounded context schemas
├── redis/
│   └── redis.conf             # Redis configuration (LRU, persistence)
└── monitoring/
    ├── prometheus/
    │   └── prometheus.yml      # Scrape configs for all services
    └── grafana/
        └── provisioning/
            ├── datasources/    # Prometheus datasource
            └── dashboards/     # Dashboard provider config
```

## Services

| Service | Port | Purpose |
|---|---|---|
| Backend (FastAPI) | 8000 | API server |
| Frontend (Next.js) | 3000 | Web application |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache + rate limiting |
| Nginx | 80 | Reverse proxy |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Dashboards (admin/admin) |

## Usage

All services are managed via Docker Compose from the repository root:

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f backend

# Stop everything
docker compose down

# Stop and remove volumes (destructive)
docker compose down -v
```

## Database Initialization

On first start, PostgreSQL runs `postgres/init/01-create-schemas.sql`, which creates the 10 bounded context schemas (identity, content, learning, assessment, mastery, scheduling, analytics, billing, administration, infrastructure) per Task 004.

## Monitoring

- **Prometheus** is available at `http://localhost:9090`.
- **Grafana** is available at `http://localhost:3001` (admin/admin).
- Dashboards are auto-provisioned from `monitoring/grafana/provisioning/`.
